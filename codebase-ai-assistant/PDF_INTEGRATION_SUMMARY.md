# PDF Integration - Quick Summary

## What's Changing?

Users can now upload **PDF documents** along with repository links. The system will:
1. Extract text from PDFs
2. Store PDF content
3. Use PDF content to enhance AI analysis

---

## Key Changes

### 1. Database
- **New Table**: `repository_documents` - Stores PDF metadata and extracted text
- **Updated Table**: `repositories` - Tracks document count

### 2. New Services
- **PDFProcessor**: Extracts text from PDFs
- **DocumentStorage**: Handles file uploads and storage

### 3. API Updates
- **POST /api/repository/connect**: Now accepts PDF files
- **New Endpoints**: Document management (upload, get, delete)

### 4. Workflow Integration
- **Chat/Q&A**: PDF content included in context
- **Impact Analysis**: PDF requirements checked
- **Code Generation**: PDF standards referenced

---

## Request Format

### Before (Current)
```json
POST /api/repository/connect
{
    "github_url": "https://github.com/user/repo",
    "branch": "main"
}
```

### After (With PDFs)
```http
POST /api/repository/connect
Content-Type: multipart/form-data

github_url: "https://github.com/user/repo"
branch: "main"
pdf_files: [file1.pdf, file2.pdf]  # File uploads
pdf_urls: ["https://example.com/doc.pdf"]  # URLs
```

---

## Data Flow

```
User Upload
    │
    ├─► Repository Clone (existing)
    │
    ├─► PDF Upload/Download (new)
    │   ├─► Save file
    │   ├─► Extract text
    │   └─► Store in database
    │
    ├─► Combined Context
    │   ├─► Code structure (from repo)
    │   └─► Documentation (from PDFs)
    │
    └─► AI Analysis
        ├─► Chat uses PDF context
        ├─► Analysis checks PDF requirements
        └─► Code generation follows PDF standards
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- ✅ Database schema
- ✅ PDF processing service
- ✅ File upload handling

### Phase 2: Integration (Week 2)
- ✅ Chat endpoint integration
- ✅ Analysis endpoint integration
- ✅ Code generation integration

### Phase 3: Polish (Week 3)
- ✅ Error handling
- ✅ Performance optimization
- ✅ Documentation

---

## Technical Details

### PDF Processing
- **Library**: `pdfplumber` (primary), `pypdf` (fallback)
- **Extraction**: Full text + metadata + page-by-page
- **Storage**: Summary in DB, full text in filesystem

### Storage
- **Initial**: Local filesystem (`/tmp/documents`)
- **Future**: Supabase Storage (scalable)

### Limits
- **Max PDF Size**: 50MB
- **Max Pages**: 500 pages
- **Max PDFs per Repo**: No hard limit (warn if >10)

---

## Backward Compatibility

✅ **No Breaking Changes**
- Existing JSON-only requests still work
- PDF fields are optional
- Existing repositories unaffected

---

## Dependencies to Add

```txt
pdfplumber==0.10.3
pypdf==3.17.0
Pillow==10.1.0
python-multipart==0.0.6
requests==2.31.0
```

---

## Example Use Cases

1. **Requirements Document**: Upload requirements PDF → System checks code against requirements
2. **API Documentation**: Upload API docs → System references docs in code generation
3. **Design Specs**: Upload design PDF → System validates changes against design
4. **User Guides**: Upload user guide → System answers questions using guide content

---

## Next Steps

1. Review the detailed plan: `PDF_INTEGRATION_PLAN.md`
2. Approve approach and storage strategy
3. Begin implementation starting with database migration
4. Test with sample PDFs
5. Deploy incrementally

---

**Questions?** See the full plan document for detailed implementation details.

