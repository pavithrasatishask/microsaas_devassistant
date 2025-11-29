# PDF Integration Plan

## Overview

This document outlines the plan to integrate PDF document support into the CodeBase AI Assistant. Users will be able to upload PDF files along with repository links, and the system will extract and analyze PDF content to provide enhanced context for code analysis, Q&A, and impact assessment.

---

## Requirements

### User Flow
1. User provides:
   - GitHub repository URL (existing)
   - **PDF file(s)** (new) - via file upload or URL
2. System processes:
   - Repository cloning and indexing (existing)
   - **PDF text extraction and indexing** (new)
3. System uses combined context:
   - Code structure from repository
   - **Documentation/requirements from PDF** (new)
   - Combined context for AI analysis

### Use Cases
- **Requirements Documents**: PDFs containing project requirements, specifications
- **Design Documents**: Architecture diagrams, system design PDFs
- **API Documentation**: PDF documentation for APIs
- **User Guides**: PDF user manuals or guides
- **System Prompts**: PDFs containing AI system prompts or guidelines

---

## Architecture Changes

### High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│              Repository Connection Endpoint              │
│         POST /api/repository/connect                     │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│   GitHub     │ │   PDF       │ │   Combined │
│   Repo       │ │   Upload    │ │   Context  │
│   Clone      │ │   Process   │ │   Storage  │
└───────┬──────┘ └─────┬──────┘ └─────┬──────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    Repository Record         │
        │  (with PDF references)       │
        └─────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Database Schema Changes

#### New Table: `repository_documents`

```sql
CREATE TABLE repository_documents (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT REFERENCES repositories(id) ON DELETE CASCADE,
    document_type VARCHAR(50) DEFAULT 'pdf' CHECK (document_type IN ('pdf', 'docx', 'txt')),
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT,  -- Local filesystem path
    file_url TEXT,   -- If uploaded to Supabase Storage
    file_size BIGINT,  -- Size in bytes
    pages INTEGER,     -- Number of pages (for PDFs)
    extracted_text TEXT,  -- Full extracted text
    text_summary TEXT,    -- AI-generated summary
    metadata JSONB,      -- Additional metadata (author, title, etc.)
    processing_status VARCHAR(50) DEFAULT 'pending' 
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_repository_documents_repo_id ON repository_documents(repo_id);
CREATE INDEX idx_repository_documents_status ON repository_documents(processing_status);
```

#### Update `repositories` Table

```sql
ALTER TABLE repositories 
ADD COLUMN documents_count INTEGER DEFAULT 0,
ADD COLUMN has_documents BOOLEAN DEFAULT FALSE;
```

---

### Phase 2: New Services

#### 2.1 PDF Processing Service

**File**: `services/pdf_processor.py`

**Responsibilities**:
- Extract text from PDF files
- Extract metadata (title, author, pages)
- Handle different PDF formats
- Generate summaries
- Error handling for corrupted PDFs

**Key Methods**:
```python
class PDFProcessor:
    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and metadata from PDF."""
        # Returns: {
        #     'text': str,
        #     'pages': int,
        #     'metadata': dict,
        #     'page_texts': List[str]  # Text per page
        # }
    
    def extract_text_from_url(self, pdf_url: str) -> Dict[str, Any]:
        """Download and extract text from PDF URL."""
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """Generate summary using Claude (optional)."""
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """Validate PDF file integrity."""
```

**Dependencies**:
- `PyPDF2` or `pypdf` - PDF text extraction
- `pdfplumber` - Better text extraction (handles tables, formatting)
- `requests` - Download PDFs from URLs

#### 2.2 Document Storage Service

**File**: `services/document_storage.py`

**Responsibilities**:
- Handle file uploads (multipart/form-data)
- Store files locally or in Supabase Storage
- Manage file paths and URLs
- Clean up old files

