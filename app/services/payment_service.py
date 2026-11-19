import logging
from typing import List, Optional
from datetime import date
from decimal import Decimal
from app.models.payment import Pagamento
from app.repositories.payment_repository import PaymentRepository

logger = logging.getLogger(__name__)

class PaymentService:
    """
    Camada de serviço responsável pelas regras de pagamentos demonstrativos/simulados da Fase 3.
    Regras fundamentais:
    - Zero processamento financeiro real ou integração com gateways externos.
    - Pagamentos demonstrativos são gravados individualmente por parcela com status 'pendente'.
    - NUNCA marcar pagamentos demonstrativos com status 'pago'.
    - Preservar rigorosamente as formas de pagamento permitidas pela CHECK constraint do PostgreSQL.
    """

    @classmethod
    def validar_forma_pagamento(cls, forma_pagamento: str) -> bool:
        """Verifica se a forma de pagamento é válida segundo as constraints do PostgreSQL."""
        return forma_pagamento in Pagamento.FORMAS_PAGAMENTO_PERMITIDAS

    @classmethod
    def gerar_parcelas_demonstrativas(
        cls,
        matricula_id: int,
        valor_total: Decimal,
        quantidade_parcelas: int,
        forma_pagamento: str,
        data_base_vencimento: Optional[date] = None,
        valor_cobranca: Optional[Decimal] = None
    ) -> List[Pagamento]:
        """
        Gera as parcelas demonstrativas individuais com status 'pendente' e pagamento_data=None.
        Garante a soma exata de R$ 1.399,90 no plano Anual (11x R$ 116,66 e 12ª de R$ 116,64).
        """
        if not cls.validar_forma_pagamento(forma_pagamento):
            raise ValueError(
                f"Forma de pagamento '{forma_pagamento}' não permitida. "
                f"Valores válidos: {Pagamento.FORMAS_PAGAMENTO_PERMITIDAS}"
            )

        return Pagamento.gerar_parcelas(
            matricula_id=matricula_id,
            valor_total=valor_total,
            quantidade_parcelas=quantidade_parcelas,
            forma_pagamento=forma_pagamento,
            data_base_vencimento=data_base_vencimento,
            valor_cobranca=valor_cobranca
        )

    @classmethod
    def salvar_parcelas_transacional(cls, cursor, parcelas: List[Pagamento]) -> List[Pagamento]:
        """Persiste em lote as parcelas de pagamento dentro do mesmo cursor da transação atômica."""
        return PaymentRepository.create_many_transactional(cursor, parcelas)

    @classmethod
    def cancelar_parcelas_pendentes_transacional(cls, cursor, matricula_id: int) -> int:
        """Cancela todas as parcelas pendentes vinculadas à matrícula dentro do cursor transacional."""
        return PaymentRepository.cancel_pending_by_matricula_id(cursor, matricula_id)

    @classmethod
    def listar_pagamentos_por_matricula(cls, matricula_id: int) -> List[Pagamento]:
        """Retorna o histórico de parcelas de pagamentos vinculadas a uma matrícula."""
        return PaymentRepository.list_by_matricula_id(matricula_id)

    @classmethod
    def obter_pagamento_por_id(cls, pagamento_id: int) -> Optional[Pagamento]:
        """Recupera um registro de pagamento por seu identificador numérico."""
        return PaymentRepository.find_by_id(pagamento_id)
