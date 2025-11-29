"""Supabase database client service."""
from supabase import create_client, Client
from config import Config
from typing import Optional, Dict, Any, List
import os


class SupabaseClient:
    """Supabase database client wrapper."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
            raise ValueError("Supabase URL and KEY must be set in environment variables")
        
        # Initialize Supabase client
        # Remove proxy env vars temporarily to avoid compatibility issues
        proxy_vars = {}
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            if key in os.environ:
                proxy_vars[key] = os.environ.pop(key)
        
        try:
            self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        except TypeError as e:
            # Handle proxy-related TypeError
            if 'proxy' in str(e).lower():
                # The supabase client is trying to pass proxy to httpx, but httpx doesn't accept it
                # Try to work around this by monkey-patching httpx.Client
                import httpx
                
                # Store original __init__
                _original_httpx_init = httpx.Client.__init__
                
                def _patched_httpx_init(self, *args, **kwargs):
                    # Remove proxy from kwargs before calling original init
                    kwargs.pop('proxy', None)
                    return _original_httpx_init(self, *args, **kwargs)
                
                # Apply patch
                httpx.Client.__init__ = _patched_httpx_init
                
                try:
                    # Retry creating the client
                    self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
                finally:
                    # Restore original
                    httpx.Client.__init__ = _original_httpx_init
            else:
                raise
        finally:
            # Restore proxy vars if they existed
            os.environ.update(proxy_vars)
    
    # Repository operations
    def create_repository(self, name: str, github_url: str, branch: str = 'main', 
                         local_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a new repository record."""
        data = {
            'name': name,
            'github_url': github_url,
            'branch': branch,
            'local_path': local_path
        }
        result = self.client.table('repositories').insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_repository(self, repo_id: int) -> Optional[Dict[str, Any]]:
        """Get repository by ID."""
        result = self.client.table('repositories').select('*').eq('id', repo_id).execute()
        return result.data[0] if result.data else None
    
    def update_repository(self, repo_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update repository record."""
        result = self.client.table('repositories').update(updates).eq('id', repo_id).execute()
        return result.data[0] if result.data else {}
    
    # Conversation operations
    def create_conversation(self, repo_id: int, title: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation."""
        data = {
            'repo_id': repo_id,
            'title': title
        }
        result = self.client.table('conversations').insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_conversation(self, conv_id: int) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        result = self.client.table('conversations').select('*').eq('id', conv_id).execute()
        return result.data[0] if result.data else None
    
    def get_conversation_messages(self, conv_id: int) -> List[Dict[str, Any]]:
        """Get all messages for a conversation."""
        result = self.client.table('messages').select('*').eq('conversation_id', conv_id).order('created_at').execute()
        return result.data if result.data else []
    
    # Message operations
    def create_message(self, conversation_id: int, role: str, content: str, 
                      tokens_used: int = 0) -> Dict[str, Any]:
        """Create a new message."""
        data = {
            'conversation_id': conversation_id,
            'role': role,
            'content': content,
            'tokens_used': tokens_used
        }
        result = self.client.table('messages').insert(data).execute()
        return result.data[0] if result.data else {}
    
    # Impact analysis operations
    def create_impact_analysis(self, conversation_id: int, request_type: str,
                               request_description: str, affected_files: List[str],
                               affected_features: List[str], risk_level: str,
                               warnings: List[str], recommendation: str) -> Dict[str, Any]:
        """Create an impact analysis record."""
        data = {
            'conversation_id': conversation_id,
            'request_type': request_type,
            'request_description': request_description,
            'affected_files': affected_files,
            'affected_features': affected_features,
            'risk_level': risk_level,
            'warnings': warnings,
            'recommendation': recommendation
        }
        result = self.client.table('impact_analyses').insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_impact_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Get impact analysis by ID."""
        result = self.client.table('impact_analyses').select('*').eq('id', analysis_id).execute()
        return result.data[0] if result.data else None
    
    # Code changes operations
    def create_code_change(self, analysis_id: int, file_path: str, 
                          original_code: Optional[str] = None,
                          new_code: Optional[str] = None) -> Dict[str, Any]:
        """Create a code change record."""
        data = {
            'analysis_id': analysis_id,
            'file_path': file_path,
            'original_code': original_code,
            'new_code': new_code,
            'status': 'pending'
        }
        result = self.client.table('code_changes').insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_code_changes(self, analysis_id: int) -> List[Dict[str, Any]]:
        """Get all code changes for an analysis."""
        result = self.client.table('code_changes').select('*').eq('analysis_id', analysis_id).execute()
        return result.data if result.data else []
    
    def update_code_change_status(self, change_id: int, status: str) -> Dict[str, Any]:
        """Update code change status."""
        data = {'status': status}
        if status == 'applied':
            from datetime import datetime
            data['applied_at'] = datetime.utcnow().isoformat()
        
        result = self.client.table('code_changes').update(data).eq('id', change_id).execute()
        return result.data[0] if result.data else {}
    
    # Document operations
    def create_document(self, repo_id: int, file_name: str, file_path: Optional[str] = None,
                       file_url: Optional[str] = None, file_size: Optional[int] = None,
                       pages: Optional[int] = None, extracted_text: Optional[str] = None,
                       text_summary: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
                       document_type: str = 'pdf', processing_status: str = 'pending',
                       error_message: Optional[str] = None) -> Dict[str, Any]:
        """Create a new document record."""
        data = {
            'repo_id': repo_id,
            'document_type': document_type,
            'file_name': file_name,
            'processing_status': processing_status
        }
        
        if file_path:
            data['file_path'] = file_path
        if file_url:
            data['file_url'] = file_url
        if file_size:
            data['file_size'] = file_size
        if pages:
            data['pages'] = pages
        if extracted_text:
            data['extracted_text'] = extracted_text
        if text_summary:
            data['text_summary'] = text_summary
        if metadata:
            data['metadata'] = metadata
        if error_message:
            data['error_message'] = error_message
        
        result = self.client.table('repository_documents').insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        result = self.client.table('repository_documents').select('*').eq('id', doc_id).execute()
        return result.data[0] if result.data else None
    
    def get_repository_documents(self, repo_id: int) -> List[Dict[str, Any]]:
        """Get all documents for a repository."""
        result = self.client.table('repository_documents').select('*').eq('repo_id', repo_id).order('created_at', desc=False).execute()
        # Reverse to get newest first
        return list(reversed(result.data)) if result.data else []
    
    def update_document(self, doc_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update document record."""
        from datetime import datetime
        updates['updated_at'] = datetime.utcnow().isoformat()
        result = self.client.table('repository_documents').update(updates).eq('id', doc_id).execute()
        return result.data[0] if result.data else {}
    
    def delete_document(self, doc_id: int) -> bool:
        """Delete document record."""
        result = self.client.table('repository_documents').delete().eq('id', doc_id).execute()
        return True
    
    def update_repository_document_count(self, repo_id: int):
        """Update repository document count."""
        documents = self.get_repository_documents(repo_id)
        count = len([d for d in documents if d.get('processing_status') == 'completed'])
        has_docs = count > 0
        
        self.update_repository(repo_id, {
            'documents_count': count,
            'has_documents': has_docs
        })

