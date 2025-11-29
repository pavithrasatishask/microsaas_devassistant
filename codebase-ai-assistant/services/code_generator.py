"""Code generator service for generating and applying code changes."""
import ast
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from git import Repo
from services.claude_service import ClaudeService
from services.supabase_client import SupabaseClient
from utils.ast_parser import parse_python_file


class CodeGenerator:
    """Generate and apply code changes."""
    
    def __init__(self, claude_service: ClaudeService, supabase_client: SupabaseClient):
        """Initialize code generator."""
        self.claude = claude_service
        self.supabase = supabase_client
    
    def generate_implementation(self, requirement: str, impact_analysis: Dict[str, Any],
                               repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate code implementation.
        
        Steps:
        1. Validate requirement is approved (if needed)
        2. Load existing code for affected files
        3. Use Claude to generate changes
        4. Validate generated code syntax
        5. Create backup of original files
        6. Return change set
        
        Returns:
            Dictionary with changes list, tests_generated, documentation_updated
        """
        repo_path = repo_data.get('local_path')
        if not repo_path or not os.path.exists(repo_path):
            raise ValueError(f"Repository path not found: {repo_path}")
        
        # Load existing code for affected files
        affected_files = impact_analysis.get('affected_files', [])
        existing_code_map = {}
        
        for file_path in affected_files:
            full_path = Path(repo_path) / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        existing_code_map[file_path] = f.read()
                except Exception as e:
                    print(f"Warning: Could not read {file_path}: {str(e)}")
        
        # Build context for Claude
        context = {
            'existing_code': '\n\n'.join([
                f"File: {path}\n{code[:5000]}"  # Limit code size
                for path, code in existing_code_map.items()
            ])
        }
        
        # Generate code using Claude
        generation_result = self.claude.generate_code(requirement, context)
        changes = generation_result.get('changes', [])
        
        # Validate generated code
        validated_changes = []
        for change in changes:
            file_path = change.get('file_path', '')
            new_code = change.get('new_code', '')
            
            # Validate syntax
            validation = self.validate_generated_code(new_code, file_path)
            
            if validation.get('valid', False):
                # Get original code if file exists
                original_code = existing_code_map.get(file_path, '')
                
                validated_changes.append({
                    'file_path': file_path,
                    'action': 'modify' if original_code else 'create',
                    'original_code': original_code,
                    'new_code': new_code,
                    'explanation': change.get('explanation', ''),
                    'validation': validation
                })
            else:
                # Include invalid changes with errors
                validated_changes.append({
                    'file_path': file_path,
                    'action': 'error',
                    'original_code': existing_code_map.get(file_path, ''),
                    'new_code': new_code,
                    'explanation': change.get('explanation', ''),
                    'validation': validation,
                    'errors': validation.get('errors', [])
                })
        
        return {
            'changes': validated_changes,
            'tests_generated': False,  # Could be enhanced
            'documentation_updated': False,  # Could be enhanced
            'tokens_used': generation_result.get('tokens_used', 0),
            'cost': generation_result.get('cost', {})
        }
    
    def validate_generated_code(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        Validate generated code.
        
        Checks:
        - Syntax errors (use ast.parse)
        - Import errors
        - Indentation
        - Basic linting
        
        Returns:
            Dictionary with valid flag, errors, warnings
        """
        errors = []
        warnings = []
        
        # Check if it's a Python file
        if not file_path.endswith('.py'):
            return {
                'valid': True,
                'errors': [],
                'warnings': ['Not a Python file, skipping syntax validation']
            }
        
        # Try to parse with AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error: {str(e)} at line {e.lineno}")
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
        
        # Basic checks
        if not code.strip():
            warnings.append("Generated code is empty")
        
        # Check for common issues
        if 'import' in code and 'from' in code:
            # Check for potentially problematic imports
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    # Basic import validation
                    if '..' in line:
                        warnings.append(f"Relative import at line {i}: {line.strip()}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def apply_changes(self, change_id: int, repo_path: str) -> Dict[str, Any]:
        """
        Apply approved code changes to repository.
        
        Steps:
        1. Create backup branch
        2. Apply changes
        3. Commit changes
        4. Update database status
        
        Returns:
            Dictionary with success, commit_hash, files_modified
        """
        # Get code changes from database
        change_record = self.supabase.client.table('code_changes').select('*').eq('id', change_id).execute()
        if not change_record.data:
            raise ValueError(f"Code change {change_id} not found")
        
        change = change_record.data[0]
        
        if change['status'] != 'approved':
            raise ValueError(f"Code change {change_id} is not approved (status: {change['status']})")
        
        # Get all changes for this analysis
        analysis_id = change['analysis_id']
        all_changes = self.supabase.get_code_changes(analysis_id)
        
        # Initialize git repo
        try:
            repo = Repo(repo_path)
        except Exception as e:
            raise ValueError(f"Failed to initialize git repository: {str(e)}")
        
        # Create backup branch
        backup_branch = f"backup-before-apply-{change_id}"
        try:
            repo.git.checkout('-b', backup_branch)
        except Exception:
            # Branch might already exist
            repo.git.checkout(backup_branch)
        
        # Apply changes
        files_modified = []
        for change_item in all_changes:
            if change_item['status'] != 'approved':
                continue
            
            file_path = change_item['file_path']
            new_code = change_item['new_code']
            full_path = Path(repo_path) / file_path
            
            # Create directory if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write new code
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_code)
                files_modified.append(file_path)
            except Exception as e:
                raise ValueError(f"Failed to write {file_path}: {str(e)}")
        
        # Commit changes
        try:
            repo.git.add([str(Path(repo_path) / f) for f in files_modified])
            commit = repo.index.commit(f"Apply code changes from analysis {analysis_id}")
            commit_hash = commit.hexsha
        except Exception as e:
            raise ValueError(f"Failed to commit changes: {str(e)}")
        
        # Update database status
        for change_item in all_changes:
            if change_item['status'] == 'approved':
                self.supabase.update_code_change_status(change_item['id'], 'applied')
        
        return {
            'success': True,
            'commit_hash': commit_hash,
            'files_modified': files_modified,
            'backup_branch': backup_branch
        }

