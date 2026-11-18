from app.routes.main import main_bp
from app.routes.auth import auth_bp

def register_routes(app):
    """Registra todos os Blueprints na aplicação Flask."""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

__all__ = ["main_bp", "auth_bp", "register_routes"]
