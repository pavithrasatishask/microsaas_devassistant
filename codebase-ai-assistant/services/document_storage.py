"""Document storage service for handling PDF file uploads and storage."""
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from werkzeug.utils import secure_filename
from config import Config


class DocumentStorage:
    """Handle document file storage and management."""
    
    def __init__(self):
        """Initialize document storage."""
        self.base_path = Path(Config.PDF_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.max_file_size_mb = Config.MAX_PDF_SIZE_MB
    
    def save_uploaded_file(self, file, repo_id: int) -> Dict[str, Any]:
        """
        Save uploaded file and return path information.
        
        Args:
            file: Flask file object from request.files
            repo_id: Repository ID
            
        Returns:
            Dictionary with file_path, file_name, file_size
        """
        if not file or not file.filename:
            raise ValueError("No file provided")
        
        # Validate file extension
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.pdf'):
            raise ValueError("Only PDF files are supported")
        
        # Create repository-specific directory
        repo_dir = self.base_path / str(repo_id)
        repo_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename if file exists
        file_path = repo_dir / filename
        if file_path.exists():
            # Add hash to filename
            name_part = file_path.stem
            ext_part = file_path.suffix
            file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
            filename = f"{name_part}_{file_hash}{ext_part}"
            file_path = repo_dir / filename
        
        # Save file
        file.save(str(file_path))
        
        # Get file size
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb > self.max_file_size_mb:
            # Delete file if too large
            os.remove(file_path)
            raise ValueError(f"File too large: {file_size_mb:.2f}MB (max: {self.max_file_size_mb}MB)")
        
        return {
            'file_path': str(file_path),
            'file_name': filename,
            'file_size': file_size,
            'file_size_mb': file_size_mb
        }
    
    def save_from_url(self, url: str, repo_id: int, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Download and save file from URL.
        
        Args:
            url: URL to PDF file
            repo_id: Repository ID
            filename: Optional filename (will be extracted from URL if not provided)
            
        Returns:
            Dictionary with file_path, file_name, file_size
        """
        import requests
        
        try:
            # Download file
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determine filename
            if not filename:
                # Try to get from URL
                filename = url.split('/')[-1]
                if '?' in filename:
                    filename = filename.split('?')[0]
                if not filename or not filename.endswith('.pdf'):
                    filename = f"document_{hashlib.md5(url.encode()).hexdigest()[:8]}.pdf"
            
            filename = secure_filename(filename)
            
            # Create repository-specific directory
            repo_dir = self.base_path / str(repo_id)
            repo_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = repo_dir / filename
            if file_path.exists():
                # Add hash if exists
                name_part = file_path.stem
                ext_part = file_path.suffix
                file_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"{name_part}_{file_hash}{ext_part}"
                file_path = repo_dir / filename
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            if file_size_mb > self.max_file_size_mb:
                os.remove(file_path)
                raise ValueError(f"File too large: {file_size_mb:.2f}MB (max: {self.max_file_size_mb}MB)")
            
            return {
                'file_path': str(file_path),
                'file_name': filename,
                'file_size': file_size,
                'file_size_mb': file_size_mb,
                'source_url': url
            }
            
        except requests.RequestException as e:
            raise ValueError(f"Failed to download file from URL: {str(e)}")
    
    def get_file_path(self, repo_id: int, filename: str) -> Optional[str]:
        """
        Get local file path for document.
        
        Args:
            repo_id: Repository ID
            filename: Document filename
            
        Returns:
            Full file path or None if not found
        """
        file_path = self.base_path / str(repo_id) / secure_filename(filename)
        if file_path.exists():
            return str(file_path)
        return None
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            file_path: Full path to file
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def get_repo_documents_path(self, repo_id: int) -> Path:
        """
        Get the directory path for a repository's documents.
        
        Args:
            repo_id: Repository ID
            
        Returns:
            Path object for repository documents directory
        """
        return self.base_path / str(repo_id)
    
    def list_repo_documents(self, repo_id: int) -> List[Dict[str, Any]]:
        """
        List all documents for a repository.
        
        Args:
            repo_id: Repository ID
            
        Returns:
            List of document file information
        """
        repo_dir = self.get_repo_documents_path(repo_id)
        if not repo_dir.exists():
            return []
        
        documents = []
        for file_path in repo_dir.glob('*.pdf'):
            file_stat = file_path.stat()
            documents.append({
                'file_name': file_path.name,
                'file_path': str(file_path),
                'file_size': file_stat.st_size,
                'file_size_mb': file_stat.st_size / (1024 * 1024),
                'modified_at': file_stat.st_mtime
            })
        
        return documents