**Key Methods**:
```python
class DocumentStorage:
    def save_uploaded_file(self, file, repo_id: int) -> Dict[str, Any]:
        """Save uploaded file and return path/URL."""
    
    def save_from_url(self, url: str, repo_id: int) -> Dict[str, Any]:
        """Download and save file from URL."""
    
    def get_file_path(self, doc_id: int) -> str:
        """Get local file path for document."""
    
    def delete_file(self, doc_id: int) -> bool:
        """Delete file and database record."""
```

**Storage Strategy**:
- **Option 1**: Local filesystem (similar to repositories)
  - Path: `{REPOS_BASE_PATH}/documents/{repo_id}/{filename}`
  - Pros: Simple, no additional service
  - Cons: Not scalable, backup needed

- **Option 2**: Supabase Storage (recommended)
  - Bucket: `repository-documents`
  - Path: `{repo_id}/{filename}`
  - Pros: Scalable, accessible, backup included
  - Cons: Requires Supabase Storage setup

---

### Phase 3: API Endpoint Changes

#### 3.1 Update Repository Connect Endpoint

**Current**: `POST /api/repository/connect`
- Accepts: JSON with `github_url` and `branch`

**Updated**: `POST /api/repository/connect`
- Accepts: **Multipart form data** or JSON
- New fields:
  - `pdf_files`: List of uploaded PDF files (multipart)
  - `pdf_urls`: List of PDF URLs (JSON)
  - `github_url`: Repository URL (existing)
  - `branch`: Branch name (existing)

**Request Format**:
```python
# Option 1: Multipart form data
POST /api/repository/connect
Content-Type: multipart/form-data

github_url: "https://github.com/user/repo"
branch: "main"
pdf_files: [file1.pdf, file2.pdf]  # File uploads
pdf_urls: ["https://example.com/doc1.pdf"]  # URL strings
```

**Response Format**:
```json
{
    "success": true,
    "data": {
        "repo_id": 1,
        "name": "repo-name",
        "files_indexed": 25,
        "documents_processed": 2,
        "documents": [
            {
                "id": 1,
                "file_name": "requirements.pdf",
                "pages": 10,
                "status": "completed"
            }
        ],
        "status": "indexed"
    }
}
```

#### 3.2 New Endpoints

**Add Document to Repository**:
```
POST /api/repository/<repo_id>/documents
Content-Type: multipart/form-data

pdf_file: <file>
pdf_url: "https://..." (optional)
```

**Get Repository Documents**:
```
GET /api/repository/<repo_id>/documents
```

**Get Document Content**:
```
GET /api/repository/documents/<doc_id>
```

**Delete Document**:
```
DELETE /api/repository/documents/<doc_id>
```

---

### Phase 4: Integration with Existing Workflows

#### 4.1 Chat/Q&A Integration

**File**: `routes/chat.py` - `ask_question()`

**Changes**:
- Retrieve PDF documents for repository
- Include PDF text in context sent to Claude
- Prioritize relevant PDF sections based on question

**Updated Context Building**:
```python
# In ClaudeService.analyze_architecture_question()
repo_context = {
    'structure': structure,
    'relevant_files': relevant_files,
    'documentation': pdf_texts,  # NEW: PDF content
    'pdf_summaries': pdf_summaries  # NEW: PDF summaries
}
```

#### 4.2 Impact Analysis Integration

**File**: `routes/analysis.py` - `analyze_change_request()`

**Changes**:
- Include PDF requirements/constraints in impact analysis
- Check if change conflicts with documented requirements
- Reference relevant PDF sections in warnings

**Updated Prompt**:
```python
# In ImpactDetector.analyze_change_impact()
context = {
    'repo_structure': structure,
    'dependency_graph': dependency_graph,
    'requirements_docs': pdf_requirements,  # NEW
    'design_docs': pdf_design_docs  # NEW
}
```

#### 4.3 Code Generation Integration

**File**: `services/code_generator.py` - `generate_implementation()`

**Changes**:
- Include PDF requirements in code generation prompt
- Ensure generated code follows documented standards
- Reference PDF sections in code comments

