from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any
from app.models.academy import Plano, Modalidade
from app.models.user import Aluno

@dataclass
class MatriculaModalidade:
    """
    Representa o vínculo de uma modalidade esportiva liberada para uma matrícula específica.
    Reflete a tabela matricula_modalidades no PostgreSQL.
    Colunas reais:
      - matricula_id: INTEGER
      - plano_id: INTEGER (parte da chave estrangeira composta)
      - modalidade_id: INTEGER
    """
    matricula_id: int
    plano_id: int
    modalidade_id: int

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "matricula_id": self.matricula_id,
            "plano_id": self.plano_id,
            "modalidade_id": self.modalidade_id
        }

@dataclass
class Matricula:
    """
    Representa a entidade de Matrícula de um Aluno em um Plano.
    Reflete rigorosamente as colunas reais da tabela matriculas no PostgreSQL:
      - id: SERIAL PRIMARY KEY
      - aluno_id: INTEGER (FK alunos.id)
      - plano_id: INTEGER (FK planos.id)
      - data_inicio: DATE
      - data_fim: DATE
      - status: VARCHAR ('pendente', 'ativa', 'suspensa', 'encerrada', 'cancelada')
      - opcao_pagamento_id: INTEGER (FK opcoes_pagamento_planos.id)
      - tipo_cobranca: VARCHAR
      - valor_cobranca: NUMERIC / Decimal
      - valor_total_contratado: NUMERIC / Decimal
      - quantidade_parcelas: INTEGER
      - criado_em: TIMESTAMP
    """
    aluno_id: int
    plano_id: int
    data_inicio: date
    data_fim: date
    status: str = "ativa"
    opcao_pagamento_id: Optional[int] = None
    tipo_cobranca: Optional[str] = None
    valor_cobranca: Optional[Decimal] = None
    valor_total_contratado: Optional[Decimal] = None
    quantidade_parcelas: Optional[int] = 1
    id: Optional[int] = None
    criado_em: Optional[datetime] = None

    # Agregações opcionais de conveniência
    plano: Optional[Plano] = None
    aluno: Optional[Aluno] = None
    modalidades: List[Modalidade] = field(default_factory=list)

    STATUS_PERMITIDOS = ("pendente", "ativa", "suspensa", "encerrada", "cancelada")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def is_ativa(self) -> bool:
        """Verifica se a matrícula possui status 'ativa' e está dentro da vigência."""
        hoje = date.today()
        fim = self.data_fim
        if isinstance(fim, str):
            fim = date.fromisoformat(fim)
        return self.status == "ativa" and fim >= hoje

    def to_dict(self):
        return {
            "id": self.id,
            "aluno_id": self.aluno_id,
            "plano_id": self.plano_id,
            "data_inicio": self.data_inicio.isoformat() if isinstance(self.data_inicio, (date, datetime)) else self.data_inicio,
            "data_fim": self.data_fim.isoformat() if isinstance(self.data_fim, (date, datetime)) else self.data_fim,
            "status": self.status,
            "opcao_pagamento_id": self.opcao_pagamento_id,
            "tipo_cobranca": self.tipo_cobranca,
            "valor_cobranca": float(self.valor_cobranca) if isinstance(self.valor_cobranca, Decimal) else self.valor_cobranca,
            "valor_total_contratado": float(self.valor_total_contratado) if isinstance(self.valor_total_contratado, Decimal) else self.valor_total_contratado,
            "quantidade_parcelas": self.quantidade_parcelas,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "plano": self.plano.to_dict() if self.plano else None,
            "modalidades": [m.to_dict() for m in self.modalidades]
        }
