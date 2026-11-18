import os
import logging
from flask import g, current_app

logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Retorna uma conexão ativa com o banco PostgreSQL no contexto da requisição (g.db).
    Caso psycopg2 não esteja instalado ou o banco esteja inacessível, retorna None ou lança erro amigável.
    """
    if "db" not in g:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(
                host=current_app.config.get("DB_HOST", "localhost"),
                port=current_app.config.get("DB_PORT", "5432"),
                dbname=current_app.config.get("DB_NAME", "fightacademy_db"),
                user=current_app.config.get("DB_USER", "postgres"),
                password=current_app.config.get("DB_PASSWORD", "postgres"),
                cursor_factory=RealDictCursor
            )
            g.db = conn
        except ImportError:
            logger.warning("psycopg2 não está instalado. Instale com 'pip install psycopg2-binary' para persistência PostgreSQL.")
            g.db = None
        except Exception as e:
            logger.error(f"Erro ao conectar ao PostgreSQL: {e}")
            g.db = None

    return g.db

def close_db(e=None):
    """Fecha a conexão com o banco ao finalizar o contexto da requisição."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    """Registra funções de ciclo de vida do banco no aplicativo Flask."""
    app.teardown_appcontext(close_db)
