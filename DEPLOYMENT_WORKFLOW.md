# Deployment Workflow Documentation
**System:** Nonogram Web (Next.js + Python)  
**Platform:** Railway.app  
**Date:** 2026-09-05  
**Status:** Production-ready

---

## Overview

The Nonogram system is a **dual-runtime container** deployed on Railway.app:
- **Python 3.11** (backend): Puzzle generation engine
- **Node.js 20** (frontend): Next.js web server
- **Custom Node.js server** (server.js): Orchestrates both runtimes

Container lifecycle:
```
Docker build → Install Python + Node.js → Build Next.js → Start server.js → Listen 0.0.0.0:8080
```

---

## Architecture Overview

### Request Flow

```
User Browser
    ↓
Next.js Server (Node.js:3000 internally)
    ↓ [HTTP POST /api/generate]
API Handler (api/generate.py - serverless-compatible)
    ↓
Python sys.path insert (src/)
    ↓
orchestrator.generate(GenerationRequest)
    ↓ [Sourcing → Clues → Solver → Difficulty → Export]
Puzzle Files (PNG/SVG/JSON/CSV)
    ↓
Temp directory cleanup
    ↓
JSON Response (file paths)
    ↓
Browser (download files)
```

### Container Composition

```
Runtime              Version    Role
─────────────────────────────────────────────────────────────
Python              3.11-slim   Puzzle generation engine
Node.js             20          Next.js framework
Next.js             15          React web framework
React               18          UI components
TypeScript          5           Type checking
Pillow              10.0+       Image processing
NumPy               1.24+       Array operations
ReportLab           4.0+        PDF export
Tailwind CSS        4           Styling
Playwright          (dev)       E2E testing
```

---

## Dockerfile Breakdown

### Stage 1: Base Image & Dependencies

```dockerfile
FROM python:3.11-slim
```

- **Choice:** python:3.11-slim (not 3.14 like CLAUDE.md)
  - Reason: Railway default Python version at deployment time
  - `slim` variant reduces image size
  - Missing: `3.14` compatibility check

### Stage 2: System Packages

```dockerfile
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*
```

- **curl:** Required for Node.js setup script
- **git:** Not strictly needed for runtime (could remove)
- **Cleanup:** `rm -rf /var/lib/apt/lists/*` reduces image size

### Stage 3: Node.js Installation

```dockerfile
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*
```

- **deb.nodesource:** Official Node.js repository for Ubuntu/Debian
- **Node.js 20:** LTS version (security support through April 2026)
- **Why not default apt nodejs?** Often outdated; deb.nodesource stays current

### Stage 4: Directory Structure

```dockerfile
WORKDIR /app
COPY . .
```

- **Single stage:** All files copied at once
- **Alternative (better):** Multi-stage build to separate Python/Node layers
  - Current approach: Redundant copies; no layer caching

### Stage 5: Python Setup

```dockerfile
RUN pip3 install -e . --no-cache-dir
```

- **`-e .`:** Editable install; reads pyproject.toml from /app
  - Installs: nonogram CLI + dependencies (Pillow, NumPy, ReportLab)
- **`--no-cache-dir`:** Reduces image size
- **Missing:** pip cache optimization (`--cache-dir` would be better for layer reuse)

### Stage 6: Next.js Build

```dockerfile
WORKDIR /app/nonogram-web
RUN npm install --no-cache-dir
RUN npm run build
```

- **npm install:** Installs all node_modules (large)
- **npm run build:** Next.js produces .next/ directory
  - Compilation happens in container (slow; consider pre-built artifacts)
- **Alternative:** Pre-build next.js in CI, COPY .next/ instead

### Stage 7: Environment & Runtime

```dockerfile
WORKDIR /app/nonogram-web
EXPOSE 8080
ENV PYTHONPATH=/app/src
ENV PORT=8080
ENV NODE_ENV=production
CMD ["node", "server.js"]
```

- **PYTHONPATH=/app/src:** Allows Python to find nonogram package
- **PORT=8080:** Next.js reads from env; custom server.js uses it
- **NODE_ENV=production:** Next.js optimization
- **server.js:** Custom Node.js server (not next start)

---

## Custom Server (server.js)

### Why Custom Server?

```javascript
const { createServer } = require('http');
const next = require('next');

const app = next({ dev: false });
const handle = app.getRequestHandler();

createServer(async (req, res) => {
  try {
    const parsedUrl = parse(req.url, true);
    await handle(req, res, parsedUrl);
  } catch (err) {
    console.error('Request error:', err);
    res.statusCode = 500;
    res.end('Internal server error');
  }
}).listen(port, hostname);
```

**Problems solved:**

1. **Port Binding:** Railway requires binding to `0.0.0.0:PORT`
   - `next start` binds to localhost (inaccessible from outside container)
   - Custom server binds to `0.0.0.0` explicitly

