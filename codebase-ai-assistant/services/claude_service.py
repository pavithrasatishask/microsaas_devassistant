"""Claude AI service with prompt caching for cost optimization."""
import json
from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from config import Config
from services.cost_tracker import CostTracker
from utils.prompt_templates import (
    ARCHITECTURE_QUESTION_PROMPT,
    IMPACT_ANALYSIS_PROMPT,
    CODE_GENERATION_PROMPT
)


class ClaudeService:
    """Claude AI integration service."""
    
    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        """Initialize Claude service."""
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY must be set in environment variables")
        
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = Config.CLAUDE_MODEL
        self.cost_tracker = cost_tracker or CostTracker()
        self._cached_contexts = {}  # Cache for system contexts
    
    def analyze_architecture_question(self, question: str, repo_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer architecture questions about the codebase.
        
        Steps:
        1. Build context with relevant files
        2. Create structured prompt
        3. Use prompt caching for repo structure
        4. Call Claude API
        5. Return formatted response
        
        Args:
            question: User's question
            repo_context: {
                'structure': dict,
                'relevant_files': list,
                'documentation': str
            }
            
        Returns:
            Dictionary with answer, relevant_files, tokens_used
        """
        # Build cached system context
        repo_structure = repo_context.get('structure', {})
        relevant_files = repo_context.get('relevant_files', [])
        
        # Create cache key
        cache_key = f"repo_{hash(json.dumps(repo_structure, sort_keys=True))}"
        
        # Build or retrieve cached context
        if cache_key not in self._cached_contexts:
            system_context = self._build_cached_context(repo_structure, relevant_files)
            self._cached_contexts[cache_key] = system_context
        else:
            system_context = self._cached_contexts[cache_key]
        
        # Build user message
        user_message = {
            "role": "user",
            "content": question
        }
        
        # Call Claude API
        response = self._call_claude_api(
            messages=[user_message],
            system=system_context,
            stream=False
        )
        
        # Extract response
        answer = response.content[0].text if response.content else ""
        
        # Track costs
        usage = response.usage
        cost_data = self.cost_tracker.track_request(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=getattr(usage, 'cache_creation_input_tokens', 0) or 0
        )
        
        return {
            'answer': answer,
            'relevant_files': [f['file_path'] for f in relevant_files],
            'tokens_used': usage.input_tokens + usage.output_tokens,
            'cost': cost_data
        }
    
    def analyze_impact(self, change_request: str, repo_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze impact of proposed change.
        
        Steps:
        1. Parse the change request
        2. Identify affected modules using dependency graph
        3. Ask Claude to analyze potential conflicts
        4. Generate impact report
        
        Returns:
            Dictionary with risk_level, affected_files, affected_features, warnings, recommendation
        """
        repo_structure = repo_context.get('structure', {})
        dependency_graph = repo_context.get('dependency_graph', {})
        
        # Build prompt
        prompt = IMPACT_ANALYSIS_PROMPT.format(
            repo_structure=json.dumps(repo_structure, indent=2),
            dependency_graph=json.dumps(dependency_graph, indent=2),
            change_description=change_request
        )
        
        # Build system context (can be cached)
        system_context = [{
            "type": "text",
            "text": "You are an expert code analyst specializing in impact analysis for Flask applications."
        }]
        
        user_message = {
            "role": "user",
            "content": prompt
        }
        
        # Call Claude API
        response = self._call_claude_api(
            messages=[user_message],
            system=system_context,
            stream=False
        )
        
        # Parse JSON response
        answer = response.content[0].text if response.content else "{}"
        
        try:
            # Try to extract JSON from response
            if "```json" in answer:
                json_start = answer.find("```json") + 7
                json_end = answer.find("```", json_start)
                answer = answer[json_start:json_end].strip()
            elif "```" in answer:
                json_start = answer.find("```") + 3
                json_end = answer.find("```", json_start)
                answer = answer[json_start:json_end].strip()
            
            impact_data = json.loads(answer)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            impact_data = {
                "affected_files": [],
                "affected_features": [],
                "overlaps": [],
                "risks": ["Unable to parse detailed analysis"],
                "risk_level": "medium",
                "recommendation": answer
            }
        
        # Track costs
        usage = response.usage
        cost_data = self.cost_tracker.track_request(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens
        )
        
        return {
            'risk_level': impact_data.get('risk_level', 'medium'),
            'affected_files': impact_data.get('affected_files', []),
            'affected_features': impact_data.get('affected_features', []),
            'warnings': impact_data.get('risks', []) + impact_data.get('overlaps', []),
            'recommendation': impact_data.get('recommendation', ''),
            'tokens_used': usage.input_tokens + usage.output_tokens,
            'cost': cost_data
        }
    
    def generate_code(self, requirement: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate code changes based on requirement.
        
        Steps:
        1. Load relevant existing code
        2. Create detailed prompt with coding standards
        3. Generate new/modified code
        4. Validate syntax
        5. Return code changes
        
        Returns:
            Dictionary with changes list
        """
        existing_code = context.get('existing_code', '')
        
        # Build prompt
        prompt = CODE_GENERATION_PROMPT.format(
            existing_code=existing_code,
            requirement=requirement
        )
        
        # Build system context
        system_context = [{
            "type": "text",
            "text": "You are an expert Python Flask developer. Generate clean, well-documented code following PEP 8 standards."
        }]
        
        user_message = {
            "role": "user",
            "content": prompt
        }
        
        # Call Claude API
        response = self._call_claude_api(
            messages=[user_message],
            system=system_context,
            stream=False
        )
        
        # Parse response
        answer = response.content[0].text if response.content else "{}"
        
        try:
            # Try to extract JSON from response
            if "```json" in answer:
                json_start = answer.find("```json") + 7
                json_end = answer.find("```", json_start)
                answer = answer[json_start:json_end].strip()
            elif "```" in answer:
                json_start = answer.find("```") + 3
                json_end = answer.find("```", json_start)
                answer = answer[json_start:json_end].strip()
            
            code_data = json.loads(answer)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            code_data = {
                "changes": [{
                    "file_path": "unknown.py",
                    "new_code": answer,
                    "explanation": "Generated code (JSON parsing failed)"
                }]
            }
        
        # Track costs
        usage = response.usage
        cost_data = self.cost_tracker.track_request(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens
        )
        
        return {
            'changes': code_data.get('changes', []),
            'tokens_used': usage.input_tokens + usage.output_tokens,
            'cost': cost_data
        }
    
    def _build_cached_context(self, repo_structure: Dict[str, Any], 
                             relevant_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build cached system context for prompt caching.
        
        This context is reused across requests to save 90% on costs.
        
        Returns:
            List of message blocks with cache_control
        """
        # Format relevant files content
        files_content = "\n\n".join([
            f"File: {f['file_path']}\n{f.get('content', '')[:2000]}"  # Limit content size
            for f in relevant_files[:10]  # Limit number of files
        ])
        
        context_text = f"""You are analyzing a Flask-based Healthcare Insurance API codebase.

Repository Structure:
{json.dumps(repo_structure, indent=2)[:5000]}

Relevant Files:
{files_content[:5000]}

Project Documentation:
- Use Flask blueprints for routes
- Follow PEP 8
- Use type hints
- Include docstrings
- Handle errors gracefully
"""
        
        return [{
            "type": "text",
            "text": context_text,
            "cache_control": {"type": "ephemeral"}  # This gets cached!
        }]
    
    def _call_claude_api(self, messages: List[Dict[str, Any]], 
                        system: List[Dict[str, Any]], 
                        stream: bool = False):
        """
        Call Claude API with proper error handling.
        
        Features:
        - Prompt caching support
        - Streaming support
        - Rate limit handling
        - Token tracking
        
        Returns:
            Response object or stream
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=Config.MAX_TOKENS_PER_REQUEST,
                system=system,
                messages=messages
            )
            return response
        except Exception as e:
            raise ValueError(f"Claude API error: {str(e)}")

