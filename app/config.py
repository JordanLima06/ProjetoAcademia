import os
from datetime import timedelta
from typing import Optional, Type

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def is_production_mode() -> bool:
    """
    Identifica se o ambiente de execução atual é de produção através de:
    - VERCEL=1 (ambiente serverless da Vercel)
    - APP_ENV=production
    - FLASK_ENV=production
    """
    if os.getenv("VERCEL") in ("1", "true", "True"):
        return True
    if (os.getenv("APP_ENV") or "").strip().lower() == "production":
        return True
    if (os.getenv("FLASK_ENV") or "").strip().lower() == "production":
        return True
    return False

class Config:
    """Configurações base da aplicação."""
    SECRET_KEY = os.getenv("SECRET_KEY", "fightacademy-secret-key-dev-change-in-production")
    DEBUG = False
    TESTING = False
    IS_PRODUCTION = False

    # Configurações de Sessão e Cookies
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1")

    # Configurações de Proteção CSRF (Flask-WTF)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_SECRET_KEY = SECRET_KEY

    # Configurações do PostgreSQL
    # Prioriza DATABASE_URL e utiliza POSTGRES_URL como alternativa
    DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or None

    # Parâmetros individuais para desenvolvimento local
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "academia")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")

class DevelopmentConfig(Config):
    """Configurações para ambiente de desenvolvimento."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    IS_PRODUCTION = False

class ProductionConfig(Config):
    """Configurações para ambiente de produção (Vercel + Neon)."""
    DEBUG = False
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() in ("true", "1")
    IS_PRODUCTION = True

    @classmethod
    def validate_production_config(cls):
        """
        Valida a presença de configurações essenciais de produção.
        A ausência de DATABASE_URL ou POSTGRES_URL gera erro explícito de configuração.
        É estritamente proibido utilizar localhost como fallback em produção.
        """
        db_url = cls.DATABASE_URL or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        if not db_url:
            raise RuntimeError(
                "Configuração inválida para produção: DATABASE_URL ou POSTGRES_URL não configurada. "
                "É estritamente proibido utilizar localhost como fallback em ambiente de produção."
            )

class TestingConfig(Config):
    """Configurações para execução de testes."""
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = True
    IS_PRODUCTION = False

def get_config_class() -> Type[Config]:
    """
    Identifica dinamicamente a classe de configuração baseada no ambiente.
    Considera VERCEL=1 ou APP_ENV=production ou FLASK_ENV=production para produção.
    """
    if os.getenv("FLASK_ENV") == "testing" or os.getenv("TESTING") in ("1", "true", "True"):
        return TestingConfig

    if is_production_mode():
        return ProductionConfig

    return DevelopmentConfig
