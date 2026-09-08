# Admin Console Requirements Document

**Document Version**: 1.0  
**Last Updated**: 2026-09-08  
**Status**: Active  

## Executive Summary

The Admin Console is a Wave 3 feature enabling authorized users to:
1. Upload images in batch
2. Configure puzzle generation parameters
3. Generate nonogram puzzles from images
4. Review and manage generated puzzles
5. Export puzzles for book compilation

## 1. Overview & Objectives

### Purpose
Enable administrators to efficiently create and manage puzzle batches for the Christmas Nonogram Book collection without requiring technical CLI knowledge.

### Key User Journey
```
Image Upload → Configuration → Preview → Generation → Review → Approval
```

### Target Users
- Book creators/editors
- Quality reviewers
- Batch administrators
- System operators

## 2. Functional Requirements

### 2.1 Image Upload & Batch Management

#### REQ-2.1.1: Image Upload
- **Description**: Users can upload one or more images simultaneously
- **Supported Formats**: PNG, JPG, GIF, WebP
- **Constraints**:
  - Max file size: 2 MB per image
  - Max batch size: 50 images
  - Max total batch: 100 MB
- **Acceptance Criteria**:
  - System accepts multiple file selection
  - Progress indicator shows upload status
  - File type validation on client-side
  - File size validation before upload
  - Duplicate filenames handled gracefully

#### REQ-2.1.2: Batch Creation
- **Description**: System creates unique batch session for each upload
- **Data Stored**:
  - Batch ID (UUID)
  - Upload timestamp
  - User identity
  - File metadata (name, size, dimensions)
  - Processing status
- **Acceptance Criteria**:
  - Batch ID generated on upload
  - Session data persists across page navigation
  - Batch status trackable via batch ID

### 2.2 Image Preview & Configuration

#### REQ-2.2.1: Image Preview
- **Description**: Display original uploaded images before puzzle generation
- **Display Requirements**:
  - Original image shown (not modified)
  - Image dimensions displayed
  - File size information shown
  - Filename displayed
- **Acceptance Criteria**:
  - Original images display without artifacts
  - Scaling preserves aspect ratio
  - Resolution readable on screen
  - Load time < 1 second per image

#### REQ-2.2.2: Puzzle Size Configuration
- **Description**: Configure puzzle grid size for each image
- **Configuration Options**:
  - **Fixed Size**: Set exact grid dimensions (10-30 cells)
  - **Minimum Size**: Auto-scale to minimum readable size
  - **Maximum Size**: Auto-scale to maximum quality size
- **Per-Image Configuration**:
  - Apply different settings to different images
  - Override global settings for specific images
  - Show predicted output size in real-time
- **Global Settings**:
  - Apply same configuration to all images at once
  - Quick preset buttons (Small/Medium/Large)
- **Acceptance Criteria**:
  - Size range: 10×10 to 30×30 cells
  - Preview shows predicted dimensions
  - Configuration persists across pages
  - Mode switches show/hide appropriate controls

#### REQ-2.2.3: Puzzle Naming
- **Description**: Customize puzzle names for identification
- **Default**: Derived from filename (without extension)
- **Customization**:
  - Edit per-puzzle name
  - Alphanumeric + spaces allowed
  - Max 100 characters
- **Acceptance Criteria**:
  - Default name extracted correctly
  - Custom names saved and displayed
  - Special characters rejected gracefully

### 2.3 Puzzle Generation

#### REQ-2.3.1: Generation Pipeline
- **Description**: Convert images to nonogram puzzles
- **Process**:
  1. Image preprocessing (resize, threshold, binarize)
  2. Grid generation (run-length encoding)
  3. Quality scoring
  4. Difficulty calculation
  5. Puzzle storage
- **Acceptance Criteria**:
  - Generation completes within timeout (60s per image)
  - Progress tracked and reported
  - Errors captured and displayed
  - Partial failures don't block other images

#### REQ-2.3.2: Quality Filtering
- **Description**: Automatic quality assessment of generated puzzles
- **Metrics**:
  - Quality score (0-100)
  - Difficulty tier (Easy/Medium/Hard)
  - Solvability confidence
- **Filtering**:
  - Configurable minimum quality threshold
  - Puzzles below threshold excluded from output
  - User informed of rejected puzzles
- **Acceptance Criteria**:
  - Quality score calculated for each puzzle
  - Threshold filter works correctly
  - Rejected puzzles list shown
  - Filter value saved with batch