---

### Phase 5: PDF Content Processing Strategy

#### 5.1 Text Extraction

**Approach**:
1. **Full Text Extraction**: Extract all text from PDF
2. **Page-by-Page**: Store text per page for better context
3. **Metadata Extraction**: Title, author, creation date
4. **Structure Detection**: Headers, sections, lists

**Libraries**:
- Primary: `pdfplumber` (handles tables, formatting better)
- Fallback: `PyPDF2` or `pypdf` (simpler, more reliable)

#### 5.2 Text Storage

**Options**:
1. **Store in Database** (JSONB column)
   - Pros: Fast access, searchable
   - Cons: Large documents may hit size limits

2. **Store in Filesystem** (text files)
   - Pros: No size limits
   - Cons: Additional file management

3. **Hybrid** (Recommended)
   - Store summary in database
   - Store full text in filesystem
   - Cache frequently accessed pages

#### 5.3 Chunking Strategy

For large PDFs, chunk text for better AI context:
- **Page-based chunks**: Each page is a chunk
- **Section-based chunks**: Split by headers
- **Size-based chunks**: Split by token count (max 2000 tokens/chunk)

---

### Phase 6: Configuration Updates

**File**: `config.py`

**New Configuration**:
```python
class Config:
    # ... existing config ...
    
    # PDF Processing
    PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", "/tmp/documents")
    MAX_PDF_SIZE_MB = 50  # Max PDF file size
    MAX_PDF_PAGES = 500   # Max pages per PDF
    PDF_TEXT_CHUNK_SIZE = 2000  # Tokens per chunk
    
    # Supabase Storage (if using)
    SUPABASE_STORAGE_BUCKET = "repository-documents"
```

---

### Phase 7: Dependencies

**New Requirements** (`requirements.txt`):
```
# PDF Processing
pdfplumber==0.10.3  # Primary PDF text extraction
pypdf==3.17.0       # Fallback PDF library
Pillow==10.1.0      # Image processing (if PDFs contain images)

# File handling
python-multipart==0.0.6  # For Flask file uploads
requests==2.31.0          # Download PDFs from URLs
```

---

## Implementation Steps

### Step 1: Database Migration
1. Create `repository_documents` table
2. Add columns to `repositories` table
3. Create indexes

### Step 2: PDF Processing Service
1. Create `services/pdf_processor.py`
2. Implement text extraction
3. Add error handling
4. Add tests

### Step 3: Document Storage Service
1. Create `services/document_storage.py`
2. Implement file upload handling
3. Implement URL download
4. Set up storage (local or Supabase)

### Step 4: Database Client Updates
1. Add document CRUD methods to `SupabaseClient`
2. Add document retrieval methods

### Step 5: API Endpoint Updates
1. Update `POST /api/repository/connect` to accept PDFs
2. Add new document management endpoints
3. Update response formats

### Step 6: Workflow Integration
1. Update chat endpoint to include PDF context
2. Update analysis endpoint to include PDF requirements
3. Update code generation to reference PDFs

### Step 7: Testing
1. Test PDF upload
2. Test PDF text extraction
3. Test integration with existing workflows
4. Test error handling

---

## Error Handling

### PDF Processing Errors
- **Corrupted PDF**: Return error, skip file
- **Password Protected**: Return error, request password
- **Too Large**: Reject file, return size limit error
- **Unsupported Format**: Return format error

### Storage Errors
- **Disk Full**: Return storage error
- **Permission Denied**: Return permission error
- **Network Error** (URL download): Retry with exponential backoff

---

## Security Considerations

### File Upload Security
1. **File Type Validation**: Only accept `.pdf` files
2. **File Size Limits**: Enforce `MAX_PDF_SIZE_MB`
3. **Filename Sanitization**: Prevent path traversal attacks
4. **Virus Scanning**: Consider adding virus scanning (future)

