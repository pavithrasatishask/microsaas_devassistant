# Quick Start Guide

## Prerequisites

- Python 3.9 or higher
- Supabase account and project
- Anthropic Claude API key
- Git installed (for repository cloning)

## Setup Steps

### 1. Clone or Navigate to Project

```bash
cd codebase-ai-assistant
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Supabase Database

1. Go to your Supabase project
2. Navigate to SQL Editor
3. Run the SQL from `database_schema.sql` to create all tables

### 5. Configure Environment Variables

Copy `env.example` to `.env`:

```bash
# Windows
copy env.example .env

# Mac/Linux
cp env.example .env
```

Edit `.env` and fill in your credentials:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET_KEY=your-secret-key
REPOS_BASE_PATH=C:\temp\repositories  # Windows
# or
REPOS_BASE_PATH=/tmp/repositories     # Mac/Linux
```

### 6. Create Repository Storage Directory

```bash
# Windows
mkdir C:\temp\repositories

# Mac/Linux
mkdir -p /tmp/repositories
```

### 7. Run the Application

```bash
python app.py
```

The API will start on `http://localhost:5000`

## Testing the API

### 1. Connect a Repository

```bash
curl -X POST http://localhost:5000/api/repository/connect \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/your-username/your-repo",
    "branch": "main"
  }'
```

### 2. Ask a Question

```bash
curl -X POST http://localhost:5000/api/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": 1,
    "question": "How does user authentication work?"
  }'
```

### 3. Analyze Impact

```bash
curl -X POST http://localhost:5000/api/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": 1,
    "change_description": "Add email validation for user registration"
  }'
```

## Common Issues

### Issue: "Supabase URL and KEY must be set"

**Solution**: Make sure your `.env` file exists and contains valid Supabase credentials.

### Issue: "Failed to clone repository"

**Solution**: 
- Ensure the repository is public or you have proper SSH keys configured
- Check that Git is installed and accessible
- Verify the repository URL is correct

### Issue: "Claude API error"

**Solution**:
- Verify your `ANTHROPIC_API_KEY` is correct
- Check your Anthropic account has sufficient credits
- Ensure you're using a valid API key format

### Issue: Import errors

**Solution**: Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Next Steps

1. Test with your Healthcare Insurance API repository
2. Review the API endpoints in the README
3. Customize prompts in `utils/prompt_templates.py`
4. Add authentication middleware if needed
5. Set up monitoring for API costs

## Support

For issues or questions, refer to the main README.md file.

