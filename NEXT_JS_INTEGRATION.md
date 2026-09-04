# Next.js Integration Summary

This document summarizes the clean integration between the Next.js frontend and the Python nonogram generator.

## What Was Done

### 1. **Simplified Form (Frontend)**
- **File:** `nonogram-web/app/components/GeneratorForm.tsx`
- **Changes:**
  - Removed multi-mode selector (kept image mode only for web UI)
  - Kept intelligent image preview with aspect ratio detection
  - Suggested grid sizes based on image dimensions
  - Clean form with width/height/difficulty/seed/export format controls
- **Removed:** density and library_key fields (not needed for web)

### 2. **Node.js API Route (Backend)**
- **File:** `nonogram-web/app/api/generate/route.ts`
- **Implementation:**
  - Parses multipart form data (image upload + fields)
  - Calls `nonogram generate` CLI via subprocess
  - Parses CLI output to extract metadata (seed, file paths)
  - Returns JSON response with puzzle name, seed, and file locations
  - Handles errors gracefully with helpful messages
  - Cleans up temporary files
- **Supported Parameters:**
  - `mode`: "image" (others can be added)
  - `width`, `height`: grid dimensions
  - `name`: optional puzzle name
  - `difficulty`: any/easy/medium/hard
  - `seed`: optional integer for reproducibility
  - `export_formats`: array of formats (json, csv, png, svg, pdf)
  - `image`: uploaded file

### 3. **Updated Frontend Response Handler (page.tsx)**
- **File:** `nonogram-web/app/page.tsx`
- **Changes:**
  - Properly handles the API response format
  - Checks for success (has `name` and `seed`)
  - Displays error messages from API
  - Shows results with puzzle metadata

### 4. **Results Display (ResultDisplay.tsx)**
- **File:** `nonogram-web/app/components/ResultDisplay.tsx`
- **Already had:** proper display of puzzle name, seed, and file paths
- **Note:** File paths shown are server-side (in project puzzles/ directory)

### 5. **Python API Handler (Optional/Fallback)**
- **File:** `nonogram-web/api/generate.py`
- **Purpose:** Serverless Python function for Vercel deployment
- **Features:**
  - Can parse multipart form data directly
  - Uses Python web module's submission/multipart handlers
  - Calls orchestrator.generate() and export_puzzle()
  - Returns JSON response
- **Note:** May not be used if Node.js route handles everything

### 6. **Documentation**
- **File:** `nonogram-web/SETUP.md`
  - Comprehensive local development guide
  - Deployment instructions
  - Troubleshooting tips
  - Architecture explanation
- **Updated:** `nonogram-web/README.md`
  - Revised quick start
  - Updated architecture diagram
  - Simplified testing instructions

## How It Works Locally

```bash
# 1. Setup (one time)
python3.14 -m venv .venv
./.venv/bin/pip install -e '.[dev]'

cd nonogram-web
npm install
ln -s ../src src

# 2. Run (with venv activated)
source .venv/bin/activate
npm run dev

# 3. Use
# Open http://localhost:3000
# Upload image → Generate → See results
```

## How It Works on Vercel

1. Vercel detects Next.js project
2. Builds and deploys the Next.js app
3. Python runtime is available for subprocess calls
4. When user submits form:
   - Next.js route receives multipart data
   - Calls `nonogram` CLI (available in Vercel Python environment)
   - Returns results as JSON
   - Files are saved to Vercel's ephemeral filesystem

## Key Design Decisions

### Why Node.js Route + CLI (Not Direct Python)?

✅ **Pros:**
- Reuses existing CLI (battle-tested)
- Works with subprocess in both local and Vercel environments
- Simpler than trying to import Python in Node.js
- All CLI features automatically available
- Easy to extend (just add new CLI flags)

✅ **Compatibility:**
- Works locally with activated venv
- Works on Vercel with Python runtime
- No extra abstraction layer

### Why Image Mode Only on Web?

✅ **Pros:**
- CLI still supports all modes (random, library, image)
- Web UI focused on most common use case (image-based)
- Users can still use random/library modes via CLI

### How Files Are Handled

**Local Development:**
- Files saved to `./puzzles/` (configurable)
- Paths returned in JSON response
- User can access files directly

**Vercel Deployment:**
- Files saved to ephemeral filesystem
- Paths returned in JSON response
- Files cleaned up between invocations
- Future enhancement: persist with S3/Vercel KV

## Testing

### Manual Testing
```bash
# Start dev server
npm run dev

# Open http://localhost:3000
# 1. Upload test image
# 2. Adjust grid size
# 3. Select export formats
# 4. Click Generate
# 5. Check DevTools Network tab for response
```

### Checking Generated Files
```bash
ls -la ./puzzles/
```

### Debugging
- DevTools Network tab: see full request/response
- Terminal: see CLI output and errors
- Browser console: see client-side errors

## What's Ready

✅ Image-based puzzle generation from web UI  
✅ Grid size configuration with smart suggestions  
✅ Difficulty and seed selection  
✅ Multiple export formats  
✅ Error handling and user feedback  
✅ Local development setup  
✅ Vercel deployment ready  

## What's Not Included

❌ File download/serving (returns paths only)  
❌ Persistent storage (files ephemeral on Vercel)  
❌ User authentication  
❌ Puzzle gallery/history  
❌ Random/Library modes on web (CLI-only)  

These can be added later if needed.

## Next Steps for You

1. **Test locally:**
   ```bash
   source .venv/bin/activate
   cd nonogram-web
   npm run dev
   ```

2. **Try the form:**
   - Upload a test image
   - Generate a puzzle
   - Check the results

3. **Deploy to Vercel** (when ready):
   ```bash
   git add .
   git commit -m "feat: Nonogram web UI with Next.js + Python integration"
   git push
   # Go to vercel.com → Import repo → Deploy
   ```

4. **Future enhancements:**
   - Add file download endpoint (`/api/files/[...path]`)
   - Persist files with S3 or Vercel KV
   - Add puzzle gallery
   - Extend to support random/library modes

## References

- **Setup Guide:** `nonogram-web/SETUP.md`
- **Updated README:** `nonogram-web/README.md`
- **Architecture Docs:** `meta/architecture/`
- **Kanban Cards:** `meta/kanban/cards/`
- **Python CLI:** `src/nonogram/cli.py`
- **Requirements:** `requirements.md`
