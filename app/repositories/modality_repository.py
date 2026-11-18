from typing import List, Optional
from app.models.academy import Modalidade

class ModalityRepository:
    """Repositório de dados e persistência das modalidades esportivas."""

    _DATA = [
        Modalidade(
            slug="musculacao",
            nome="Musculação",
            descricao="Treine com os melhores equipamentos e instrutores para alcançar seus objetivos de forma eficiente.",
            imagem="assets/musculacao.jpeg",
            tag="Força e Hipertrófia"
        ),
        Modalidade(
            slug="boxe",
            nome="Boxe",
            descricao="Aprenda técnicas de boxe com profissionais experientes e melhore sua resistência e força.",
            imagem="assets/boxe.jpeg",
            tag="Agilidade e Resistência"
        ),
        Modalidade(
            slug="jiu-jitsu",
            nome="Jiu-Jitsu",
            descricao="Desenvolva habilidades de defesa pessoal e condicionamento físico com aulas de Jiu-Jitsu.",
            imagem="assets/jiujitsu.jpeg",
            tag="Estratégia e controle"
        ),
        Modalidade(
            slug="funcional",
            nome="Funcional",
            descricao="Aulas dinâmicas que combinam força, resistência e flexibilidade para um treino completo.",
            imagem="assets/funcional.jpeg",
            tag="Mobilidade e equilíbrio"
        ),
        Modalidade(
            slug="crossfit",
            nome="CrossFit",
            descricao="Treino de alta intensidade que combina exercícios funcionais e movimentos variados.",
            imagem="assets/crossfit.jpeg",
            tag="Força e resistência"
        )
    ]

    @classmethod
    def get_all(cls) -> List[Modalidade]:
        return cls._DATA

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional[Modalidade]:
        return next((m for m in cls._DATA if m.slug == slug), None)
