"""Flask admin panel application for nonogram puzzle management."""

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime
import json
import os

from .batch_generator import get_batch_generator, BatchStatus
from .puzzle_review import get_puzzle_review_service, PuzzleFilter
from .book_manager import get_book_manager, BookStatus


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
