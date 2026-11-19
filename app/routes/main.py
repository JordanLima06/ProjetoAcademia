from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from app.services.academy_service import AcademyService
from app.services.trial_service import TrialService

main_bp = Blueprint("main", __name__)

@main_bp.get("/")
def home():
    planos = AcademyService.list_plans()
    modalidades = AcademyService.list_modalities()
    return render_template(
        "home.html",
        planos=planos,
        modalidades=modalidades
    )

@main_bp.get("/planos")
def listar_planos():
    planos = AcademyService.list_plans()
    return render_template("planos.html", planos=planos)

@main_bp.get("/modalidades/<slug>")
def detalhe_modalidade(slug):
    modalidade = AcademyService.get_modality(slug)
    if modalidade is None:
        abort(404)

    return render_template(
        "detalhes.html",
        item=modalidade,
        categoria="Modalidades"
    )

@main_bp.get("/modalidades")
def modalidade():
    modalidades = AcademyService.list_modalities()
    return render_template(
        "modalidades.html",
        modalidades=modalidades
    )

@main_bp.get("/sobre")
def sobre():
    return render_template("sobre.html")

@main_bp.get("/design")
def design_system():
    return render_template("design.html")

@main_bp.route("/aula-experimental", methods=["GET", "POST"])
def aula_experimental():
    modalidades = AcademyService.list_modalities()

    if request.method == "POST":
        dados = {
            "nome": request.form.get("nome"),
            "telefone": request.form.get("telefone"),
            "email": request.form.get("email"),
            "modalidade_id": request.form.get("modalidade_id"),
            "dia_preferido": request.form.get("dia_preferido"),
            "periodo_preferido": request.form.get("periodo_preferido"),
            "objetivo": request.form.get("objetivo")
        }

        sucesso, mensagem, solicitacao = TrialService.solicitar_aula(dados)
        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("main.aula_experimental", sucesso="1"))

        flash(mensagem, "danger")
        return render_template(
            "aula_experimental.html",
            modalidades=modalidades,
            dados=dados,
            modalidade_param=str(dados.get("modalidade_id") or "")
        ), 400

    modalidade_param = (request.args.get("modalidade") or request.args.get("modalidade_id") or "").strip()
    sucesso_param = request.args.get("sucesso") == "1"

    return render_template(
        "aula_experimental.html",
        modalidades=modalidades,
        modalidade_param=modalidade_param,
        sucesso=sucesso_param,
        dados={}
    )
