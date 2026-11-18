from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        sucesso, mensagem, usuario = AuthService.authenticate(email, senha)
        if sucesso and usuario:
            session["user_id"] = usuario.id
            session["user_nome"] = usuario.nome
            flash(mensagem, "success")
            return redirect(url_for("home"))
        flash(mensagem, "danger")

    return render_template("login.html")

@auth_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        confirmar = request.form.get("confirmar")

        sucesso, mensagem, usuario = AuthService.register(nome, email, senha, confirmar)
        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("login"))
        flash(mensagem, "danger")

    return render_template("cadastro.html")

@auth_bp.get("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.", "info")
    return redirect(url_for("home"))
