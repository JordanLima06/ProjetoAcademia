from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Any

@dataclass
class SolicitacaoAulaExperimental:
    """
    Entidade que representa uma solicitação de aula experimental de um visitante.
    Reflete a tabela solicitacoes_aula_experimental no PostgreSQL.
    """
    nome: str
    telefone: str
    modalidade_id: Optional[int]
    email: Optional[str] = None
    dia_preferido: Optional[date] = None
    periodo_preferido: Optional[str] = None
    objetivo: Optional[str] = None
    status: str = "nova"
    id: Optional[int] = None
    criado_em: Optional[datetime] = None

    # Status permitidos pelo CHECK da tabela
    STATUS_VALIDOS = ("nova", "contatada", "agendada", "realizada", "cancelada")

    # Períodos permitidos pelo CHECK da tabela
    PERIODOS_VALIDOS = ("manha", "tarde", "noite")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "telefone": self.telefone,
            "email": self.email,
            "modalidade_id": self.modalidade_id,
            "dia_preferido": self.dia_preferido.isoformat() if isinstance(self.dia_preferido, date) else self.dia_preferido,
            "periodo_preferido": self.periodo_preferido,
            "objetivo": self.objetivo,
            "status": self.status,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None
        }
