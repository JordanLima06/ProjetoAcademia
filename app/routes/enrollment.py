import logging
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from app.utils.auth_decorators import login_required, role_required
from app.repositories.user_repository import UserRepository
from app.services.academy_service import AcademyService
from app.services.enrollment_service import EnrollmentService
from app.services.payment_service import PaymentService
from app.models.payment import Pagamento

logger = logging.getLogger(__name__)

enrollment_bp = Blueprint("enrollment", __name__)

@enrollment_bp.route("/contratar/<plano_slug>", methods=["GET"])
@login_required
@role_required("aluno")
def contratar(plano_slug):
    """
    Exibe a tela de contratação demonstrativa do plano selecionado.
    Apresenta resumo do plano, modalidades liberadas, opções comerciais e seleção de pagamento simulado.
    """
    aluno = UserRepository.find_aluno_by_user_id(g.user.id)
    if not aluno:
        flash("Perfil de aluno não localizado.", "danger")
        return redirect(url_for("main.home"))

    # Verifica se já possui matrícula vigente (ativa ou pendente)
    matricula_atual = EnrollmentService.obter_matricula_atual(aluno.id)
    if matricula_atual and matricula_atual.status in ("ativa", "pendente") and matricula_atual.data_fim >= date.today():
        nome_plano = matricula_atual.plano.nome if matricula_atual.plano else "atual"
        status_nome = "ativa" if matricula_atual.status == "ativa" else "pendente de pagamento"
        flash(
            f"Você já possui uma matrícula {status_nome} no plano {nome_plano}. "
            "Consulte os detalhes na área da sua matrícula.",
            "info"
        )
        return redirect(url_for("enrollment.minha_matricula"))

    plano = AcademyService.get_plan(plano_slug)
    if not plano or not plano.ativo:
        flash("Plano não encontrado ou indisponível.", "danger")
        return redirect(url_for("main.listar_planos"))

    modalidades = AcademyService.list_modalities_by_plan(plano.id)
    opcoes_pagamento = plano.opcoes_pagamento

    formas_pagamento = [
        {"codigo": "pix", "nome": "PIX (Simulação Instantânea)"},
        {"codigo": "cartao_credito", "nome": "Cartão de Crédito (Simulação de Parcelas)"},
        {"codigo": "boleto", "nome": "Boleto Bancário (Simulação)"}
    ]

    return render_template(
        "contratar.html",
        plano=plano,
        modalidades=modalidades,
        opcoes_pagamento=opcoes_pagamento,
        formas_pagamento=formas_pagamento,
        aluno=aluno
    )

@enrollment_bp.route("/contratar/<plano_slug>", methods=["POST"])
@login_required
@role_required("aluno")
def processar_contratacao(plano_slug):
    """
    Processa a contratação demonstrativa em transação atômica única no PostgreSQL.
    """
    aluno = UserRepository.find_aluno_by_user_id(g.user.id)
    if not aluno:
        flash("Perfil de aluno não localizado.", "danger")
        return redirect(url_for("main.home"))

    opcao_id_raw = request.form.get("opcao_pagamento_id")
    forma_pagamento = request.form.get("forma_pagamento", "").strip()

    if not opcao_id_raw:
        flash("Por favor, selecione uma condição comercial de pagamento.", "warning")
        return redirect(url_for("enrollment.contratar", plano_slug=plano_slug))

    if not forma_pagamento or forma_pagamento not in Pagamento.FORMAS_PAGAMENTO_PERMITIDAS:
        flash("Por favor, selecione uma forma de pagamento válida.", "warning")
        return redirect(url_for("enrollment.contratar", plano_slug=plano_slug))

    try:
        opcao_pagamento_id = int(opcao_id_raw)
    except (ValueError, TypeError):
        flash("Identificador de condição comercial inválido.", "danger")
        return redirect(url_for("enrollment.contratar", plano_slug=plano_slug))

    sucesso, matricula, mensagem = EnrollmentService.contratar_plano_demonstrativo(
        aluno_id=aluno.id,
        plano_slug=plano_slug,
        opcao_pagamento_id=opcao_pagamento_id,
        forma_pagamento=forma_pagamento
    )

    if sucesso:
        flash(mensagem, "success")
        return redirect(url_for("enrollment.minha_matricula"))
    else:
        flash(mensagem, "danger")
        return redirect(url_for("enrollment.contratar", plano_slug=plano_slug))

@enrollment_bp.route("/minha-matricula", methods=["GET"])
@login_required
@role_required("aluno")
def minha_matricula():
    """
    Exibe a área do aluno com detalhes da matrícula ativa, modalidades liberadas
    e histórico de parcelas demonstrativas.
    """
    aluno = UserRepository.find_aluno_by_user_id(g.user.id)
    if not aluno:
        flash("Perfil de aluno não localizado.", "danger")
        return redirect(url_for("main.home"))

    matricula_ativa = EnrollmentService.obter_matricula_ativa(aluno.id)
    pagamentos = []
    if matricula_ativa:
        pagamentos = PaymentService.listar_pagamentos_por_matricula(matricula_ativa.id)

    historico = EnrollmentService.obter_historico_matriculas(aluno.id)

    return render_template(
        "minha_matricula.html",
        matricula=matricula_ativa,
        pagamentos=pagamentos,
        historico=historico,
        aluno=aluno
    )

@enrollment_bp.route("/minha-matricula/cancelar", methods=["POST"])
@login_required
@role_required("aluno")
def cancelar_matricula():
    """Cancela a matrícula ativa do aluno."""
    aluno = UserRepository.find_aluno_by_user_id(g.user.id)
    if not aluno:
        flash("Perfil de aluno não localizado.", "danger")
        return redirect(url_for("main.home"))

    matricula_id_raw = request.form.get("matricula_id")
    if not matricula_id_raw:
        flash("Matrícula não informada para cancelamento.", "warning")
        return redirect(url_for("enrollment.minha_matricula"))

    try:
        matricula_id = int(matricula_id_raw)
    except (ValueError, TypeError):
        flash("Identificador de matrícula inválido.", "danger")
        return redirect(url_for("enrollment.minha_matricula"))

    sucesso, mensagem = EnrollmentService.cancelar_matricula(aluno.id, matricula_id)
    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("enrollment.minha_matricula"))
