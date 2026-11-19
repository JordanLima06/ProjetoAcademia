import logging
from typing import List, Optional, Dict
from datetime import datetime, date
from decimal import Decimal
from flask import current_app, has_app_context
from app.db import get_db_connection
from app.models.payment import Pagamento

logger = logging.getLogger(__name__)

class PaymentRepository:
    """
    Repositório de persistência e consultas SQL para a tabela pagamentos.
    Utiliza rigorosamente as colunas reais do schema do PostgreSQL:
      - id: SERIAL PRIMARY KEY
      - matricula_id: INTEGER (FK matriculas.id)
      - numero_parcela: INTEGER
      - valor: NUMERIC / Decimal
      - vencimento: DATE
      - pagamento_data: TIMESTAMP / DATE (NULL para demonstrativos)
      - status: VARCHAR ('pendente', 'pago', 'cancelado', etc.)
      - forma_pagamento: VARCHAR ('pix', 'dinheiro', 'cartao_credito', etc.)
      - criado_em: TIMESTAMP
    """

    # Armazenamento em memória exclusivo para testes automatizados isolados quando TESTING=True e sem conexão DB
    _TEST_PAGAMENTOS: Dict[int, Pagamento] = {}
    _TEST_ID_SEQ = 1

    @classmethod
    def _is_testing(cls) -> bool:
        return has_app_context() and bool(current_app.config.get("TESTING"))

    @classmethod
    def create_transactional(cls, cursor, pagamento: Pagamento) -> Pagamento:
        """
        Insere um registro demonstrativo de parcela de pagamento utilizando o cursor de uma transação ativa.

        Regras obrigatórias:
        - Pagamentos demonstrativos NUNCA recebem status 'pago'.
        - O status 'simulado' é removido por não existir na constraint do banco; usa-se 'pendente'.
        - Para pagamentos pendentes demonstrativos, pagamento_data deve ser NULL (None).
        - A forma_pagamento deve respeitar a constraint do PostgreSQL.
        """
        # Trava de segurança para demonstrativos
        if pagamento.status in ("simulado", "pago"):
            logger.warning(
                f"Status '{pagamento.status}' inadequado para registro demonstrativo. "
                "Ajustando obrigatoriamente para 'pendente'."
            )
            pagamento.status = "pendente"

        if pagamento.status == "pendente":
            pagamento.pagamento_data = None

        if pagamento.forma_pagamento not in Pagamento.FORMAS_PAGAMENTO_PERMITIDAS:
            raise ValueError(
                f"Forma de pagamento '{pagamento.forma_pagamento}' não permitida pelo banco. "
                f"Permitidas: {Pagamento.FORMAS_PAGAMENTO_PERMITIDAS}"
            )

        cursor.execute(
            """
            INSERT INTO pagamentos (
                matricula_id,
                numero_parcela,
                valor,
                vencimento,
                pagamento_data,
                status,
                forma_pagamento
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, criado_em
            """,
            (
                pagamento.matricula_id,
                pagamento.numero_parcela,
                pagamento.valor,
                pagamento.vencimento,
                pagamento.pagamento_data,
                pagamento.status,
                pagamento.forma_pagamento
            )
        )
        row = cursor.fetchone()
        pagamento.id = row["id"]
        pagamento.criado_em = row.get("criado_em")

        logger.info(
            f"Registro de pagamento id={pagamento.id} (parcela {pagamento.numero_parcela}, "
            f"valor={pagamento.valor}, status={pagamento.status}) gravado com sucesso no cursor transacional."
        )
        return pagamento

    @classmethod
    def create_many_transactional(cls, cursor, pagamentos: List[Pagamento]) -> List[Pagamento]:
        """
        Insere uma coleção de parcelas de pagamento na mesma transação atômica.
        Garante a gravação de cada parcela individual (ex.: 12 parcelas do plano anual).
        """
        resultados = []
        for p in pagamentos:
            gravado = cls.create_transactional(cursor, p)
            resultados.append(gravado)
        return resultados

    @classmethod
    def cancel_pending_by_matricula_id(cls, cursor, matricula_id: int) -> int:
        """
        Atualiza o status de todas as parcelas pendentes vinculadas à matrícula para 'cancelado'.
        Preserva rigorosamente parcelas com qualquer outro status (ex.: pago, falhou, estornado).
        Retorna a quantidade de parcelas atualizadas.
        """
        if not matricula_id:
            return 0

        if cursor is not None:
            cursor.execute(
                """
                UPDATE pagamentos
                SET status = 'cancelado'
                WHERE matricula_id = %s
                AND status = 'pendente'
                """,
                (matricula_id,)
            )
            afetados = cursor.rowcount
            logger.info(f"{afetados} pagamentos pendentes da matrícula id={matricula_id} foram atualizados para 'cancelado'.")
            return afetados

        # Fallback de teste em memória
        if cls._is_testing():
            afetados = 0
            for p in cls._TEST_PAGAMENTOS.values():
                if p.matricula_id == matricula_id and p.status == "pendente":
                    p.status = "cancelado"
                    afetados += 1
            return afetados

        return 0

    @classmethod
    def find_by_id(cls, pagamento_id: int) -> Optional[Pagamento]:
        """Busca um pagamento pelo seu ID numérico no PostgreSQL com todas as colunas reais."""
        if not pagamento_id:
            return None

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar pagamento id {pagamento_id}.")
            if cls._is_testing():
                return cls._TEST_PAGAMENTOS.get(pagamento_id)
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, matricula_id, numero_parcela, valor, vencimento,
                           pagamento_data, status, forma_pagamento, criado_em
                    FROM pagamentos
                    WHERE id = %s
                    """,
                    (pagamento_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                return cls._row_to_pagamento(row)
        except Exception as e:
            logger.error(f"Erro ao buscar pagamento id {pagamento_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return cls._TEST_PAGAMENTOS.get(pagamento_id)
            return None

    @classmethod
    def list_by_matricula_id(cls, matricula_id: int) -> List[Pagamento]:
        """Retorna o histórico de parcelas de pagamentos vinculadas a uma matrícula."""
        if not matricula_id:
            return []

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao listar pagamentos da matrícula {matricula_id}.")
            if cls._is_testing():
                lista = [p for p in cls._TEST_PAGAMENTOS.values() if p.matricula_id == matricula_id]
                return sorted(lista, key=lambda p: (p.numero_parcela, p.id or 0))
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, matricula_id, numero_parcela, valor, vencimento,
                           pagamento_data, status, forma_pagamento, criado_em
                    FROM pagamentos
                    WHERE matricula_id = %s
                    ORDER BY numero_parcela ASC, id ASC
                    """,
                    (matricula_id,)
                )
                rows = cursor.fetchall()
                return [cls._row_to_pagamento(row) for row in rows]
        except Exception as e:
            logger.error(f"Erro ao listar pagamentos da matrícula {matricula_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                lista = [p for p in cls._TEST_PAGAMENTOS.values() if p.matricula_id == matricula_id]
                return sorted(lista, key=lambda p: (p.numero_parcela, p.id or 0))
            return []

    @staticmethod
    def _row_to_pagamento(row: dict) -> Pagamento:
        """Converte dicionário retornado do PostgreSQL em uma instância de Pagamento com precisão Decimal."""
        return Pagamento(
            id=row["id"],
            matricula_id=row["matricula_id"],
            numero_parcela=row["numero_parcela"],
            valor=Decimal(str(row["valor"])),
            vencimento=row["vencimento"],
            pagamento_data=row.get("pagamento_data"),
            status=row.get("status", "pendente"),
            forma_pagamento=row["forma_pagamento"],
            criado_em=row.get("criado_em")
        )
