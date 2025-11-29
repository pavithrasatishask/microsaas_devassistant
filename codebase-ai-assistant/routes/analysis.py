"""Impact analysis endpoints."""
from flask import Blueprint, request
from services.supabase_client import SupabaseClient
from services.repository_analyzer import RepositoryAnalyzer
from services.claude_service import ClaudeService
from services.impact_detector import ImpactDetector
from services.cost_tracker import CostTracker
from utils.helpers import format_error_response, format_success_response

analysis_bp = Blueprint('analysis', __name__)

# Lazy initialization - services created on first use
_supabase = None
_analyzer = None
_cost_tracker = None
_claude = None
_impact_detector = None

def get_services():
    """Get or create service instances (lazy initialization)."""
    global _supabase, _analyzer, _cost_tracker, _claude, _impact_detector
    if _supabase is None:
        _supabase = SupabaseClient()
        _analyzer = RepositoryAnalyzer(_supabase)
        _cost_tracker = CostTracker()
        _claude = ClaudeService(_cost_tracker)
        _impact_detector = ImpactDetector(_claude, _analyzer)
    return _supabase, _analyzer, _cost_tracker, _claude, _impact_detector


@analysis_bp.route('/analyze', methods=['POST'])
def analyze_change_request():
    """
    Analyze impact of a proposed change.
    
    Request:
        {
            "repo_id": 1,
            "conversation_id": 5,
            "change_description": "Add automatic claim pre-approval for amounts under $500"
        }
    
    Response:
        {
            "analysis_id": 10,
            "risk_level": "medium",
            "affected_files": [
                "services/claim_service.py",
                "routes/claims.py"
            ],
            "affected_features": [
                "Manual claim approval workflow",
                "Approval notification system"
            ],
            "warnings": [
                "Will bypass existing approval workflow for small claims",
                "May affect audit trail completeness"
            ],
            "recommendation": "Review compliance requirements before proceeding",
            "should_proceed": false,
            "requires_approval": true
        }
    """
    try:
        data = request.get_json()
        repo_id = data.get('repo_id')
        conversation_id = data.get('conversation_id')
        change_description = data.get('change_description')
        
        if not repo_id or not change_description:
            return format_error_response("repo_id and change_description are required", 400)
        
        # Get services
        supabase, analyzer, cost_tracker, claude, impact_detector = get_services()
        
        # Get repository
        repo = supabase.get_repository(repo_id)
        if not repo:
            return format_error_response(f"Repository {repo_id} not found", 404)
        
        # Get or create conversation
        if not conversation_id:
            conv = supabase.create_conversation(repo_id, title=change_description[:50])
            conversation_id = conv['id']
        
        # Get PDF documents for repository
        pdf_documents = supabase.get_repository_documents(repo_id)
        pdf_context = _build_pdf_context(pdf_documents, change_description)
        
        # Analyze impact
        repo_data = {
            'structure_json': repo.get('structure_json', {}),
            'local_path': repo.get('local_path'),
            'pdf_documents': pdf_context  # Add PDF context
        }
        
        impact_result = impact_detector.analyze_change_impact(
            change_description,
            repo_id,
            repo_data
        )
        
        # Save analysis to database
        analysis = supabase.create_impact_analysis(
            conversation_id=conversation_id,
            request_type='change_request',
            request_description=change_description,
            affected_files=impact_result.get('affected_files', []),
            affected_features=impact_result.get('affected_features', []),
            risk_level=impact_result.get('risk_level', 'medium'),
            warnings=impact_result.get('warnings', []),
            recommendation=impact_result.get('recommendation', '')
        )
        
        response = {
            'analysis_id': analysis['id'],
            'risk_level': impact_result['risk_level'],
            'affected_files': impact_result['affected_files'],
            'affected_features': impact_result['affected_features'],
            'warnings': impact_result['warnings'],
            'recommendation': impact_result['recommendation'],
            'should_proceed': impact_result.get('should_proceed', False),
            'requires_approval': impact_result.get('requires_approval', False),
            'overlaps': impact_result.get('overlaps', [])
        }
        
        return format_success_response(response)
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@analysis_bp.route('/<int:analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    """
    Get detailed analysis report.
    
    Response:
        {
            "id": 10,
            "conversation_id": 5,
            "risk_level": "medium",
            "affected_files": [...],
            ...
        }
    """
    try:
        supabase, _, _, _, _ = get_services()
        analysis = supabase.get_impact_analysis(analysis_id)
        
        if not analysis:
            return format_error_response(f"Analysis {analysis_id} not found", 404)
        
        return format_success_response(analysis)
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


def _build_pdf_context(documents: list, query: str = None) -> dict:
    """Build PDF context from repository documents."""
    if not documents:
        return {'text': '', 'summaries': []}
    
    # Filter to completed documents
    completed_docs = [d for d in documents if d.get('processing_status') == 'completed']
    
    if not completed_docs:
        return {'text': '', 'summaries': []}
    
    # Build text from summaries (to avoid token limits)
    pdf_texts = []
    summaries = []
    
    for doc in completed_docs:
        summary = doc.get('text_summary', '')
        extracted_text = doc.get('extracted_text', '')
        file_name = doc.get('file_name', 'unknown.pdf')
        
        if summary:
            pdf_texts.append(f"Document: {file_name}\n{summary}")
            summaries.append({
                'file_name': file_name,
                'summary': summary,
                'pages': doc.get('pages', 0)
            })
        elif extracted_text:
            # Use first 1000 chars if no summary
            truncated = extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text
            pdf_texts.append(f"Document: {file_name}\n{truncated}")
            summaries.append({
                'file_name': file_name,
                'summary': truncated,
                'pages': doc.get('pages', 0)
            })
    
    combined_text = "\n\n---\n\n".join(pdf_texts)
    
    return {
        'text': combined_text,
        'summaries': summaries
    }

