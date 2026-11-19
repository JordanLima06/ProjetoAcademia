from typing import List, Optional
from app.models.academy import Plano, Modalidade, OpcaoPagamento
from app.repositories.plan_repository import PlanRepository
from app.repositories.modality_repository import ModalityRepository

class AcademyService:
    """Regras de negócio para consulta e organização de planos e modalidades."""

    @classmethod
    def list_plans(cls, only_active: bool = True) -> List[Plano]:
        """Retorna todos os planos ativos."""
        return PlanRepository.get_all(only_active=only_active)

    @classmethod
    def get_plan(cls, slug: str) -> Optional[Plano]:
        """Busca um plano pelo slug textual."""
        return PlanRepository.get_by_slug(slug)

    @classmethod
    def get_plan_by_id(cls, plan_id: int) -> Optional[Plano]:
        """Busca um plano pelo identificador numérico."""
        return PlanRepository.get_by_id(plan_id)

    @classmethod
    def list_modalities(cls, only_active: bool = True) -> List[Modalidade]:
        """Retorna todas as modalidades ativas."""
        return ModalityRepository.get_all(only_active=only_active)

    @classmethod
    def get_modality(cls, slug: str) -> Optional[Modalidade]:
        """Busca uma modalidade pelo slug único."""
        return ModalityRepository.get_by_slug(slug)

    @classmethod
    def get_modality_by_id(cls, modality_id: int) -> Optional[Modalidade]:
        """Busca uma modalidade por seu ID."""
        return ModalityRepository.get_by_id(modality_id)

    @classmethod
    def list_modalities_by_plan(cls, plan_id: int, only_active: bool = True) -> List[Modalidade]:
        """Retorna as modalidades associadas a um plano específico."""
        return ModalityRepository.get_by_plan_id(plan_id, only_active=only_active)

    @classmethod
    def get_payment_options(cls, plan_id: int) -> List[OpcaoPagamento]:
        """Retorna as opções de pagamento cadastradas para um plano."""
        plano = cls.get_plan_by_id(plan_id)
        if plano and plano.opcoes_pagamento:
            return plano.opcoes_pagamento
        return []

    @classmethod
    def get_payment_option_by_id(cls, option_id: int) -> Optional[OpcaoPagamento]:
        """Busca uma opção de pagamento por seu ID."""
        return PlanRepository.get_payment_option_by_id(option_id)
