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
from .image_manager import get_image_manager
from .image_to_puzzle import create_puzzle_from_image
from .grid_renderer import grid_to_svg, get_svg_filename
from .print_specs import PrintSpecValidator

# Import the professional export PDF module
from nonogram.export.pdf import render_pages
from nonogram.export import ExportPayload
from nonogram import clues

# Import DB session factory for DB-backed services
from nonogram.db import session_scope


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

    # Add CORS and security headers for Chrome compatibility
    @app.after_request
    def add_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    # Construct DB-backed service instances with session_factory
    # (persists batches/puzzles to the database via DATABASE_URL env var)
    puzzle_review = PuzzleReviewService(session_factory=session_scope)
    batch_gen = BatchGenerator(puzzle_review_service=puzzle_review, session_factory=session_scope)
    book_mgr = get_book_manager()

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

            # Store quality filter in session
            session["batch_quality_filter"] = quality_filter

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
            # Create batch job
            batch_id = batch_gen.create_batch(
                count=len(images),
                sizes=[20],
                theme="image",
                source="images",  # Use "images" not "image"
                quality_filter=session.get("batch_quality_filter", 0),
            )

            # Process each image and generate puzzles
            # Use the DB-backed puzzle_review service created in create_app(), not the legacy one
            quality_filter = session.get("batch_quality_filter", 0)
            generated_count = 0
            errors = []

            for image in images:
                try:
                    # Predict puzzle size based on image
                    width, height = image.predict_size()

                    # Convert image to puzzle
                    puzzle_data = create_puzzle_from_image(
                        image.file_path,
                        target_width=width,
                        target_height=height,
                        theme="image",
                    )

                    if not puzzle_data:
                        errors.append(f"Failed to process {image.original_filename}")
                        continue

                    # Check quality filter
                    if puzzle_data["quality_score"] < quality_filter:
                        continue

                    # Store puzzle
                    puzzle_id = puzzle_review.add_puzzle(
                        grid=puzzle_data["grid"],
                        clues_rows=puzzle_data["clues_rows"],
                        clues_cols=puzzle_data["clues_cols"],
                        width=puzzle_data["width"],
                        height=puzzle_data["height"],
                        theme=puzzle_data["theme"],
                        difficulty_score=puzzle_data["difficulty_score"],
                        difficulty_tier=puzzle_data["difficulty_tier"],
                        quality_score=puzzle_data["quality_score"],
                        recognizability=puzzle_data["recognizability"],
                        strategies_used=puzzle_data["strategies_used"],
                        batch_id=batch_id,
                        source_image=image.original_filename,
                    )

                    generated_count += 1

                except Exception as e:
                    errors.append(f"Error processing {image.original_filename}: {str(e)}")

            # Update batch with final puzzle count
            batch_gen._update_batch_status(batch_id, puzzle_count=generated_count)

            # Show results
            if generated_count > 0:
                flash(f"✅ Generated {generated_count} puzzle(s) from {len(images)} image(s)", "success")
            else:
                flash("No valid puzzles generated", "warning")

            if errors:
                for error in errors[:3]:  # Show first 3 errors
                    flash(error, "info")
                if len(errors) > 3:
                    flash(f"... and {len(errors) - 3} more errors", "info")

            # Clear session
            session.pop("batch_quality_filter", None)

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
                size=size,
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
                size=size,
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

        # TODO: Implement Step 3 puzzle arrangement
        flash("Step 3: Puzzle Arrangement (Coming soon)", "info")
        return redirect(url_for("book_detail", book_id=book_id))

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
                size=size,
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
        """Serve cropped preview (what will be used for puzzle generation)."""
        import numpy as np
        from PIL import Image as PILImage
        import os
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)

        if not image:
            return "Not found", 404

        try:
            # Verify file exists
            if not os.path.exists(image.file_path):
                return f"File not found: {image.file_path}", 404

            # Load and crop blank space around content
            img = PILImage.open(image.file_path).convert('L')
            arr = np.array(img)

            # Find rows and columns with content (not blank/white)
            content_threshold = 200
            has_content = arr < content_threshold

            # Find bounding box of content
            rows_with_content = np.any(has_content, axis=1)
            cols_with_content = np.any(has_content, axis=0)

            if np.any(rows_with_content) and np.any(cols_with_content):
                # Get indices of rows/cols with content
                row_indices = np.where(rows_with_content)[0]
                col_indices = np.where(cols_with_content)[0]

                # Crop to bounding box
                top = row_indices[0]
                bottom = row_indices[-1] + 1
                left = col_indices[0]
                right = col_indices[-1] + 1

                img = img.crop((left, top, right, bottom))

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

    @app.route("/api/puzzle-grid/<file_id>")
    def api_puzzle_grid(file_id):
        """Get puzzle grid as SVG for preview."""
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)

        if not image:
            return "Not found", 404

        try:
            # Get predicted size
            width, height = image.predict_size()

            # Convert image to puzzle grid
            puzzle_data = create_puzzle_from_image(
                image.file_path,
                target_width=width,
                target_height=height,
            )

            if not puzzle_data:
                return "Failed to generate puzzle grid", 500

            # Generate SVG
            svg = grid_to_svg(puzzle_data["grid"], cell_size=20)

            return svg, 200, {"Content-Type": "image/svg+xml"}

        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route("/api/puzzle-grid/<file_id>/download")
    def api_puzzle_grid_download(file_id):
        """Download puzzle grid as SVG file."""
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)

        if not image:
            return "Not found", 404

        try:
            # Get predicted size
            width, height = image.predict_size()

            # Convert image to puzzle grid
            puzzle_data = create_puzzle_from_image(
                image.file_path,
                target_width=width,
                target_height=height,
            )

            if not puzzle_data:
                return "Failed to generate puzzle grid", 500

            # Generate SVG
            svg_bytes = grid_to_svg(puzzle_data["grid"], cell_size=20).encode("utf-8")
            filename = get_svg_filename(image.original_filename)

            return send_file(
                BytesIO(svg_bytes),
                mimetype="image/svg+xml",
                as_attachment=True,
                download_name=filename,
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
            import traceback
            print(f"PDF generation error for {puzzle_id}: {str(e)}")
            traceback.print_exc()
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
            "books": [{"id": str(b.id), "title": b.title} for b in books],
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
