"""Prompt templates for Claude AI interactions."""

ARCHITECTURE_QUESTION_PROMPT = """You are analyzing a Flask-based Healthcare Insurance API codebase.

Repository Structure:
{repo_structure}

Relevant Files:
{relevant_files}

User Question: {question}

Please provide a clear, developer-friendly explanation that covers:
1. The relevant code components
2. How they interact
3. The data flow
4. Any important design patterns or considerations

Keep the explanation concise but comprehensive."""

IMPACT_ANALYSIS_PROMPT = """You are analyzing the impact of a proposed code change.

Current Codebase Structure:
{repo_structure}

Dependency Graph:
{dependency_graph}

Additional Documentation (PDFs):
{pdf_documents}

Proposed Change:
{change_description}

Please analyze:
1. Which files and modules will be affected?
2. Are there any existing features that overlap with this change?
3. Does this change conflict with any documented requirements or specifications?
4. What are the potential risks or conflicts?
5. What is your recommendation?

Respond in JSON format:
{{
    "affected_files": ["file1.py", "file2.py"],
    "affected_features": ["feature1", "feature2"],
    "overlaps": ["overlap description"],
    "risks": ["risk1", "risk2"],
    "risk_level": "low|medium|high|critical",
    "recommendation": "detailed recommendation"
}}"""

CODE_GENERATION_PROMPT = """You are generating code for a Flask-based Healthcare Insurance API.

Existing Code:
{existing_code}

Project Coding Standards:
- Use Flask blueprints
- Follow PEP 8
- Include type hints
- Add comprehensive docstrings
- Handle errors gracefully

Requirement:
{requirement}

Generate the necessary code changes. For each file:
1. Provide the complete modified code
2. Explain what changed and why
3. Suggest any tests that should be added

Respond in JSON format:
{{
    "changes": [
        {{
            "file_path": "path/to/file.py",
            "new_code": "complete file content",
            "explanation": "what changed and why"
        }}
    ]
}}"""

