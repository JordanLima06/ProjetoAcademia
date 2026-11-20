import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.auth_service import AuthService
from app.services.academy_service import AcademyService

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Autentica o usuário e inicia a sessão segura."""
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        sucesso, mensagem, usuario = AuthService.authenticate(email, senha)
        if sucesso and usuario:
            # Limpa dados anteriores da sessão no cookie antes de preencher as novas credenciais
            session.clear()
            session.permanent = True
            session["user_id"] = usuario.id
            session["user_nome"] = usuario.nome
            session["user_email"] = usuario.email
            session["user_tipo"] = usuario.tipo
            session["auth_fingerprint"] = AuthService.get_password_fingerprint(usuario.senha)

            flash(mensagem, "success")
            next_url = request.args.get("next")
            # Validação simples de segurança de redirecionamento (apenas caminhos relativos)
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("main.home"))

        flash(mensagem, "danger")

    return render_template("login.html")

@auth_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    """Processa o cadastro de novos alunos no FightAcademy."""
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

        sucesso, mensagem, usuario, aluno = AuthService.register_aluno(dados)
        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("auth.login"))

        flash(mensagem, "danger")
        return render_template(
            "cadastro.html",
            planos=planos,
            modalidades=modalidades,
            dados=dados
        ), 400

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