2. **Error Handling:** Wraps request handler in try-catch
   - Prevents server crashes on malformed requests
   - Logs errors for debugging

3. **URL Parsing:** Preserves query strings and fragments
   - Next.js App Router depends on this

### Current Configuration

```javascript
const dev = process.env.NODE_ENV !== 'production';
const hostname = '0.0.0.0';  // Accessible from outside
const port = parseInt(process.env.PORT || '3000', 10);  // Railway: PORT=8080
```

**Missing:**

- HTTPS/TLS (Railway terminates SSL; server uses HTTP only)
- Request logging (only errors logged)
- Health checks (no /health endpoint)

---

## API Handler (api/generate.py)

### Entry Point

```python
def handler(request: Any) -> Dict[str, Any]:
    """POST /api/generate - Generate a nonogram puzzle from image upload"""
```

### Request Parsing

**Content-Type detection:**
```python
media_type = content_type.split(';', 1)[0].strip().lower()

if media_type == 'multipart/form-data':
    parsed = multipart.read(content_type, body_bytes)
else:
    posted = submission.read(body_bytes.decode('utf-8'))
```

**Flow:**
1. Extract `Content-Type` header
2. Parse multipart (file upload) or urlencoded (form fields)
3. Return `ParsedSubmission` with `.request` (GenerationRequest) or `.unreadable` (errors)

### Error Handling

```python
if posted.request is None:
    return {
        'statusCode': 400,
        'body': json.dumps({'error': ' or '.join(posted.unreadable)})
    }

try:
    puzzle = orchestrator.generate(posted.request)
    written = orchestrator.export_puzzle(puzzle)
    # Return file paths
except NonogramError as e:
    return {'statusCode': 400, 'body': json.dumps({'error': str(e)})}
finally:
    # Cleanup temp image file
    if image_path and image_path.exists():
        image_path.unlink()
```

**Patterns:**
- ✅ Cleanup in finally block (always runs)
- ✅ Custom error codes (400, 500)
- ⚠️ No timeout handling (could hang on slow grids)

### Response Format

Success (200):
```json
{
  "name": "puzzle-name",
  "seed": 42,
  "files": {
    "json": "/tmp/puzzle-1234.json",
    "png": "/tmp/puzzle-1234.png",
    "svg": "/tmp/puzzle-1234.svg"
  }
}
```

Error (400):
```json
{
  "error": "Grid size out of range (10-30)"
}
```

---

## Environment Variables

| Variable | Value | Source | Purpose |
|----------|-------|--------|---------|
| **PYTHONPATH** | /app/src | Dockerfile | Module resolution for nonogram package |
| **PORT** | 8080 | Railway | Server listening port |
| **NODE_ENV** | production | Dockerfile | Next.js optimization mode |
| **PATH** | (system) | Railway | Includes python3.11, node, npm |

**Missing:**
- LOG_LEVEL (hardcoded console logs)
- API_TIMEOUT (no timeout on puzzle generation)
- MAX_FILE_SIZE (multipart file size limit)
- CORS_ORIGIN (if public API, needs CORS headers)

---

## Deployment Process on Railway

### 1. Connect Repository

```bash
railway link          # Link local repo to Railway project
# or use Railway dashboard
```

### 2. Dockerfile Detection

Railway scans repo root for Dockerfile:
```
✓ Found Dockerfile in project root
✓ Will build using: docker build -t app:latest .
```

### 3. Build Phase (Local or Railway)

```bash
docker build -t nonogram-web:latest .
```

**Timeline:**
- `python:3.11-slim` pull: ~2 min
- apt-get update + Node.js setup: ~2 min
- pip install (Pillow + NumPy): ~3 min (compilation)
- npm install: ~2 min
- npm run build: ~1 min
- **Total:** ~10 min

**Optimization opportunities:**
- Pre-build node_modules as layer (BuildKit)
- Use binary wheels for NumPy/Pillow (not recompiling)
- Separate Python and Node layers

### 4. Push to Railway Registry

```bash
docker tag nonogram-web:latest railway.app/abc123/nonogram-web:latest
docker push railway.app/abc123/nonogram-web:latest
```

### 5. Deploy Container

```bash
railway deploy --json | jq '.url'
# Output: https://nonogram-web-abc.railway.app
```

Railway:
- Creates container from image
- Assigns random subdomain (e.g., `nonogram-web-abc.railway.app`)
- Exposes port 8080 → HTTPS (Railway terminates SSL)
- Starts health check (if /health endpoint exists)

### 6. Health Checks (if enabled)

Default: Railway checks `GET /:3000` (Next.js root page)

Current behavior:
- Returns HTML (page renders)
- Railway interprets 200 OK → "healthy"

**Better:** Add explicit /health endpoint
```python
# Add to server.js or Next.js route
app.get('/health', (req, res) => res.json({status: 'ok'}))
```

