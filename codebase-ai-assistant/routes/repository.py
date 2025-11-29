"""Repository management endpoints."""
from flask import Blueprint, request
from services.supabase_client import SupabaseClient
from services.repository_analyzer import RepositoryAnalyzer
from services.pdf_processor import PDFProcessor
from services.document_storage import DocumentStorage
from utils.helpers import format_error_response, format_success_response

repository_bp = Blueprint('repository', __name__)

# Lazy initialization - services created on first use
_supabase = None
_analyzer = None
_pdf_processor = None
_doc_storage = None

def get_services():
    """Get or create service instances (lazy initialization)."""
    global _supabase, _analyzer, _pdf_processor, _doc_storage
    if _supabase is None:
        _supabase = SupabaseClient()
        _analyzer = RepositoryAnalyzer(_supabase)
        _pdf_processor = PDFProcessor()
        _doc_storage = DocumentStorage()
    return _supabase, _analyzer, _pdf_processor, _doc_storage


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
    
    Request (Multipart) - COMMENTED OUT: Uncomment for local execution/testing with curl file uploads:
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
        # Original JSON-only implementation (for production/frontend use)
        data = request.get_json()
        if not data:
            return format_error_response("JSON body is required", 400)
        
        github_url = data.get('github_url')
        branch = data.get('branch', 'main')
        pdf_urls = data.get('pdf_urls', [])
        
        # COMMENTED OUT: Multipart form data support for local execution/testing
        # Uncomment the block below to enable file uploads via curl (multipart/form-data)
        # This allows testing without a frontend by using: curl -F "github_url=..." -F "pdf_files=@file.pdf"
        # if request.is_json:
        #     data = request.get_json()
        #     github_url = data.get('github_url')
        #     branch = data.get('branch', 'main')
        #     pdf_urls = data.get('pdf_urls', [])
        #     pdf_files = []
        # else:
        #     # Multipart form data
        #     github_url = request.form.get('github_url')
        #     branch = request.form.get('branch', 'main')
        #     pdf_urls = request.form.getlist('pdf_urls') if 'pdf_urls' in request.form else []
        #     pdf_files = request.files.getlist('pdf_files') if 'pdf_files' in request.files else []
        
        if not github_url:
            return format_error_response("github_url is required", 400)
        
        # Get services
        supabase, analyzer, pdf_processor, doc_storage = get_services()
        
        # Connect repository (existing functionality)
        result = analyzer.connect_repository(github_url, branch)
        repo_id = result['repo_id']
        
        # Process PDF files from URLs (JSON request)
        documents_processed = []
        if pdf_urls:
            # COMMENTED OUT: File upload processing - uncomment when multipart is enabled above
            # pdf_files = []  # Set empty when using JSON-only
            documents_processed = _process_pdfs(repo_id, [], pdf_urls, supabase, pdf_processor, doc_storage)
        
        # COMMENTED OUT: Process uploaded PDF files (multipart) - uncomment when multipart is enabled
        # if pdf_files or pdf_urls:
        #     documents_processed = _process_pdfs(repo_id, pdf_files, pdf_urls, supabase, pdf_processor, doc_storage)
        
        result['documents_processed'] = len(documents_processed)
        result['documents'] = documents_processed
        
        return format_success_response(result, 201)
    
    except ValueError as e:
        return format_error_response(str(e), 400)
    except Exception as e:
        return format_error_response(f"Internal error: {str(e)}", 500)


def _process_pdfs(repo_id: int, pdf_files: list, pdf_urls: list, supabase, pdf_processor, doc_storage) -> list:
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
                    error_message=str(e)[:500]  # Limit error message length
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
                    file_name=url.split('/')[-1] if '/' in url else 'document.pdf',
                    file_url=url,
                    processing_status='failed',
                    error_message=str(e)[:500]  # Limit error message length
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
        supabase, _, _, _ = get_services()
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
        _, analyzer, _, _ = get_services()
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
    
    Request (JSON):
        {
            "pdf_url": "https://..."  # required
        }
    
    Request (Multipart) - COMMENTED OUT: Uncomment for local execution/testing with curl file uploads:
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
        supabase, _, pdf_processor, doc_storage = get_services()
        # Check repository exists
        repo = supabase.get_repository(repo_id)
        if not repo:
            return format_error_response(f"Repository {repo_id} not found", 404)
        
        # Original JSON-only implementation (for production/frontend use)
        data = request.get_json()
        if not data:
            return format_error_response("JSON body is required", 400)
        
        pdf_url = data.get('pdf_url')
        
        # COMMENTED OUT: Multipart form data support for local execution/testing
        # Uncomment the block below to enable file uploads via curl (multipart/form-data)
        # This allows testing without a frontend by using: curl -F "pdf_file=@file.pdf"
        # pdf_file = request.files.get('pdf_file')
        # pdf_url = request.form.get('pdf_url')
        
        if not pdf_url:
            return format_error_response("pdf_url is required", 400)
        
        # Process PDF from URL (JSON request)
        documents = _process_pdfs(repo_id, 
                                  [],  # Empty file list for JSON-only
                                  [pdf_url],
                                  supabase, pdf_processor, doc_storage)
        
        # COMMENTED OUT: Process uploaded file (multipart) - uncomment when multipart is enabled
        # if not pdf_file and not pdf_url:
        #     return format_error_response("Either pdf_file or pdf_url is required", 400)
        # documents = _process_pdfs(repo_id, 
        #                           [pdf_file] if pdf_file else [], 
        #                           [pdf_url] if pdf_url else [],
        #                           supabase, pdf_processor, doc_storage)
        
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
        supabase, _, _, _ = get_services()
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
        supabase, _, _, _ = get_services()
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
        supabase, _, _, doc_storage = get_services()
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

