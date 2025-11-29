"""Helper utilities for authentication and common functions."""
import jwt
from functools import wraps
from flask import request, jsonify
from config import Config


def token_required(f):
    """Decorator to require JWT token for protected routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            request.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(*args, **kwargs)
    
    return decorated


def validate_github_url(url: str) -> bool:
    """Validate GitHub repository URL."""
    if not url:
        return False
    
    valid_prefixes = ['https://github.com/', 'http://github.com/', 'git@github.com:']
    return any(url.startswith(prefix) for prefix in valid_prefixes)


def sanitize_path(path: str) -> str:
    """Sanitize file path to prevent directory traversal."""
    import os
    # Remove any path traversal attempts
    path = os.path.normpath(path)
    # Remove leading slashes and dots
    path = path.lstrip('/').lstrip('.')
    return path


def format_error_response(message: str, status_code: int = 400) -> tuple:
    """Format error response."""
    return jsonify({'error': message}), status_code


def format_success_response(data: dict, status_code: int = 200) -> tuple:
    """Format success response."""
    return jsonify(data), status_code