#### REQ-2.3.3: Progress Indication
- **Description**: Real-time progress feedback during generation
- **Display**:
  - Overall progress bar (0-100%)
  - Completed count ("25/50 Generated")
  - Current processing image
  - Estimated time remaining
  - Generation status (Processing/Complete)
- **Acceptance Criteria**:
  - Progress updates every 1-2 seconds
  - Accurate count tracking
  - Time estimate within ±20% accuracy
  - No blocking during progress display

### 2.4 Puzzle Review & Management

#### REQ-2.4.1: Generated Puzzles Display
- **Description**: Display generated puzzles for review and management
- **Display Format**:
  - SVG puzzle grid preview
  - Puzzle metadata (size, difficulty, quality score)
  - Source image filename
  - Generation timestamp
- **Grid Display**:
  - Cell-based SVG visualization
  - Reasonable size (200-400px display area)
  - Smooth rendering
  - No original image shown (puzzle grid only)
- **Acceptance Criteria**:
  - SVG grids render correctly
  - No broken image displays
  - All metadata shown accurately
  - Grid size appropriate for viewing

#### REQ-2.4.2: Puzzle Actions
- **Description**: Approve/reject individual puzzles
- **Actions**:
  - **Approve**: Mark puzzle as ready for book
  - **Reject**: Remove puzzle from batch
  - **View Details**: See full puzzle metadata
  - **Download SVG**: Save puzzle grid as file
- **Confirmation**:
  - Reject action requires confirmation
  - Success feedback shown
  - Database updated immediately
- **Acceptance Criteria**:
  - Approve button marks puzzle as approved
  - Reject button removes puzzle with confirmation
  - Downloads produce valid .svg files
  - Actions persist in database

#### REQ-2.4.3: Puzzle Filtering & Sorting
- **Description**: Filter and sort puzzles for efficient review
- **Filter Options**:
  - By difficulty (Easy/Medium/Hard)
  - By quality score range
  - By approval status (Approved/Rejected/Pending)
  - By source image
- **Sort Options**:
  - By quality score (ascending/descending)
  - By difficulty tier
  - By generation time
  - By source image name
- **Acceptance Criteria**:
  - Filters apply without page reload
  - Multiple filters can be combined
  - Sort preserves filters
  - Result count shown

### 2.5 Batch Summary & Export

#### REQ-2.5.1: Batch Summary
- **Description**: Overview of batch generation results
- **Summary Displays**:
  - Total images uploaded
  - Total puzzles generated
  - Puzzles approved/rejected counts
  - Average quality score
  - Difficulty distribution
  - Generation duration
- **Acceptance Criteria**:
  - All metrics calculated correctly
  - Summary updates after each action
  - Percentages shown alongside counts

#### REQ-2.5.2: Batch Export
- **Description**: Export approved puzzles for book generation
- **Export Options**:
  - JSON format (with clues, metadata)
  - CSV format (puzzle metadata only)
  - SVG archive (all puzzle grids)
  - Database export (for direct import)
- **Content**:
  - Approved puzzles only
  - Complete puzzle data (grid, clues, metadata)
  - Source image information
  - Generation metadata
- **Acceptance Criteria**:
  - Export file generated successfully
  - All approved puzzles included
  - Data integrity verified
  - Export completes within 30 seconds

## 3. Non-Functional Requirements

### 3.1 Performance

#### REQ-3.1.1: Response Times
| Operation | Target | Acceptable |
|-----------|--------|-----------|
| Page load | < 1s | < 3s |
| Image upload | < 5s | < 10s |
| Image preview | < 1s | < 2s |
| Puzzle generation (50 puzzles) | < 30s | < 60s |
| SVG rendering | < 500ms | < 1s |
| Batch export | < 30s | < 60s |

#### REQ-3.1.2: Scalability
- Support up to 50 images per batch
- Handle up to 200 puzzles per batch
- Support concurrent batch processing
- Database queries < 100ms

### 3.2 Availability & Reliability

#### REQ-3.2.1: Uptime
- Target: 99.5% uptime (admin hours)
- Graceful degradation on partial failures
- Error recovery without data loss

#### REQ-3.2.2: Error Handling
- Invalid images handled gracefully
- Network interruptions recoverable
- Partial batch failures don't block entire batch
- Clear error messages shown to user

### 3.3 Security

#### REQ-3.3.1: Authentication
- Only authenticated users can access admin console
- Session-based authentication required
- Session timeout after 30 minutes of inactivity
- HTTPS only (no HTTP)

