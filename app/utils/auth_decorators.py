import hmac
import logging
from functools import wraps
from flask import session, redirect, url_for, flash, abort, g, request
from app.repositories.user_repository import (
    UserRepository,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

def login_required(f):
    """
    Exige autenticação ativa.
    Recupera o usuário atualizado do PostgreSQL e o disponibiliza em g.user.
    Diferencia com rigor:
    - Usuário inexistente: limpa a sessão e redireciona.
    - Usuário inativo: limpa a sessão e redireciona.
    - Fingerprint divergente: limpa a sessão e redireciona (revogação de sessão desatualizada).
    - Indisponibilidade do PostgreSQL: retorna HTTP 503 sem limpar a sessão do usuário.
    - Erro inesperado de banco: retorna HTTP 500 sem limpar a sessão do usuário.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Faça login para acessar esta página.", "warning")
            return redirect(url_for("auth.login", next=request.path))

        try:
            user = UserRepository.find_by_id(user_id)
        except DatabaseConnectionError as conn_err:
            logger.error(f"PostgreSQL indisponível em @login_required: {conn_err}")
            return "Serviço temporariamente indisponível. Por favor, tente novamente em instantes.", 503
        except DatabaseError as db_err:
            logger.error(f"Erro inesperado no PostgreSQL em @login_required: {db_err}")
            return "Erro interno do servidor ao processar autenticação. Tente novamente mais tarde.", 500

        # Usuário inexistente
        if user is None:
            session.clear()
            flash("Sua conta não foi encontrada ou a sessão expirou. Faça login novamente.", "warning")
            return redirect(url_for("auth.login"))

        # Usuário inativo
        if not user.ativo:
            session.clear()
            flash("Sua conta está desativada. Entre em contato com a academia.", "danger")
            return redirect(url_for("auth.login"))

        # Validação da impressão digital da credencial (HMAC-SHA256 com compare_digest)
        auth_fp = session.get("auth_fingerprint")
        current_fp = AuthService.get_password_fingerprint(user.senha)
        if not auth_fp or not isinstance(auth_fp, str) or not hmac.compare_digest(auth_fp, current_fp):
            session.clear()
            flash("Sua senha foi alterada recentemente ou sua sessão expirou. Faça login novamente.", "warning")
            return redirect(url_for("auth.login"))

        g.user = user
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Exige permissão específica baseada no tipo de usuário.
    Verifica o tipo diretamente em g.user.tipo (atualizado em tempo real do PostgreSQL),
    não confiando exclusivamente no valor gravado na sessão.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Garante que g.user esteja populado com dados frescos do banco
            if not hasattr(g, "user") or g.user is None:
                user_id = session.get("user_id")
                if not user_id:
                    flash("Faça login para continuar.", "warning")
                    return redirect(url_for("auth.login", next=request.path))

                try:
                    user = UserRepository.find_by_id(user_id)
                except DatabaseConnectionError as conn_err:
                    logger.error(f"PostgreSQL indisponível em @role_required: {conn_err}")
                    return "Serviço temporariamente indisponível. Por favor, tente novamente em instantes.", 503
                except DatabaseError as db_err:
                    logger.error(f"Erro inesperado no PostgreSQL em @role_required: {db_err}")
                    return "Erro interno do servidor ao processar autenticação. Tente novamente mais tarde.", 500

                if user is None:
                    session.clear()
                    flash("Sua conta não foi encontrada ou a sessão expirou. Faça login novamente.", "warning")
                    return redirect(url_for("auth.login"))

                if not user.ativo:
                    session.clear()
                    flash("Sua conta está desativada. Faça login novamente.", "danger")
                    return redirect(url_for("auth.login"))

                auth_fp = session.get("auth_fingerprint")
                current_fp = AuthService.get_password_fingerprint(user.senha)
                if not auth_fp or not isinstance(auth_fp, str) or not hmac.compare_digest(auth_fp, current_fp):
                    session.clear()
                    flash("Sua senha foi alterada recentemente ou sua sessão expirou. Faça login novamente.", "warning")
                    return redirect(url_for("auth.login"))

                g.user = user

            if g.user.tipo not in allowed_roles:
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Retorna o usuário autenticado da requisição atual (g.user) ou None."""
    return getattr(g, "user", None)
