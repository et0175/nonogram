# Nonogram Web - Setup & Development Guide

This is a Next.js frontend for the nonogram puzzle generator, integrated with the Python CLI via subprocess calls.

## Architecture

```
┌──────────────────────────────────────────┐
│  Next.js Frontend (React)                │
│  - GeneratorForm.tsx (image mode)        │
│  - ResultDisplay.tsx                     │
└──────────────────┬───────────────────────┘
                   │ FormData with image
                   ↓
┌──────────────────────────────────────────┐
│  Node.js API Route                       │
│  app/api/generate/route.ts               │
│  - Parse multipart form data             │
│  - Call nonogram CLI via subprocess      │
│  - Extract & return JSON response        │
└──────────────────┬───────────────────────┘
                   │ spawn subprocess
                   ↓
┌──────────────────────────────────────────┐
│  Python nonogram CLI                     │
│  ./.venv/bin/python -m nonogram generate │
│  - Supports: random, image, library modes│
│  - Outputs: seed, file paths, metadata   │
└──────────────────────────────────────────┘
```

## Local Development Setup

### 1. Install Python Dependencies

From the project root (not inside `nonogram-web`):

```bash
python3.14 -m venv .venv
./.venv/bin/pip install -e '.[dev]'
```

### 2. Install Node.js Dependencies

```bash
cd nonogram-web
npm install
```

### 3. Create Symlink to Python Source

The Next.js app needs access to your Python source code:

**macOS/Linux:**
```bash
cd nonogram-web
ln -s ../src src
```

**Windows:**
```bash
cd nonogram-web
mklink /d src ..\..\src
```

### 4. Run Development Server

**Option A: With venv activated**

```bash
# Activate venv
source .venv/bin/activate

# Run Next.js dev server (it will find nonogram in PATH)
cd nonogram-web
npm run dev
```

**Option B: Without activating venv**

```bash
# Run Next.js with explicit Python path
PYTHONPATH=.venv/lib/python3.14/site-packages \
npm run dev -- --experimental-edge-functions
```

Visit `http://localhost:3000` and try uploading an image.

## Testing

### Manual Testing

1. Go to http://localhost:3000
2. Upload a test image (JPG, PNG, etc.)
3. Adjust grid size (Width × Height)
4. Select export formats (JSON, CSV, PNG, SVG, PDF)
5. Click "Generate Puzzle"
6. Check the response in Network tab (DevTools)

### Checking Generated Files

By default, puzzles are saved to `./puzzles/` (see `src/nonogram/orchestrator.py` for default output dir).

```bash
ls -la ./puzzles/
```

### API Error Debugging

1. Open DevTools (F12)
2. Go to Network tab
3. Look for POST request to `/api/generate`
4. Check response body for error message
5. Check browser console for client-side errors
6. Check terminal output for server-side errors

## How the API Works

### Request

```http
POST /api/generate
Content-Type: multipart/form-data

image:              (File)
mode:               "image"
width:              (number, e.g. "20")
height:             (number, e.g. "20")
name:               (optional, puzzle name)
difficulty:         (optional, "easy"/"medium"/"hard"/"any")
seed:               (optional, integer for reproducibility)
export_formats:     (array, e.g. ["json", "png"])
```

### Response (Success)

```json
{
  "name": "puzzle_name",
  "seed": 12345,
  "files": {
    "json": "/path/to/puzzle_name.json",
    "png": "/path/to/puzzle_name.png"
  }
}
```

### Response (Error)

```json
{
  "error": "Error message describing what went wrong"
}
```

## Features Supported

### Frontend (Web Form)

- ✅ Image mode (upload image → generate puzzle)
- ✅ Image preview with cropping detection
- ✅ Suggested grid sizes based on image aspect ratio
- ✅ Custom puzzle name (optional)
- ✅ Difficulty selection (any/easy/medium/hard)
- ✅ Seed input for reproducible generation
- ✅ Multiple export formats (JSON, CSV, PNG, SVG, PDF)

### Backend (CLI)

Supports all CLI modes (called via subprocess):
- ✅ `--mode image` - from uploaded image
- ✅ `--mode random` - procedural generation
- ✅ `--mode library` - from template library
- ✅ All export formats
- ✅ Difficulty targeting
- ✅ Seed-based reproducibility

## Deployment to Vercel

### Prerequisites

- GitHub repository with this code
- Vercel account (free tier works)

### Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "feat: Nonogram web UI with Python integration"
   git push origin main
   ```

2. **Connect to Vercel**
   - Go to vercel.com
   - Click "New Project"
   - Import your GitHub repo
   - Vercel auto-detects Next.js + Python

3. **Configure Environment** (usually not needed)
   - Runtime: Node.js + Python should auto-detect
   - No special environment variables needed

4. **Deploy**
   - Click "Deploy"
   - Wait ~3-5 minutes
   - Your site is live!

### Known Limitations on Vercel Free Tier

- **Timeout:** 10 seconds for serverless functions
  - Large images or high density grids may timeout
  - Consider reducing max grid size or density in production
- **Cold starts:** First request after inactivity ~500-1000ms
- **File storage:** Generated files are temporary (cleaned up between invocations)
  - Use Vercel KV or S3 to persist files

## Troubleshooting

### "nonogram: command not found"

The CLI is not in your PATH. Solution:
```bash
# Activate the venv before running dev server
source .venv/bin/activate
npm run dev
```

### "Grid size out of range" error

Check your input values. Typical ranges:
- Width/Height: 5-40
- Density: 1-99%
- Seed: any positive integer

### "Image file is required"

Make sure you upload an image file in image mode.

### "Generation timeout (60 seconds)"

The puzzle took too long to generate. Try:
- Smaller grid size
- Lower density (for random mode)
- Different seed to avoid difficult search spaces

### Files not found after generation

On Vercel, files are temporary. The API returns file paths, but they won't be accessible to users. Options:
1. **Base64 encode files** - include in JSON response
2. **Use Vercel KV** - persistent cache
3. **Use S3** - external file storage
4. **Local only** - perfect for local development

## File Structure

```
nonogram-web/
├── app/
│   ├── api/
│   │   └── generate/
│   │       └── route.ts           # Node.js handler (parses form, calls CLI)
│   ├── components/
│   │   ├── GeneratorForm.tsx      # Image upload form
│   │   └── ResultDisplay.tsx      # Results display
│   ├── layout.tsx
│   ├── page.tsx                   # Main page
│   └── globals.css
├── api/
│   ├── generate.py                # Python handler (fallback/Vercel)
│   └── requirements.txt
├── src/                           # Symlink to ../src (Python package)
├── package.json
├── tsconfig.json
├── next.config.js
└── vercel.json                    # Vercel config
```

## Next Steps

1. **Add file downloads** - Create `/api/files/[...path]` endpoint to serve generated files
2. **Add statistics** - Track generation time, puzzle difficulty
3. **Add gallery** - Show previously generated puzzles
4. **Mobile UI** - Optimize for touch and smaller screens
5. **Support for library/random modes** - Extend form to allow other generation modes

## References

- [Next.js Documentation](https://nextjs.org/docs)
- [Vercel Python Functions](https://vercel.com/docs/functions/serverless-functions/python)
- [Nonogram Package](../README.md)
- [Architecture Docs](../meta/architecture/)
