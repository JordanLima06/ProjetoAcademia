from flask import Flask, render_template, abort

app = Flask(__name__)

planos = [
    {
        "slug": "essencial",
        "nome": "Essencial",
        "preco": 79.90,
        "beneficios": ["Acesso à musculação", "Treino personalizado", "Avaliação física", "Area de cardio"]
    },
    {
        "slug": "perfomance",
        "nome": "Perfomance",
        "preco": 109.90,
        "beneficios": ["Todos os benefícios do plano Essencial", "Aulas de boxe", "Aulas de jiu-jitsu", "Aulas de funcional"]
    },
    {
        "slug": "premium",
        "nome": "Premium",
        "preco": 139.90,
        "beneficios": ["Todos os benefícios do plano Perfomance", "Treino personalizado", "Acompanhamento de evolução", "Acesso a todas modalidades"]
    }
]

modalidades = [
    {
        "slug": "musculacao",
        "nome": "Musculação",
        "descricao": "Treine com os melhores equipamentos e instrutores para alcançar seus objetivos de forma eficiente.",
        "imagem": "assets/musculacao.jpeg"
    },
    {
        "slug": "boxe",
        "nome": "Boxe",
        "descricao": "Aprenda técnicas de boxe com profissionais experientes e melhore sua resistência e força.",
        "imagem": "assets/boxe.jpeg"
    },
    {
        "slug": "jiu-jitsu",
        "nome": "Jiu-Jitsu",
        "descricao": "Desenvolva habilidades de defesa pessoal e condicionamento físico com aulas de Jiu-Jitsu.",
        "imagem": "assets/jiujitsu.jpeg"
    },
    {
        "slug": "funcional",
        "nome": "Funcional",
        "descricao": "Aulas dinâmicas que combinam força, resistência e flexibilidade para um treino completo.",
        "imagem": "assets/funcional.jpeg"
    },
    {
        "slug": "crossfit",
        "nome": "CrossFit",
        "descricao": "Treino de alta intensidade que combina exercícios funcionais e movimentos variados.",
        "imagem": "assets/crossfit.jpeg"
    }
]

@app.get("/")
def home():
    return render_template(
        "home.html",
        planos=planos,
        modalidades=modalidades
    )

@app.get("/planos")
def listar_planos():
    return render_template("planos.html", planos=planos)


@app.get("/modalidades/<slug>")
def detalhe_modalidade(slug):
    modalidade = next(
        (m for m in modalidades if m["slug"] == slug),
        None
    )

    if modalidade is None:
        abort(404)

    return render_template(
        "detalhes.html",
        item=modalidade,
        categoria="Modalidades"
    )

if __name__ == "__main__":
    app.run(debug=True)