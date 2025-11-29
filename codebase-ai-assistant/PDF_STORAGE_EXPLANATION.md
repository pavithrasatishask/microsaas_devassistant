# PDF Storage Architecture - Detailed Explanation

## Important Clarification

**PDF files are NOT stored in the Git repository (main branch, feature branches, or any branch).**

PDFs are stored **separately** in the AI Assistant system's storage, completely independent of the Git repository.

---

## Storage Architecture

### Two Separate Systems

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Assistant System                      │
│                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐    │
│  │   Git Repository     │    │   PDF Documents       │    │
│  │   (Cloned Code)     │    │   (Separate Storage) │    │
│  └──────────────────────┘    └──────────────────────┘    │
│           │                           │                    │
│           │                           │                    │
│           └───────────┬───────────────┘                    │
│                       │                                     │
│              ┌────────▼────────┐                           │
│              │  Database Link  │                           │
│              │  (repo_id)      │                           │
│              └─────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. Repository Cloning (Existing Flow)

**What Happens:**
- User provides: `github_url` and `branch` (e.g., "main" or "feature/new-feature")
- System clones the repository to local filesystem
- Location: `{REPOS_BASE_PATH}/{repo_name}/`
- Example: `/tmp/repositories/healthcare-insurance-api/`

**This is the CODE repository - it contains:**
- Python files (.py)
- Configuration files
- README, etc.
- **This is what gets analyzed for code structure**

**Branch Handling:**
- The system checks out the specified branch (main, feature, etc.)
- It analyzes whatever code is in that branch
- The branch is just for **reading/analyzing** the code
- **No changes are made to the Git repository**

### 2. PDF Storage (New Flow)

**What Happens:**
- User uploads PDF files along with repository connection
- PDFs are saved to a **completely separate location**
- Location: `{PDF_STORAGE_PATH}/documents/{repo_id}/{filename}`
- Example: `/tmp/documents/1/requirements.pdf`

**PDFs are stored:**
- **Outside** the Git repository
- In the AI Assistant's document storage
- Linked to the repository via database (`repo_id` foreign key)
- **Never committed to Git**

---

## File System Structure

### Current Structure (Repositories Only)

```
/tmp/repositories/
├── healthcare-insurance-api/     ← Cloned Git repo
│   ├── .git/                     ← Git metadata
│   ├── routes/
│   │   └── claims.py
│   ├── services/
│   │   └── claim_service.py
│   └── README.md
└── another-repo/
    └── ...
```

### New Structure (With PDFs)

```
/tmp/repositories/
├── healthcare-insurance-api/     ← Cloned Git repo (unchanged)
│   ├── .git/
│   ├── routes/
│   └── services/
└── another-repo/
    └── ...

/tmp/documents/                    ← NEW: PDF storage (separate!)
├── 1/                            ← repo_id = 1
│   ├── requirements.pdf          ← PDF files
│   ├── design-spec.pdf
│   └── extracted_text/           ← Extracted text cache
│       ├── requirements.txt
│       └── design-spec.txt
└── 2/                            ← repo_id = 2
    └── api-docs.pdf
```

**Key Points:**
- PDFs are in `/tmp/documents/` (separate directory)
- Repositories are in `/tmp/repositories/` (unchanged)
- PDFs are organized by `repo_id`, not repository name
- **No PDFs are inside the Git repository folders**

---

## Database Relationships

### How PDFs Link to Repositories

```sql
-- Repositories table
repositories
├── id: 1
├── name: "healthcare-insurance-api"
├── github_url: "https://github.com/user/repo"
├── branch: "main"                    ← Which branch was analyzed
└── local_path: "/tmp/repositories/healthcare-insurance-api"

-- Documents table (NEW)
repository_documents
├── id: 1
├── repo_id: 1                         ← Links to repository
├── file_name: "requirements.pdf"
├── file_path: "/tmp/documents/1/requirements.pdf"  ← Separate location
└── extracted_text: "Full text content..."
```

**The Link:**
- `repository_documents.repo_id` → `repositories.id`
- This is a **database relationship**, not a file system relationship
- PDFs are stored separately but logically linked

---

## Workflow Example

### Step-by-Step: User Connects Repository with PDFs

1. **User Request:**
   ```http
   POST /api/repository/connect
   Content-Type: multipart/form-data
   
   github_url: "https://github.com/user/repo"
   branch: "main"
   pdf_files: [requirements.pdf, design.pdf]
   ```

2. **System Actions:**

   **A. Clone Repository (Existing)**
   ```
   Git clone → /tmp/repositories/repo-name/
   Checkout branch: "main"
   Analyze code structure
   Store in database
   ```

   **B. Process PDFs (New)**
   ```
   Save PDF → /tmp/documents/{repo_id}/requirements.pdf
   Extract text from PDF
   Store metadata in database
   Link to repository via repo_id
   ```

3. **Result:**
   - Repository code analyzed and stored
   - PDFs stored separately
   - Both linked in database
   - **No PDFs in Git repository**

