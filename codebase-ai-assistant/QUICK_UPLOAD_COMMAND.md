# Quick Upload Command for Windows PowerShell

## Your Exact Command (Single Line)

Copy and paste this into PowerShell:

```powershell
curl -X POST http://localhost:5000/api/repository/connect -F "github_url=https://github.com/pavithrasatishask/HealthcareInsuranceApp" -F "branch=main" -F "pdf_files=@C:\Users\pavithra.krishnan\Downloads\US HealthCare Knowledge Base.pdf"
```

## Important Notes

1. **Make sure the server is running first**:
   ```powershell
   python app.py
   ```

2. **Make sure you have a `.env` file** with Supabase credentials:
   ```env
   SUPABASE_URL=your-url
   SUPABASE_KEY=your-key
   ANTHROPIC_API_KEY=your-key
   ```

3. **File path**: Make sure the PDF file exists at that location

## Alternative: Using PowerShell's Invoke-RestMethod

If curl doesn't work, use this PowerShell native command:

```powershell
$uri = "http://localhost:5000/api/repository/connect"
$filePath = "C:\Users\pavithra.krishnan\Downloads\US HealthCare Knowledge Base.pdf"

$formData = @{
    github_url = "https://github.com/pavithrasatishask/HealthcareInsuranceApp"
    branch = "main"
    pdf_files = Get-Item $filePath
}

Invoke-RestMethod -Uri $uri -Method Post -Form $formData
```

## If You Get Supabase Error

The error about 'proxy' is a known issue. Make sure:
1. Your `.env` file is in the `codebase-ai-assistant` folder
2. Environment variables are set correctly
3. Restart the Flask server after creating/updating `.env`

