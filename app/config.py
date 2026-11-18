import os

class Config:
    """Configurações base da aplicação."""
    SECRET_KEY = os.getenv("SECRET_KEY", "fightacademy-secret-key-dev-change-in-production")
    DEBUG = False
    TESTING = False

    # Configurações do PostgreSQL
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "academia")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

class DevelopmentConfig(Config):
    """Configurações para ambiente de desenvolvimento."""
    DEBUG = True

class ProductionConfig(Config):
    """Configurações para ambiente de produção."""
    DEBUG = False

class TestingConfig(Config):
    """Configurações para execução de testes."""
    TESTING = True
    DEBUG = True
