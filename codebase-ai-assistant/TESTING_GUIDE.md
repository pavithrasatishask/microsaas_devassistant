# Backend Testing Guide - PDF Integration

## Overview

This guide shows how to test the PDF integration functionality using command-line tools (curl) or Postman. No frontend required!

---

## Prerequisites

1. **Database Migration**: Run the migration first
   ```sql
   -- In Supabase SQL Editor, run:
   \i database_migration_pdf.sql
   -- Or copy/paste the SQL from database_migration_pdf.sql
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Server**:
   ```bash
   python app.py
   ```
   Server should start on `http://localhost:5000`

4. **Prepare Test Files**:
   - Have a PDF file ready (e.g., `requirements.pdf`)
   - Know a GitHub repository URL to test with

---

## Testing Workflow

### Step 1: Connect Repository with PDF (Single Request)

This is the **main way** to test - upload repository URL and PDF in one request.

#### Using curl (Command Line)

```bash
# Test 1: Upload PDF file with repository
curl -X POST http://localhost:5000/api/repository/connect \
  -F "github_url=https://github.com/your-username/your-repo" \
  -F "branch=main" \
  -F "pdf_files=@/path/to/your/requirements.pdf"

# Example with actual file:
curl -X POST http://localhost:5000/api/repository/connect \
  -F "github_url=https://github.com/user/healthcare-api" \
  -F "branch=main" \
  -F "pdf_files=@C:\Users\YourName\Documents\requirements.pdf"
```

**Note**: The `@` symbol tells curl to upload the file. Use the full path to your PDF.

#### Using PowerShell (Windows)

```powershell
# PowerShell version
$uri = "http://localhost:5000/api/repository/connect"
$formData = @{
    github_url = "https://github.com/your-username/your-repo"
    branch = "main"
    pdf_files = Get-Item "C:\path\to\your\requirements.pdf"
}

Invoke-RestMethod -Uri $uri -Method Post -Form $formData
```

#### Expected Response

```json
{
    "success": true,
    "data": {
        "repo_id": 1,
        "name": "your-repo",
        "files_indexed": 25,
        "documents_processed": 1,
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

---

### Step 2: Connect Repository with Multiple PDFs

```bash
# Upload multiple PDFs at once
curl -X POST http://localhost:5000/api/repository/connect \
  -F "github_url=https://github.com/user/repo" \
  -F "branch=main" \
  -F "pdf_files=@requirements.pdf" \
  -F "pdf_files=@design-spec.pdf" \
  -F "pdf_files=@api-docs.pdf"
```

---

### Step 3: Connect Repository with PDF URL

If your PDF is hosted online, you can use a URL:

```bash
# Using JSON (for PDF URLs)
curl -X POST http://localhost:5000/api/repository/connect \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/user/repo",
    "branch": "main",
    "pdf_urls": [
      "https://example.com/requirements.pdf",
      "https://example.com/design.pdf"
    ]
  }'
```

---

### Step 4: Connect Repository First, Add PDFs Later

#### 4a. Connect Repository (No PDFs)

```bash
curl -X POST http://localhost:5000/api/repository/connect \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/user/repo",
    "branch": "main"
  }'
```

**Save the `repo_id` from the response!**

#### 4b. Add PDF to Existing Repository

```bash
# Replace <repo_id> with the ID from step 4a
curl -X POST http://localhost:5000/api/repository/<repo_id>/documents \
  -F "pdf_file=@requirements.pdf"

# Example:
curl -X POST http://localhost:5000/api/repository/1/documents \
  -F "pdf_file=@C:\Users\YourName\Documents\requirements.pdf"
```

---

## Testing Individual Endpoints

### 1. Get Repository Details

```bash
curl http://localhost:5000/api/repository/1
```

### 2. List All Documents for a Repository

```bash
curl http://localhost:5000/api/repository/1/documents
```

**Expected Response**:
```json
{
    "success": true,
    "data": {
        "documents": [
            {
                "id": 1,
                "repo_id": 1,
                "file_name": "requirements.pdf",
                "pages": 10,
                "processing_status": "completed",
                "text_summary": "This document outlines...",
                "created_at": "2025-01-15T10:30:00Z"
            }
        ]
    }
}
```

### 3. Get Specific Document

```bash
curl http://localhost:5000/api/repository/documents/1
```

**Expected Response**:
```json
{
    "success": true,
    "data": {
        "id": 1,
        "file_name": "requirements.pdf",
        "extracted_text": "Full text content...",
        "text_summary": "Summary...",
        "pages": 10,
        "metadata": {
            "title": "Requirements Document",
            "author": "John Doe"
        }
    }
}
```

### 4. Delete Document

```bash
curl -X DELETE http://localhost:5000/api/repository/documents/1
```

---

## Testing PDF Integration with Chat

### Step 1: Connect Repository with PDF (from above)

### Step 2: Ask a Question

```bash
curl -X POST http://localhost:5000/api/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": 1,
    "question": "What are the requirements for user authentication?"
  }'
```

**Expected**: The answer should reference content from the PDF if relevant.

---

## Testing PDF Integration with Impact Analysis

### Step 1: Connect Repository with PDF (from above)

### Step 2: Analyze a Change

```bash
curl -X POST http://localhost:5000/api/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": 1,
    "change_description": "Add email validation for user registration"
  }'
```

**Expected**: The analysis should check if the change conflicts with requirements in the PDF.

---

## Quick Test Script

Create a file `test_pdf_integration.sh` (or `.bat` for Windows):

```bash
#!/bin/bash

