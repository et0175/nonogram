# API Directory

REST API reference, endpoint documentation, and integration guides.

## Contents

This directory contains:
- REST API endpoint documentation
- Request/response examples
- Authentication and authorization
- Rate limiting and quotas
- WebSocket API (if applicable)
- SDK and client library guides
- Integration examples

## API Endpoints

### Puzzle Generation
- `POST /api/puzzles/generate` - Generate a new puzzle
- `GET /api/puzzles/{id}` - Retrieve a puzzle
- `DELETE /api/puzzles/{id}` - Delete a puzzle

### Puzzle Solving
- `POST /api/puzzles/{id}/solve` - Solve a puzzle
- `GET /api/puzzles/{id}/status` - Check solving status

### Image Upload
- `POST /api/images/upload` - Upload image for puzzle generation
- `GET /api/images/{id}` - Retrieve uploaded image

### Export
- `GET /api/puzzles/{id}/export?format=json` - Export puzzle
- `GET /api/puzzles/{id}/export?format=svg` - Export as SVG
- `GET /api/puzzles/{id}/export?format=png` - Export as PNG

### Health
- `GET /health` - Health check endpoint
- `GET /diagnostics` - Diagnostic information

## Request Format

All requests should include:
```json
{
  "size": 20,
  "density": 30,
  "seed": 42,
  "format": "json"
}
```

## Response Format

Success responses:
```json
{
  "status": "success",
  "data": { /* puzzle data */ },
  "timestamp": "2026-09-05T12:00:00Z"
}
```

Error responses:
```json
{
  "status": "error",
  "message": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2026-09-05T12:00:00Z"
}
```

## Authentication

- API key authentication (header-based)
- Bearer token support
- CORS configuration for web clients

## Rate Limiting

- Standard tier: 100 requests/minute
- Premium tier: 1000 requests/minute
- Burst limit: 20 requests/second

## Error Codes

- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid auth)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `409` - Conflict (resource already exists)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `503` - Service Unavailable

## Integration Guides

### Python
```python
import requests

response = requests.post('https://api.example.com/api/puzzles/generate', 
    json={'size': 20, 'density': 30, 'seed': 42},
    headers={'Authorization': 'Bearer YOUR_TOKEN'})
puzzle = response.json()
```

### JavaScript/Node.js
```javascript
const response = await fetch('https://api.example.com/api/puzzles/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    size: 20,
    density: 30,
    seed: 42
  })
});
const puzzle = await response.json();
```

### cURL
```bash
curl -X POST https://api.example.com/api/puzzles/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"size": 20, "density": 30, "seed": 42}'
```

## Web UI Integration

The web UI (COMP-008) uses the same API endpoints. See:
- ../guides/NEXT_JS_INTEGRATION.md for frontend implementation
- ../guides/FORM_REDESIGN_COMPLETE.md for form submission

## Versioning

- Current API version: v1
- Breaking changes increment major version
- Non-breaking additions increment minor version
- Bug fixes increment patch version

## Related Documentation

- See ../deployment/ for production API setup
- See ../guides/ for feature implementation
- See ../tests/requirements.md for API specifications
- See ../reports/test-reports/ for API test results

## OpenAPI/Swagger

OpenAPI specification available at:
- Swagger UI: `/swagger-ui`
- OpenAPI JSON: `/openapi.json`
- OpenAPI YAML: `/openapi.yaml`

---
Last updated: 2026-09-05
