# CodeBase AI Assistant Backend

A Flask-based backend for an AI-powered codebase assistant that analyzes codebases, detects feature impacts, and generates code changes using Claude AI.

## Features

- **Repository Management**: Connect and index GitHub repositories
- **Architecture Questions**: Ask questions about codebase architecture
- **Impact Analysis**: Analyze the impact of proposed code changes
- **Code Generation**: Generate code changes based on requirements
- **Cost Optimization**: Prompt caching to reduce API costs by 90%

## Technology Stack

- **Framework**: Flask 3.0.0
- **Database**: Supabase (PostgreSQL)
- **AI Provider**: Anthropic Claude (Haiku 4.5)
- **Code Analysis**: Python AST, NetworkX for dependency graphs

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Anthropic Claude API
ANTHROPIC_API_KEY=your_anthropic_api_key

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key

# Repository Storage
REPOS_BASE_PATH=/tmp/repositories

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379
```

### 3. Set Up Database

Run the SQL schema in `database_schema.sql` in your Supabase project to create the required tables.

### 4. Run the Application

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Repository Management

- `POST /api/repository/connect` - Connect and index a GitHub repository
- `GET /api/repository/<repo_id>` - Get repository details
- `POST /api/repository/<repo_id>/refresh` - Refresh repository index

### Chat/Questions

- `POST /api/chat/ask` - Ask a question about the codebase
- `GET /api/chat/conversation/<conv_id>` - Get conversation history
- `POST /api/chat/stream` - Stream AI response (SSE)

### Impact Analysis

- `POST /api/analysis/analyze` - Analyze impact of a proposed change
- `GET /api/analysis/<analysis_id>` - Get detailed analysis report

### Code Implementation

- `POST /api/implementation/generate` - Generate code for approved change
- `GET /api/implementation/changes/<change_id>` - Get code changes
- `POST /api/implementation/changes/<change_id>/approve` - Approve code changes
- `POST /api/implementation/changes/<change_id>/apply` - Apply code changes to repository

## Project Structure

```
codebase-ai-assistant/
├── app.py                          # Main Flask application
├── config.py                       # Configuration
├── requirements.txt                # Dependencies
├── database_schema.sql              # Database schema
├── routes/
│   ├── repository.py               # Repository management endpoints
│   ├── chat.py                     # Chat/question endpoints
│   ├── analysis.py                 # Impact analysis endpoints
│   └── implementation.py           # Code generation endpoints
├── services/
│   ├── supabase_client.py          # Database connection
│   ├── claude_service.py           # Claude AI integration
│   ├── repository_analyzer.py     # Code parsing & indexing
│   ├── impact_detector.py          # Impact analysis logic
│   ├── code_generator.py           # Code generation logic
│   └── cost_tracker.py             # Cost tracking
└── utils/
    ├── helpers.py                  # Auth decorators, utilities
    ├── ast_parser.py               # AST parsing utilities
    └── prompt_templates.py         # Claude prompt templates
```

## Implementation Notes

- **Prompt Caching**: System contexts are cached to reduce API costs by 90%
- **Cost Tracking**: All API requests are tracked with token usage and cost estimates
- **Dependency Analysis**: Uses NetworkX to build dependency graphs
- **Code Validation**: Generated code is validated for syntax errors before application

## Testing

Use Postman or Thunder Client to test the API endpoints. Example requests are provided in the route docstrings.

## Next Steps

1. Test thoroughly with the Healthcare Insurance API from Phase 1
2. Document all API endpoints with examples
3. Add authentication middleware
4. Implement rate limiting
5. Add comprehensive error handling
6. Prepare for Phase 3: Frontend development

## License

MIT

