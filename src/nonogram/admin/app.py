"""Flask admin panel application for nonogram puzzle management."""

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, send_file
from datetime import datetime
from pathlib import Path
import json
import os

from .batch_generator import get_batch_generator, BatchStatus
from .puzzle_review import get_puzzle_review_service, PuzzleFilter
from .book_manager import get_book_manager, BookStatus
from .image_manager import get_image_manager


def create_app(debug=None):
    """Create and configure the Flask admin panel app."""
    app = Flask(__name__, template_folder="templates")

    # Configuration from environment
    if debug is None:
        debug = os.getenv("FLASK_ENV") == "development"

    app.config["DEBUG"] = debug
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    app.config["ENV"] = os.getenv("FLASK_ENV", "production" if not debug else "development")

    puzzle_review = get_puzzle_review_service()
    batch_gen = get_batch_generator(puzzle_review_service=puzzle_review)
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
        """Create a new batch generation job from images."""
        if request.method == "POST":
            try:
                image_source = request.form.get("image_source")
                quality_filter = int(request.form.get("quality_filter", 0))

                if not image_source:
                    flash("Please select image source (upload or directory)", "error")
                    return render_template("batch_create.html")

                # Handle file uploads or directory selection
                if image_source == "upload":
                    if "images" not in request.files or len(request.files.getlist("images")) == 0:
                        flash("Please select at least one image", "error")
                        return render_template("batch_create.html")
                    # Store uploaded files in session for next step
                    # TODO: Save to temporary location and redirect to image selection page
                    flash("Image upload - TODO: Implement CARD-004p (image selection page)", "warning")

                elif image_source == "directory":
                    if "directory" not in request.files or len(request.files.getlist("directory")) == 0:
                        flash("Please select a directory with images", "error")
                        return render_template("batch_create.html")
                    # TODO: Handle directory selection
                    flash("Directory selection - TODO: Implement CARD-004p (image selection page)", "warning")

                # TODO: After images are processed, redirect to /batch/select-images
                # For now, show placeholder message
                return render_template("batch_create.html")

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        return render_template("batch_create.html")

    @app.route("/batch/from-images", methods=["POST"])
    def create_batch_from_images():
        """Handle image-based batch creation (from simplified form)."""
        try:
            quality_filter = int(request.form.get("quality_filter", 0))

            # Get image manager
            image_mgr = get_image_manager()

            # Store quality filter in session
            session["quality_filter"] = quality_filter

            # Process both individual files and directory files
            all_files = []
            uploaded_count = 0

            # Collect files from individual file input
            if "images" in request.files:
                all_files.extend(request.files.getlist("images"))

            # Collect files from directory input
            if "directory" in request.files:
                all_files.extend(request.files.getlist("directory"))

            # Check if we got any files
            if not all_files or all(not f.filename for f in all_files):
                flash("Please select at least one image file or directory", "error")
                return redirect(url_for("create_batch"))

            # Only clear previous selections if new files are being uploaded
            image_mgr.clear_all()

            # Process all files
            import tempfile
            for file in all_files:
                if file.filename:
                    # Save to temp location
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
                        file.save(tmp.name)
                        # Add to manager
                        if image_mgr.add_image(tmp.name, file.filename):
                            uploaded_count += 1
                        # Clean up temp file
                        try:
                            os.unlink(tmp.name)
                        except:
                            pass

            if uploaded_count == 0:
                flash("No valid images found", "error")
                return redirect(url_for("create_batch"))

            flash(f"✓ Loaded {uploaded_count} image{uploaded_count != 1 and 's' or ''}", "success")
            return redirect(url_for("select_images"))

        except Exception as e:
            flash(f"❌ Error: {str(e)}", "error")
            return redirect(url_for("create_batch"))

    @app.route("/api/image/<file_id>")
    def serve_image(file_id):
        """Serve image file for display (binary format).

        Args:
            file_id: Unique identifier for uploaded image

        Returns:
            Binary image data with appropriate MIME type
        """
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)

        if not image:
            return jsonify({"error": "Image not found"}), 404

        try:
            # Verify file exists
            if not os.path.exists(image.file_path):
                return jsonify({"error": "Image file not found on disk"}), 404

            # Map image format to MIME type
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
            }
            mime_type = mime_types.get(image.format.lower(), 'image/png')

            # Serve file with proper MIME type
            return send_file(
                image.file_path,
                mimetype=mime_type,
                as_attachment=False,
                download_name=image.original_filename
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/batch/select-images")
    def select_images():
        """Display image selection page (CARD-004p)."""
        image_mgr = get_image_manager()
        images = image_mgr.get_all_images()

        if not images:
            flash("No images selected. Please upload or select from a directory.", "warning")
            return redirect(url_for("create_batch"))

        return render_template(
            "image_selection.html",
            images=images,
            total_size_mb=image_mgr.get_total_size_mb(),
            image_ids=",".join(img.file_id for img in images),
        )

    @app.route("/batch/preview-images", methods=["GET", "POST"])
    def preview_images():
        """Preview and configure image sizes (CARD-004q)."""
        image_mgr = get_image_manager()
        images = image_mgr.get_all_images()

        if not images:
            flash("No images to preview. Please select images first.", "warning")
            return redirect(url_for("create_batch"))

        if request.method == "POST":
            # Handle size configuration updates
            for image in images:
                file_id = image.file_id
                size_mode = request.form.get(f"mode_{file_id}", "fixed")
                size_value = int(request.form.get(f"value_{file_id}", 20))
                puzzle_name = request.form.get(f"name_{file_id}", image.puzzle_name)

                image_mgr.update_image_size(file_id, size_mode, size_value)
                image_mgr.update_image_name(file_id, puzzle_name)

            # Redirect to generation confirmation step
            flash("✓ Sizes configured. Ready to generate puzzles!", "success")
            return redirect(url_for("generate_batch_from_images"))

        return render_template(
            "image_preview.html",
            images=images,
            total_size_mb=image_mgr.get_total_size_mb(),
        )

    @app.route("/batch/generate", methods=["GET", "POST"])
    def generate_batch_from_images():
        """Generate puzzles from configured images (CARD-004r)."""
        image_mgr = get_image_manager()
        images = image_mgr.get_all_images()

        if not images:
            flash("No images to generate from. Please start over.", "warning")
            return redirect(url_for("create_batch"))

        if request.method == "POST":
            try:
                import uuid
                from datetime import datetime

                # Create batch job manually (workaround for image-based generation)
                batch_id = str(uuid.uuid4())
                from nonogram.admin.batch_generator import BatchJob, BatchStatus

                job = BatchJob(
                    batch_id=batch_id,
                    status=BatchStatus.GENERATING,
                    total_count=len(images),
                    theme="christmas",
                )
                batch_gen.jobs[batch_id] = job

                # Generate puzzles from images
                generated_count = 0
                for image in images:
                    try:
                        # For now, generate a single puzzle per image using MockGenerator
                        # TODO: Implement actual image-to-nonogram conversion
                        from nonogram.admin.puzzle_review import MockGenerator

                        generator = MockGenerator(seed=hash(image.file_id) % 999999)
                        size = image.predict_size()
                        puzzles = generator.generate_batch(
                            count=1,
                            sizes=[size],
                            theme="christmas",
                        )

                        if puzzles:
                            puzzle = puzzles[0]
                            # Add to review service (will link to batch via batch_id param)
                            puzzle_review.add_puzzle(
                                grid=puzzle["grid"],
                                clues_rows=puzzle["clues_rows"],
                                clues_cols=puzzle["clues_cols"],
                                width=puzzle["width"],
                                height=puzzle["height"],
                                theme=puzzle["theme"],
                                difficulty_score=puzzle.get("difficulty_score", 50),
                                difficulty_tier=puzzle.get("difficulty_tier", "medium"),
                                quality_score=puzzle.get("quality_score", 50),
                                recognizability=puzzle.get("recognizability", "medium"),
                                strategies_used=puzzle.get("strategies_used", []),
                                batch_id=batch_id,
                                source_image=image.puzzle_name,
                            )
                            generated_count += 1

                    except Exception as e:
                        flash(f"Error generating from {image.puzzle_name}: {str(e)}", "warning")
                        job.error_message = str(e)

                # Mark batch as complete
                job.status = BatchStatus.COMPLETE
                job.completed_count = generated_count
                job.puzzle_count = generated_count
                job.updated_at = datetime.utcnow()
                job.completed_at = datetime.utcnow()

                # Clear image manager for next batch
                image_mgr.clear_all()

                flash(f"Generated {generated_count} puzzle{generated_count != 1 and 's' or ''} from {len(images)} image{len(images) != 1 and 's' or ''}", "success")
                return redirect(url_for("batch_status", batch_id=batch_id))

            except Exception as e:
                flash(f"Error: {str(e)}", "error")
                return render_template(
                    "generate_batch.html",
                    images=images,
                    error=str(e),
                )

        return render_template(
            "generate_batch.html",
            images=images,
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
        size = request.args.get("size", type=int)
        difficulty = request.args.get("difficulty")
        quality_min = request.args.get("quality_min", type=int)
        limit = request.args.get("limit", 25, type=int)
        offset = request.args.get("offset", 0, type=int)

        try:
            filter_opts = PuzzleFilter(
                size=size,
                difficulty=difficulty,
                quality_min=quality_min,
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
            )

        except ValueError as e:
            flash(f"Filter error: {str(e)}", "error")
            return render_template("puzzles_list.html", puzzles=[], error=str(e))

    @app.route("/puzzle/<puzzle_id>/approve", methods=["POST"])
    def approve_puzzle(puzzle_id):
        """Approve a puzzle."""
        if puzzle_review.approve_puzzle(puzzle_id):
            flash(f"Puzzle {puzzle_id} approved", "success")
        else:
            flash(f"Puzzle not found", "error")

        return redirect(url_for("puzzles_list"))

    @app.route("/puzzle/<puzzle_id>/reject", methods=["POST"])
    def reject_puzzle(puzzle_id):
        """Reject a puzzle."""
        if puzzle_review.reject_puzzle(puzzle_id):
            flash(f"Puzzle {puzzle_id} rejected", "success")
        else:
            flash(f"Puzzle not found", "error")

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
                return redirect(url_for("book_detail", book_id=book_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        return render_template("book_create.html")

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
