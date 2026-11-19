from functools import wraps
from flask import session, redirect, url_for, flash, abort, g, request
from app.repositories.user_repository import UserRepository

def login_required(f):
    """
    Exige autenticação ativa.
    Recupera o usuário atualizado do PostgreSQL e o disponibiliza em g.user.
    Se o usuário não existir ou estiver inativo, limpa a sessão e redireciona para o login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Faça login para acessar esta página.", "warning")
            return redirect(url_for("auth.login", next=request.path))

        user = UserRepository.find_by_id(user_id)
        if not user or not user.ativo:
            session.clear()
            flash("Sua conta está desativada ou a sessão expirou. Faça login novamente.", "danger")
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
                user = UserRepository.find_by_id(user_id)
                if not user or not user.ativo:
                    session.clear()
                    flash("Sua conta está desativada. Faça login novamente.", "danger")
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
