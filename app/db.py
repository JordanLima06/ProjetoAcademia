import os
import re
import logging
from flask import g, current_app, has_app_context
from app.config import Config, is_production_mode

logger = logging.getLogger(__name__)

def normalize_database_url(url: str) -> str:
    """
    Normaliza a URL do PostgreSQL para psycopg2:
    - Converte prefixo legado 'postgres://' para 'postgresql://' se presente.
    - Preserva integralmente todos os parâmetros originais da conexão Neon
      (ex: sslmode=require, channel_binding=require, endpoint, etc.).
    """
    if not url:
        return ""
    sanitized = url.strip()
    if sanitized.startswith("postgres://"):
        sanitized = "postgresql://" + sanitized[len("postgres://"):]
    return sanitized

def _sanitize_db_error(e: Exception) -> str:
    """Remove senhas e dados sensíveis de mensagens de erro para evitar vazamento em logs."""
    msg = str(e)
    # Mascara formato URI :password@
    msg = re.sub(r":([^:@\s]+)@", ":*****@", msg)
    # Mascara formato chave-valor password=xxx
    msg = re.sub(r"(password\s*=\s*)([^\s;]+)", r"\1*****", msg, flags=re.IGNORECASE)
    return msg

def _get_config_value(key: str, default=None):
    """Recupera valor de configuração de forma segura com fallback para app.config.Config."""
    if has_app_context() and current_app:
        return current_app.config.get(key, getattr(Config, key, default))
    return getattr(Config, key, default)

def get_db_connection():
    """
    Retorna uma conexão ativa com o banco PostgreSQL no contexto da requisição (g.db)
    ou uma nova conexão quando fora do contexto web.
    
    Regras de conexão:
    1. Prioriza DATABASE_URL (ou POSTGRES_URL) como URI completa para Neon / Vercel.
    2. Em ambiente de produção, a ausência de URL gera erro explícito de configuração,
       sendo estritamente proibido o uso de localhost como fallback.
    3. No desenvolvimento local sem URL, utiliza os parâmetros individuais (DB_HOST, etc.).
    4. Garante a preservação do cursor_factory=RealDictCursor em ambos os modos.
    5. Mascara credenciais e senhas em quaisquer logs de exceção.
    """
    in_context = has_app_context()

    if in_context and "db" in g:
        return g.db

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # 1. Recupera DATABASE_URL ou POSTGRES_URL prioritariamente
        database_url = _get_config_value("DATABASE_URL")
        if not database_url:
            database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

        is_prod = is_production_mode()
        if in_context and current_app and current_app.config.get("IS_PRODUCTION"):
            is_prod = True

        # 2. Em produção, a ausência de DATABASE_URL ou POSTGRES_URL é proibida
        if is_prod and not database_url:
            logger.error(
                "Falha crítica de configuração em produção: DATABASE_URL ou POSTGRES_URL não configurada. "
                "O uso de localhost como fallback em ambiente de produção é estritamente proibido."
            )
            raise RuntimeError(
                "Configuração inválida para produção: DATABASE_URL ou POSTGRES_URL não configurada. "
                "É estritamente proibido utilizar localhost como fallback em ambiente de produção."
            )

        # 3. Conexão via URI completa (Neon / Vercel / Produção)
        if database_url:
            normalized_url = normalize_database_url(database_url)
            conn = psycopg2.connect(
                normalized_url,
                cursor_factory=RealDictCursor
            )
        else:
            # 4. Fallback exclusivo para desenvolvimento local com parâmetros individuais
            conn = psycopg2.connect(
                host=_get_config_value("DB_HOST", Config.DB_HOST),
                port=_get_config_value("DB_PORT", Config.DB_PORT),
                dbname=_get_config_value("DB_NAME", Config.DB_NAME),
                user=_get_config_value("DB_USER", Config.DB_USER),
                password=_get_config_value("DB_PASSWORD", Config.DB_PASSWORD),
                cursor_factory=RealDictCursor
            )

        if in_context:
            g.db = conn
        return conn
    except ImportError:
        logger.error("psycopg2 não está instalado. Instale psycopg2-binary para conexão com PostgreSQL.")
        return None
    except RuntimeError:
        # Re-lança exceção de validação explícita de produção
        raise
    except Exception as e:
        safe_msg = _sanitize_db_error(e)
        logger.error(f"Erro ao conectar ao PostgreSQL: {safe_msg}")
        return None

def close_db(e=None):
    """Fecha a conexão com o banco ao finalizar o contexto da requisição."""
    if has_app_context():
        db = g.pop("db", None)
        if db is not None:
            try:
                db.close()
            except Exception as close_err:
                logger.warning(f"Erro ao fechar conexão com o banco: {close_err}")

def init_app(app):
    """Registra funções de ciclo de vida do banco no aplicativo Flask."""
    app.teardown_appcontext(close_db)
