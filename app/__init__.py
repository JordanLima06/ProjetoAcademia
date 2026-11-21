from flask import Flask, url_for, request, session, g
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.routing import BuildError
from app.config import DevelopmentConfig, ProductionConfig, TestingConfig, get_config_class, is_production_mode
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

    # Garante sincronia entre WTF_CSRF_SECRET_KEY e SECRET_KEY em qualquer modo de inicialização
    if not app.config.get("WTF_CSRF_SECRET_KEY") or (
        isinstance(config_class, dict)
        and "SECRET_KEY" in config_class
        and "WTF_CSRF_SECRET_KEY" not in config_class
    ):
        app.config["WTF_CSRF_SECRET_KEY"] = app.config["SECRET_KEY"]

    # Suporte a cabeçalhos de proxy reverso (Vercel / HTTPS)
    if app.config.get("IS_PRODUCTION") or is_production_mode():
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Inicialização da proteção CSRF global (Flask-WTF)
    csrf.init_app(app)

    _NO_CACHE_ENDPOINTS = frozenset({
        "auth.login",
        "auth.logout",
        "auth.cadastro",
        "auth.solicitar_recuperacao",
        "auth.redefinir_senha",
        "main.aula_experimental",
        "enrollment.contratar",
        "enrollment.processar_contratacao",
        "enrollment.minha_matricula",
        "enrollment.cancelar_matricula",
        "student.painel",
        "student.perfil",
        "student.alterar_senha",
    })

    @app.before_request
    def ensure_csrf_session_token():
        """
        Garante a presença do token CSRF na sessão apenas para rotas de aplicação.
        Ignora arquivos estáticos e rotas inexistentes (404, ex.: /favicon.ico) para evitar
        condições de corrida e sobrescritas indevidas do cookie de sessão no navegador.
        Limpa eventual cache em g.csrf_token quando a sessão atual não possui csrf_token.
        """
        if request.endpoint is None or request.endpoint == "static":
            return
        if request.method in ("GET", "HEAD", "OPTIONS") and "csrf_token" not in session:
            g.pop("csrf_token", None)
            generate_csrf()

    @app.after_request
    def set_security_and_cache_headers(response):
        """
        Evita armazenamento em cache de páginas autenticadas, formulários com CSRF
        e qualquer resposta de aplicação que modifique o cookie de sessão.
        """
        if request.endpoint == "static":
            return response

        if (
            "user_id" in session
            or request.endpoint in _NO_CACHE_ENDPOINTS
            or session.modified
        ):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

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
