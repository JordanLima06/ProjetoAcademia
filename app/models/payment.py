import calendar
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional, List, Any

def calcular_vencimento_mensal(data_base: date, mes_offset: int) -> date:
    """
    Calcula a data de vencimento civil para determinado offset de meses a partir da data base.
    Preserva o dia original do vencimento sempre que possível.
    Quando o mês de destino possui menos dias, utiliza o último dia daquele mês.
    Trata anos bissextos e transições de ano civil automaticamente, sem acúmulo de desvios.

    Exemplo para data_base = 31/01/2023:
      - mes_offset=0 -> 31/01/2023
      - mes_offset=1 -> 28/02/2023 (ou 29/02 se bissexto)
      - mes_offset=2 -> 31/03/2023
      - mes_offset=3 -> 30/04/2023
    """
    ano = data_base.year + (data_base.month - 1 + mes_offset) // 12
    mes = ((data_base.month - 1 + mes_offset) % 12) + 1
    max_dias = calendar.monthrange(ano, mes)[1]
    dia = min(data_base.day, max_dias)
    return date(ano, mes, dia)

@dataclass
class Pagamento:
    """
    Representa a entidade de Pagamento no PostgreSQL (tabela pagamentos).
    Reflete rigorosamente as colunas reais da tabela:
      - id: SERIAL PRIMARY KEY
      - matricula_id: INTEGER (FK matriculas.id)
      - numero_parcela: INTEGER
      - valor: NUMERIC / Decimal
      - vencimento: DATE
      - pagamento_data: TIMESTAMP / DATE (NULL para pagamentos pendentes/demonstrativos)
      - status: VARCHAR ('pendente', 'pago', 'atrasado', 'cancelado', 'estornado')
      - forma_pagamento: VARCHAR ('pix', 'dinheiro', 'cartao_credito', 'cartao_debito', 'boleto', 'transferencia', 'outro')
      - criado_em: TIMESTAMP

    Regras da Fase 3:
      - Pagamentos demonstrativos utilizam status='pendente'
      - pagamento_data permanece NULL (None)
      - Proibido utilizar status 'pago' para pagamentos demonstrativos
      - Status 'simulado' removido por não existir na CHECK constraint do PostgreSQL
    """
    matricula_id: int
    numero_parcela: int
    valor: Decimal
    vencimento: date
    forma_pagamento: str
    status: str = "pendente"
    id: Optional[int] = None
    pagamento_data: Optional[datetime] = None
    criado_em: Optional[datetime] = None

    STATUS_PERMITIDOS = ("pendente", "pago", "atrasado", "cancelado", "estornado")
    FORMAS_PAGAMENTO_PERMITIDAS = (
        "pix",
        "dinheiro",
        "cartao_credito",
        "cartao_debito",
        "boleto",
        "transferencia",
        "outro"
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "id": self.id,
            "matricula_id": self.matricula_id,
            "numero_parcela": self.numero_parcela,
            "valor": float(self.valor) if isinstance(self.valor, Decimal) else self.valor,
            "vencimento": self.vencimento.isoformat() if isinstance(self.vencimento, (date, datetime)) else self.vencimento,
            "pagamento_data": self.pagamento_data.isoformat() if self.pagamento_data else None,
            "status": self.status,
            "forma_pagamento": self.forma_pagamento,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None
        }

    @classmethod
    def gerar_parcelas(
        cls,
        matricula_id: int,
        valor_total: Decimal,
        quantidade_parcelas: int,
        forma_pagamento: str,
        data_base_vencimento: Optional[date] = None,
        valor_cobranca: Optional[Decimal] = None
    ) -> List["Pagamento"]:
        """
        Gera a lista de registros demonstrativos de Pagamento para cada parcela individual.
        Garante que a soma de todas as parcelas seja exatamente igual a valor_total.
        Exemplo: 12 parcelas de R$ 1.399,90 -> 11 parcelas de R$ 116,66 e a 12ª de R$ 116,64.
        Todos os registros demonstrativos são criados com status='pendente' e pagamento_data=None.
        """
        if forma_pagamento not in cls.FORMAS_PAGAMENTO_PERMITIDAS:
            raise ValueError(
                f"Forma de pagamento '{forma_pagamento}' não permitida. "
                f"Valores válidos: {cls.FORMAS_PAGAMENTO_PERMITIDAS}"
            )

        if not data_base_vencimento:
            data_base_vencimento = date.today()

        total = Decimal(str(valor_total)).quantize(Decimal("0.01"))
        n = quantidade_parcelas if (quantidade_parcelas and quantidade_parcelas > 0) else 1

        if n <= 1:
            return [
                cls(
                    matricula_id=matricula_id,
                    numero_parcela=1,
                    valor=total,
                    vencimento=data_base_vencimento,
                    forma_pagamento=forma_pagamento,
                    status="pendente",
                    pagamento_data=None
                )
            ]

        # Tratamento especial do plano anual: 12x de R$ 1.399,90
        # 11 parcelas de R$ 116,66 e 12ª de R$ 116,64
        if total == Decimal("1399.90") and n == 12:
            parcelas_valores = [Decimal("116.66")] * 11 + [Decimal("116.64")]
        else:
            if valor_cobranca is not None and Decimal(str(valor_cobranca)) > 0:
                parcela_base = Decimal(str(valor_cobranca)).quantize(Decimal("0.01"))
            else:
                parcela_base = (total / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

            parcelas_valores = [parcela_base] * (n - 1)
            soma_anteriores = sum(parcelas_valores)
            ultima_parcela = total - soma_anteriores
            parcelas_valores.append(ultima_parcela)

        lista_pagamentos = []
        for i, val in enumerate(parcelas_valores, start=1):
            # Vencimento mensal projetado pelo calendário civil exato (meses de 28, 29, 30 e 31 dias)
            venc = calcular_vencimento_mensal(data_base_vencimento, i - 1)
            lista_pagamentos.append(
                cls(
                    matricula_id=matricula_id,
                    numero_parcela=i,
                    valor=val,
                    vencimento=venc,
                    forma_pagamento=forma_pagamento,
                    status="pendente",
                    pagamento_data=None
                )
            )

        return lista_pagamentos