### Access Control
1. **Repository Ownership**: Only repository owner can upload documents
2. **Document Access**: Documents tied to repository access
3. **URL Validation**: Validate PDF URLs before downloading

---

## Performance Considerations

### PDF Processing
- **Async Processing**: Process PDFs asynchronously for large files
- **Caching**: Cache extracted text to avoid re-processing
- **Chunking**: Process large PDFs in chunks

### Storage
- **Cleanup**: Remove old/unused documents
- **Compression**: Compress stored text files
- **CDN**: Use CDN for document URLs (if using Supabase Storage)

---

## Future Enhancements

### Phase 2 Features
1. **OCR Support**: Extract text from scanned PDFs (images)
2. **Table Extraction**: Better handling of PDF tables
3. **Image Extraction**: Extract and store images from PDFs
4. **Multi-format Support**: DOCX, TXT, Markdown
5. **Document Search**: Full-text search across PDFs
6. **Document Versioning**: Track document versions
7. **AI Summarization**: Auto-generate summaries using Claude

---

## Migration Guide

### For Existing Repositories
- Existing repositories will have `has_documents: false`
- Documents can be added later via new endpoints
- No breaking changes to existing API

### Backward Compatibility
- `POST /api/repository/connect` still works with JSON only
- PDF fields are optional
- Existing workflows continue to work without PDFs

---

## Testing Plan

### Unit Tests
- PDF text extraction
- PDF metadata extraction
- File upload handling
- Error handling

### Integration Tests
- Repository connection with PDFs
- Chat with PDF context
- Impact analysis with PDF requirements
- Code generation with PDF references

### End-to-End Tests
- Full workflow: Upload repo + PDF → Ask question → Get answer with PDF context
- Full workflow: Upload repo + PDF → Analyze change → Generate code

---

## Rollout Strategy

### Phase 1: Core Functionality (Week 1-2)
- Database schema
- PDF processing service
- Basic file upload

### Phase 2: Integration (Week 3)
- Chat integration
- Analysis integration
- Code generation integration

### Phase 3: Polish (Week 4)
- Error handling
- Performance optimization
- Documentation

---

## Questions to Resolve

1. **Storage Location**: Local filesystem vs Supabase Storage?
   - **Recommendation**: Start with local, migrate to Supabase Storage later

2. **PDF Size Limits**: What's the maximum PDF size?
   - **Recommendation**: 50MB, 500 pages

3. **Processing**: Synchronous vs Asynchronous?
   - **Recommendation**: Synchronous for small PDFs (<10MB), async for larger

4. **Text Storage**: Database vs Filesystem?
   - **Recommendation**: Hybrid - summary in DB, full text in filesystem

5. **Multiple PDFs**: How many PDFs per repository?
   - **Recommendation**: No hard limit, but warn if >10 PDFs

---

## Summary

This plan outlines a comprehensive approach to integrating PDF support:

1. **Database**: New `repository_documents` table
2. **Services**: PDF processor and document storage services
3. **API**: Updated endpoints to accept PDFs
4. **Integration**: PDF content included in all AI workflows
5. **Storage**: Local filesystem initially, Supabase Storage later
6. **Processing**: Text extraction with pdfplumber
7. **Context**: PDF content included in Claude prompts

The implementation is designed to be:
- **Non-breaking**: Existing functionality continues to work
- **Scalable**: Can handle multiple PDFs per repository
- **Extensible**: Easy to add more document types later
- **Secure**: File validation and access control

---

## Next Steps

1. **Review and Approve Plan**: Get stakeholder approval
2. **Set Up Development Environment**: Install PDF libraries
3. **Create Database Migration**: SQL scripts for schema changes
4. **Implement Core Services**: PDF processor and storage
5. **Update API Endpoints**: Add PDF support
6. **Test Integration**: Verify with sample PDFs
7. **Deploy**: Roll out to production

---

**Estimated Development Time**: 2-3 weeks
**Complexity**: Medium
**Risk Level**: Low (non-breaking changes)