---

## Deployment Verification Checklist

After deployment:

- [ ] **URL accessible** - `curl https://nonogram-web-abc.railway.app`
- [ ] **Form loads** - Browser displays puzzle generator
- [ ] **Random generation works** - Submit form with default params
- [ ] **File download works** - Files downloadable (JSON/PNG/SVG)
- [ ] **Image upload works** - Switch to image mode, upload test PNG
- [ ] **Error handling works** - Invalid params show error message
- [ ] **Logs available** - Railway dashboard shows container logs
- [ ] **Performance acceptable** - Puzzle gen takes <30s for 20x20

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| **404 Not Found** | Next.js not built | `npm run build` in Dockerfile |
| **Port binding failed** | Binding to localhost not 0.0.0.0 | Check server.js hostname |
| **Python import error** | PYTHONPATH not set | Set in Dockerfile ENV |
| **Slow builds** | Recompiling NumPy/Pillow | Use prebuilt wheels |
| **OOM (out of memory)** | Large image processing | Reduce max file size |
| **Timeouts on 30x30 grids** | Solver takes >30s | Increase Railway timeout or add NFR-002 |

---

## Scaling & Performance

### Current Limits

- **Memory:** Railway default (depends on plan)
- **CPU:** 1 core (shared)
- **Concurrency:** Single Node.js process (single-threaded)
- **Disk:** 100GB ephemeral (temp files cleaned)

### Bottlenecks

1. **Solver at 30x30+** - Constraint propagation can take seconds
2. **Image processing** - Floyd-Steinberg dithering on large images
3. **PDF export** - ReportLab rendering for large grids

### Optimization Strategies

- **Cache puzzle metadata** - Avoid re-generating if params match
- **Worker threads** - Offload solver to background threads
- **Pre-compute difficulty scores** - For common grid sizes
- **Stream PDF response** - Start sending before complete

### Monitoring

Missing:
- Response time tracking
- Error rate monitoring
- Memory usage tracking
- Concurrent user limit

Recommended:
```python
# Add timing/metrics
import time
start = time.time()
puzzle = orchestrator.generate(req)
elapsed = time.time() - start
print(f"[metrics] generation_time_ms={elapsed*1000} grid_size={puzzle.size}")
```

---

## Rollback & Recovery

### Rollback Strategy

```bash
railway rollback <previous-deployment-id>
# or re-deploy previous version
git revert HEAD~1
git push origin main
# Railway rebuilds and redeploys
```

### Recovery from Crash

- Railway auto-restarts container on failure
- Logs preserved in Railway dashboard
- No persistent state (stateless design)

### Manual Recovery

```bash
# SSH into Railway container
railway shell

# Check logs
tail -f /var/log/container.log

# Restart manually
kill -9 $(pgrep -f "node server.js")
```

---

## Next Steps & Improvements

### High Priority

1. ✅ Add explicit `/health` endpoint for health checks
2. ✅ Log all requests with timing (structured logging)
3. ✅ Add API_TIMEOUT env var to prevent hanging
4. ✅ Document max file size limits

### Medium Priority

1. Multi-stage Dockerfile for faster builds
2. Separate Python/Node processes (not in one container)
3. Add `/metrics` endpoint for monitoring
4. Database layer for puzzle caching

### Low Priority

1. Kubernetes deployment (current Railway is sufficient)
2. Separate staging/production deployments
3. Automated performance testing

---

## Testing Deployment

### Local Docker

```bash
# Build locally
docker build -t nonogram-local:latest .

# Run locally
docker run -p 8080:8080 nonogram-local:latest

# Test
curl http://localhost:8080
# Should see HTML page
```

### Integration Tests

```bash
cd nonogram-web
npm run test:e2e  # Playwright tests (assumes server running)
```

### Load Testing

```bash
# Using ab (ApacheBench)
ab -n 100 -c 10 http://localhost:8080/

# Using hey
go install github.com/rakyll/hey@latest
hey -n 100 -c 10 -m POST -d '{"size":20, "density":30}' http://localhost:8080/api/generate
```

---

## Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| **Build** | ✅ Working | Single-stage; can optimize to multi-stage |
| **Runtime** | ✅ Working | Custom server handles port binding |
| **API** | ✅ Working | Handles form submission, image upload, exports |
| **Deployment** | ✅ Working | Railway auto-detects Dockerfile |
| **Error Handling** | ✅ Partial | Handles parser errors; no timeout on solver |
| **Monitoring** | ⚠️ Basic | Logs to console; no metrics |
| **Performance** | ⚠️ Good | Adequate for single user; not tested at scale |
| **Security** | ⚠️ Needs Review | No input size limits; no rate limiting |

---

**Last Updated:** 2026-09-05  
**Audience:** Deployment team, DevOps, Future maintainers  
**Next Review:** After forge:reverse drift completes
