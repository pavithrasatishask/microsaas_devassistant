"""Chat/question endpoints."""
from flask import Blueprint, request
from services.supabase_client import SupabaseClient
from services.repository_analyzer import RepositoryAnalyzer
from services.claude_service import ClaudeService
from services.cost_tracker import CostTracker
from utils.helpers import format_error_response, format_success_response

chat_bp = Blueprint('chat', __name__)

# Lazy initialization - services created on first use
_supabase = None
_analyzer = None
_cost_tracker = None
_claude = None

def get_services():
    """Get or create service instances (lazy initialization)."""
    global _supabase, _analyzer, _cost_tracker, _claude
    if _supabase is None:
        _supabase = SupabaseClient()
        _analyzer = RepositoryAnalyzer(_supabase)
        _cost_tracker = CostTracker()
        _claude = ClaudeService(_cost_tracker)
    return _supabase, _analyzer, _cost_tracker, _claude


@chat_bp.route('/ask', methods=['POST'])
def ask_question():
    """
    Ask a question about the codebase.
    
    Request:
        {
            "repo_id": 1,
            "conversation_id": 5 (optional),
            "question": "How does the claims processing flow work?"
        }
    
    Response:
        {
            "conversation_id": 5,
            "message_id": 42,
            "answer": "The claims processing flow ...",
            "relevant_files": [
                "routes/claims.py",
                "services/claim_service.py"
            ],
            "tokens_used": 1250
        }
    """
    try:
        data = request.get_json()
        repo_id = data.get('repo_id')
        conversation_id = data.get('conversation_id')
        question = data.get('question')
        
        if not repo_id or not question:
            return format_error_response("repo_id and question are required", 400)
        
        # Get services
        supabase, analyzer, cost_tracker, claude = get_services()
        
        # Get repository
        repo = supabase.get_repository(repo_id)
        if not repo:
            return format_error_response(f"Repository {repo_id} not found", 404)
        
        # Get or create conversation
        if not conversation_id:
            conv = supabase.create_conversation(repo_id, title=question[:50])
            conversation_id = conv['id']
        else:
            conv = supabase.get_conversation(conversation_id)
            if not conv:
                return format_error_response(f"Conversation {conversation_id} not found", 404)
        
        # Save user message
        user_message = supabase.create_message(conversation_id, 'user', question)
        
        # Get relevant files
        relevant_files = analyzer.get_relevant_files(question, repo_id, top_k=5)
        
        # Get PDF documents for repository
        pdf_documents = supabase.get_repository_documents(repo_id)
        pdf_context = _build_pdf_context(pdf_documents, question)
        
        # Build repo context
        structure = repo.get('structure_json', {}).get('structure', {})
        repo_context = {
            'structure': structure,
            'relevant_files': relevant_files,
            'documentation': pdf_context.get('text', ''),
            'pdf_summaries': pdf_context.get('summaries', [])
        }
        
        # Get answer from Claude
        result = claude.analyze_architecture_question(question, repo_context)
        
        # Save assistant message
        assistant_message = supabase.create_message(
            conversation_id,
            'assistant',
            result['answer'],
            tokens_used=result.get('tokens_used', 0)
        )
        
        response = {
            'conversation_id': conversation_id,
            'message_id': assistant_message['id'],
            'answer': result['answer'],
            'relevant_files': result.get('relevant_files', []),
            'tokens_used': result.get('tokens_used', 0),
            'cost': result.get('cost', {})
        }
        
        return format_success_response(response)
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@chat_bp.route('/conversation/<int:conv_id>', methods=['GET'])
def get_conversation(conv_id):
    """
    Get conversation history.
    
    Response:
        {
            "id": 5,
            "repo_id": 1,
            "title": "How does...",
            "messages": [...]
        }
    """
    try:
        supabase, _, _, _ = get_services()
        conv = supabase.get_conversation(conv_id)
        if not conv:
            return format_error_response(f"Conversation {conv_id} not found", 404)
        
        messages = supabase.get_conversation_messages(conv_id)
        
        response = {
            'id': conv['id'],
            'repo_id': conv['repo_id'],
            'title': conv.get('title'),
            'messages': messages,
            'created_at': conv.get('created_at'),
            'updated_at': conv.get('updated_at')
        }
        
        return format_success_response(response)
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@chat_bp.route('/stream', methods=['POST'])
def stream_response():
    """
    Stream AI response for real-time display.
    
    Uses Server-Sent Events (SSE).
    
    Note: This is a simplified version. Full SSE implementation would require
    more complex streaming from Claude API.
    """
    try:
        data = request.get_json()
        repo_id = data.get('repo_id')
        question = data.get('question')
        
        if not repo_id or not question:
            return format_error_response("repo_id and question are required", 400)
        
        # For now, return regular response
        # Full SSE implementation would stream chunks from Claude
        return ask_question()
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)

