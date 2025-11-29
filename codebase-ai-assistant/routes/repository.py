"""Repository management endpoints."""
from flask import Blueprint, request, jsonify
from services.supabase_client import SupabaseClient
from services.repository_analyzer import RepositoryAnalyzer
from services.pdf_processor import PDFProcessor
from services.document_storage import DocumentStorage
from utils.helpers import format_error_response, format_success_response

repository_bp = Blueprint('repository', __name__)

# Initialize services
supabase = SupabaseClient()
analyzer = RepositoryAnalyzer(supabase)
pdf_processor = PDFProcessor()
doc_storage = DocumentStorage()


@repository_bp.route('/connect', methods=['POST'])
def connect_repository():
    """
    Connect and index a GitHub repository with optional PDF documents.
    
    Request (JSON):
        {
            "github_url": "https://github.com/user/repo",
            "branch": "main",
            "pdf_urls": ["https://example.com/doc.pdf"]  # optional
        }
    
    Request (Multipart):
        github_url: "https://github.com/user/repo"
        branch: "main"
        pdf_files: [file1.pdf, file2.pdf]  # optional
        pdf_urls: ["https://example.com/doc.pdf"]  # optional
    
    Response:
        {
            "repo_id": 1,
            "name": "healthcare-insurance-api",
            "files_indexed": 25,
            "documents_processed": 2,
            "documents": [...],
            "status": "indexed"
        }
    """
    try:
        # Handle both JSON and multipart form data
        if request.is_json:
            data = request.get_json()
            github_url = data.get('github_url')
            branch = data.get('branch', 'main')
            pdf_urls = data.get('pdf_urls', [])
            pdf_files = []
        else:
            # Multipart form data
            github_url = request.form.get('github_url')
            branch = request.form.get('branch', 'main')
            pdf_urls = request.form.getlist('pdf_urls') if 'pdf_urls' in request.form else []
            pdf_files = request.files.getlist('pdf_files') if 'pdf_files' in request.files else []
        
        if not github_url:
            return format_error_response("github_url is required", 400)
        
        # Connect repository (existing functionality)
        result = analyzer.connect_repository(github_url, branch)
        repo_id = result['repo_id']
        
        # Process PDF files
        documents_processed = []
        if pdf_files or pdf_urls:
            documents_processed = _process_pdfs(repo_id, pdf_files, pdf_urls)
        
        result['documents_processed'] = len(documents_processed)
        result['documents'] = documents_processed
        
        return format_success_response(result, 201)
    
    except ValueError as e:
        return format_error_response(str(e), 400)
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


def _process_pdfs(repo_id: int, pdf_files: list, pdf_urls: list) -> list:
    """Process uploaded PDF files and URLs."""
    documents = []
    
    # Process uploaded files
    for file in pdf_files:
        try:
            # Save file
            file_info = doc_storage.save_uploaded_file(file, repo_id)
            
            # Extract text
            pdf_data = pdf_processor.extract_text(file_info['file_path'])
            
            # Generate summary
            summary = pdf_processor.generate_summary(pdf_data['text'])
            
            # Create document record
            doc = supabase.create_document(
                repo_id=repo_id,
                file_name=file_info['file_name'],
                file_path=file_info['file_path'],
                file_size=file_info['file_size'],
                pages=pdf_data['pages'],
                extracted_text=pdf_data['text'],
                text_summary=summary,
                metadata=pdf_data['metadata']
            )
            
            # Update status to completed
            supabase.update_document(doc['id'], {'processing_status': 'completed'})
            
            documents.append({
                'id': doc['id'],
                'file_name': file_info['file_name'],
                'pages': pdf_data['pages'],
                'status': 'completed'
            })
        except Exception as e:
            # Create failed document record
            try:
                doc = supabase.create_document(
                    repo_id=repo_id,
                    file_name=file.filename if hasattr(file, 'filename') else 'unknown.pdf',
                    processing_status='failed',
                    error_message=str(e)
                )
                documents.append({
                    'id': doc['id'],
                    'file_name': file.filename if hasattr(file, 'filename') else 'unknown.pdf',
                    'status': 'failed',
                    'error': str(e)
                })
            except:
                pass
    
    # Process URLs
    for url in pdf_urls:
        try:
            # Download and save
            file_info = doc_storage.save_from_url(url, repo_id)
            
            # Extract text
            pdf_data = pdf_processor.extract_text(file_info['file_path'])
            
            # Generate summary
            summary = pdf_processor.generate_summary(pdf_data['text'])
            
            # Create document record
            doc = supabase.create_document(
                repo_id=repo_id,
                file_name=file_info['file_name'],
                file_path=file_info['file_path'],
                file_url=url,
                file_size=file_info['file_size'],
                pages=pdf_data['pages'],
                extracted_text=pdf_data['text'],
                text_summary=summary,
                metadata=pdf_data['metadata']
            )
            
            # Update status to completed
            supabase.update_document(doc['id'], {'processing_status': 'completed'})
            
            documents.append({
                'id': doc['id'],
                'file_name': file_info['file_name'],
                'pages': pdf_data['pages'],
                'status': 'completed'
            })
        except Exception as e:
            # Create failed document record
            try:
                doc = supabase.create_document(
                    repo_id=repo_id,
                    file_name=url.split('/')[-1],
                    file_url=url,
                    processing_status='failed',
                    error_message=str(e)
                )
                documents.append({
                    'id': doc['id'],
                    'file_name': url.split('/')[-1],
                    'status': 'failed',
                    'error': str(e)
                })
            except:
                pass
    
    # Update repository document count
    if documents:
        supabase.update_repository_document_count(repo_id)
    
    return documents


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


