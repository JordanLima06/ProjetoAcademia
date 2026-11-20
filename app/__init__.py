from flask import Flask, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.routing import BuildError
from app.config import DevelopmentConfig, ProductionConfig, TestingConfig, get_config_class
from app import db
from app.routes import register_routes

csrf = CSRFProtect()

def create_app(config_class=None):
    """
    Application Factory: cria e configura a instância da aplicação Flask.
    Seleciona dinamicamente a configuração apropriada:
    - ProductionConfig para Vercel (VERCEL=1), APP_ENV=production ou FLASK_ENV=production.
    - DevelopmentConfig para execução local padrão.
    - TestingConfig quando explicitamente informado ou em testes.
    """
    if config_class is None:
        config_class = get_config_class()

    # Valida configurações essenciais em ambiente de produção
    if isinstance(config_class, type) and issubclass(config_class, ProductionConfig):
        config_class.validate_production_config()

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    if isinstance(config_class, type):
        app.config.from_object(config_class)
    elif config_class:
        app.config.from_mapping(config_class)
    else:
        app.config.from_object(DevelopmentConfig)

    # Inicialização da proteção CSRF global (Flask-WTF)
    csrf.init_app(app)

    # Ciclo de vida e teardown do PostgreSQL
    db.init_app(app)

    # Registro de Blueprints
    register_routes(app)

    # Garante compatibilidade total para chamadas url_for em templates legados sem prefixo de blueprint
    @app.context_processor
    def inject_url_for():
        def smart_url_for(endpoint, **values):
            try:
                return url_for(endpoint, **values)
            except BuildError:
                for bp in ["main", "auth", "enrollment", "student"]:
                    try:
                        return url_for(f"{bp}.{endpoint}", **values)
                    except BuildError:
                        pass
                raise
        return dict(url_for=smart_url_for)

    return app
