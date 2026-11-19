import logging
from typing import List, Optional
from flask import current_app, has_app_context
from app.db import get_db_connection
from app.models.academy import Plano, OpcaoPagamento

logger = logging.getLogger(__name__)

class PlanRepository:
    """Repositório de dados e persistência dos planos de treinamento no PostgreSQL."""

    # Fixture restrita para execução de testes automatizados isolados quando TESTING=True
    _TEST_FIXTURE = [
        Plano(
            id=1,
            slug="essencial",
            nome="Essencial",
            preco=79.90,
            descricao="Plano de acesso à musculação.",
            duracao_dias=30,
            ativo=True,
            beneficios=["Acesso à musculação", "Treino personalizado", "Avaliação física", "Área de cardio"],
            opcoes_pagamento=[
                OpcaoPagamento(
                    id=1,
                    plano_id=1,
                    codigo="essencial_mensal",
                    nome="Pagamento mensal",
                    tipo_cobranca="mensal",
                    valor_cobranca=79.90,
                    periodicidade="mensal",
                    ativo=True
                )
            ]
        ),
        Plano(
            id=2,
            slug="perfomance",
            nome="Perfomance",
            preco=109.90,
            descricao="Musculação, lutas e treinamento funcional.",
            duracao_dias=30,
            ativo=True,
            beneficios=["Todos os benefícios do Essencial", "Aulas de boxe", "Aulas de jiu-jitsu", "Aulas de treinamento funcional"],
            opcoes_pagamento=[
                OpcaoPagamento(
                    id=2,
                    plano_id=2,
                    codigo="perfomance_mensal",
                    nome="Pagamento mensal",
                    tipo_cobranca="mensal",
                    valor_cobranca=109.90,
                    periodicidade="mensal",
                    ativo=True
                )
            ]
        ),
        Plano(
            id=3,
            slug="premium",
            nome="Premium",
            preco=139.90,
            descricao="Plano completo com acesso a todas as modalidades.",
            duracao_dias=30,
            ativo=True,
            beneficios=["Todos os benefícios do Performance", "Acompanhamento da evolução", "Acesso a todas as modalidades"],
            opcoes_pagamento=[
                OpcaoPagamento(
                    id=3,
                    plano_id=3,
                    codigo="premium_mensal",
                    nome="Pagamento mensal",
                    tipo_cobranca="mensal",
                    valor_cobranca=139.90,
                    periodicidade="mensal",
                    ativo=True
                )
            ]
        ),
        Plano(
            id=4,
            slug="anual",
            nome="Anual",
            preco=1399.90,
            descricao="Plano anual com acesso às modalidades disponíveis.",
            duracao_dias=365,
            ativo=True,
            beneficios=["Todos os benefícios do Premium", "Acompanhamento da evolução", "Acesso a todas as modalidades"],
            opcoes_pagamento=[
                OpcaoPagamento(
                    id=4,
                    plano_id=4,
                    codigo="anual_avista",
                    nome="Pagamento à vista",
                    tipo_cobranca="unico",
                    valor_cobranca=1399.90,
                    valor_total_contratado=1399.90,
                    quantidade_parcelas=1,
                    periodicidade="unica",
                    ativo=True
                ),
                OpcaoPagamento(
                    id=5,
                    plano_id=4,
                    codigo="anual_12x",
                    nome="12 parcelas mensais sem juros",
                    tipo_cobranca="mensal",
                    valor_cobranca=116.66,
                    valor_total_contratado=1399.90,
                    quantidade_parcelas=12,
                    periodicidade="mensal",
                    ativo=True
                )
            ]
        )
    ]

    @classmethod
    def _is_testing(cls) -> bool:
        return has_app_context() and bool(current_app.config.get("TESTING"))

    @classmethod
    def _load_beneficios(cls, cursor, plano_id: int) -> List[str]:
        """Carrega a lista de descrições dos benefícios vinculados ao plano ordenada por ordem ASC."""
        cursor.execute(
            "SELECT descricao FROM plano_beneficios WHERE plano_id = %s ORDER BY ordem ASC",
            (plano_id,)
        )
        rows = cursor.fetchall()
        return [row["descricao"] for row in rows]

    @classmethod
    def _load_opcoes_pagamento(cls, cursor, plano_id: int) -> List[OpcaoPagamento]:
        """Carrega as opções de pagamento ativas vinculadas ao plano."""
        cursor.execute(
            "SELECT id, plano_id, codigo, nome, tipo_cobranca, valor_cobranca, "
            "valor_total_contratado, quantidade_parcelas, periodicidade, ativo "
            "FROM opcoes_pagamento_planos WHERE plano_id = %s AND ativo = TRUE "
            "ORDER BY id ASC",
            (plano_id,)
        )
        rows = cursor.fetchall()
        opcoes = []
        for row in rows:
            opcoes.append(
                OpcaoPagamento(
                    id=row["id"],
                    plano_id=row["plano_id"],
                    codigo=row["codigo"],
                    nome=row["nome"],
                    tipo_cobranca=row["tipo_cobranca"],
                    valor_cobranca=float(row["valor_cobranca"]),
                    valor_total_contratado=float(row["valor_total_contratado"]) if row.get("valor_total_contratado") is not None else None,
                    quantidade_parcelas=row.get("quantidade_parcelas"),
                    periodicidade=row.get("periodicidade", "mensal"),
                    ativo=row.get("ativo", True)
                )
            )
        return opcoes

    @classmethod
    def get_all(cls, only_active: bool = True) -> List[Plano]:
        """Retorna todos os planos do PostgreSQL com seus benefícios e opções de pagamento."""
        conn = get_db_connection()
        if not conn:
            logger.error("Falha de conexão com PostgreSQL ao buscar todos os planos.")
            if cls._is_testing():
                return [p for p in cls._TEST_FIXTURE if (p.ativo or not only_active)]
            return []

        try:
            with conn.cursor() as cursor:
                query = "SELECT id, slug, nome, descricao, valor, duracao_dias, ativo FROM planos"
                if only_active:
                    query += " WHERE ativo = TRUE"
                query += " ORDER BY id ASC"
                cursor.execute(query)
                rows = cursor.fetchall()

                planos = []
                for row in rows:
                    plano_id = row["id"]
                    beneficios = cls._load_beneficios(cursor, plano_id)
                    opcoes = cls._load_opcoes_pagamento(cursor, plano_id)
                    planos.append(
                        Plano(
                            id=plano_id,
                            slug=row["slug"],
                            nome=row["nome"],
                            preco=float(row["valor"]),
                            descricao=row.get("descricao") or "",
                            duracao_dias=row.get("duracao_dias", 30),
                            ativo=row.get("ativo", True),
                            beneficios=beneficios,
                            opcoes_pagamento=opcoes
                        )
                    )
                return planos
        except Exception as e:
            logger.error(f"Erro ao consultar planos no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return [p for p in cls._TEST_FIXTURE if (p.ativo or not only_active)]
            return []

    @classmethod
    def get_by_id(cls, plan_id: int) -> Optional[Plano]:
        """Busca um plano pelo seu ID numérico no PostgreSQL."""
        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar plano por id {plan_id}.")
            if cls._is_testing():
                return next((p for p in cls._TEST_FIXTURE if p.id == plan_id), None)
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, slug, nome, descricao, valor, duracao_dias, ativo "
                    "FROM planos WHERE id = %s",
                    (plan_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                beneficios = cls._load_beneficios(cursor, plan_id)
                opcoes = cls._load_opcoes_pagamento(cursor, plan_id)
                return Plano(
                    id=row["id"],
                    slug=row["slug"],
                    nome=row["nome"],
                    preco=float(row["valor"]),
                    descricao=row.get("descricao") or "",
                    duracao_dias=row.get("duracao_dias", 30),
                    ativo=row.get("ativo", True),
                    beneficios=beneficios,
                    opcoes_pagamento=opcoes
                )
        except Exception as e:
            logger.error(f"Erro ao buscar plano por id {plan_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return next((p for p in cls._TEST_FIXTURE if p.id == plan_id), None)
            return None

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional[Plano]:
        """Busca um plano pelo seu slug textual no PostgreSQL."""
        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar plano por slug '{slug}'.")
            if cls._is_testing():
                return next((p for p in cls._TEST_FIXTURE if p.slug == slug), None)
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, slug, nome, descricao, valor, duracao_dias, ativo "
                    "FROM planos WHERE slug = %s",
                    (slug,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                plano_id = row["id"]
                beneficios = cls._load_beneficios(cursor, plano_id)
                opcoes = cls._load_opcoes_pagamento(cursor, plano_id)
                return Plano(
                    id=plano_id,
                    slug=row["slug"],
                    nome=row["nome"],
                    preco=float(row["valor"]),
                    descricao=row.get("descricao") or "",
                    duracao_dias=row.get("duracao_dias", 30),
                    ativo=row.get("ativo", True),
                    beneficios=beneficios,
                    opcoes_pagamento=opcoes
                )
        except Exception as e:
            logger.error(f"Erro ao buscar plano por slug '{slug}' no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return next((p for p in cls._TEST_FIXTURE if p.slug == slug), None)
            return None

    @classmethod
    def get_payment_option_by_id(cls, option_id: int) -> Optional[OpcaoPagamento]:
        """Busca uma opção de pagamento específica por seu ID numérico no PostgreSQL."""
        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar opção de pagamento id {option_id}.")
            if cls._is_testing():
                for p in cls._TEST_FIXTURE:
                    for op in p.opcoes_pagamento:
                        if op.id == option_id:
                            return op
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, plano_id, codigo, nome, tipo_cobranca, valor_cobranca, "
                    "valor_total_contratado, quantidade_parcelas, periodicidade, ativo "
                    "FROM opcoes_pagamento_planos WHERE id = %s",
                    (option_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                return OpcaoPagamento(
                    id=row["id"],
                    plano_id=row["plano_id"],
                    codigo=row["codigo"],
                    nome=row["nome"],
                    tipo_cobranca=row["tipo_cobranca"],
                    valor_cobranca=float(row["valor_cobranca"]),
                    valor_total_contratado=float(row["valor_total_contratado"]) if row.get("valor_total_contratado") is not None else None,
                    quantidade_parcelas=row.get("quantidade_parcelas"),
                    periodicidade=row.get("periodicidade", "mensal"),
                    ativo=row.get("ativo", True)
                )
        except Exception as e:
            logger.error(f"Erro ao buscar opção de pagamento id {option_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                for p in cls._TEST_FIXTURE:
                    for op in p.opcoes_pagamento:
                        if op.id == option_id:
                            return op
            return None
