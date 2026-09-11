"""Flask admin panel application for nonogram puzzle management."""

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, send_file
from datetime import datetime
import json
import os
import tempfile
import uuid
from pathlib import Path
from io import BytesIO

from .batch_generator import get_batch_generator, BatchStatus, BatchGenerator
from .puzzle_review import get_puzzle_review_service, PuzzleFilter, PuzzleReviewService
from .book_manager import get_book_manager, BookStatus
from .pdf_generator import get_pdf_generator
from .image_manager import CANNOT_FIT, MOVED_TO_LARGE, SIZE_PRESETS, get_image_manager
from .grid_renderer import grid_to_svg
from .print_specs import PrintSpecValidator
from .book_pdf_generator import BookPDFGenerator

# Import the professional export PDF module
from nonogram.export.pdf import render_pages
from nonogram.export import ExportPayload
from nonogram import clues, orchestrator
from nonogram.errors import GenerationAbandoned, NonogramError
from nonogram.limits import MAX_SIZE, MIN_SIZE

# CARD-050: real image-mode quality/recognizability, in place of the
# density-only heuristic and hardcoded "medium" this replaces below.
from PIL import Image as PILImage
from nonogram.analysis.quality_metric import measure_quality


def _generate_image_puzzle(image, width, height):
    """Generate ``image`` at ``(width, height)``; if that extent is abandoned
    (not uniquely solvable within the pixel-nudge bound), retry at the
    long-side ±1 neighbours from ``image.neighbour_extents`` (CARD-062).

    Generation is deterministic per picture and extent, so no extent is tried
    twice. On the predicted extent any other error propagates at once: a
    different extent cannot fix an unreadable picture. On a neighbour, any
    other ``NonogramError`` (e.g. a solver timeout) ends the retry and the
    predicted extent's abandonment is what gets reported — that is the
    picture's real problem, not the neighbour's side effect.

    Returns:
        ``(puzzle, extent_used)``.

    Raises:
        GenerationAbandoned: the predicted extent's own error, when it and
            every neighbour were abandoned.
    """
    first_abandonment = None
    for extent in [(width, height), *image.neighbour_extents((width, height))]:
        request = orchestrator.GenerationRequest(
            mode="image",
            image=Path(image.file_path),
            image_filename=image.original_filename,
            width=extent[0],
            height=extent[1],
        )
        try:
            return orchestrator.generate(request), extent
        except GenerationAbandoned as error:
            if first_abandonment is None:
                first_abandonment = error
        except NonogramError:
            if first_abandonment is None:
                raise
            break
    raise first_abandonment


