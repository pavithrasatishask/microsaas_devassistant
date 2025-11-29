"""PDF processing service for extracting text and metadata from PDF files."""
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import pdfplumber
import pypdf
import requests
from config import Config


class PDFProcessor:
    """Process PDF files to extract text and metadata."""
    
    def __init__(self):
        """Initialize PDF processor."""
        self.max_pdf_size_mb = Config.MAX_PDF_SIZE_MB
        self.max_pdf_pages = Config.MAX_PDF_PAGES
    
    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with text, pages, metadata, page_texts
        """
        if not os.path.exists(pdf_path):
            raise ValueError(f"PDF file not found: {pdf_path}")
        
        # Validate file size
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        if file_size_mb > self.max_pdf_size_mb:
            raise ValueError(f"PDF too large: {file_size_mb:.2f}MB (max: {self.max_pdf_size_mb}MB)")
        
        # Try pdfplumber first (better for tables and formatting)
        try:
            return self._extract_with_pdfplumber(pdf_path)
        except Exception as e:
            # Fallback to pypdf
            try:
                return self._extract_with_pypdf(pdf_path)
            except Exception as e2:
                raise ValueError(f"Failed to extract text from PDF: {str(e2)}")
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text using pdfplumber (better quality)."""
        text_parts = []
        page_texts = []
        metadata = {}
        total_pages = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            if total_pages > self.max_pdf_pages:
                raise ValueError(f"PDF has too many pages: {total_pages} (max: {self.max_pdf_pages})")
            
            # Extract metadata
            if pdf.metadata:
                metadata = {
                    'title': pdf.metadata.get('Title', ''),
                    'author': pdf.metadata.get('Author', ''),
                    'subject': pdf.metadata.get('Subject', ''),
                    'creator': pdf.metadata.get('Creator', ''),
                    'producer': pdf.metadata.get('Producer', ''),
                    'creation_date': str(pdf.metadata.get('CreationDate', '')),
                    'modification_date': str(pdf.metadata.get('ModDate', ''))
                }
            
            # Extract text from each page
            for i, page in enumerate(pdf.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        page_texts.append(page_text)
                        text_parts.append(f"--- Page {i} ---\n{page_text}")
                except Exception as e:
                    # Skip pages that can't be extracted
                    page_texts.append(f"[Page {i}: Unable to extract text]")
                    text_parts.append(f"--- Page {i} ---\n[Unable to extract text]")
        
        full_text = "\n\n".join(text_parts)
        
        return {
            'text': full_text,
            'pages': total_pages,
            'metadata': metadata,
            'page_texts': page_texts,
            'extraction_method': 'pdfplumber'
        }
    
    def _extract_with_pypdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text using pypdf (fallback)."""
        text_parts = []
        page_texts = []
        metadata = {}
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            if total_pages > self.max_pdf_pages:
                raise ValueError(f"PDF has too many pages: {total_pages} (max: {self.max_pdf_pages})")
            
            # Extract metadata
            if pdf_reader.metadata:
                metadata = {
                    'title': pdf_reader.metadata.get('/Title', ''),
                    'author': pdf_reader.metadata.get('/Author', ''),
                    'subject': pdf_reader.metadata.get('/Subject', ''),
                    'creator': pdf_reader.metadata.get('/Creator', ''),
                    'producer': pdf_reader.metadata.get('/Producer', ''),
                    'creation_date': str(pdf_reader.metadata.get('/CreationDate', '')),
                    'modification_date': str(pdf_reader.metadata.get('/ModDate', ''))
                }
            
            # Extract text from each page
            for i, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        page_texts.append(page_text)
                        text_parts.append(f"--- Page {i} ---\n{page_text}")
                except Exception as e:
                    page_texts.append(f"[Page {i}: Unable to extract text]")
                    text_parts.append(f"--- Page {i} ---\n[Unable to extract text]")
        
        full_text = "\n\n".join(text_parts)
        
        return {
            'text': full_text,
            'pages': total_pages,
            'metadata': metadata,
            'page_texts': page_texts,
            'extraction_method': 'pypdf'
        }
    
    def extract_text_from_url(self, pdf_url: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Download PDF from URL and extract text.
        
        Args:
            pdf_url: URL to PDF file
            save_path: Optional path to save downloaded PDF
            
        Returns:
            Dictionary with text, pages, metadata, page_texts
        """
        try:
            # Download PDF
            response = requests.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determine save path
            if not save_path:
                # Create temp file
                import tempfile
                temp_dir = Path(Config.PDF_STORAGE_PATH) / "temp"
                temp_dir.mkdir(parents=True, exist_ok=True)
                save_path = str(temp_dir / f"downloaded_{hash(pdf_url)}.pdf")
            
            # Save to file
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract text
            result = self.extract_text(save_path)
            
            # Clean up temp file if we created it
            if not save_path.startswith(str(Config.PDF_STORAGE_PATH)):
                try:
                    os.remove(save_path)
                except:
                    pass
            
            return result
            
        except requests.RequestException as e:
            raise ValueError(f"Failed to download PDF from URL: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to process PDF from URL: {str(e)}")
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """
        Generate a summary of the PDF text.
        
        For now, returns first N characters. Can be enhanced with Claude AI.
        
        Args:
            text: Full text content
            max_length: Maximum summary length
            
        Returns:
            Summary text
        """
        if not text:
            return ""
        
        # Simple summary: first paragraph or first N characters
        paragraphs = text.split('\n\n')
        if paragraphs:
            first_para = paragraphs[0].strip()
            if len(first_para) <= max_length:
                return first_para
        
        # Truncate to max_length
        summary = text[:max_length].strip()
        if len(text) > max_length:
            summary += "..."
        
        return summary
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """
        Validate PDF file integrity.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not os.path.exists(pdf_path):
                return False
            
            # Try to open with pypdf (lightweight check)
            with open(pdf_path, 'rb') as f:
                pdf_reader = pypdf.PdfReader(f)
                # Just check if we can read it
                _ = len(pdf_reader.pages)
            
            return True
        except Exception:
            return False
    
    def chunk_text(self, text: str, chunk_size: int = None) -> List[str]:
        """
        Split text into chunks for better AI processing.
        
        Args:
            text: Full text to chunk
            chunk_size: Approximate tokens per chunk (default from config)
            
        Returns:
            List of text chunks
        """
        if chunk_size is None:
            chunk_size = Config.PDF_TEXT_CHUNK_SIZE
        
        # Simple chunking by paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para.split())  # Approximate token count
            if current_size + para_size > chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks

