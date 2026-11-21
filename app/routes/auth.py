import logging
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from flask_wtf.csrf import generate_csrf
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.academy_service import AcademyService
from app.services.enrollment_service import EnrollmentService

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


def _is_safe_next_url(next_url: str) -> bool:
    """Valida redirecionamento relativo seguro para evitar Open Redirect."""
    return bool(
        next_url
        and next_url.startswith("/")
        and not next_url.startswith("//")
        and not next_url.startswith("/\\")
    )


def _extract_contratar_slug(next_url: str):
    """Extrai o slug do plano quando next_url aponta para /contratar/<slug>."""
    if not _is_safe_next_url(next_url):
        return None
    prefix = "/contratar/"
    if not next_url.startswith(prefix):
        return None
    slug = next_url[len(prefix):].split("?", 1)[0].strip("/")
    if not slug or "/" in slug:
        return None
    return slug


def _ensure_csrf_session_sync():
    """
    Garante que session['csrf_token'] exista e esteja sincronizado com g.csrf_token,
    marcando session.modified = True para emissão explícita do cookie de sessão.
    """
    if "csrf_token" not in session:
        g.pop("csrf_token", None)
    token = generate_csrf()
    if "csrf_token" in session:
        session.modified = True
    return token


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Autentica o usuário e inicia a sessão segura preservando fluxo de contratação pendente."""
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        next_url = (request.form.get("next") or request.args.get("next") or "").strip()

        sucesso, mensagem, usuario = AuthService.authenticate(email, senha)
        if sucesso and usuario:
            # Captura seleção de plano pendente antes de limpar a sessão anônima
            pending_plan_slug = session.get("pending_plan_slug")
            pending_plan_user_id = session.get("pending_plan_user_id")

            # Limpa dados anteriores da sessão no cookie antes de preencher as novas credenciais
            session.clear()
            session.permanent = True
            session["user_id"] = usuario.id
            session["user_nome"] = usuario.nome
            session["user_email"] = usuario.email
            session["user_tipo"] = usuario.tipo
            session["auth_fingerprint"] = AuthService.get_password_fingerprint(usuario.senha)
            g.pop("csrf_token", None)
            generate_csrf()

            flash(mensagem, "success")

            next_contratar_slug = _extract_contratar_slug(next_url)
            pertence_a_outro_usuario = (
                pending_plan_user_id is not None
                and pending_plan_user_id != usuario.id
                and next_contratar_slug == pending_plan_slug
            )
            if pertence_a_outro_usuario:
                next_url = ""
                next_contratar_slug = None

            if usuario.tipo == "aluno":
                candidate_slug = next_contratar_slug
                if not candidate_slug and pending_plan_slug and (
                    pending_plan_user_id is None or pending_plan_user_id == usuario.id
                ):
                    candidate_slug = pending_plan_slug

                if candidate_slug:
                    plano_valido = AcademyService.get_plan(candidate_slug)
                    if plano_valido and plano_valido.ativo:
                        aluno = UserRepository.find_aluno_by_user_id(usuario.id)
                        matricula_atual = (
                            EnrollmentService.obter_matricula_atual(aluno.id) if aluno else None
                        )
                        possui_vigente = bool(
                            matricula_atual
                            and matricula_atual.status in ("ativa", "pendente")
                            and matricula_atual.data_fim >= date.today()
                        )
                        if possui_vigente:
                            return redirect(url_for("student.painel"))

                        session["pending_plan_slug"] = plano_valido.slug
                        session["pending_plan_user_id"] = usuario.id
                        return redirect(url_for("enrollment.contratar", plano_slug=plano_valido.slug))

            # Validação de segurança de redirecionamento (apenas caminhos relativos)
            if _is_safe_next_url(next_url):
                return redirect(next_url)
            return redirect(url_for("main.home"))

        flash(mensagem, "danger")
        _ensure_csrf_session_sync()
        safe_next = next_url if _is_safe_next_url(next_url) else ""
        return render_template("login.html", next_url=safe_next)

    # Garante sincronização explícita do token CSRF e emissão do cookie de sessão no GET /login
    _ensure_csrf_session_sync()

    next_url = (request.args.get("next") or "").strip()
    if not _is_safe_next_url(next_url):
        next_url = ""

    return render_template("login.html", next_url=next_url)


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    """Processa o cadastro de novos alunos no FightAcademy preservando o plano selecionado."""
    planos = AcademyService.list_plans()
    modalidades = AcademyService.list_modalities()

    if request.method == "POST":
        dados = {
            "nome": request.form.get("nome"),
            "email": request.form.get("email"),
            "telefone": request.form.get("telefone"),
            "data_nascimento": request.form.get("data_nascimento"),
            "senha": request.form.get("senha"),
            "confirmar": request.form.get("confirmar"),
            "plano": request.form.get("plano"),
            "modalidade": request.form.get("modalidade"),
            "objetivo": request.form.get("objetivo")
        }

        plano_slug = (dados.get("plano") or "").strip()
        plano_valido = None
        if plano_slug:
            plano_valido = AcademyService.get_plan(plano_slug)
            if not plano_valido or not plano_valido.ativo:
                flash("Plano selecionado não encontrado ou indisponível.", "danger")
                _ensure_csrf_session_sync()
                return render_template(
                    "cadastro.html",
                    planos=planos,
                    modalidades=modalidades,
                    dados=dados
                ), 400

        sucesso, mensagem, usuario, aluno = AuthService.register_aluno(dados)
        if sucesso:
            _ensure_csrf_session_sync()
            if plano_valido and plano_valido.ativo:
                session["pending_plan_slug"] = plano_valido.slug
                session["pending_plan_user_id"] = usuario.id
                session.modified = True
                flash(
                    f"Cadastro realizado com sucesso! Faça login para concluir a contratação do plano {plano_valido.nome}.",
                    "success"
                )
                return redirect(
                    url_for(
                        "auth.login",
                        next=url_for("enrollment.contratar", plano_slug=plano_valido.slug)
                    )
                )

            session.pop("pending_plan_slug", None)
            session.pop("pending_plan_user_id", None)
            session.modified = True
            flash(mensagem, "success")
            return redirect(url_for("auth.login"))

        flash(mensagem, "danger")
        _ensure_csrf_session_sync()
        return render_template(
            "cadastro.html",
            planos=planos,
            modalidades=modalidades,
            dados=dados
        ), 400

    # Garante sincronização explícita do token CSRF e emissão do cookie de sessão no GET /cadastro
    _ensure_csrf_session_sync()
    return render_template(
        "cadastro.html",
        planos=planos,
        modalidades=modalidades,
        dados={}
    )

@auth_bp.post("/logout")
def logout():
    """Encerra a sessão atual com limpeza completa via POST protegido por CSRF."""
    session.clear()
    g.pop("csrf_token", None)
    generate_csrf()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("main.home"))

@auth_bp.route("/recuperar-senha", methods=["POST"])
def solicitar_recuperacao():
    """
    Processa a solicitação de recuperação de senha.
    Documenta a dependência de um serviço de envio de e-mail (SMTP/API).
    Gera o token seguro assinado para uso do sistema.
    """
    email = request.form.get("email")
    sucesso, mensagem, token = AuthService.generate_password_reset_token(email)

    if sucesso and token:
        logger.info(
            f"[Recuperação de Senha] Serviço de envio de e-mail não configurado. "
            f"Token assinado gerado para '{email}': {token}"
        )
        flash(
            "O serviço de envio de e-mails para recuperação de senha não está configurado neste servidor. "
            "Contate o suporte da academia para redefinir seu acesso.",
            "warning"
        )
    else:
        flash(mensagem, "warning")

    return redirect(url_for("auth.login"))

@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    """Permite redefinir a senha através de token assinado temporário com proteção contra reutilização."""
    if request.method == "POST":
        nova_senha = request.form.get("senha")
        confirmar = request.form.get("confirmar")

        sucesso, mensagem = AuthService.validate_and_reset_password(token, nova_senha, confirmar)
        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("auth.login"))

        flash(mensagem, "danger")

    return render_template("login.html", token_redefinicao=token)
