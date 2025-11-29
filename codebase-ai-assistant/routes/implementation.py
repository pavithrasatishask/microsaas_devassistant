"""Code implementation endpoints."""
from flask import Blueprint, request
from services.supabase_client import SupabaseClient
from services.claude_service import ClaudeService
from services.code_generator import CodeGenerator
from services.cost_tracker import CostTracker
from utils.helpers import format_error_response, format_success_response

implementation_bp = Blueprint('implementation', __name__)

# Lazy initialization - services created on first use
_supabase = None
_cost_tracker = None
_claude = None
_code_generator = None

def get_services():
    """Get or create service instances (lazy initialization)."""
    global _supabase, _cost_tracker, _claude, _code_generator
    if _supabase is None:
        _supabase = SupabaseClient()
        _cost_tracker = CostTracker()
        _claude = ClaudeService(_cost_tracker)
        _code_generator = CodeGenerator(_claude, _supabase)
    return _supabase, _cost_tracker, _claude, _code_generator


@implementation_bp.route('/generate', methods=['POST'])
def generate_code():
    """
    Generate code for approved change.
    
    Request:
        {
            "analysis_id": 10,
            "approved": true
        }
    
    Response:
        {
            "change_id": 15,
            "changes": [
                {
                    "file_path": "services/claim_service.py",
                    "action": "modify",
                    "diff": "...",
                    "explanation": "Added auto-approval logic..."
                }
            ],
            "status": "pending"
        }
    """
    try:
        data = request.get_json()
        analysis_id = data.get('analysis_id')
        approved = data.get('approved', False)
        
        if not analysis_id:
            return format_error_response("analysis_id is required", 400)
        
        if not approved:
            return format_error_response("Change must be approved before generating code", 400)
        
        # Get services
        supabase, _, _, code_generator = get_services()
        
        # Get impact analysis
        analysis = supabase.get_impact_analysis(analysis_id)
        if not analysis:
            return format_error_response(f"Analysis {analysis_id} not found", 404)
        
        # Get repository
        conversation_id = analysis.get('conversation_id')
        conv = supabase.get_conversation(conversation_id)
        if not conv:
            return format_error_response(f"Conversation not found", 404)
        
        repo_id = conv['repo_id']
        repo = supabase.get_repository(repo_id)
        if not repo:
            return format_error_response(f"Repository not found", 404)
        
        # Generate code
        requirement = analysis.get('request_description', '')
        repo_data = {
            'structure_json': repo.get('structure_json', {}),
            'local_path': repo.get('local_path')
        }
        
        generation_result = code_generator.generate_implementation(
            requirement,
            analysis,
            repo_data
        )
        
        # Save code changes to database
        change_ids = []
        for change in generation_result.get('changes', []):
            code_change = supabase.create_code_change(
                analysis_id=analysis_id,
                file_path=change['file_path'],
                original_code=change.get('original_code'),
                new_code=change.get('new_code')
            )
            change_ids.append(code_change['id'])
        
        response = {
            'change_id': change_ids[0] if change_ids else None,
            'change_ids': change_ids,
            'changes': generation_result.get('changes', []),
            'status': 'pending',
            'tokens_used': generation_result.get('tokens_used', 0),
            'cost': generation_result.get('cost', {})
        }
        
        return format_success_response(response)
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@implementation_bp.route('/changes/<int:change_id>', methods=['GET'])
def get_code_changes(change_id):
    """
    Get generated code changes.
    
    Response:
        {
            "id": 15,
            "analysis_id": 10,
            "file_path": "services/claim_service.py",
            "original_code": "...",
            "new_code": "...",
            "status": "pending"
        }
    """
    try:
        # Get services
        supabase, _, _, _ = get_services()
        
        # Get the change record
        result = supabase.client.table('code_changes').select('*').eq('id', change_id).execute()
        
        if not result.data:
            return format_error_response(f"Code change {change_id} not found", 404)
        
        change = result.data[0]
        
        # Get all changes for the same analysis
        analysis_id = change['analysis_id']
        all_changes = supabase.get_code_changes(analysis_id)
        
        return format_success_response({
            'change': change,
            'all_changes': all_changes
        })
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@implementation_bp.route('/changes/<int:change_id>/approve', methods=['POST'])
def approve_code_changes(change_id):
    """
    Approve code changes.
    
    Request:
        {
            "approved": true
        }
    """
    try:
        # Get services
        supabase, _, _, _ = get_services()
        
        data = request.get_json()
        approved = data.get('approved', False)
        
        status = 'approved' if approved else 'rejected'
        result = supabase.update_code_change_status(change_id, status)
        
        # Also update all changes for the same analysis
        change_record = supabase.client.table('code_changes').select('*').eq('id', change_id).execute()
        if change_record.data:
            analysis_id = change_record.data[0]['analysis_id']
            all_changes = supabase.get_code_changes(analysis_id)
            for change in all_changes:
                if change['id'] != change_id:
                    supabase.update_code_change_status(change['id'], status)
        
        return format_success_response({
            'change_id': change_id,
            'status': status
        })
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@implementation_bp.route('/changes/<int:change_id>/apply', methods=['POST'])
def apply_code_changes(change_id):
    """
    Apply approved code changes to repository.
    
    Response:
        {
            "success": true,
            "commit_hash": "abc123...",
            "files_modified": ["services/claim_service.py"]
        }
    """
    try:
        # Get services
        supabase, _, _, code_generator = get_services()
        
        # Get change record to find repository
        change_record = supabase.client.table('code_changes').select('*').eq('id', change_id).execute()
        if not change_record.data:
            return format_error_response(f"Code change {change_id} not found", 404)
        
        change = change_record.data[0]
        analysis_id = change['analysis_id']
        
        # Get analysis to find repository
        analysis = supabase.get_impact_analysis(analysis_id)
        if not analysis:
            return format_error_response(f"Analysis not found", 404)
        
        conversation_id = analysis.get('conversation_id')
        conv = supabase.get_conversation(conversation_id)
        if not conv:
            return format_error_response(f"Conversation not found", 404)
        
        repo_id = conv['repo_id']
        repo = supabase.get_repository(repo_id)
        if not repo or not repo.get('local_path'):
            return format_error_response(f"Repository path not found", 404)
        
        # Apply changes
        result = code_generator.apply_changes(change_id, repo['local_path'])
        
        return format_success_response(result)
    
    except ValueError as e:
        return format_error_response(str(e), 400)
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)

