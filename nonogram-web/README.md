# Nonogram Web – Next.js + Python Integration

This is the web frontend for the nonogram puzzle generator. It's a modern React/Next.js application that generates uniquely-solvable nonogram puzzles via the Python nonogram CLI.

## Architecture

```
Frontend (React)           →  Node.js API Route      →  Python CLI  →  Your Solver
GeneratorForm.tsx             app/api/generate/          src/nonogram/
(image upload)                route.ts                   (orchestrator, etc.)
ResultDisplay.tsx             (subprocess)
```

- **Frontend:** React components (Next.js 14) for image upload and results
- **Backend:** Node.js API route that calls the nonogram CLI via subprocess
- **Core Logic:** Existing Python solver, clues, export, and difficulty modules

## Project Structure

```
nonogram-web/
├── app/
│   ├── layout.tsx              Root layout
│   ├── page.tsx                Main page with form
│   ├── globals.css             Global styles
│   └── components/
│       ├── GeneratorForm.tsx    Form component
│       └── ResultDisplay.tsx    Results display
│
├── api/
│   ├── generate.py             Vercel Python serverless function
│   └── requirements.txt         Python dependencies (Pillow, NumPy)
│
├── src/                        Symlink to ../src (your Python package)
│   └── nonogram/               → ../../src/nonogram
│
├── package.json                Node.js dependencies
├── tsconfig.json               TypeScript config
├── next.config.js              Next.js config
├── vercel.json                 Vercel deployment config
└── .gitignore
```

## Quick Start

**For detailed setup instructions, see [SETUP.md](./SETUP.md)**

### Quick Setup (3 steps)

**1. Install Python dependencies** (from project root, not nonogram-web/)
```bash
python3.14 -m venv .venv
./.venv/bin/pip install -e '.[dev]'
```

**2. Install Node dependencies**
```bash
cd nonogram-web
npm install
ln -s ../src src  # Create symlink (Windows: mklink /d src ..\..\src)
```

**3. Run development server** (with venv activated)
```bash
source .venv/bin/activate  # Or just run: .venv/bin/python -m next dev
cd nonogram-web
npm run dev
```

Visit `http://localhost:3000` to use the generator.

## How It Works

### Frontend Flow

1. User uploads an image and fills form (grid size, difficulty, seed, export formats)
2. User clicks "Generate Puzzle"
3. Form data is sent as multipart/form-data POST to `/api/generate`
4. Results (puzzle name, seed, file paths) are displayed

### Backend Flow

1. `app/api/generate/route.ts` (Node.js) receives the multipart request
2. Parses form fields and extracts the uploaded image file
3. Saves image to temporary file
4. Calls `nonogram generate --mode image --image <path> ...` via subprocess
5. Parses CLI output to extract seed and file paths
6. Returns JSON with results to frontend

### Data Flow Diagram

```
Image Upload
    ↓
Frontend Form
    ↓
POST /api/generate (multipart/form-data)
    ↓
Node.js Route Handler
    ↓
Write image to temp file
    ↓
spawn subprocess: nonogram generate --mode image ...
    ↓
Python CLI (orchestrator.generate + export_puzzle)
    ↓
Parse output (seed, file paths)
    ↓
Return JSON
    ↓
Frontend: Show results
```

## API Testing

### Web UI Testing

1. Start dev server: `npm run dev`
2. Go to `http://localhost:3000`
3. Upload an image
4. Adjust grid size and select export formats
5. Click "Generate Puzzle"
6. Check Network tab in DevTools for `/api/generate` response

### Curl Testing (if needed)

```bash
# Create temp image file
echo "fake image data" > /tmp/test.png

# Test API (requires form-data)
curl -X POST http://localhost:3000/api/generate \
  -F "mode=image" \
  -F "width=20" \
  -F "height=20" \
  -F "image=@/tmp/test.png" \
  -F "export_formats=json"
```

## Deployment to Vercel

### Prerequisites

- GitHub account
- Vercel account (free tier available)
- Your code pushed to a GitHub repo

### Deploy in 5 Steps

1. **Create a GitHub repo**
   ```bash
   cd nonogram-web
   git init
   git add .
   git commit -m "Initial Next.js + nonogram setup"
   git remote add origin https://github.com/YOUR_GITHUB/nonogram-web.git
   git push -u origin main
   ```

2. **Connect to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repo

3. **Configure (if needed)**
   - Vercel auto-detects Next.js
   - It will also detect `api/generate.py` as a Python function
   - Environment: `vercel.json` specifies build commands