BASE_URL="http://localhost:5000"
REPO_URL="https://github.com/your-username/your-repo"
PDF_PATH="./test-requirements.pdf"

echo "1. Connecting repository with PDF..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/repository/connect" \
  -F "github_url=$REPO_URL" \
  -F "branch=main" \
  -F "pdf_files=@$PDF_PATH")

echo "$RESPONSE" | python -m json.tool

# Extract repo_id (requires jq or python)
REPO_ID=$(echo "$RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['data']['repo_id'])")

echo "\n2. Repository ID: $REPO_ID"
echo "\n3. Getting repository documents..."
curl -s "$BASE_URL/api/repository/$REPO_ID/documents" | python -m json.tool

echo "\n4. Testing chat with PDF context..."
curl -s -X POST "$BASE_URL/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d "{\"repo_id\": $REPO_ID, \"question\": \"What are the main requirements?\"}" \
  | python -m json.tool
```

---

## Using Postman

### Setup

1. **Create Collection**: "PDF Integration Tests"

2. **Add Request**: "Connect Repository with PDF"
   - Method: `POST`
   - URL: `http://localhost:5000/api/repository/connect`
   - Body Type: `form-data`
   - Fields:
     - `github_url`: `https://github.com/user/repo` (Text)
     - `branch`: `main` (Text)
     - `pdf_files`: Select file (File)

3. **Add Request**: "Get Repository Documents"
   - Method: `GET`
   - URL: `http://localhost:5000/api/repository/{{repo_id}}/documents`
   - Variables: Set `repo_id` in collection variables

4. **Add Request**: "Ask Question with PDF Context"
   - Method: `POST`
   - URL: `http://localhost:5000/api/chat/ask`
   - Body: `raw` JSON
   ```json
   {
     "repo_id": 1,
     "question": "What are the requirements?"
   }
   ```

---

## Testing Checklist

### Basic Functionality
- [ ] Connect repository without PDF (should work)
- [ ] Connect repository with PDF file upload
- [ ] Connect repository with PDF URL
- [ ] Connect repository with multiple PDFs
- [ ] Add PDF to existing repository
- [ ] List repository documents
- [ ] Get specific document details
- [ ] Delete document

### PDF Processing
- [ ] PDF text extraction works
- [ ] PDF metadata extracted (pages, title, etc.)
- [ ] Summary generated
- [ ] Error handling for invalid PDFs
- [ ] Error handling for too-large PDFs

### Integration
- [ ] Chat includes PDF context in answers
- [ ] Impact analysis checks PDF requirements
- [ ] PDF content appears in AI responses

### Error Cases
- [ ] Invalid PDF file (should fail gracefully)
- [ ] PDF too large (should reject)
- [ ] Invalid repository URL (should fail)
- [ ] Non-existent document ID (should return 404)

---

## Common Issues & Solutions

### Issue: "No file provided"
**Solution**: Make sure you're using `-F` for form data and `@` before file path in curl

### Issue: "PDF too large"
**Solution**: Check file size. Default limit is 50MB. Adjust in `config.py` if needed.

### Issue: "Failed to extract text"
**Solution**: PDF might be corrupted, password-protected, or image-only. Try a different PDF.

### Issue: "Repository not found"
**Solution**: Make sure the repository URL is correct and accessible.

### Issue: Connection refused
**Solution**: Make sure the Flask server is running on port 5000.

---

## Sample Test Data

### Test PDF Requirements
- **Small PDF** (< 1MB): Quick test
- **Medium PDF** (1-10MB): Normal use case
- **Large PDF** (10-50MB): Test limits
- **Multi-page PDF** (10+ pages): Test pagination
- **Image PDF** (scanned): Test OCR (if implemented)

### Test Repository
Use a public repository you have access to, or create a test repository.

---

## Expected File Locations

After uploading, PDFs are stored at:
```
{PDF_STORAGE_PATH}/{repo_id}/{filename}
```

Default: `/tmp/documents/1/requirements.pdf`

**Note**: You don't need to place files here manually. The system stores them automatically when you upload via API.

---

## Debugging

### Check Server Logs
```bash
# If running Flask with debug mode
python app.py
# Watch console for errors
```

### Check Database
```sql
-- In Supabase SQL Editor
SELECT * FROM repository_documents;
SELECT * FROM repositories WHERE has_documents = true;
```

### Check File System
```bash
# Linux/Mac
ls -la /tmp/documents/

# Windows PowerShell
Get-ChildItem C:\tmp\documents\
```

---

## Next Steps After Testing

1. **Verify PDF content in responses**: Check if chat/analysis references PDF content
2. **Test error handling**: Try invalid files, large files, etc.
3. **Performance testing**: Test with multiple large PDFs
4. **Integration testing**: Full workflow from upload to AI response

---

## Example Complete Test Flow

```bash
# 1. Start server
python app.py

# 2. In another terminal, connect repo with PDF
curl -X POST http://localhost:5000/api/repository/connect \
  -F "github_url=https://github.com/user/repo" \
  -F "branch=main" \
  -F "pdf_files=@requirements.pdf"

# 3. Note the repo_id from response (e.g., 1)

# 4. List documents
curl http://localhost:5000/api/repository/1/documents

# 5. Ask question (should use PDF context)
curl -X POST http://localhost:5000/api/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"repo_id": 1, "question": "What are the requirements?"}'

# 6. Test impact analysis
curl -X POST http://localhost:5000/api/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_id": 1, "change_description": "Add new feature"}'
```

---

**Ready to test!** Start with Step 1 above and work through the checklist.

