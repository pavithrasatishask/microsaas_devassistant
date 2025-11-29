"""AST parsing utilities for Python code analysis."""
import ast
import os
from typing import Dict, List, Any


def parse_python_file(file_path: str) -> Dict[str, Any]:
    """
    Parse Python file using AST.
    
    Extract:
    - Classes and their methods
    - Functions and their signatures
    - Import statements
    - Docstrings
    - Decorators
    
    Args:
        file_path: Path to Python file
        
    Returns:
        Dictionary with parsed structure
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=file_path)
        
        parser = ASTParser()
        return parser.parse(tree, file_path)
    except SyntaxError as e:
        return {
            'error': f'Syntax error: {str(e)}',
            'classes': [],
            'functions': [],
            'imports': [],
            'docstring': None
        }
    except Exception as e:
        return {
            'error': f'Parse error: {str(e)}',
            'classes': [],
            'functions': [],
            'imports': [],
            'docstring': None
        }


class ASTParser(ast.NodeVisitor):
    """AST visitor to extract code structure."""
    
    def __init__(self):
        self.classes = []
        self.functions = []
        self.imports = []
        self.docstring = None
        self.current_class = None
    
    def parse(self, tree: ast.AST, file_path: str) -> Dict[str, Any]:
        """Parse AST tree and return structure."""
        self.file_path = file_path
        self.visit(tree)
        
        # Extract module-level docstring
        if isinstance(tree, ast.Module) and tree.body:
            first_node = tree.body[0]
            if isinstance(first_node, ast.Expr) and isinstance(first_node.value, ast.Str):
                self.docstring = first_node.value.s
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        class_info = {
            'name': node.name,
            'methods': [],
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'bases': [self._get_name(base) for base in node.bases],
            'docstring': ast.get_docstring(node)
        }
        
        self.current_class = node.name
        
        # Visit methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._extract_function_info(item, is_method=True)
                class_info['methods'].append(method_info)
        
        self.classes.append(class_info)
        self.current_class = None
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        if self.current_class is None:  # Only top-level functions
            func_info = self._extract_function_info(node, is_method=False)
            self.functions.append(func_info)
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import):
        """Visit import statement."""
        for alias in node.names:
            self.imports.append({
                'type': 'import',
                'module': alias.name,
                'alias': alias.asname
            })
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from import statement."""
        module = node.module or ''
        for alias in node.names:
            self.imports.append({
                'type': 'from_import',
                'module': module,
                'name': alias.name,
                'alias': alias.asname
            })
        self.generic_visit(node)
    
    def _extract_function_info(self, node: ast.FunctionDef, is_method: bool) -> Dict[str, Any]:
        """Extract function/method information."""
        args = []
        for arg in node.args.args:
            arg_info = {'name': arg.arg}
            if arg.annotation:
                arg_info['type'] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
            args.append(arg_info)
        
        return_info = None
        if node.returns:
            return_info = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
        
        return {
            'name': node.name,
            'args': args,
            'return_type': return_info,
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'docstring': ast.get_docstring(node),
            'is_method': is_method,
            'class': self.current_class if is_method else None
        }
    
    def _get_decorator_name(self, node: ast.AST) -> str:
        """Get decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return str(node)
    
    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)


def extract_file_structure(file_path: str) -> Dict[str, Any]:
    """Extract structure from a Python file."""
    return parse_python_file(file_path)