4. **Deploy**
   - Click "Deploy"
   - Wait ~2 minutes for the build
   - Your site is live! 🎉

5. **Your URL**
   ```
   https://nonogram-web.vercel.app
   ```

### Environment Variables

Add these in Vercel's project settings if needed:

```
PYTHONPATH=/var/task/src
```

(Usually not needed — `vercel.json` handles this.)

## How Files Are Handled

### Current Behavior

Files are generated in `/tmp` (temporary storage) and paths are returned in the JSON response.

```json
{
  "name": "puzzle_abc123",
  "seed": 42,
  "files": {
    "json": "/tmp/puzzle_abc123.json",
    "png": "/tmp/puzzle_abc123.png",
    "csv": "/tmp/puzzle_abc123.csv",
    "svg": "/tmp/puzzle_abc123.svg"
  }
}
```

### Limitations

- **Temp files are cleaned between invocations** — users can't revisit the files later
- **No download links** — the paths shown are server-side only
- **Free tier timeout:** 10 seconds (could timeout on large grids)

### Future: Add File Downloads

To let users download files, add a `/api/files/[...path]` endpoint:

```python
# api/files/[...path].py
import os
from pathlib import Path

def handler(request):
    path = request.path.replace('/api/files/', '')
    file_path = Path('/tmp') / path
    
    if not file_path.exists():
        return {'statusCode': 404, 'body': 'Not found'}
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': f'attachment; filename="{path}"'
        },
        'body': content.decode('latin1'),  # Binary content as string
        'isBase64Encoded': True
    }
```

Or use **Vercel KV** for persistent storage (requires paid tier).

## Customization

### Change the Form Fields

Edit `app/components/GeneratorForm.tsx`:
- Add/remove input fields
- Change default values
- Modify validation rules

### Change the Styling

Edit `app/globals.css` for global styles, or use inline `style={}` in components.

### Change Export Formats

In `GeneratorForm.tsx`, the export formats are hardcoded:
```tsx
{['json', 'csv', 'png', 'svg'].map((format) => (
```

Modify the array to match what your orchestrator supports.

## Troubleshooting

### "Cannot find module 'nonogram'"

Make sure the symlink exists:
```bash
ls -la src/  # should show -> ../src
```

If not, recreate it (see "Create the Symlink" above).

### "POST /api/generate returns 500"

Check the function's stderr:
1. On Vercel: go to Deployments → Logs → Filter by "generate"
2. Locally: `vercel dev` shows errors in the terminal

Common issues:
- Python dependencies missing → add to `api/requirements.txt`
- Import path wrong → check `sys.path.insert()` in `api/generate.py`
- Orchestrator error → same error appears in the response

### Form submission doesn't call the API

Check browser dev tools:
1. Open DevTools (F12)
2. Go to Network tab
3. Submit the form
4. Look for POST to `/api/generate` — check status and response

### Files not found after generation

Files are in `/tmp` and are temporary. The API returns paths, but those paths won't be available to users outside the Vercel function. To fix, either:
- Return files as base64-encoded data (for small files)
- Add a `/api/files/` endpoint (see section above)
- Use Vercel KV or S3 for persistent storage

## Testing

### Manual Testing

1. Start dev server: `npm run dev`
2. Go to `http://localhost:3000`
3. Fill form and submit
4. Check Network tab for `/api/generate` response

### Automated Testing

Currently no test suite for the frontend. To add:

```bash
npm install --save-dev jest @testing-library/react
```

Then write tests in `app/__tests__/` and run `npm test`.

## Related Files

- **Your nonogram source:** `../src/nonogram/` (orchestrator, solver, exporters, etc.)
- **Web handler (legacy):** `../src/nonogram/web/handler.py` (local http.server version)
- **Architecture docs:** `../meta/architecture/` (ADRs, C4 diagrams, requirements)
- **Kanban cards:** `../meta/kanban/cards/` (detailed notes on each component)

## Common Next Steps

1. **Deploy to Vercel** → See "Deployment" section
2. **Add file downloads** → Create `/api/files/[...path].py`
3. **Add image upload** → Modify form to accept file input, handle multipart in API
4. **Add job queue** → For grids that take >10s (Vercel timeout)
5. **Add user authentication** → Use Vercel Auth or NextAuth.js
6. **Add a database** → Store puzzles, track stats, etc.

## License

Same as parent nonogram project (see root LICENSE).
