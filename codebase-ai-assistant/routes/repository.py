"""Repository management endpoints."""
from flask import Blueprint, request, jsonify
from services.supabase_client import SupabaseClient
from services.repository_analyzer import RepositoryAnalyzer
from utils.helpers import format_error_response, format_success_response

repository_bp = Blueprint('repository', __name__)

# Initialize services
supabase = SupabaseClient()
analyzer = RepositoryAnalyzer(supabase)


@repository_bp.route('/connect', methods=['POST'])
def connect_repository():
    """
    Connect and index a GitHub repository.
    
    Request:
        {
            "github_url": "https://github.com/user/repo",
            "branch": "main"
        }
    
    Response:
        {
            "repo_id": 1,
            "name": "healthcare-insurance-api",
            "files_indexed": 25,
            "status": "indexed"
        }
    """
    try:
        data = request.get_json()
        github_url = data.get('github_url')
        branch = data.get('branch', 'main')
        
        if not github_url:
            return format_error_response("github_url is required", 400)
        
        result = analyzer.connect_repository(github_url, branch)
        return format_success_response(result, 201)
    
    except ValueError as e:
        return format_error_response(str(e), 400)
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@repository_bp.route('/<int:repo_id>', methods=['GET'])
def get_repository(repo_id):
    """
    Get repository details and structure.
    
    Response:
        {
            "id": 1,
            "name": "healthcare-insurance-api",
            "structure": {...},
            "last_indexed": "2025-01-15T10:30:00Z",
            "files": [...]
        }
    """
    try:
        repo = supabase.get_repository(repo_id)
        
        if not repo:
            return format_error_response(f"Repository {repo_id} not found", 404)
        
        structure = repo.get('structure_json', {})
        
        response = {
            'id': repo['id'],
            'name': repo['name'],
            'github_url': repo['github_url'],
            'branch': repo.get('branch', 'main'),
            'structure': structure.get('structure', {}),
            'dependency_graph': structure.get('dependency_graph', {}),
            'last_indexed': repo.get('last_indexed'),
            'created_at': repo.get('created_at')
        }
        
        return format_success_response(response)
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@repository_bp.route('/<int:repo_id>/refresh', methods=['POST'])
def refresh_repository(repo_id):
    """
    Pull latest changes and re-index repository.
    
    Response:
        {
            "repo_id": 1,
            "name": "healthcare-insurance-api",
            "files_indexed": 25,
            "status": "indexed"
        }
    """
    try:
        result = analyzer.refresh_repository(repo_id)
        return format_success_response(result)
    
    except ValueError as e:
        return format_error_response(str(e), 400)
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)

