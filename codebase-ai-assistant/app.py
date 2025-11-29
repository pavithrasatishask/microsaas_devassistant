"""Main Flask application for CodeBase AI Assistant."""
from flask import Flask
from flask_cors import CORS
from config import Config
from routes.repository import repository_bp
from routes.chat import chat_bp
from routes.analysis import analysis_bp
from routes.implementation import implementation_bp


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Register blueprints
    app.register_blueprint(repository_bp, url_prefix='/api/repository')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(implementation_bp, url_prefix='/api/implementation')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return {
            'status': 'healthy',
            'service': 'CodeBase AI Assistant',
            'version': '1.0.0'
        }, 200
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint with API information."""
        return {
            'service': 'CodeBase AI Assistant Backend',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'repository': '/api/repository',
                'chat': '/api/chat',
                'analysis': '/api/analysis',
                'implementation': '/api/implementation'
            }
        }, 200
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.FLASK_DEBUG
    )