---

## Branch Handling

### How Branches Work

**Repository Branch:**
- The `branch` parameter specifies which Git branch to analyze
- Example: `branch: "main"` or `branch: "feature/new-feature"`
- System checks out that branch and analyzes its code
- **This is for reading code, not storing PDFs**

**PDF Storage:**
- PDFs are **NOT branch-specific**
- PDFs are associated with the **repository** (repo_id)
- Same PDFs are available regardless of which branch you're analyzing
- If you analyze `main` branch, you get the same PDFs
- If you analyze `feature/new-feature` branch, you still get the same PDFs

### Example Scenario

```
Repository: healthcare-insurance-api
├── Branch: main
│   └── Code: routes/claims.py (version 1.0)
│
└── Branch: feature/new-feature
    └── Code: routes/claims.py (version 2.0)

PDFs (same for both branches):
├── requirements.pdf
└── design-spec.pdf
```

**When analyzing `main` branch:**
- Code context: routes/claims.py (v1.0)
- PDF context: requirements.pdf, design-spec.pdf

**When analyzing `feature/new-feature` branch:**
- Code context: routes/claims.py (v2.0)
- PDF context: requirements.pdf, design-spec.pdf (same PDFs)

---

## Why This Design?

### Separation of Concerns

1. **Code Repository:**
   - Managed by Git
   - Version controlled
   - Belongs to the project owner
   - We only **read** from it

2. **PDF Documents:**
   - Managed by AI Assistant
   - Not version controlled in Git
   - Supplementary information
   - Stored separately for analysis

### Benefits

✅ **No Git Pollution**: PDFs don't clutter the code repository
✅ **Flexibility**: PDFs can be updated without touching Git
✅ **Independence**: PDFs available regardless of branch
✅ **Security**: PDFs stored with proper access control
✅ **Scalability**: Can store many PDFs without affecting Git repo size

---

## Alternative: If You Want PDFs in Git

### Option A: Store PDFs in Git Repository (Not Recommended)

If you wanted PDFs in the Git repo, you would:
1. Manually commit PDFs to your repository
2. System would find them in the cloned repo
3. Extract and process them

**Problems:**
- ❌ Increases repository size
- ❌ PDFs become part of version control
- ❌ Harder to manage separately
- ❌ Requires Git access to update PDFs

### Option B: Current Design (Recommended)

PDFs stored separately:
- ✅ Clean separation
- ✅ Easy to manage
- ✅ No Git repository bloat
- ✅ Can update PDFs independently

---

## Storage Options

### Option 1: Local Filesystem (Initial Implementation)

```
Location: /tmp/documents/{repo_id}/{filename}
```

**Pros:**
- Simple to implement
- No additional services needed
- Fast access

**Cons:**
- Not scalable
- Requires backup strategy
- Single server only

### Option 2: Supabase Storage (Future)

```
Bucket: repository-documents
Path: {repo_id}/{filename}
URL: https://{project}.supabase.co/storage/v1/object/public/repository-documents/{repo_id}/{filename}
```

**Pros:**
- Scalable
- Accessible via URLs
- Built-in backup
- Multi-server support

**Cons:**
- Requires Supabase Storage setup
- Slightly more complex

---

## Summary

### Key Points

1. **PDFs are NOT in Git repositories**
   - Not in main branch
   - Not in feature branches
   - Not in any branch

2. **PDFs are stored separately**
   - In AI Assistant's document storage
   - Organized by repository ID
   - Linked via database

3. **Branch parameter is for code analysis only**
   - Determines which Git branch to analyze
   - Does not affect PDF storage
   - PDFs are repository-wide, not branch-specific

4. **Two separate storage systems**
   - `/tmp/repositories/` → Git repositories (code)
   - `/tmp/documents/` → PDF documents (separate)

### Visual Summary

```
User Upload
    │
    ├─► Repository → Cloned to /tmp/repositories/ (Git code)
    │   └─► Analyzed based on branch parameter
    │
    └─► PDFs → Stored to /tmp/documents/ (separate storage)
        └─► Linked via database (repo_id)
        
Both linked in database, but stored separately!
```

---

## Questions Answered

**Q: Will PDFs be in the main branch?**
A: No, PDFs are not in any Git branch. They're stored separately.

**Q: Will PDFs be in feature branches?**
A: No, PDFs are stored outside the Git repository entirely.

**Q: Where are PDFs actually stored?**
A: In the AI Assistant's document storage: `/tmp/documents/{repo_id}/`

**Q: How are PDFs linked to repositories?**
A: Via database foreign key: `repository_documents.repo_id` → `repositories.id`

**Q: Can I have different PDFs for different branches?**
A: Currently, PDFs are repository-wide. Branch-specific PDFs would require additional design.

---

## Future Enhancements

If you need branch-specific PDFs:
- Add `branch` column to `repository_documents` table
- Filter PDFs by branch when building context
- Store PDFs in branch-specific folders

But for now, PDFs are repository-wide and stored completely separately from Git.