#### REQ-3.3.2: Authorization
- Users can only see their own batches
- Admins can view all batches
- File upload restricted to admin users
- API endpoints require authentication

#### REQ-3.3.3: Data Protection
- Uploaded images stored securely
- Temporary files deleted after processing
- Database records encrypted at rest
- Access logs maintained

### 3.4 Data Integrity

#### REQ-3.4.1: Consistency
- Batch state consistent across all operations
- Database transactions atomic
- No partial uploads or corrupted data
- Rollback on generation failure

#### REQ-3.4.2: Validation
- Input validation on all forms
- File type validation
- Size constraints enforced
- Duplicate detection

## 4. UI/UX Requirements

### 4.1 Page Flow

#### REQ-4.1.1: Step-by-Step Workflow
1. **Batch Create Page**
   - File upload input
   - File selection feedback
   - Upload button
   - Cancel option

2. **Preview & Configure Page**
   - Display all uploaded images
   - Per-image configuration controls
   - Global configuration option
   - Navigation buttons (Back/Next)

3. **Generation Confirmation Page**
   - Summary of configuration
   - Confirmation checkbox
   - Generation button
   - Cancel option

4. **Processing Page**
   - Progress indicator
   - Live update of status
   - Optional: Cancel generation

5. **Review & Manage Page**
   - Generated puzzle grid display
   - Approve/Reject buttons
   - Download options
   - Filter/sort controls

### 4.2 Accessibility

#### REQ-4.2.1: WCAG Compliance
- WCAG 2.1 Level AA compliance
- Keyboard navigation support
- Screen reader compatible
- Sufficient color contrast (4.5:1 for text)
- Alternative text for images

#### REQ-4.2.2: Responsive Design
- Mobile-friendly layout (optional, lower priority)
- Tablet support
- Desktop optimized (primary focus)
- Breakpoints: 768px, 1024px, 1280px

### 4.3 User Feedback

#### REQ-4.3.1: Status Indication
- Visual feedback for all actions
- Toast notifications for results
- Loading indicators during processing
- Success/error messages clear and actionable

#### REQ-4.3.2: Form Validation
- Real-time validation feedback
- Clear error messages
- Suggested corrections
- Inline help text

## 5. API Specifications

### 5.1 Image Upload API

#### Endpoint: `POST /api/batch/from-images`
```
Request:
  - Content-Type: multipart/form-data
  - Body: one or more image files
  
Response (201 Created):
  {
    "batch_id": "uuid",
    "images": [
      {
        "file_id": "id",
        "filename": "name.png",
        "width": 800,
        "height": 600,
        "size_bytes": 12345
      }
    ],
    "created_at": "2026-09-08T12:00:00Z"
  }
```

### 5.2 Puzzle Generation API

#### Endpoint: `POST /batch/<batch_id>/generate-puzzles`
```
Request:
  {
    "size_mode": "fixed|min|max",
    "size_value": 20,
    "quality_threshold": 50
  }
  
Response (202 Accepted):
  {
    "batch_id": "uuid",
    "status": "processing",
    "puzzles_count": 50,
    "estimated_time": 25
  }
```

### 5.3 Puzzle Approve/Reject API

#### Endpoint: `POST /puzzles/<puzzle_id>/approve`
```
Request: (empty body)

Response (200 OK):
  {
    "puzzle_id": "uuid",
    "status": "approved",
    "updated_at": "2026-09-08T12:05:00Z"
  }
```

#### Endpoint: `POST /puzzles/<puzzle_id>/reject`
```
Request: (empty body)

Response (200 OK):
  {
    "puzzle_id": "uuid",
    "status": "rejected",
    "updated_at": "2026-09-08T12:05:00Z"
  }
```

### 5.4 SVG Grid API

#### Endpoint: `GET /api/puzzle/<puzzle_id>/grid`
```
Response (200 OK):
  Content-Type: image/svg+xml
  Body: SVG XML content
```

#### Endpoint: `GET /api/puzzle/<puzzle_id>/grid/download`
```
Response (200 OK):
  Content-Type: application/octet-stream
  Content-Disposition: attachment; filename="puzzle.svg"
  Body: SVG file content
```

## 6. Data Model

### 6.1 Batch Entity
```
Batch {
  id: UUID (primary key)
  user_id: UUID (foreign key)
  created_at: DateTime
  updated_at: DateTime
  status: enum (uploading, ready, generating, complete)
  total_images: Integer
  total_puzzles: Integer
  approved_count: Integer
  rejected_count: Integer
  metadata: JSON
}
```

