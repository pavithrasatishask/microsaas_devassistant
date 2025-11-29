# How to Upload PDF Files - Quick Guide

## PowerShell (Windows) - Single Line Command

```powershell
curl -X POST http://localhost:5000/api/repository/connect -F "github_url=https://github.com/pavithrasatishask/HealthcareInsuranceApp" -F "branch=main" -F "pdf_files=@C:\Users\pavithra.krishnan\Downloads\US HealthCare Knowledge Base.pdf"
```

## PowerShell (Windows) - Multi-Line (Using Backticks)

```powershell
curl -X POST http://localhost:5000/api/repository/connect `
  -F "github_url=https://github.com/pavithrasatishask/HealthcareInsuranceApp" `
  -F "branch=main" `
  -F "pdf_files=@C:\Users\pavithra.krishnan\Downloads\US HealthCare Knowledge Base.pdf"
```

## Important Notes for Windows

1. **Use Single Quotes or No Quotes for Paths with Spaces**:
   ```powershell
   # If filename has spaces, use quotes:
   -F "pdf_files=@'C:\Users\...\file name.pdf'"
   ```

2. **Escape Backslashes** (if needed):
   ```powershell
   -F "pdf_files=@C:\\Users\\...\\file.pdf"
   ```

3. **Use Forward Slashes** (alternative):
   ```powershell
   -F "pdf_files=@C:/Users/pavithra.krishnan/Downloads/US HealthCare Knowledge Base.pdf"
   ```

## Step-by-Step

### 1. Make Sure Server is Running

```powershell
# In one terminal, start the server:
python app.py
```

### 2. In Another Terminal, Run the Upload Command

```powershell
curl -X POST http://localhost:5000/api/repository/connect -F "github_url=https://github.com/pavithrasatishask/HealthcareInsuranceApp" -F "branch=main" -F "pdf_files=@C:\Users\pavithra.krishnan\Downloads\US HealthCare Knowledge Base.pdf"
```

### 3. Expected Response

```json
{
    "success": true,
    "data": {
        "repo_id": 1,
        "name": "HealthcareInsuranceApp",
        "files_indexed": 25,
        "documents_processed": 1,
        "documents": [
            {
                "id": 1,
                "file_name": "US HealthCare Knowledge Base.pdf",
                "pages": 10,
                "status": "completed"
            }
        ],
        "status": "indexed"
    }
}
```

## Alternative: Using Invoke-RestMethod (PowerShell Native)

```powershell
$uri = "http://localhost:5000/api/repository/connect"
$formData = @{
    github_url = "https://github.com/pavithrasatishask/HealthcareInsuranceApp"
    branch = "main"
    pdf_files = Get-Item "C:\Users\pavithra.krishnan\Downloads\US HealthCare Knowledge Base.pdf"
}

Invoke-RestMethod -Uri $uri -Method Post -Form $formData
```

## Troubleshooting

### Issue: "File not found"
- Check the file path is correct
- Use full absolute path
- Check file name spelling (case-sensitive)

### Issue: "Connection refused"
- Make sure Flask server is running on port 5000
- Check: `python app.py`

### Issue: "ModuleNotFoundError"
- Install dependencies: `pip install -r requirements.txt`

### Issue: "Supabase URL and KEY must be set"
- Create `.env` file with your Supabase credentials
- See `env.example` for format

---

**Quick Copy-Paste Command** (adjust file path as needed):

```powershell
curl -X POST http://localhost:5000/api/repository/connect -F "github_url=https://github.com/pavithrasatishask/HealthcareInsuranceApp" -F "branch=main" -F "pdf_files=@C:\Users\pavithra.krishnan\Downloads\US HealthCare Knowledge Base.pdf"
```

