"""Repository analyzer service for cloning, parsing, and indexing repositories."""
import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from git import Repo, GitCommandError
import networkx as nx
from utils.ast_parser import parse_python_file
from services.supabase_client import SupabaseClient
from config import Config
from utils.helpers import validate_github_url


class RepositoryAnalyzer:
    """Analyze and index repositories."""
    
    def __init__(self, supabase_client: SupabaseClient):
        """Initialize repository analyzer."""
        self.supabase = supabase_client
        self.repos_base_path = Path(Config.REPOS_BASE_PATH)
        self.repos_base_path.mkdir(parents=True, exist_ok=True)
    
    def connect_repository(self, github_url: str, branch: str = 'main') -> Dict[str, Any]:
        """
        Clone repository and create initial index.
        
        Steps:
        1. Validate GitHub URL
        2. Clone repository to local path
        3. Parse all Python files
        4. Extract structure (classes, functions, imports)
        5. Build dependency graph
        6. Extract documentation
        7. Store in database
        
        Returns:
            Dictionary with repo_id, name, structure, files_indexed
        """
        # Validate URL
        if not validate_github_url(github_url):
            raise ValueError(f"Invalid GitHub URL: {github_url}")
        
        # Extract repository name
        repo_name = self._extract_repo_name(github_url)
        local_path = self.repos_base_path / repo_name
        
        # Clone repository
        try:
            if local_path.exists():
                # Update existing repository
                repo = Repo(local_path)
                repo.remotes.origin.fetch()
                repo.git.checkout(branch)
                repo.remotes.origin.pull()
            else:
                # Clone new repository
                repo = Repo.clone_from(github_url, str(local_path), branch=branch)
        except GitCommandError as e:
            raise ValueError(f"Failed to clone repository: {str(e)}")
        
        # Check repository size
        repo_size_mb = self._get_repo_size(local_path)
        if repo_size_mb > Config.MAX_REPO_SIZE_MB:
            raise ValueError(f"Repository too large: {repo_size_mb}MB (max: {Config.MAX_REPO_SIZE_MB}MB)")
        
        # Parse all Python files
        structure = self._parse_repository(local_path)
        
        # Build dependency graph
        dependency_graph = self.build_dependency_graph(structure)
        
        # Store in database
        repo_data = {
            'name': repo_name,
            'github_url': github_url,
            'branch': branch,
            'local_path': str(local_path),
            'structure_json': {
                'structure': structure,
                'dependency_graph': dependency_graph
            }
        }
        
        db_repo = self.supabase.create_repository(
            repo_data['name'],
            repo_data['github_url'],
            repo_data['branch'],
            repo_data['local_path']
        )
        
        # Update with structure
        from datetime import datetime
        self.supabase.update_repository(db_repo['id'], {
            'structure_json': repo_data['structure_json'],
            'last_indexed': datetime.utcnow().isoformat()
        })
        
        files_indexed = structure.get('files_parsed', 0)
        
        return {
            'repo_id': db_repo['id'],
            'name': repo_name,
            'structure': structure,
            'files_indexed': files_indexed,
            'status': 'indexed'
        }
    
    def _parse_repository(self, repo_path: Path) -> Dict[str, Any]:
        """Parse all Python files in repository."""
        structure = {
            'files': [],
            'classes': [],
            'functions': [],
            'imports': [],
            'files_parsed': 0
        }
        
        # Find all Python files
        python_files = list(repo_path.rglob('*.py'))
        
        # Filter out common directories to ignore
        ignore_dirs = {'.git', '__pycache__', 'venv', 'env', 'node_modules', '.venv'}
        
        for py_file in python_files:
            # Skip files in ignored directories
            if any(ignore_dir in py_file.parts for ignore_dir in ignore_dirs):
                continue
            
            try:
                relative_path = str(py_file.relative_to(repo_path))
                parsed = parse_python_file(str(py_file))
                
                if 'error' not in parsed:
                    file_info = {
                        'file_path': relative_path,
                        'classes': parsed.get('classes', []),
                        'functions': parsed.get('functions', []),
                        'imports': parsed.get('imports', []),
                        'docstring': parsed.get('docstring')
                    }
                    
                    structure['files'].append(file_info)
                    structure['classes'].extend([
                        {**cls, 'file_path': relative_path} 
                        for cls in parsed.get('classes', [])
                    ])
                    structure['functions'].extend([
                        {**func, 'file_path': relative_path} 
                        for func in parsed.get('functions', [])
                    ])
                    structure['imports'].extend([
                        {**imp, 'file_path': relative_path} 
                        for imp in parsed.get('imports', [])
                    ])
                    structure['files_parsed'] += 1
            except Exception as e:
                # Skip files that can't be parsed
                print(f"Warning: Could not parse {py_file}: {str(e)}")
                continue
        
        return structure
    
    def build_dependency_graph(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build dependency graph using networkx.
        
        Map:
        - Which files import which modules
        - Which functions call which functions
        - Class inheritance relationships
        
        Returns:
            Dictionary with nodes, edges, circular_dependencies
        """
        G = nx.DiGraph()
        
        # Add nodes (files)
        for file_info in structure.get('files', []):
            file_path = file_info['file_path']
            G.add_node(file_path, type='file')
            
            # Add class nodes
            for cls in file_info.get('classes', []):
                class_name = f"{file_path}::{cls['name']}"
                G.add_node(class_name, type='class', file=file_path)
                G.add_edge(file_path, class_name, type='contains')
            
            # Add function nodes
            for func in file_info.get('functions', []):
                func_name = f"{file_path}::{func['name']}"
                G.add_node(func_name, type='function', file=file_path)
                G.add_edge(file_path, func_name, type='contains')
        
        # Add edges based on imports
        for file_info in structure.get('files', []):
            file_path = file_info['file_path']
            for imp in file_info.get('imports', []):
                if imp['type'] == 'from_import':
                    module = imp.get('module', '')
                    # Try to find matching files
                    target_files = [
                        f['file_path'] for f in structure.get('files', [])
                        if module.replace('.', '/') in f['file_path'] or 
                           any(module.split('.')[-1] in f['file_path'] for _ in [1])
                    ]
                    for target in target_files:
                        if target != file_path:
                            G.add_edge(file_path, target, type='imports')
        
        # Detect circular dependencies
        try:
            cycles = list(nx.simple_cycles(G))
            circular_dependencies = [list(cycle) for cycle in cycles]
        except:
            circular_dependencies = []
        
        return {
            'nodes': [{'id': node, **data} for node, data in G.nodes(data=True)],
            'edges': [{'source': u, 'target': v, **data} for u, v, data in G.edges(data=True)],
            'circular_dependencies': circular_dependencies
        }
    
    def get_relevant_files(self, query: str, repo_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find most relevant files for a query.
        
        Use:
        - Keyword matching in file names
        - Matching in function/class names
        - Matching in docstrings
        
        Returns:
            List of relevant files with relevance scores
        """
        repo = self.supabase.get_repository(repo_id)
        if not repo or not repo.get('structure_json'):
            return []
        
        structure = repo['structure_json'].get('structure', {})
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        scored_files = []
        
        for file_info in structure.get('files', []):
            score = 0.0
            file_path = file_info['file_path']
            file_name = Path(file_path).name.lower()
            
            # Check file name
            for term in query_terms:
                if term in file_name:
                    score += 2.0
            
            # Check class names
            for cls in file_info.get('classes', []):
                cls_name = cls['name'].lower()
                for term in query_terms:
                    if term in cls_name:
                        score += 1.5
            
            # Check function names
            for func in file_info.get('functions', []):
                func_name = func['name'].lower()
                for term in query_terms:
                    if term in func_name:
                        score += 1.0
            
            # Check docstrings
            docstring = file_info.get('docstring', '').lower()
            for term in query_terms:
                if term in docstring:
                    score += 0.5
            
            if score > 0:
                scored_files.append({
                    'file_path': file_path,
                    'relevance_score': score,
                    'content': self._get_file_content(repo.get('local_path'), file_path)
                })
        
        # Sort by score and return top_k
        scored_files.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_files[:top_k]
    
    def _get_file_content(self, repo_path: str, file_path: str) -> str:
        """Get file content."""
        try:
            full_path = Path(repo_path) / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        return ""
    
    def _extract_repo_name(self, github_url: str) -> str:
        """Extract repository name from GitHub URL."""
        # Handle different URL formats
        if github_url.endswith('.git'):
            github_url = github_url[:-4]
        
        parts = github_url.rstrip('/').split('/')
        return parts[-1] if parts else 'repository'
    
    def _get_repo_size(self, repo_path: Path) -> float:
        """Get repository size in MB."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(repo_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
        return total_size / (1024 * 1024)  # Convert to MB
    
    def refresh_repository(self, repo_id: int) -> Dict[str, Any]:
        """Pull latest changes and re-index repository."""
        repo = self.supabase.get_repository(repo_id)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")
        
        github_url = repo['github_url']
        branch = repo.get('branch', 'main')
        
        return self.connect_repository(github_url, branch)