def create_app(debug=None):
    """Create and configure the Flask admin panel app."""
    app = Flask(__name__, template_folder="templates")

    # Configuration from environment
    if debug is None:
        debug = os.getenv("FLASK_ENV") == "development"

    app.config["DEBUG"] = debug
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    app.config["ENV"] = os.getenv("FLASK_ENV", "production" if not debug else "development")
    app.config["SESSION_COOKIE_SECURE"] = False  # Allow localhost
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Chrome compatibility

    # Resolve the DB session factory fresh on every create_app() call rather
    # than once at module-import time. DATABASE_URL can differ per call (the
    # test suite relies on this to toggle DB-backed vs. in-memory mode via
    # monkeypatch), and a module-level check would freeze whatever value was
    # in the environment the first time this module happened to be imported.
    session_scope = None
    if os.getenv('DATABASE_URL'):
        try:
            from nonogram.db import session_scope as db_session_scope
            session_scope = db_session_scope
        except Exception:
            # Database not configured; will use in-memory mode
            session_scope = None

    # Add CORS and security headers for Chrome compatibility
    @app.after_request
    def add_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    # Custom Jinja2 filter for first N characters (avoids slice filter issues)
    app.jinja_env.filters['first_n'] = lambda s, n: str(s)[:n] if s else ''

    # The supported grid range, for form bounds and labels (CARD-063).
    app.jinja_env.globals.update(MIN_SIZE=MIN_SIZE, MAX_SIZE=MAX_SIZE)

    # Construct service instances
    # If DATABASE_URL is set, use DB-backed persistence; otherwise use in-memory mode
    if session_scope:
        puzzle_review = PuzzleReviewService(session_factory=session_scope)
        batch_gen = BatchGenerator(puzzle_review_service=puzzle_review, session_factory=session_scope)
        book_mgr = get_book_manager(session_factory=session_scope)
        app.logger.info("Database persistence enabled (DATABASE_URL set)")
    else:
        puzzle_review = PuzzleReviewService(session_factory=None)
        batch_gen = BatchGenerator(puzzle_review_service=puzzle_review, session_factory=None)
        book_mgr = get_book_manager()
        app.logger.info("Running in in-memory mode (DATABASE_URL not set)")

    # Exposed on the app object (rather than left as route closures only) so
    # tests and management scripts can introspect which mode was actually
    # constructed, instead of only being reachable indirectly through a route.
    app.puzzle_review_service = puzzle_review
    app.batch_generator = batch_gen
    app.book_manager = book_mgr

    @app.route("/")
    def dashboard():
        """Admin dashboard overview."""
        batch_stats = {
            "total_batches": len(batch_gen.jobs),
            "pending": sum(
                1 for j in batch_gen.jobs.values() if j.status == BatchStatus.PENDING
            ),
            "generating": sum(
                1 for j in batch_gen.jobs.values()
                if j.status == BatchStatus.GENERATING
            ),
            "complete": sum(
                1 for j in batch_gen.jobs.values() if j.status == BatchStatus.COMPLETE
            ),
        }

        puzzle_stats = puzzle_review.get_stats()
        book_stats = {
            "total_books": len(book_mgr.books),
            "draft": len(book_mgr.get_books_by_status(BookStatus.DRAFT.value)),
            "ready_for_pdf": len(
                book_mgr.get_books_by_status(BookStatus.READY_FOR_PDF.value)
            ),
            "published": len(
                book_mgr.get_books_by_status(BookStatus.PUBLISHED.value)
            ),
        }

        return render_template(
            "dashboard.html",
            batch_stats=batch_stats,
            puzzle_stats=puzzle_stats,
            book_stats=book_stats,
        )

    @app.route("/batch/create", methods=["GET", "POST"])
    def create_batch():
        """Create a new batch generation job."""
        if request.method == "POST":
            try:
                count = int(request.form.get("count", 100))
                sizes = [int(s) for s in request.form.get("sizes", "20").split(",")]
                theme = request.form.get("theme", "christmas")
                source = request.form.get("source", "random")
                quality_filter = int(request.form.get("quality_filter", 0))

                batch_id = batch_gen.create_batch(
                    count=count,
                    sizes=sizes,
                    theme=theme,
                    source=source,
                    quality_filter=quality_filter,
                )

                flash(f"Batch created: {batch_id}", "success")
                return redirect(url_for("batch_status", batch_id=batch_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        return render_template("batch_create.html")

    @app.route("/batch/from-images", methods=["POST"])
    def batch_from_images():
        """Handle image uploads from both individual files and directories."""
        try:
            # Get uploaded files from both sources
            individual_files = request.files.getlist("image_files") or []
            directory_files = request.files.getlist("directory") or []
            all_files = individual_files + directory_files
            quality_filter = int(request.form.get("quality_filter", 0))

            # Clear previous batch
            image_mgr = get_image_manager()
            image_mgr.clear_all()

            if not all_files or not any(f.filename for f in all_files):
                flash("No images selected", "error")
                return redirect(url_for("batch_select_images"))

            # Valid image extensions
            valid_extensions = {'.png', '.jpg', '.jpeg', '.gif'}

            # Process uploaded files
            processed_count = 0
            for file in all_files:
                if file and file.filename:
                    # Skip directories and invalid file types
                    file_ext = Path(file.filename).suffix.lower()
                    if not file_ext or file_ext not in valid_extensions:
                        continue

                    try:
                        # Save to persistent uploads directory (not system temp)
                        uploads_dir = Path(tempfile.gettempdir()) / "nonogram_uploads"
                        uploads_dir.mkdir(exist_ok=True)

                        # Extract just the filename (remove any directory path from directory uploads)
                        # When uploading a directory, file.filename includes the path like "birds/raven1.jpg"
                        # We want just "raven1.jpg" to avoid creating nested directories
                        just_filename = Path(file.filename).name
                        safe_filename = just_filename.replace(" ", "_")
                        temp_path = uploads_dir / f"{uuid.uuid4().hex}_{safe_filename}"
                        file.save(str(temp_path))

                        # Add to image manager
                        image = image_mgr.add_image(str(temp_path), file.filename)
                        if image:
                            processed_count += 1
                        else:
                            flash(f"Could not process {file.filename}", "warning")

                    except Exception as e:
                        flash(f"Error processing {file.filename}: {str(e)}", "warning")

            if processed_count == 0:
                flash("No valid images to process", "error")
                return redirect(url_for("batch_select_images"))

            # Read default size from page 1 selection and apply to all images
            default_size = request.form.get("default_size", "medium")
            size_mapping = SIZE_PRESETS

            if default_size in size_mapping:
                size_value, size_mode = size_mapping[default_size]
                # Apply to all loaded images
                for image in image_mgr.get_all_images():
                    if size_mode == "max":
                        image_mgr.update_image_size(image.file_id, "max", 0)
                    else:
                        image_mgr.update_image_size(image.file_id, size_mode, size_value)

            # Store quality filter and default size in session
            session["batch_quality_filter"] = quality_filter
            session["batch_default_size"] = default_size

            flash(f"Loaded {processed_count} image(s) from selected files/folder(s)", "success")
            return redirect(url_for("preview_batch_images"))

        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for("batch_select_images"))

    @app.route("/batch/select-images", methods=["GET", "POST"])
    def batch_select_images():
        """Select images for batch generation (Wave 3 workflow)."""
        return render_template("batch_create.html")

    @app.route("/batch/preview-images", methods=["GET", "POST"])
    def preview_batch_images():
        """Preview and configure sizes for selected images."""
        image_mgr = get_image_manager()
        images = image_mgr.get_all_images()

        if not images:
            flash("No images loaded. Please upload images first.", "error")
            return redirect(url_for("batch_select_images"))

        if request.method == "POST":
            try:
                # Validate image count before processing
                if len(images) < 1 or len(images) > 200:
                    flash(f"❌ Invalid image count: {len(images)}. Must be 1-200 images.", "error")
                    return render_template(
                        "image_preview.html",
                        images=images,
                        total_size_mb=image_mgr.get_total_size_mb(),
                    )

                # Update configuration for each image
                for image in images:
                    file_id = image.file_id
                    mode = request.form.get(f"mode_{file_id}", "fixed")
                    value = int(request.form.get(f"value_{file_id}", 20))
                    name = request.form.get(f"name_{file_id}", image.puzzle_name)

                    # Update image configuration
                    image_mgr.update_image_size(file_id, mode, value)
                    image_mgr.update_image_name(file_id, name)

                flash("Configuration saved", "success")
                return redirect(url_for("generate_batch_puzzles"))  # GET to show confirmation

            except ValueError as e:
                flash(f"Configuration error: {str(e)}", "error")
                return render_template(
                    "image_preview.html",
                    images=images,
                    total_size_mb=image_mgr.get_total_size_mb(),
                )

        # Get stats for display
        total_size_mb = image_mgr.get_total_size_mb()

        return render_template(
            "image_preview.html",
            images=images,
            total_size_mb=total_size_mb,
        )

    @app.route("/batch/generate-puzzles", methods=["GET", "POST"])
    def generate_batch_puzzles():
        """Generate puzzles from configured images (actual E2E conversion)."""
        image_mgr = get_image_manager()
        images = image_mgr.get_all_images()

        if not images:
            flash("No images to process", "error")
            return redirect(url_for("batch_select_images"))

        # GET: Show confirmation page
        if request.method == "GET":
            return render_template(
                "generate_batch.html",
                images=images,
            )

        # POST: Actually generate puzzles
        try:
            # Extract configured sizes from images (unique values)
            sizes = list(set(img.size_value if img.size_mode in ("fixed", "short") else 20 for img in images))

            # Create batch job
            batch_id = batch_gen.create_batch(
                count=len(images),
                sizes=sorted(sizes),
                theme="image",
                source="images",  # Use "images" not "image"
                quality_filter=session.get("batch_quality_filter", 0),
            )

            # Process each image and generate puzzles
            # Use the DB-backed puzzle_review service created in create_app(), not the legacy one
            quality_filter = session.get("batch_quality_filter", 0)
            generated_count = 0
            errors = []
            adjustments = []
            skipped = []
            moved = []

            for image in images:
                try:
                    # CARD-064: a picture even Large would cut below
                    # MIN_KEPT_SHARE is never generated; it is reported.
                    fit = image.size_fit()
                    if fit.status == CANNOT_FIT:
                        skipped.append(
                            f"{image.original_filename} skipped: too elongated for any "
                            f"supported size (even Large keeps only {fit.kept:.0%})"
                        )
                        continue
                    width, height = fit.extent

                    # Convert image to puzzle through the canonical,
                    # solver-verified pipeline (CARD-049) — the same
                    # judge_candidate uniqueness check and bounded pixel-nudge
                    # recovery `nonogram generate --mode image` runs, instead
                    # of a grid nothing ever solver-checks. One call per
                    # extent tried: orchestrator.generate_batch() has no
                    # per-item image-path parameter.
                    puzzle, used = _generate_image_puzzle(image, width, height)

                    # CARD-050 (AC-1): a real measurement against the source
                    # picture this puzzle was converted from, replacing the
                    # output-grid-density-only heuristic and the hardcoded
                    # "medium" recognizability that used to live here (and
                    # still live in image_to_puzzle.create_puzzle_from_image,
                    # which is preview-only in this pipeline — see CARD-049).
                    # Puzzle.grid is already the ADR-0012 boundary type
                    # (list[list[bool]]) measure_quality expects; the source
                    # image is re-opened from the same file path the
                    # GenerationRequest above was given.
                    original_image = PILImage.open(image.file_path)
                    quality_metrics = measure_quality(original_image, puzzle.grid)
                    quality_score = quality_metrics.quality_score
                    recognizability = quality_metrics.recognizability.value

                    # Check quality filter
                    if quality_score < quality_filter:
                        continue

                    # Store puzzle — difficulty_score/difficulty_tier come
                    # from nonogram.difficulty.score_difficulty via the real
                    # SolverSignals orchestrator.generate() computed, not from
                    # grid size alone (AC-3).
                    puzzle_id = puzzle_review.add_puzzle(
                        grid=puzzle.grid,
                        clues_rows=puzzle.clues.rows,
                        clues_cols=puzzle.clues.columns,
                        width=puzzle.width,
                        height=puzzle.height,
                        theme="image",
                        difficulty_score=puzzle.difficulty_score,
                        difficulty_tier=puzzle.difficulty_tier,
                        quality_score=quality_score,
                        recognizability=recognizability,
                        strategies_used=[],
                        batch_id=batch_id,
                        source_image=image.original_filename,
                    )

                    generated_count += 1
                    if fit.status == MOVED_TO_LARGE:
                        # CARD-064 (G-2): the chosen size was not used — say
                        # so in the results too, not only in the preview.
                        reason = (
                            f"the chosen size {fit.chosen[0]}x{fit.chosen[1]} would "
                            f"cut it (keeps {fit.chosen_kept:.0%})"
                            if fit.chosen is not None
                            else "the chosen size can't keep its shape"
                        )
                        moved.append(f"{image.original_filename}: moved up to Large — {reason}")
                    if used != (width, height):
                        note = (
                            f"{image.original_filename}: generated at "
                            f"{used[0]}x{used[1]} — {width}x{height} had no "
                            f"unique solution"
                        )
                        # A ±1 retry (CARD-062) can land under MIN_KEPT_SHARE;
                        # it is kept, but never silently.
                        if not image.keeps_enough(used):
                            note += f"; it keeps {image.kept_share(used):.0%} of the picture"
                        adjustments.append(note)

                except NonogramError as e:
                    # E.g. GenerationAbandoned: the conversion (and every
                    # bounded pixel-nudge attempt) never came out uniquely
                    # solvable, at the predicted extent or either long-side
                    # neighbour (CARD-062). Record it and keep processing the rest of the
                    # batch (AC-2) instead of failing the whole request.
                    errors.append(f"Error processing {image.original_filename}: {str(e)}")
                except Exception as e:
                    errors.append(f"Error processing {image.original_filename}: {str(e)}")

            # Update batch with final puzzle count
            batch_gen._update_batch_status(batch_id, puzzle_count=generated_count)

            # Show results
            if generated_count > 0:
                flash(f"✅ Generated {generated_count} puzzle(s) from {len(images)} image(s)", "success")
            else:
                flash("No valid puzzles generated", "warning")

            for note in moved[:3]:
                flash(note, "info")
            if len(moved) > 3:
                flash(f"... and {len(moved) - 3} more pictures moved up to Large", "info")

            for adjustment in adjustments[:3]:
                flash(adjustment, "info")
            if len(adjustments) > 3:
                flash(f"... and {len(adjustments) - 3} more size adjustments", "info")

            for note in skipped[:3]:
                flash(note, "info")
            if len(skipped) > 3:
                flash(f"... and {len(skipped) - 3} more skipped pictures", "info")

            if errors:
                for error in errors[:3]:  # Show first 3 errors
                    flash(error, "info")
                if len(errors) > 3:
                    flash(f"... and {len(errors) - 3} more errors", "info")

            # Clear session and image manager
            session.pop("batch_quality_filter", None)
            session.pop("batch_default_size", None)
            image_mgr.clear_all()  # Clear images so next workflow starts fresh

            return redirect(url_for("generated_puzzles", batch_id=batch_id))

        except ValueError as e:
            # Handle validation errors with helpful message
            error_msg = str(e)
            if "must be" in error_msg.lower():
                flash(f"❌ {error_msg}", "error")
            else:
                flash(f"❌ Generation failed: {error_msg}", "error")
            return render_template(
                "generate_batch.html",
                images=images,
            )
        except Exception as e:
            flash(f"❌ Unexpected error: {str(e)}", "error")
            return render_template(
                "generate_batch.html",
                images=images,
            )

    @app.route("/batch/<batch_id>/generated-puzzles")
    def generated_puzzles(batch_id):
        """Display generated puzzles with SVG grids."""
        # Get puzzles for this batch using batch_generator
        puzzles = batch_gen.get_batch_puzzles(batch_id, offset=0, limit=100)

        if not puzzles:
            flash("No puzzles generated for this batch", "warning")
            return redirect(url_for("batch_status", batch_id=batch_id))

        # Get batch job info for total image count
        batch_job = batch_gen.get_batch_status(batch_id)
        total_images = batch_job.total_count if batch_job else len(puzzles)
        filtered_count = total_images - len(puzzles) if batch_job else 0

        return render_template(
            "generated_puzzles.html",
            batch_id=batch_id,
            puzzles=puzzles,
            total_images=total_images,
            filtered_count=filtered_count,
        )

    @app.route("/batch/<batch_id>")
    def batch_status(batch_id):
        """View batch status and puzzles."""
        job = batch_gen.get_batch_status(batch_id)
        if not job:
            flash("Batch not found", "error")
            return redirect(url_for("dashboard"))

        puzzles = batch_gen.get_batch_puzzles(batch_id, offset=0, limit=50)

        return render_template(
            "batch_status.html",
            batch_id=batch_id,
            job=job,
            puzzles=puzzles or [],
        )

    @app.route("/puzzles")
    def puzzles_list():
        """List and filter puzzles."""
        # Basic filters
        size = request.args.get("size", type=int)
        difficulty = request.args.get("difficulty")
        quality_min = request.args.get("quality_min", type=int)

        # New filters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        book_id = request.args.get("book_id")
        puzzle_name = request.args.get("puzzle_name")
        sort_by = request.args.get("sort_by", "batch_id,-size,quality")

        # Pagination
        limit = request.args.get("limit", 25, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Get available books for filter dropdown
        books = book_mgr.get_all_books()

        try:
            filter_opts = PuzzleFilter(
                size=(size, size) if size is not None else None,
                difficulty=difficulty,
                quality_min=quality_min,
                date_from=date_from,
                date_to=date_to,
                book_id=book_id,
                puzzle_name=puzzle_name,
                sort_by=sort_by,
                limit=limit,
                offset=offset,
            )
            result = puzzle_review.filter_puzzles(filter_opts)

            return render_template(
                "puzzles_list.html",
                puzzles=result.puzzles,
                total_count=result.total_count,
                offset=result.offset,
                limit=result.limit,
                has_more=result.has_more,
                books=books,
            )

        except ValueError as e:
            flash(f"Filter error: {str(e)}", "error")
            return render_template("puzzles_list.html", puzzles=[], error=str(e), books=books)

    @app.route("/puzzle/<puzzle_id>/approve", methods=["POST"])
    def approve_puzzle(puzzle_id):
        """Approve a puzzle."""
        batch_id = request.args.get("batch_id")
        if puzzle_review.approve_puzzle(puzzle_id):
            flash(f"Puzzle {puzzle_id} approved", "success")
        else:
            flash(f"Puzzle not found", "error")

        # Return to batch if batch_id provided, else global puzzles list
        if batch_id:
            return redirect(url_for("generated_puzzles", batch_id=batch_id))
        return redirect(url_for("puzzles_list"))

    @app.route("/puzzle/<puzzle_id>/reject", methods=["POST"])
    def reject_puzzle(puzzle_id):
        """Reject a puzzle."""
        batch_id = request.args.get("batch_id")
        if puzzle_review.reject_puzzle(puzzle_id):
            flash(f"Puzzle {puzzle_id} rejected", "success")
        else:
            flash(f"Puzzle not found", "error")

        # Return to batch if batch_id provided, else global puzzles list
        if batch_id:
            return redirect(url_for("generated_puzzles", batch_id=batch_id))
        return redirect(url_for("puzzles_list"))

    @app.route("/books")
    def books_list():
        """List all books."""
        books = book_mgr.get_all_books()
        return render_template("books_list.html", books=books)

    @app.route("/book/create", methods=["GET", "POST"])
    def create_book():
        """Create a new book."""
        if request.method == "POST":
            try:
                title = request.form.get("title")
                description = request.form.get("description")
                theme = request.form.get("theme", "christmas")
                target_audience = request.form.get("target_audience")

                book_id = book_mgr.create_book(
                    title=title,
                    description=description,
                    theme=theme,
                    target_audience=target_audience,
                )

                flash(f"Book created: {book_id}", "success")
                return redirect(url_for("setup_print", book_id=book_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        return render_template("book_create.html")

    @app.route("/book/<book_id>/setup-print", methods=["GET", "POST"])
    def setup_print(book_id):
        """Configure print specifications for a book (Step 1 of scaffolding)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if request.method == "POST":
            try:
                # Get form data
                unit = request.form.get("unit", "cm")
                width_input = request.form.get("width")
                height_input = request.form.get("height")

                session["unit_preference"] = unit  # Persist unit preference in session

                # Convert to cm if input was in inches
                if unit == "inches":
                    width_cm = PrintSpecValidator.inches_to_cm(width_input)
                    height_cm = PrintSpecValidator.inches_to_cm(height_input)
                else:
                    width_cm = width_input
                    height_cm = height_input

                # Validate and create spec
                spec, error = PrintSpecValidator.create_spec(
                    width_cm=width_cm,
                    height_cm=height_cm,
                )

                if error:
                    flash(f"Error: {error}", "error")
                else:
                    # Store in book metadata (for now, using the in-memory manager)
                    # In production, this would update the Book row in the database
                    book.metadata.size = f"{spec.trim_width_cm}×{spec.trim_height_cm} cm"
                    book.updated_at = datetime.utcnow()

                    flash(f"Print specs set: {spec.trim_width_cm} × {spec.trim_height_cm} cm", "success")
                    # Proceed to Step 2: Puzzle Selection
                    return redirect(url_for("select_puzzles_for_book", book_id=book_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        # Prepare default trim size
        default_width = "15.24"
        default_height = "22.86"
        unit_preference = session.get("unit_preference", "cm")

        # Convert defaults to inches if that's the preference
        if unit_preference == "inches":
            default_width = PrintSpecValidator.cm_to_inches(default_width)
            default_height = PrintSpecValidator.cm_to_inches(default_height)

        context = {
            "book": book,
            "default_width": default_width,
            "default_height": default_height,
            "unit_preference": unit_preference,
        }

        return render_template("book_setup_print.html", **context)

    @app.route("/book/<book_id>/select-puzzles", methods=["GET", "POST"])
    def select_puzzles_for_book(book_id):
        """Select and add puzzles to a book (Step 2 of scaffolding)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if request.method == "POST":
            # Get selected puzzle IDs from form
            selected_ids = request.form.getlist("puzzle_ids")

            if not selected_ids:
                flash("No puzzles selected. Please select at least one puzzle.", "info")
            else:
                try:
                    # Add puzzles to the book
                    if book_mgr.add_puzzles_to_book(book_id, selected_ids):
                        flash(f"Added {len(selected_ids)} puzzle(s) to book", "success")
                        # Proceed to Step 3: Puzzle Arrangement
                        return redirect(url_for("arrange_puzzles_in_book", book_id=book_id))
                    else:
                        flash("Book not found", "error")
                except ValueError as e:
                    flash(f"Error: {str(e)}", "error")

        # Get filter parameters from query string
        size = request.args.get("size", type=int)
        difficulty = request.args.get("difficulty")
        quality_min = request.args.get("quality_min", type=int)
        theme = request.args.get("theme")
        status = request.args.get("status", "approved")  # Default to approved only
        puzzle_name = request.args.get("puzzle_name")
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Build filter: exclude puzzles already in this book
        try:
            filter_opts = PuzzleFilter(
                size=(size, size) if size is not None else None,
                difficulty=difficulty,
                quality_min=quality_min,
                theme=theme,
                status=status,
                puzzle_name=puzzle_name,
                book_id="unassigned",  # Only show puzzles NOT in any book
                limit=limit,
                offset=offset,
            )
            result = puzzle_review.filter_puzzles(filter_opts)

            # Additional filter: exclude puzzles already in this book
            filtered_puzzles = [
                p for p in result.puzzles
                if p.get("book_id") is None
            ]

            context = {
                "book": book,
                "puzzles": filtered_puzzles,
                "total_count": len(filtered_puzzles),
                "has_more": result.has_more,
                "size": size,
                "difficulty": difficulty,
                "quality_min": quality_min,
                "theme": theme,
                "status": status,
                "puzzle_name": puzzle_name,
                "limit": limit,
                "offset": offset,
            }

            return render_template("book_select_puzzles.html", **context)

        except ValueError as e:
            flash(f"Filter error: {str(e)}", "error")
            return render_template(
                "book_select_puzzles.html",
                book=book,
                puzzles=[],
                total_count=0,
                has_more=False,
                error=str(e),
            )

    @app.route("/book/<book_id>/arrange-puzzles", methods=["GET", "POST"])
    def arrange_puzzles_in_book(book_id):
        """Arrange and name puzzles in a book (Step 3 of scaffolding)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        # Handle puzzle reordering and title updates via AJAX or form submission
        if request.method == "POST":
            action = request.form.get("action")

            try:
                if action == "move_up":
                    puzzle_id = request.form.get("puzzle_id")
                    book_mgr.move_puzzle_up(book_id, puzzle_id)
                    flash(f"Moved puzzle up", "success")

                elif action == "move_down":
                    puzzle_id = request.form.get("puzzle_id")
                    book_mgr.move_puzzle_down(book_id, puzzle_id)
                    flash(f"Moved puzzle down", "success")

                elif action == "set_title":
                    puzzle_id = request.form.get("puzzle_id")
                    title = request.form.get("title")
                    book_mgr.set_puzzle_title(book_id, puzzle_id, title)
                    flash(f"Updated puzzle title", "success")

                elif action == "delete":
                    puzzle_id = request.form.get("puzzle_id")
                    book_mgr.remove_puzzle_from_book(book_id, puzzle_id)
                    flash(f"Removed puzzle from book", "success")

                elif action == "finish":
                    # Proceed to Step 4: Finalization
                    return redirect(url_for("finalize_book", book_id=book_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        # Get puzzles in current order with titles
        puzzles_in_book = []
        for order_num, puzzle_id in enumerate(book.puzzle_ids, start=1):
            # Get puzzle details from puzzle_review service
            puzzle = puzzle_review.get_puzzle(puzzle_id)
            if puzzle:
                # Add custom title if set
                custom_title = book_mgr.get_puzzle_title(book_id, puzzle_id)
                puzzle["order"] = order_num
                puzzle["custom_title"] = custom_title
                puzzles_in_book.append(puzzle)

        # Calculate estimated page count
        # Rough estimate: assume each puzzle is ~1-2 pages based on height
        # Later refinement in Step 4 based on actual trim height
        page_count = max(1, len(puzzles_in_book))  # Minimum 1 page per puzzle

        context = {
            "book": book,
            "puzzles": puzzles_in_book,
            "page_count": page_count,
            "puzzle_count": len(puzzles_in_book),
        }

        return render_template("book_arrange_puzzles.html", **context)

    @app.route("/book/<book_id>/finalize", methods=["GET", "POST"])
    def finalize_book(book_id):
        """Finalize book with cover, guide, and download (Step 4 of scaffolding)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if request.method == "POST":
            action = request.form.get("action")

            try:
                if action == "clear_cover":
                    # Clear cover image (stored in session)
                    session.pop(f"book_{book_id}_cover_path", None)
                    flash("Cover image cleared", "success")

                elif action == "save_and_finish":
                    # Mark book as ready and return to books list
                    book_mgr.set_book_status(book_id, BookStatus.READY_FOR_PDF.value)
                    flash(f"Book saved: {book.metadata.title}", "success")
                    return redirect(url_for("books_list"))

                elif action == "download_pdf":
                    # Generate and download PDF
                    return generate_book_pdf_download(book, puzzle_review)

            except Exception as e:
                flash(f"Error: {str(e)}", "error")

        # Handle cover upload
        cover_image = None
        cover_path = session.get(f"book_{book_id}_cover_path")

        if "cover" in request.files:
            file = request.files["cover"]
            if file and file.filename:
                try:
                    from PIL import Image as PILImage
                    cover_image = PILImage.open(file.stream)
                    # Store filename in session (Pillow Image can't be serialized)
                    session[f"book_{book_id}_cover_path"] = file.filename
                    session[f"book_{book_id}_cover_data"] = True  # Flag it exists
                    flash("Cover image uploaded", "success")
                except Exception as e:
                    flash(f"Failed to load image: {str(e)}", "error")

        # Get puzzles in order
        puzzles_in_book = []
        for puzzle_id in book.puzzle_ids:
            puzzle = puzzle_review.get_puzzle(puzzle_id)
            if puzzle:
                custom_title = book_mgr.get_puzzle_title(book_id, puzzle_id)
                puzzle["custom_title"] = custom_title
                puzzles_in_book.append(puzzle)

        # Calculate difficulty breakdown
        easy_count = sum(1 for p in puzzles_in_book if p.get("difficulty_tier") == "Easy")
        medium_count = sum(1 for p in puzzles_in_book if p.get("difficulty_tier") == "Medium")
        hard_count = sum(1 for p in puzzles_in_book if p.get("difficulty_tier") == "Hard")

        context = {
            "book": book,
            "puzzles": puzzles_in_book,
            "puzzle_count": len(puzzles_in_book),
            "easy_count": easy_count,
            "medium_count": medium_count,
            "hard_count": hard_count,
            "page_count": max(1, len(puzzles_in_book) + 2),  # Cover + guide + puzzles
            "cover_uploaded": bool(session.get(f"book_{book_id}_cover_data")),
            "trim_width_cm": book.metadata.size.split("×")[0] if book.metadata.size else "15.24",
            "trim_height_cm": book.metadata.size.split("×")[1] if book.metadata.size and "×" in book.metadata.size else "22.86",
        }

        return render_template("book_finalize.html", **context)

    def generate_book_pdf_download(book, puzzle_review):
        """Generate PDF and return as download response."""
        from io import BytesIO
        from werkzeug.wsgi import wrap_file

        try:
            # Get puzzles
            puzzles = []
            app.logger.debug(
                "Book '%s' has %d puzzle IDs: %s",
                book.metadata.title, len(book.puzzle_ids), book.puzzle_ids,
            )

            for puzzle_id in book.puzzle_ids:
                puzzle = puzzle_review.get_puzzle(puzzle_id)
                if puzzle:
                    app.logger.debug("Retrieved puzzle %s", puzzle_id)
                    puzzles.append(puzzle)
                else:
                    app.logger.warning("Could not find puzzle %s for PDF generation", puzzle_id)

            app.logger.debug(
                "Total puzzles retrieved: %d/%d", len(puzzles), len(book.puzzle_ids)
            )

            # Generate PDF
            pdf_generator = BookPDFGenerator()
            pdf_bytes = pdf_generator.generate_book_pdf(
                puzzles=puzzles,
                book_title=book.metadata.title,
                trim_width_cm=None,  # Could extract from book.metadata.size
                trim_height_cm=None,
            )
            app.logger.debug("PDF generated successfully, size: %d bytes", len(pdf_bytes.getvalue()))

            # Create response
            pdf_bytes.seek(0)
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            filename = f"book_{timestamp}.pdf"

            return send_file(
                pdf_bytes,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            flash(f"Failed to generate PDF: {str(e)}", "error")
            return redirect(request.referrer or url_for("book_detail", book_id=book.book_id))

    @app.route("/book/<book_id>/download-pdf", methods=["POST"])
    def download_book_pdf(book_id):
        """Download book as PDF (from books list)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        return generate_book_pdf_download(book, puzzle_review)

    @app.route("/book/<book_id>/delete", methods=["POST"])
    def delete_book(book_id):
        """Delete a draft book."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        # Only allow deleting draft books
        if book.status != BookStatus.DRAFT.value:
            flash(f"Cannot delete {book.status} book. Only draft books can be deleted.", "error")
            return redirect(url_for("books_list"))

        try:
            book_mgr.delete_book(book_id)
            flash(f"Deleted book: {book.metadata.title}", "success")
        except Exception as e:
            flash(f"Failed to delete book: {str(e)}", "error")

        return redirect(url_for("books_list"))

    @app.route("/book/<book_id>")
    def book_detail(book_id):
        """View and edit book details."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        return render_template("book_detail.html", book=book)

    @app.route("/book/<book_id>/add-puzzles", methods=["POST"])
    def add_puzzles_to_book(book_id):
        """Add puzzles to a book."""
        try:
            puzzle_ids_str = request.form.get("puzzle_ids", "")
            puzzle_ids = [pid.strip() for pid in puzzle_ids_str.split(",") if pid.strip()]

            if book_mgr.add_puzzles_to_book(book_id, puzzle_ids):
                flash(f"Added {len(puzzle_ids)} puzzles to book", "success")
            else:
                flash("Book not found", "error")

        except ValueError as e:
            flash(f"Error: {str(e)}", "error")

        return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/book/<book_id>/status", methods=["POST"])
    def update_book_status(book_id):
        """Update book status."""
        status = request.form.get("status")

        try:
            if book_mgr.set_book_status(book_id, status):
                flash(f"Book status updated to {status}", "success")
            else:
                flash("Book not found", "error")

        except ValueError as e:
            flash(f"Error: {str(e)}", "error")

        return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/book/<book_id>/generate-pdf", methods=["POST"])
    def generate_book_pdf(book_id):
        """Generate PDF for a book."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if len(book.puzzle_ids) == 0:
            flash("Cannot generate PDF for book with no puzzles", "error")
            return redirect(url_for("book_detail", book_id=book_id))

        try:
            # Get puzzles for the book
            puzzle_data = []
            for puzzle_id in book.puzzle_ids:
                puzzle = puzzle_review.get_puzzle(puzzle_id)
                if puzzle:
                    puzzle_data.append(puzzle)

            if not puzzle_data:
                flash("No valid puzzles found for book", "error")
                return redirect(url_for("book_detail", book_id=book_id))

            # Generate PDF
            pdf_gen = get_pdf_generator()
            pdf_bytes = pdf_gen.generate_book_pdf(
                {
                    "title": book.metadata.title,
                    "description": book.metadata.description,
                    "theme": book.metadata.theme,
                    "target_audience": book.metadata.target_audience,
                    "page_count": len(puzzle_data),
                },
                puzzle_data
            )

            # Store PDF URL (in production, save to S3 or similar)
            book_mgr.set_pdf_url(book_id, f"PDF generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            flash("PDF generated successfully!", "success")

            # Return PDF for download
            return send_file(
                pdf_bytes,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"{book.metadata.title.replace(' ', '_')}.pdf"
            )

        except Exception as e:
            flash(f"Error generating PDF: {str(e)}", "error")
            return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/api/batch/<batch_id>/status")
    def api_batch_status(batch_id):
        """API endpoint for batch status (JSON)."""
        job = batch_gen.get_batch_status(batch_id)
        if not job:
            return jsonify({"error": "Batch not found", "batch_id": batch_id}), 404

        return jsonify(job.to_dict())

    @app.route("/api/batch/<batch_id>")
    def api_batch_status_alt(batch_id):
        """API endpoint for batch status (alternative URL)."""
        job = batch_gen.get_batch_status(batch_id)
        if not job:
            return jsonify({"error": "Batch not found", "batch_id": batch_id}), 404

        return jsonify(job.to_dict())

    @app.route("/api/puzzles")
    def api_puzzles():
        """API endpoint for filtered puzzles (JSON)."""
        try:
            size = request.args.get("size", type=int)
            difficulty = request.args.get("difficulty")
            quality_min = request.args.get("quality_min", type=int)
            limit = request.args.get("limit", 25, type=int)
            offset = request.args.get("offset", 0, type=int)

            filter_opts = PuzzleFilter(
                size=(size, size) if size is not None else None,
                difficulty=difficulty,
                quality_min=quality_min,
                limit=limit,
                offset=offset,
            )
            result = puzzle_review.filter_puzzles(filter_opts)

            return jsonify(result.to_dict())

        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/image/<file_id>")
    def api_get_image(file_id):
        """Serve uploaded image file (original, uncropped)."""
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)

        if not image:
            return "Not found", 404

        try:
            # Verify file exists
            import os
            if not os.path.exists(image.file_path):
                return f"File not found: {image.file_path}", 404

            return send_file(
                image.file_path,
                mimetype=f"image/{image.format.lower()}",
            )
        except FileNotFoundError:
            return f"File missing: {image.file_path}", 404
        except Exception as e:
            return f"Error loading image: {str(e)}", 500

    @app.route("/api/image/<file_id>/cropped")
    def api_get_cropped_image(file_id):
        """Serve cropped preview (what will be used for puzzle generation).

        Uses the same ink-bounding-box trim and aspect-preserving centre crop
        as ``nonogram.sourcing.image.generate`` (the pipeline
        :func:`nonogram.admin.image_to_puzzle.image_to_grid` now delegates to)
        so this preview shows the crop that will actually be applied, rather
        than a differently-thresholded content-only trim that never matched
        the final puzzle (which also fit-cropped to the target aspect ratio).
        """
        from nonogram.sourcing.image import load_greyscale, ink_bounding_box, fit_crop_box
        import os
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)

        if not image:
            return "Not found", 404

        try:
            # Verify file exists
            if not os.path.exists(image.file_path):
                return f"File not found: {image.file_path}", 404

            target_width, target_height = image.predict_size()

            greyscale = load_greyscale(image.file_path)
            content = greyscale.crop(ink_bounding_box(greyscale))
            final_box = fit_crop_box(*content.size, target_width, target_height)
            img = content.crop(final_box)

            # Save to bytes
            img_bytes = BytesIO()
            # Convert format to PIL-compatible name (JPEG not JPG)
            save_format = "JPEG" if image.format.upper() in ("JPG", "JPEG") else image.format.upper()
            img.save(img_bytes, format=save_format)
            img_bytes.seek(0)

            return send_file(
                img_bytes,
                mimetype=f"image/{image.format.lower()}",
            )
        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route("/api/puzzle/<puzzle_id>/grid")
    def api_puzzle_grid_from_puzzle(puzzle_id):
        """Get puzzle grid as SVG from stored puzzle."""
        # Use DB-backed puzzle_review from closure, not legacy service
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            return "Not found", 404

        try:
            # Get grid from puzzle (dict object)
            grid = puzzle.get('grid')
            if not grid:
                return "No grid data stored", 500

            # Validate grid format
            if not isinstance(grid, list) or not grid or not isinstance(grid[0], list):
                return "Invalid grid format", 500

            # Generate SVG
            svg = grid_to_svg(grid, cell_size=20)
            if not svg:
                return "Failed to generate SVG", 500

            return svg, 200, {"Content-Type": "image/svg+xml"}

        except TypeError as e:
            return f"Grid format error: {str(e)}", 500
        except Exception as e:
            return f"Error generating grid: {str(e)}", 500

    @app.route("/api/puzzle/<puzzle_id>/grid/download")
    def api_puzzle_grid_download_from_puzzle(puzzle_id):
        """Download puzzle grid as SVG file from stored puzzle."""
        # Use DB-backed puzzle_review from closure, not legacy service
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            return "Not found", 404

        try:
            # Get grid from puzzle (dict object)
            grid = puzzle.get('grid')
            if not grid:
                return "No grid data", 500

            # Generate SVG
            svg_bytes = grid_to_svg(grid, cell_size=20).encode("utf-8")
            filename = f"puzzle_{puzzle_id}.svg"

            return send_file(
                BytesIO(svg_bytes),
                mimetype="image/svg+xml",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route("/api/puzzle/<puzzle_id>/grid/download-pdf")
    def api_puzzle_grid_download_pdf(puzzle_id):
        """Download puzzle grid as PDF file with puzzle and solution pages."""
        # Use DB-backed puzzle_review from closure, not legacy service
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            return "Not found", 404

        try:
            # Validate puzzle has required fields
            grid = puzzle.get('grid')
            if not grid:
                return "No grid data", 500

            # Convert grid to clues using the standard clues module
            width = puzzle.get('width', len(grid[0]) if grid else 0)
            height = puzzle.get('height', len(grid) if grid else 0)

            row_clues = tuple(clues.encode_line(row) for row in grid)
            col_clues = tuple(clues.encode_line([grid[i][j] for i in range(height)]) for j in range(width))

            # Create ExportPayload for the professional PDF renderer
            payload = ExportPayload(
                grid=grid,
                row_clues=row_clues,
                column_clues=col_clues,
                seed=0,  # Not tracked in admin panel
                mode="image",  # Generated from image
                width=width,
                height=height,
                density=None,
                name=puzzle.get('puzzle_name', puzzle_id),
                difficulty=puzzle.get('difficulty_tier', 'Unknown'),
            )

            # Use the professional PDF renderer to generate pages
            puzzle_page, answer_page = render_pages(payload)

            # Convert to PDF bytes using Pillow
            pdf_bytes = BytesIO()
            puzzle_page.save(
                pdf_bytes,
                format="PDF",
                save_all=True,
                append_images=[answer_page],
                resolution=300,  # High quality
            )
            pdf_bytes.seek(0)

            filename = f"{puzzle_id}.pdf"
            return send_file(
                pdf_bytes,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            app.logger.exception("PDF generation error for %s", puzzle_id)
            return f"Error: {str(e)}", 500

    @app.route("/api/puzzle/<puzzle_id>/details")
    def api_puzzle_details(puzzle_id):
        """Get full puzzle details as JSON (for detail modal)."""
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            return jsonify({"error": "Puzzle not found"}), 404

        # Fetch available books for assignment dropdown
        books = book_mgr.get_all_books()

        return jsonify({
            "puzzle": puzzle,
            "books": [{"id": b.book_id, "title": b.metadata.title} for b in books],
        })

    @app.route("/puzzle/<puzzle_id>/delete", methods=["POST"])
    def delete_puzzle(puzzle_id):
        """Delete a rejected puzzle."""
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            flash("Puzzle not found", "error")
            return redirect(url_for("puzzles_list"))

        # Only allow deletion of rejected puzzles
        if puzzle.get("status") != "rejected":
            flash("Only rejected puzzles can be deleted", "error")
            return redirect(url_for("puzzles_list"))

        # Only allow deletion if not in a book
        if puzzle.get("book_id"):
            flash("Cannot delete puzzle that is in a book", "error")
            return redirect(url_for("puzzles_list"))

        # Delete from database
        try:
            import uuid as uuid_module
            from nonogram.db.models import Puzzle
            with session_scope() as db:
                puzzle_uuid = uuid_module.UUID(puzzle_id) if isinstance(puzzle_id, str) else puzzle_id
                p = db.query(Puzzle).filter(Puzzle.id == puzzle_uuid).first()
                if p:
                    db.delete(p)
            flash(f"Puzzle deleted", "success")
        except Exception as e:
            flash(f"Error deleting puzzle: {str(e)}", "error")

        return redirect(url_for("puzzles_list"))

    @app.route("/puzzle/<puzzle_id>/restore", methods=["POST"])
    def restore_puzzle(puzzle_id):
        """Restore rejected or approved puzzle back to draft."""
        if puzzle_review.restore_puzzle(puzzle_id):
            flash(f"Puzzle restored to draft", "success")
        else:
            flash(f"Puzzle not found", "error")

        # Return to previous page or puzzles list
        batch_id = request.args.get("batch_id")
        if batch_id:
            return redirect(url_for("generated_puzzles", batch_id=batch_id))
        return redirect(url_for("puzzles_list"))

    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors."""
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        return render_template("500.html", error=str(e)), 500

    return app


if __name__ == "__main__":
    app = create_app(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