### 6.2 Image Entity
```
Image {
  id: UUID (primary key)
  batch_id: UUID (foreign key)
  file_id: String (storage reference)
  filename: String
  original_filename: String
  width: Integer
  height: Integer
  size_bytes: Integer
  mime_type: String
  uploaded_at: DateTime
  puzzle_name: String
  size_mode: enum (fixed, min, max)
  size_value: Integer
}
```

### 6.3 Puzzle Entity
```
Puzzle {
  id: UUID (primary key)
  batch_id: UUID (foreign key)
  image_id: UUID (foreign key)
  width: Integer
  height: Integer
  grid: List[List[Bool]] (serialized)
  clues_horizontal: List[List[Int]] (serialized)
  clues_vertical: List[List[Int]] (serialized)
  difficulty_tier: enum (easy, medium, hard)
  quality_score: Float (0-100)
  source_image: String
  status: enum (generated, approved, rejected)
  created_at: DateTime
  updated_at: DateTime
}
```

## 7. Testing Requirements

### 7.1 Test Coverage
- **E2E Tests**: All 4 user flows covered
- **Unit Tests**: Core functions (image processing, grid generation)
- **Integration Tests**: Database operations, API endpoints
- **Performance Tests**: Generation time, batch processing
- **Security Tests**: Authentication, authorization, input validation

### 7.2 Test Cases (Minimum)
- Single image upload
- Batch upload (5+ images)
- Size configuration (all modes)
- Puzzle generation (small, medium, large batches)
- Approve/reject workflow
- SVG download
- Filter/sort operations
- Error scenarios (invalid files, timeouts)

### 7.3 Success Criteria
- 95%+ test pass rate
- < 0.5% flakiness
- All critical paths covered
- Performance targets met in tests

## 8. Deployment Requirements

### 8.1 Environment
- Python 3.14+
- Flask 2.3+
- PostgreSQL 13+
- Pillow for image processing
- Render.com deployment

### 8.2 Configuration
- Environment variables for:
  - Database connection
  - Storage location
  - Session timeout
  - Rate limits
  - Feature flags

### 8.3 Monitoring
- Error logging
- Performance metrics
- User activity tracking
- Batch processing logs

## 9. Success Metrics

### 9.1 Functionality
- [ ] All 4 user flows implemented
- [ ] All required APIs functional
- [ ] All test cases passing
- [ ] Zero critical bugs

### 9.2 Performance
- [ ] Page load < 1s
- [ ] Generation < 30s for 50 puzzles
- [ ] SVG rendering < 500ms
- [ ] Database queries < 100ms

### 9.3 Quality
- [ ] Code coverage > 80%
- [ ] No known security issues
- [ ] Accessibility WCAG 2.1 AA
- [ ] Documentation complete

### 9.4 User Satisfaction
- [ ] Intuitive workflow
- [ ] Clear error messages
- [ ] Responsive UI
- [ ] Feature completeness

## 10. Future Enhancements

### 10.1 Phase 2 (Post-MVP)
- Puzzle difficulty customization
- Advanced filtering/search
- Puzzle templates
- Batch scheduling
- Bulk operations

### 10.2 Phase 3 (Long-term)
- ML-based quality prediction
- Automatic puzzle optimization
- A/B testing framework
- Advanced analytics
- Integration with external APIs

## 11. Appendices

### A. Error Codes
| Code | Message | Action |
|------|---------|--------|
| 400 | Invalid file format | Show format requirements |
| 413 | File too large | Show size limit |
| 429 | Rate limit exceeded | Show retry time |
| 500 | Generation failed | Retry or contact support |
| 503 | Service unavailable | Show retry later message |

### B. Glossary
- **Batch**: Collection of images uploaded together
- **Puzzle**: Generated nonogram puzzle from image
- **Grid**: Puzzle cells (width × height)
- **Clues**: Run-length encoded hints (horizontal/vertical)
- **Quality Score**: 0-100 metric of puzzle fidelity
- **Difficulty Tier**: Easy/Medium/Hard classification
- **SVG**: Scalable Vector Graphics format for grids

### C. References
- Image Processing: `src/nonogram/sourcing/image.py`
- Grid Generation: `src/nonogram/sourcing/grid.py`
- Admin API: `src/nonogram/admin/app.py`
- Test Suite: `tests/e2e/test_admin_workflow.py`

---

**Document Approval**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | TBD | | |
| Tech Lead | TBD | | |
| QA Lead | TBD | | |

**Change Log**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-08 | Claude | Initial comprehensive requirements |