@repository_bp.route('/<int:repo_id>/documents', methods=['POST'])
def add_document(repo_id):
    """
    Add a PDF document to a repository.
    
    Request (Multipart):
        pdf_file: <file>  # or
        pdf_url: "https://..."  # optional
    
    Response:
        {
            "id": 1,
            "file_name": "requirements.pdf",
            "pages": 10,
            "status": "completed"
        }
    """
    try:
        # Check repository exists
        repo = supabase.get_repository(repo_id)
        if not repo:
            return format_error_response(f"Repository {repo_id} not found", 404)
        
        pdf_file = request.files.get('pdf_file')
        pdf_url = request.form.get('pdf_url')
        
        if not pdf_file and not pdf_url:
            return format_error_response("Either pdf_file or pdf_url is required", 400)
        
        documents = _process_pdfs(repo_id, 
                                  [pdf_file] if pdf_file else [], 
                                  [pdf_url] if pdf_url else [])
        
        if documents:
            return format_success_response(documents[0], 201)
        else:
            return format_error_response("Failed to process document", 500)
    
    except ValueError as e:
        return format_error_response(str(e), 400)
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@repository_bp.route('/<int:repo_id>/documents', methods=['GET'])
def get_repository_documents(repo_id):
    """
    Get all documents for a repository.
    
    Response:
        {
            "documents": [
                {
                    "id": 1,
                    "file_name": "requirements.pdf",
                    "pages": 10,
                    "status": "completed",
                    ...
                }
            ]
        }
    """
    try:
        repo = supabase.get_repository(repo_id)
        if not repo:
            return format_error_response(f"Repository {repo_id} not found", 404)
        
        documents = supabase.get_repository_documents(repo_id)
        return format_success_response({'documents': documents})
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@repository_bp.route('/documents/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """
    Get document details and content.
    
    Response:
        {
            "id": 1,
            "file_name": "requirements.pdf",
            "extracted_text": "...",
            "text_summary": "...",
            ...
        }
    """
    try:
        doc = supabase.get_document(doc_id)
        if not doc:
            return format_error_response(f"Document {doc_id} not found", 404)
        
        return format_success_response(doc)
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


@repository_bp.route('/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """
    Delete a document.
    
    Response:
        {
            "success": true,
            "message": "Document deleted"
        }
    """
    try:
        doc = supabase.get_document(doc_id)
        if not doc:
            return format_error_response(f"Document {doc_id} not found", 404)
        
        # Delete file from storage
        if doc.get('file_path'):
            doc_storage.delete_file(doc['file_path'])
        
        # Delete from database
        supabase.delete_document(doc_id)
        
        # Update repository document count
        supabase.update_repository_document_count(doc['repo_id'])
        
        return format_success_response({'message': 'Document deleted'})
    
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)

