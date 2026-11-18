from typing import List, Optional
from app.models.academy import Plano

class PlanRepository:
    """Repositório de dados e persistência dos planos de treinamento."""

    _DATA = [
        Plano(
            slug="essencial",
            nome="Essencial",
            preco=79.90,
            beneficios=["Acesso à musculação", "Treino personalizado", "Avaliação física", "Area de cardio"]
        ),
        Plano(
            slug="perfomance",
            nome="Perfomance",
            preco=109.90,
            beneficios=["Todos os benefícios do plano Essencial", "Aulas de boxe", "Aulas de jiu-jitsu", "Aulas de funcional"]
        ),
        Plano(
            slug="premium",
            nome="Premium",
            preco=139.90,
            beneficios=["Todos os benefícios do plano Perfomance", "Treino personalizado", "Acompanhamento de evolução", "Acesso a todas modalidades"]
        ),
        Plano(
            slug="anual",
            nome="Anual",
            preco=1399.90,
            beneficios=["Tudo do plano Premium", "Um mês bônus", "Consultoria nutricional", "Sem taxa de matrícula"]
        )
    ]

    @classmethod
    def get_all(cls) -> List[Plano]:
        return cls._DATA

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional[Plano]:
        return next((p for p in cls._DATA if p.slug == slug), None)
