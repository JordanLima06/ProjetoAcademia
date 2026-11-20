import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session
from app.utils.auth_decorators import login_required, role_required
from app.repositories.user_repository import UserRepository
from app.services.student_service import StudentService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

student_bp = Blueprint("student", __name__, url_prefix="/aluno")

@student_bp.route("/painel", methods=["GET"])
@login_required
@role_required("aluno")
def painel():
    """
    Dashboard central da Área do Aluno:
    Exibe dados do aluno, resumo da matrícula atual, modalidades liberadas,
    próximo vencimento de parcelas e atalhos rápidos.
    """
    dados_dashboard = StudentService.obter_dashboard_aluno(g.user.id)
    if not dados_dashboard:
        flash("Perfil de aluno não localizado.", "danger")
        return redirect(url_for("main.home"))

    return render_template(
        "aluno/painel.html",
        dashboard=dados_dashboard,
        user=dados_dashboard["user"],
        aluno=dados_dashboard["aluno"],
        matricula=dados_dashboard["matricula"],
        modalidades=dados_dashboard["modalidades_liberadas"],
        pagamentos=dados_dashboard["pagamentos"],
        parcelas_pagas=dados_dashboard["parcelas_pagas"],
        parcelas_pendentes=dados_dashboard["parcelas_pendentes"],
        proximo_vencimento=dados_dashboard["proximo_vencimento"],
        total_pago=dados_dashboard["total_pago"],
        total_pendente=dados_dashboard["total_pendente"]
    )

@student_bp.route("/perfil", methods=["GET", "POST"])
@login_required
@role_required("aluno")
def perfil():
    """
    Exibição e atualização de dados cadastrais permitidos do aluno (telefone, objetivo, data de nascimento).
    Garante que o aluno só consulte e altere os seus próprios dados (baseado em g.user.id).
    """
    aluno = UserRepository.find_aluno_by_user_id(g.user.id)
    if not aluno:
        flash("Perfil de aluno não localizado.", "danger")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        sucesso, mensagem, aluno_atualizado = StudentService.atualizar_perfil(
            user_id=g.user.id,
            dados=request.form
        )
        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("student.perfil"))
        else:
            flash(mensagem, "danger")
            # Em erro, renderiza com código 400 e os dados fornecidos para correção
            return render_template(
                "aluno/perfil.html",
                user=g.user,
                aluno=aluno,
                form_data=request.form
            ), 400

    return render_template(
        "aluno/perfil.html",
        user=g.user,
        aluno=aluno,
        form_data={}
    )

@student_bp.route("/alterar-senha", methods=["GET", "POST"])
@login_required
@role_required("aluno")
def alterar_senha():
    """
    Processa a alteração de senha autenticada do aluno.
    Exige validação da senha atual, complexidade mínima e confirmação.
    """
    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        sucesso, mensagem = StudentService.alterar_senha(
            user_id=g.user.id,
            senha_atual=senha_atual,
            nova_senha=nova_senha,
            confirmar_senha=confirmar_senha
        )

        if sucesso:
            # Preserva a sessão atual atualizando a referência da nova credencial
            user_atualizado = UserRepository.find_by_id(g.user.id)
            if user_atualizado:
                session["auth_fingerprint"] = AuthService.get_password_fingerprint(user_atualizado.senha)
            flash(mensagem, "success")
            return redirect(url_for("student.perfil"))
        else:
            flash(mensagem, "danger")
            return redirect(url_for("student.perfil"))

    # Redireciona GET direto para a tela de perfil onde o formulário está posicionado
    return redirect(url_for("student.perfil"))
