import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from nonogram import orchestrator
from nonogram.web import submission, multipart
from nonogram.errors import NonogramError


def handler(request: Any) -> Dict[str, Any]:
    """POST /api/generate - Generate a nonogram puzzle from image upload"""

    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method not allowed'})
        }

    try:
        # Get request body and content-type
        body = request.body
        if isinstance(body, bytes):
            body_bytes = body
        else:
            body_bytes = body.encode('utf-8', errors='replace')

        content_type = request.headers.get('Content-Type', '')
        media_type = content_type.split(';', 1)[0].strip().lower()

        # Parse form data - handle both urlencoded and multipart
        image_path: Path | None = None
        fields: Dict[str, list[str]] = {}

        if media_type == 'multipart/form-data':
            # Parse multipart form data (with file upload)
            parsed = multipart.read(content_type, body_bytes)
            posted = parsed.submission
            image_path = parsed.image_path
            fields = parsed.fields
        else:
            # Parse urlencoded form data
            posted = submission.read(body_bytes.decode('utf-8', errors='replace'))
            # Parse fields for potential re-population
            fields = urllib.parse.parse_qs(body_bytes.decode('utf-8', errors='replace'))

        if posted.request is None:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': ' or '.join(posted.unreadable)})
            }

        try:
            # Generate puzzle
            puzzle = orchestrator.generate(posted.request)
            written = orchestrator.export_puzzle(puzzle)

            # Convert Path objects to strings and organize by format
            files = {}
            for path in written:
                suffix = path.suffix.lstrip('.')
                files[suffix] = str(path)

            # Return paths to generated files
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'name': puzzle.name,
                    'seed': puzzle.seed,
                    'files': files
                })
            }

        except NonogramError as e:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e)})
            }
        finally:
            # Clean up uploaded temp file if it exists
            if image_path and image_path.exists():
                try:
                    image_path.unlink()
                except OSError:
                    pass

    except Exception as e:
        # Log the error for debugging
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }
