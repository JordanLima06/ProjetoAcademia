from flask import Blueprint, render_template, abort
from app.services.academy_service import AcademyService

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
