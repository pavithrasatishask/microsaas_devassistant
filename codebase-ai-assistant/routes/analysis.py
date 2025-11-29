"""Impact analysis endpoints."""
from flask import Blueprint, request, jsonify
from services.supabase_client import SupabaseClient
from services.repository_analyzer import RepositoryAnalyzer
from services.claude_service import ClaudeService
from services.impact_detector import ImpactDetector
from services.cost_tracker import CostTracker
from utils.helpers import format_error_response, format_success_response

analysis_bp = Blueprint('analysis', __name__)

# Initialize services
supabase = SupabaseClient()
analyzer = RepositoryAnalyzer(supabase)
cost_tracker = CostTracker()
claude = ClaudeService(cost_tracker)
impact_detector = ImpactDetector(claude, analyzer)


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
        
        # Get repository
        repo = supabase.get_repository(repo_id)
        if not repo:
            return format_error_response(f"Repository {repo_id} not found", 404)
        
        # Get or create conversation
        if not conversation_id:
            conv = supabase.create_conversation(repo_id, title=change_description[:50])
            conversation_id = conv['id']
        
        # Analyze impact
        repo_data = {
            'structure_json': repo.get('structure_json', {}),
            'local_path': repo.get('local_path')
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
        analysis = supabase.get_impact_analysis(analysis_id)
        
        if not analysis:
            return format_error_response(f"Analysis {analysis_id} not found", 404)
        
        return format_success_response(analysis)
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)

