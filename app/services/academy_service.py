from typing import List, Optional
from app.models.academy import Plano, Modalidade
from app.repositories.plan_repository import PlanRepository
from app.repositories.modality_repository import ModalityRepository

class AcademyService:
    """Regras de negócio para consulta e organização de planos e modalidades."""

    @classmethod
    def list_plans(cls) -> List[Plano]:
        return PlanRepository.get_all()

    @classmethod
    def get_plan(cls, slug: str) -> Optional[Plano]:
        return PlanRepository.get_by_slug(slug)

    @classmethod
    def list_modalities(cls) -> List[Modalidade]:
        return ModalityRepository.get_all()

    @classmethod
    def get_modality(cls, slug: str) -> Optional[Modalidade]:
        return ModalityRepository.get_by_slug(slug)

    @classmethod
    def get_modality_by_id(cls, modality_id: int) -> Optional[Modalidade]:
        return ModalityRepository.get_by_id(modality_id)
