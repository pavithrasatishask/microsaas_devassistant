# CodeBase AI Assistant - Technical Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Core Workflows](#core-workflows)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Component Details](#component-details)
6. [Database Schema](#database-schema)
7. [API Endpoints](#api-endpoints)
8. [Service Layer](#service-layer)
9. [Cost Optimization](#cost-optimization)
10. [Error Handling](#error-handling)

---

## System Overview

The CodeBase AI Assistant is a Flask-based backend service that provides intelligent code analysis, impact assessment, and automated code generation for Python repositories. It integrates with Anthropic's Claude AI to provide context-aware assistance for codebase understanding and modification.

### Key Features
- **Repository Indexing**: Clone and parse GitHub repositories to build comprehensive code structure maps
- **Intelligent Q&A**: Answer questions about codebase architecture using AI-powered analysis
- **Impact Analysis**: Assess the potential impact of proposed code changes before implementation
- **Code Generation**: Automatically generate code implementations based on requirements
- **Change Management**: Track, approve, and apply code changes with full audit trail

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flask Application                        │
│                    (app.py)                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  Repository  │ │    Chat    │ │  Analysis  │ │ Implementation │
│   Routes     │ │   Routes   │ │   Routes   │ │    Routes      │
└───────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────────┘
        │              │              │              │
        └──────────────┼──────────────┼──────────────┘
                       │              │
        ┌──────────────▼──────────────▼──────────────┐
        │         Service Layer                       │
        │  ┌──────────────────────────────────────┐  │
        │  │ RepositoryAnalyzer                    │  │
        │  │ ImpactDetector                       │  │
        │  │ CodeGenerator                         │  │
        │  │ ClaudeService                         │  │
        │  │ CostTracker                           │  │
        │  └──────────────────────────────────────┘  │
        └──────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  Supabase    │ │  Claude    │ │   Git      │
│  Database    │ │    API     │ │ Repository │
└──────────────┘ └────────────┘ └────────────┘
```

### Technology Stack
- **Backend Framework**: Flask (Python)
- **Database**: Supabase (PostgreSQL)
- **AI Service**: Anthropic Claude (Haiku 4.5)
- **Version Control**: GitPython
- **Code Analysis**: AST Parser, NetworkX
- **Storage**: Local filesystem for cloned repositories

---

## Core Workflows

### Workflow 1: Repository Connection and Indexing

**Endpoint**: `POST /api/repository/connect`

**Flow Diagram**:
```
User Request
    │
    ├─► Validate GitHub URL
    │
    ├─► Clone/Update Repository
    │   ├─► Check if exists locally
    │   ├─► Clone new or pull updates
    │   └─► Checkout specified branch
    │
    ├─► Parse Repository Structure
    │   ├─► Find all Python files (*.py)
    │   ├─► Filter ignored directories
    │   ├─► Parse each file with AST
    │   │   ├─► Extract classes
    │   │   ├─► Extract functions
    │   │   ├─► Extract imports
    │   │   └─► Extract docstrings
    │   └─► Build file metadata
    │
    ├─► Build Dependency Graph
    │   ├─► Create NetworkX directed graph
    │   ├─► Add file nodes
    │   ├─► Add class/function nodes
    │   ├─► Add import edges
    │   ├─► Detect circular dependencies
    │   └─► Serialize graph structure
    │
    ├─► Store in Database
    │   ├─► Create repository record
    │   ├─► Store structure JSON
    │   ├─► Store dependency graph
    │   └─► Update last_indexed timestamp
    │
    └─► Return Response
        ├─► repo_id
        ├─► files_indexed count
        └─► status
```

**Detailed Steps**:

1. **URL Validation** (`RepositoryAnalyzer.connect_repository`)
   - Validates GitHub URL format
   - Extracts repository name from URL
   - Determines local storage path

2. **Repository Cloning** (`RepositoryAnalyzer.connect_repository`)
   - Checks if repository already exists locally
   - If exists: fetches updates, checks out branch, pulls latest
   - If new: clones repository to `REPOS_BASE_PATH/repo_name`
   - Validates repository size (max 100MB)

3. **Code Parsing** (`RepositoryAnalyzer._parse_repository`)
   - Recursively finds all `.py` files
   - Filters out: `.git`, `__pycache__`, `venv`, `env`, `node_modules`
   - For each file:
     - Uses `ast_parser.parse_python_file()` to extract:
       - Classes (name, methods, docstrings)
       - Functions (name, parameters, docstrings)
       - Imports (type, module, names)
       - File-level docstrings
   - Builds aggregated structure with:
     - `files`: List of file metadata
     - `classes`: All classes across codebase
     - `functions`: All functions across codebase
     - `imports`: All import statements
     - `files_parsed`: Count of successfully parsed files

4. **Dependency Graph Construction** (`RepositoryAnalyzer.build_dependency_graph`)
   - Creates NetworkX `DiGraph` (directed graph)
   - Adds nodes:
     - File nodes (type: 'file')
     - Class nodes (type: 'class', linked to file)
     - Function nodes (type: 'function', linked to file)
   - Adds edges:
     - File → Class/Function (type: 'contains')
     - File → File (type: 'imports', based on import statements)
   - Detects circular dependencies using `nx.simple_cycles()`
   - Serializes to JSON format with:
     - `nodes`: List of node data
     - `edges`: List of edge data
     - `circular_dependencies`: List of detected cycles

5. **Database Storage** (`SupabaseClient.create_repository`)
   - Creates record in `repositories` table
   - Stores `structure_json` as JSONB containing:
     - `structure`: Parsed code structure
     - `dependency_graph`: Graph representation
   - Updates `last_indexed` timestamp

**Data Structures**:
```python
# Repository Structure
{
    "files": [
        {
            "file_path": "routes/claims.py",
            "classes": [...],
            "functions": [...],
            "imports": [...],
            "docstring": "..."
        }
    ],
    "classes": [...],
    "functions": [...],
    "imports": [...],
    "files_parsed": 25
}

# Dependency Graph
{
    "nodes": [
        {"id": "routes/claims.py", "type": "file"},
        {"id": "routes/claims.py::ClaimService", "type": "class", "file": "routes/claims.py"}
    ],
    "edges": [
        {"source": "routes/claims.py", "target": "services/claim_service.py", "type": "imports"}
    ],
    "circular_dependencies": []
}
```

---

### Workflow 2: Codebase Question & Answer

**Endpoint**: `POST /api/chat/ask`

**Flow Diagram**:
```
User Question
    │
    ├─► Get/Create Conversation
    │   ├─► Check if conversation_id provided
    │   ├─► Create new or retrieve existing
    │   └─► Save user message to database
    │
    ├─► Find Relevant Files
    │   ├─► Get repository structure
    │   ├─► Score files by relevance
    │   │   ├─► File name matching (weight: 2.0)
    │   │   ├─► Class name matching (weight: 1.5)
    │   │   ├─► Function name matching (weight: 1.0)
    │   │   └─► Docstring matching (weight: 0.5)
    │   ├─► Sort by score
    │   └─► Return top 5 files with content
    │
    ├─► Build Repository Context
    │   ├─► Repository structure
    │   ├─► Relevant file contents
    │   └─► Documentation metadata
    │
    ├─► Call Claude AI
    │   ├─► Build cached system context
    │   │   ├─► Repository structure summary
    │   │   ├─► Relevant file contents
    │   │   └─► Project conventions
    │   ├─► Create user message with question
    │   ├─► Use prompt caching (ephemeral cache)
    │   ├─► Call Claude API
    │   └─► Track token usage and costs
    │
    ├─► Save Assistant Response
    │   ├─► Store answer in messages table
    │   └─► Record tokens_used
    │
    └─► Return Response
        ├─► conversation_id
        ├─► answer
        ├─► relevant_files
        ├─► tokens_used
        └─► cost breakdown
```

**Detailed Steps**:

1. **Conversation Management** (`routes/chat.py`)
   - If `conversation_id` provided: retrieves existing conversation
   - If not: creates new conversation with question as title
   - Saves user message to `messages` table with role='user'

2. **Relevant File Discovery** (`RepositoryAnalyzer.get_relevant_files`)
   - Retrieves repository structure from database
   - Scores each file based on query terms:
     - **File name match**: +2.0 per matching term
     - **Class name match**: +1.5 per matching term
     - **Function name match**: +1.0 per matching term
     - **Docstring match**: +0.5 per matching term
   - Sorts files by relevance score (descending)
   - Returns top 5 files with:
     - `file_path`: Relative path
     - `relevance_score`: Calculated score
     - `content`: Full file content (read from disk)

3. **Context Building** (`ClaudeService.analyze_architecture_question`)
   - Builds repository context object:
     ```python
     {
         'structure': repo_structure,
         'relevant_files': [
             {
                 'file_path': 'routes/claims.py',
                 'content': '...',
                 'relevance_score': 5.5
             }
         ],
         'documentation': ''
     }
     ```

4. **Prompt Caching** (`ClaudeService._build_cached_context`)
   - Creates cache key from repository structure hash
   - Builds system context with:
     - Repository structure summary (limited to 5000 chars)
     - Relevant file contents (limited to 2000 chars per file, max 10 files)
     - Project documentation and conventions
   - Uses `cache_control: {"type": "ephemeral"}` for Claude prompt caching
   - **Cost Savings**: Cached tokens are charged at 10% of normal rate

5. **Claude API Call** (`ClaudeService._call_claude_api`)
   - Model: `claude-haiku-4-20250514`
   - Max tokens: 4096 (from Config)
   - System message: Cached context
   - User message: Question text
   - Response: Text answer

6. **Cost Tracking** (`CostTracker.track_request`)
   - Tracks:
     - Input tokens (including cached)
     - Output tokens
     - Cache creation tokens (if first time)
   - Calculates cost based on Claude Haiku pricing
   - Returns cost breakdown

7. **Response Storage** (`SupabaseClient.create_message`)
   - Saves assistant response to `messages` table
   - Records `tokens_used` for analytics
   - Links to conversation via `conversation_id`

**Prompt Template** (`utils/prompt_templates.py`):
```
You are analyzing a Flask-based Healthcare Insurance API codebase.

Repository Structure: {repo_structure}

Relevant Files: {relevant_files}

User Question: {question}

Please provide a clear, developer-friendly explanation that covers:
1. The relevant code components
2. How they interact
3. The data flow
4. Any important design patterns or considerations
```

---

### Workflow 3: Impact Analysis

**Endpoint**: `POST /api/analysis/analyze`

**Flow Diagram**:
```
Change Request
    │
    ├─► Get Repository Data
    │   ├─► Repository structure
    │   └─► Dependency graph
    │
    ├─► Claude AI Analysis
    │   ├─► Build impact analysis prompt
    │   ├─► Include structure and dependencies
    │   ├─► Call Claude API
    │   └─► Parse JSON response
    │
    ├─► Find Affected Files
    │   ├─► Use Claude-identified files
    │   ├─► Fallback: keyword-based search
    │   └─► Expand using dependency graph
    │
    ├─► Detect Feature Overlaps
    │   ├─► Extract existing features
    │   ├─► Compare with change request
    │   └─► Identify potential conflicts
    │
    ├─► Calculate Risk Level
    │   ├─► Count affected files
    │   ├─► Check for overlaps
    │   ├─► Check if affects core modules
    │   └─► Apply risk criteria
    │
    ├─► Determine Approval Requirements
    │   ├─► Low risk: auto-proceed
    │   ├─► Medium: requires review
    │   ├─► High: requires approval
    │   └─► Critical: manual review required
    │
    ├─► Save Analysis to Database
    │   ├─► Create impact_analyses record
    │   ├─► Store affected files (JSONB)
    │   ├─► Store affected features (JSONB)
    │   ├─► Store warnings (JSONB)
    │   └─► Store risk level and recommendation
    │
    └─► Return Response
        ├─► analysis_id
        ├─► risk_level
        ├─► affected_files
        ├─► affected_features
        ├─► warnings
        ├─► recommendation
        ├─► should_proceed
        └─► requires_approval
```

**Detailed Steps**:

1. **Repository Context Retrieval** (`routes/analysis.py`)
   - Gets repository from database
   - Extracts `structure_json` containing:
     - `structure`: Code structure
     - `dependency_graph`: Graph representation

2. **Claude AI Impact Analysis** (`ClaudeService.analyze_impact`)
   - Builds prompt using `IMPACT_ANALYSIS_PROMPT` template
   - Includes:
     - Repository structure (JSON)
     - Dependency graph (JSON)
     - Change description
   - Calls Claude API with structured prompt
   - Parses JSON response (handles markdown code blocks)
   - Extracts:
     - `affected_files`: List of file paths
     - `affected_features`: List of feature names
     - `overlaps`: List of overlap descriptions
     - `risks`: List of risk descriptions
     - `risk_level`: 'low' | 'medium' | 'high' | 'critical'
     - `recommendation`: Text recommendation

3. **File Discovery** (`ImpactDetector.analyze_change_impact`)
   - Primary: Uses files identified by Claude
   - Fallback: Keyword-based search (`_find_files_by_keywords`)
     - Splits change request into keywords
     - Matches keywords against file paths
   - Expansion: Uses dependency graph (`_expand_affected_files`)
     - Finds files that import affected files
     - Traverses import relationships
     - Adds dependent files to affected list

4. **Feature Overlap Detection** (`ImpactDetector.detect_feature_overlap`)
   - Extracts existing features from structure:
     - Class names (non-private)
     - Function names (non-private)
   - Compares change request keywords with feature names
   - Identifies potential conflicts
   - Returns overlap descriptions

5. **Risk Level Calculation** (`ImpactDetector.calculate_risk_level`)
   - Factors considered:
     - **Number of affected files**:
       - Low: ≤ 2 files
       - Medium: 3-5 files
       - High: 6-10 files
       - Critical: > 10 files
     - **Has overlaps**: Boolean
     - **Affects core modules**: Checks for keywords:
       - `app.py`, `config`, `auth`, `database`, `model`, `service`
     - **Warning count**: Number of warnings from Claude
   - Risk determination logic:
     ```python
     if affects_core and warnings_count > 3:
         return 'critical'
     elif affects_core or affected_files_count > 8:
         return 'high'
     elif has_overlaps or affected_files_count > 3:
         return 'medium'
     else:
         return 'low'
     ```

6. **Approval Requirements** (`ImpactDetector.analyze_change_impact`)
   - Based on `RISK_CRITERIA`:
     - **Low**: `auto_proceed: True`, no approval needed
     - **Medium**: `requires_review: True`, review recommended
     - **High**: `requires_approval: True`, approval required
     - **Critical**: `requires_approval: True`, `manual_review_required: True`

7. **Database Storage** (`SupabaseClient.create_impact_analysis`)
   - Creates record in `impact_analyses` table
   - Stores:
     - `conversation_id`: Links to conversation
     - `request_type`: 'change_request'
     - `request_description`: Original change description
     - `affected_files`: JSONB array
     - `affected_features`: JSONB array
     - `risk_level`: Enum value
     - `warnings`: JSONB array
     - `recommendation`: Text

**Risk Criteria** (`services/impact_detector.py`):
```python
RISK_CRITERIA = {
    'low': {
        'max_affected_files': 2,
        'has_overlaps': False,
        'affects_core': False,
        'auto_proceed': True
    },
    'medium': {
        'max_affected_files': 5,
        'has_overlaps': True,
        'affects_core': False,
        'auto_proceed': False,
        'requires_review': True
    },
    'high': {
        'max_affected_files': 10,
        'has_overlaps': True,
        'affects_core': True,
        'auto_proceed': False,
        'requires_approval': True
    },
    'critical': {
        'affects_core': True,
        'breaking_changes': True,
        'auto_proceed': False,
        'requires_approval': True,
        'manual_review_required': True
    }
}
```

---

### Workflow 4: Code Generation

**Endpoint**: `POST /api/implementation/generate`

**Flow Diagram**:
```
Generate Request
    │
    ├─► Validate Analysis
    │   ├─► Check analysis_id exists
    │   ├─► Verify approved flag
    │   └─► Get impact analysis
    │
    ├─► Get Repository Context
    │   ├─► Get conversation → repository
    │   ├─► Get repository structure
    │   └─► Get local repository path
    │
    ├─► Load Existing Code
    │   ├─► Get affected files from analysis
    │   ├─► Read each file from disk
    │   └─► Build code map (file_path → content)
    │
    ├─► Generate Code with Claude
    │   ├─► Build code generation prompt
    │   ├─► Include existing code context
    │   ├─► Include requirement description
    │   ├─► Call Claude API
    │   └─► Parse JSON response
    │
    ├─► Validate Generated Code
    │   ├─► For each generated change:
    │   │   ├─► Check if Python file
    │   │   ├─► Parse with AST (syntax check)
    │   │   ├─► Check for empty code
    │   │   ├─► Validate imports
    │   │   └─► Collect errors/warnings
    │   └─► Mark valid/invalid changes
    │
    ├─► Save Code Changes
    │   ├─► For each validated change:
    │   │   ├─► Create code_changes record
    │   │   ├─► Store original_code
    │   │   ├─► Store new_code
    │   │   └─► Set status: 'pending'
    │   └─► Link to analysis_id
    │
    └─► Return Response
        ├─► change_id (first change)
        ├─► change_ids (all changes)
        ├─► changes (with validation results)
        ├─► status: 'pending'
        ├─► tokens_used
        └─► cost breakdown
```

**Detailed Steps**:

1. **Request Validation** (`routes/implementation.py`)
   - Validates `analysis_id` is provided
   - Validates `approved: true` flag
   - Retrieves impact analysis from database
   - Gets conversation and repository through analysis

2. **Code Context Loading** (`CodeGenerator.generate_implementation`)
   - Gets affected files from impact analysis
   - Reads each file from repository local path
   - Builds `existing_code_map`: `{file_path: file_content}`
   - Handles read errors gracefully (skips files)

3. **Code Generation** (`ClaudeService.generate_code`)
   - Builds prompt using `CODE_GENERATION_PROMPT` template:
     ```
     Existing Code: {existing_code}
     Requirement: {requirement}
     
     Generate code changes following:
     - Flask blueprints
     - PEP 8
     - Type hints
     - Docstrings
     - Error handling
     ```
   - Calls Claude API
   - Parses JSON response:
     ```json
     {
         "changes": [
             {
                 "file_path": "services/claim_service.py",
                 "new_code": "complete file content...",
                 "explanation": "Added auto-approval logic..."
             }
         ]
     }
     ```

4. **Code Validation** (`CodeGenerator.validate_generated_code`)
   - For each generated change:
     - **File type check**: Skip validation for non-Python files
     - **AST parsing**: Uses `ast.parse()` to check syntax
       - Catches `SyntaxError` with line numbers
       - Catches general parse errors
     - **Empty code check**: Warns if code is empty
     - **Import validation**: Checks for relative imports (`..`)
     - Returns validation result:
       ```python
       {
           'valid': True/False,
           'errors': ['error1', 'error2'],
           'warnings': ['warning1', 'warning2']
       }
       ```

5. **Change Record Creation** (`CodeGenerator.generate_implementation`)
   - For each validated change:
     - Determines action: 'modify' (file exists) or 'create' (new file)
     - Creates record in `code_changes` table:
       - `analysis_id`: Links to impact analysis
       - `file_path`: Relative path
       - `original_code`: Existing code (if any)
       - `new_code`: Generated code
       - `status`: 'pending'
   - Returns list of `change_ids`

6. **Response Format**:
   ```json
   {
       "change_id": 15,
       "change_ids": [15, 16, 17],
       "changes": [
           {
               "file_path": "services/claim_service.py",
               "action": "modify",
               "original_code": "...",
               "new_code": "...",
               "explanation": "...",
               "validation": {
                   "valid": true,
                   "errors": [],
                   "warnings": []
               }
           }
       ],
       "status": "pending",
       "tokens_used": 2500,
       "cost": {...}
   }
   ```

---

### Workflow 5: Code Change Approval and Application

**Endpoints**: 
- `POST /api/implementation/changes/<change_id>/approve`
- `POST /api/implementation/changes/<change_id>/apply`

**Flow Diagram - Approval**:
```
Approve Request
    │
    ├─► Get Code Change
    │   └─► Retrieve from database
    │
    ├─► Update Status
    │   ├─► Update change to 'approved' or 'rejected'
    │   └─► Update all related changes (same analysis)
    │
    └─► Return Response
        └─► change_id, status
```

**Flow Diagram - Application**:
```
Apply Request
    │
    ├─► Validate Change Status
    │   ├─► Get change record
    │   ├─► Check status is 'approved'
    │   └─► Get all changes for analysis
    │
    ├─► Initialize Git Repository
    │   ├─► Open repository at local_path
    │   └─► Verify git is initialized
    │
    ├─► Create Backup Branch
    │   ├─► Create branch: backup-before-apply-{change_id}
    │   └─► Checkout backup branch
    │
    ├─► Apply Changes
    │   ├─► For each approved change:
    │   │   ├─► Get file_path and new_code
    │   │   ├─► Create directory if needed
    │   │   ├─► Write new_code to file
    │   │   └─► Track modified files
    │   └─► Handle write errors
    │
    ├─► Commit Changes
    │   ├─► Stage all modified files
    │   ├─► Create commit with message
    │   └─► Get commit hash
    │
    ├─► Update Database
    │   ├─► Update all changes to status: 'applied'
    │   └─► Set applied_at timestamp
    │
    └─► Return Response
        ├─► success: true
        ├─► commit_hash
        ├─► files_modified
        └─► backup_branch
```

**Detailed Steps - Approval**:

1. **Status Update** (`routes/implementation.py`)
   - Gets change record from database
   - Updates status to 'approved' or 'rejected'
   - Finds all changes with same `analysis_id`
   - Updates all related changes to same status
   - Returns confirmation

**Detailed Steps - Application**:

1. **Pre-Application Validation** (`CodeGenerator.apply_changes`)
   - Retrieves change record
   - Validates status is 'approved'
   - Gets all changes for the analysis
   - Filters to only approved changes

2. **Git Repository Setup** (`CodeGenerator.apply_changes`)
   - Uses GitPython to open repository
   - Validates repository is initialized
   - Handles git errors

3. **Backup Branch Creation** (`CodeGenerator.apply_changes`)
   - Creates branch: `backup-before-apply-{change_id}`
   - Checks out backup branch
   - If branch exists, checks it out (handles existing branch)

4. **File Writing** (`CodeGenerator.apply_changes`)
   - For each approved change:
     - Constructs full file path: `repo_path / file_path`
     - Creates parent directories if needed (`mkdir -p`)
     - Writes `new_code` to file (UTF-8 encoding)
     - Tracks file in `files_modified` list
   - Handles write errors with descriptive messages

5. **Git Commit** (`CodeGenerator.apply_changes`)
   - Stages all modified files: `git add {files}`
   - Creates commit with message:
     ```
     Apply code changes from analysis {analysis_id}
     ```
   - Captures commit hash (`hexsha`)

6. **Database Update** (`SupabaseClient.update_code_change_status`)
   - Updates all approved changes to status: 'applied'
   - Sets `applied_at` timestamp to current time
   - Links changes to commit (via analysis_id)

7. **Response**:
   ```json
   {
       "success": true,
       "commit_hash": "abc123def456...",
       "files_modified": [
           "services/claim_service.py",
           "routes/claims.py"
       ],
       "backup_branch": "backup-before-apply-15"
   }
   ```

---

## Component Details

### RepositoryAnalyzer

**Purpose**: Clone, parse, and index GitHub repositories

**Key Methods**:
- `connect_repository(github_url, branch)`: Main entry point for repository connection
- `_parse_repository(repo_path)`: Parse all Python files using AST
- `build_dependency_graph(structure)`: Build NetworkX dependency graph
- `get_relevant_files(query, repo_id, top_k)`: Find files relevant to a query
- `refresh_repository(repo_id)`: Update existing repository

**Dependencies**:
- GitPython (`Repo`)
- NetworkX (`nx.DiGraph`)
- AST Parser (`utils.ast_parser`)

### ImpactDetector

**Purpose**: Analyze potential impact of code changes

**Key Methods**:
- `analyze_change_impact(change_request, repo_id, repo_data)`: Main analysis method
- `find_affected_modules(target_file, dependency_graph)`: Find dependent modules
- `detect_feature_overlap(change_request, existing_features)`: Detect conflicts
- `calculate_risk_level(impact_data)`: Determine risk level
- `_expand_affected_files(initial_files, dependency_graph)`: Expand file list using graph

**Risk Calculation Logic**:
- Considers: file count, overlaps, core modules, warnings
- Returns: 'low' | 'medium' | 'high' | 'critical'

### CodeGenerator

**Purpose**: Generate and apply code changes

**Key Methods**:
- `generate_implementation(requirement, impact_analysis, repo_data)`: Generate code
- `validate_generated_code(code, file_path)`: Validate syntax and structure
- `apply_changes(change_id, repo_path)`: Apply approved changes to repository

**Validation Checks**:
- Python syntax (AST parsing)
- Empty code detection
- Import validation
- File type checking

### ClaudeService

**Purpose**: Interface with Anthropic Claude API

**Key Methods**:
- `analyze_architecture_question(question, repo_context)`: Answer questions
- `analyze_impact(change_request, repo_context)`: Analyze change impact
- `generate_code(requirement, context)`: Generate code implementations
- `_build_cached_context(repo_structure, relevant_files)`: Build cached prompts
- `_call_claude_api(messages, system, stream)`: Make API calls

**Cost Optimization**:
- Prompt caching with `cache_control: {"type": "ephemeral"}`
- Cached tokens charged at 10% rate
- Context reuse across requests

### SupabaseClient

**Purpose**: Database operations wrapper

**Key Methods**:
- Repository: `create_repository`, `get_repository`, `update_repository`
- Conversation: `create_conversation`, `get_conversation`, `get_conversation_messages`
- Messages: `create_message`
- Impact Analysis: `create_impact_analysis`, `get_impact_analysis`
- Code Changes: `create_code_change`, `get_code_changes`, `update_code_change_status`

### CostTracker

**Purpose**: Track API usage and costs

**Features**:
- Token counting (input, output, cached)
- Cost calculation based on Claude Haiku pricing
- Request tracking

---

## Database Schema

### Tables

#### `repositories`
- `id`: BIGSERIAL PRIMARY KEY
- `name`: VARCHAR(255) - Repository name
- `github_url`: TEXT - GitHub repository URL
- `branch`: VARCHAR(100) - Branch name (default: 'main')
- `local_path`: TEXT - Local filesystem path
- `last_indexed`: TIMESTAMP - Last indexing timestamp
- `structure_json`: JSONB - Code structure and dependency graph
- `created_at`: TIMESTAMP
- `updated_at`: TIMESTAMP

#### `conversations`
- `id`: BIGSERIAL PRIMARY KEY
- `repo_id`: BIGINT REFERENCES repositories(id)
- `title`: VARCHAR(255) - Conversation title
- `created_at`: TIMESTAMP
- `updated_at`: TIMESTAMP

#### `messages`
- `id`: BIGSERIAL PRIMARY KEY
- `conversation_id`: BIGINT REFERENCES conversations(id)
- `role`: VARCHAR(50) - 'user' | 'assistant'
- `content`: TEXT - Message content
- `tokens_used`: INTEGER - Token count
- `created_at`: TIMESTAMP

#### `impact_analyses`
- `id`: BIGSERIAL PRIMARY KEY
- `conversation_id`: BIGINT REFERENCES conversations(id)
- `request_type`: VARCHAR(100) - Type of request
- `request_description`: TEXT - Change description
- `affected_files`: JSONB - Array of file paths
- `affected_features`: JSONB - Array of feature names
- `risk_level`: VARCHAR(50) - 'low' | 'medium' | 'high' | 'critical'
- `warnings`: JSONB - Array of warning messages
- `recommendation`: TEXT - AI recommendation
- `created_at`: TIMESTAMP

#### `code_changes`
- `id`: BIGSERIAL PRIMARY KEY
- `analysis_id`: BIGINT REFERENCES impact_analyses(id)
- `file_path`: TEXT - Relative file path
- `original_code`: TEXT - Original file content
- `new_code`: TEXT - Generated code
- `status`: VARCHAR(50) - 'pending' | 'approved' | 'rejected' | 'applied'
- `applied_at`: TIMESTAMP - When change was applied
- `created_at`: TIMESTAMP

### Relationships

```
repositories (1) ──< (many) conversations
conversations (1) ──< (many) messages
conversations (1) ──< (many) impact_analyses
impact_analyses (1) ──< (many) code_changes
```

### Indexes

- `idx_repositories_name`: On `repositories(name)`
- `idx_conversations_repo_id`: On `conversations(repo_id)`
- `idx_messages_conversation_id`: On `messages(conversation_id)`
- `idx_impact_analyses_conversation_id`: On `impact_analyses(conversation_id)`
- `idx_code_changes_analysis_id`: On `code_changes(analysis_id)`

---

## API Endpoints

### Repository Endpoints

#### `POST /api/repository/connect`
Connect and index a GitHub repository.

**Request**:
```json
{
    "github_url": "https://github.com/user/repo",
    "branch": "main"
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "repo_id": 1,
        "name": "repo-name",
        "files_indexed": 25,
        "status": "indexed"
    }
}
```

#### `GET /api/repository/<repo_id>`
Get repository details and structure.

**Response**:
```json
{
    "success": true,
    "data": {
        "id": 1,
        "name": "repo-name",
        "github_url": "...",
        "branch": "main",
        "structure": {...},
        "dependency_graph": {...},
        "last_indexed": "2025-01-15T10:30:00Z"
    }
}
```

#### `POST /api/repository/<repo_id>/refresh`
Refresh repository (pull latest and re-index).

### Chat Endpoints

#### `POST /api/chat/ask`
Ask a question about the codebase.

**Request**:
```json
{
    "repo_id": 1,
    "conversation_id": 5,  // optional
    "question": "How does user authentication work?"
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "conversation_id": 5,
        "message_id": 42,
        "answer": "The authentication system...",
        "relevant_files": ["routes/auth.py", "services/auth_service.py"],
        "tokens_used": 1250,
        "cost": {
            "input_tokens": 1000,
            "output_tokens": 250,
            "cached_tokens": 500,
            "total_cost": 0.0125
        }
    }
}
```

#### `GET /api/chat/conversation/<conv_id>`
Get conversation history.

### Analysis Endpoints

#### `POST /api/analysis/analyze`
Analyze impact of a proposed change.

**Request**:
```json
{
    "repo_id": 1,
    "conversation_id": 5,  // optional
    "change_description": "Add automatic claim pre-approval for amounts under $500"
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "analysis_id": 10,
        "risk_level": "medium",
        "affected_files": ["services/claim_service.py", "routes/claims.py"],
        "affected_features": ["Manual claim approval workflow"],
        "warnings": ["Will bypass existing approval workflow"],
        "recommendation": "Review compliance requirements",
        "should_proceed": false,
        "requires_approval": true
    }
}
```

#### `GET /api/analysis/<analysis_id>`
Get detailed analysis report.

### Implementation Endpoints

#### `POST /api/implementation/generate`
Generate code for approved change.

**Request**:
```json
{
    "analysis_id": 10,
    "approved": true
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "change_id": 15,
        "change_ids": [15, 16],
        "changes": [
            {
                "file_path": "services/claim_service.py",
                "action": "modify",
                "original_code": "...",
                "new_code": "...",
                "explanation": "Added auto-approval logic",
                "validation": {
                    "valid": true,
                    "errors": [],
                    "warnings": []
                }
            }
        ],
        "status": "pending",
        "tokens_used": 2500,
        "cost": {...}
    }
}
```

#### `GET /api/implementation/changes/<change_id>`
Get code changes.

#### `POST /api/implementation/changes/<change_id>/approve`
Approve or reject code changes.

**Request**:
```json
{
    "approved": true
}
```

#### `POST /api/implementation/changes/<change_id>/apply`
Apply approved changes to repository.

**Response**:
```json
{
    "success": true,
    "data": {
        "success": true,
        "commit_hash": "abc123...",
        "files_modified": ["services/claim_service.py"],
        "backup_branch": "backup-before-apply-15"
    }
}
```

---

## Cost Optimization

### Prompt Caching Strategy

The system uses Claude's prompt caching feature to reduce costs by up to 90%.

**Implementation**:
1. **Cache Key Generation**: Hash of repository structure JSON
2. **Cached Context**: System message with repository structure and conventions
3. **Cache Control**: `{"type": "ephemeral"}` - cached for conversation duration
4. **Cost Savings**: Cached tokens charged at 10% of normal rate

**Example**:
- First request: 1000 input tokens (full price)
- Subsequent requests: 1000 input tokens (100 cached @ 10%, 900 @ full)
- Savings: ~90% on cached portion

### Token Management

- **Model**: Claude Haiku 4.5 (cost-efficient)
- **Max Tokens**: 4096 per request (Config.MAX_TOKENS_PER_REQUEST)
- **Context Limits**: 
  - Repository structure: 5000 chars
  - File contents: 2000 chars per file, max 10 files
- **Tracking**: All requests tracked via `CostTracker`

---

## Error Handling

### Error Response Format

All errors follow consistent format:
```json
{
    "success": false,
    "error": "Error message",
    "status_code": 400
}
```

### Error Types

1. **Validation Errors** (400)
   - Missing required fields
   - Invalid data formats
   - Business rule violations

2. **Not Found Errors** (404)
   - Repository not found
   - Conversation not found
   - Analysis not found

3. **Internal Errors** (500)
   - Database connection issues
   - Claude API errors
   - File system errors
   - Git operation failures

### Error Handling Strategy

- **Try-Except Blocks**: All route handlers wrapped
- **Graceful Degradation**: Partial failures handled (e.g., skip unparseable files)
- **Descriptive Messages**: Clear error messages for debugging
- **Status Codes**: Appropriate HTTP status codes

---

## Security Considerations

### Current Implementation

1. **Environment Variables**: Sensitive data (API keys) in `.env`
2. **CORS**: Enabled for all origins (should be restricted in production)
3. **Input Validation**: Basic validation on all endpoints
4. **Path Traversal**: File paths validated against repository root

### Recommendations for Production

1. **Authentication**: Add JWT-based authentication
2. **Authorization**: Role-based access control
3. **Rate Limiting**: Prevent API abuse
4. **Input Sanitization**: Enhanced validation and sanitization
5. **CORS**: Restrict to specific origins
6. **Repository Access**: Validate repository ownership/permissions
7. **File System**: Sandbox repository operations
8. **API Keys**: Rotate keys regularly, use secrets management

---

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading**: Repository structure loaded on demand
2. **Caching**: Prompt caching for Claude API
3. **Batch Operations**: Multiple changes processed together
4. **Indexing**: Database indexes on foreign keys
5. **File Size Limits**: Max repository size (100MB)

### Scalability

- **Horizontal Scaling**: Stateless Flask app can scale horizontally
- **Database**: Supabase PostgreSQL can scale
- **File Storage**: Consider cloud storage for large repositories
- **Queue System**: Consider async processing for large operations

---

## Future Enhancements

### Potential Improvements

1. **Streaming Responses**: Real-time SSE for long operations
2. **Incremental Indexing**: Only re-parse changed files
3. **Advanced Search**: Semantic search using embeddings
4. **Test Generation**: Automatic test case generation
5. **Code Review**: Automated code review suggestions
6. **Multi-Language Support**: Beyond Python
7. **Webhook Integration**: GitHub webhooks for auto-refresh
8. **Analytics Dashboard**: Usage and cost analytics

---

## Conclusion

This technical documentation provides a comprehensive overview of the CodeBase AI Assistant system, covering all major workflows, components, and implementation details. The system is designed to be modular, scalable, and cost-efficient while providing powerful code analysis and generation capabilities.

For questions or contributions, refer to the main README.md file.


