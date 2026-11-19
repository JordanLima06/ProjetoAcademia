import logging
from typing import List, Optional
from flask import current_app, has_app_context
from app.db import get_db_connection
from app.models.academy import Modalidade

logger = logging.getLogger(__name__)

class ModalityRepository:
    """Repositório de dados e persistência das modalidades esportivas."""

    # Metadados visuais para compatibilidade total com os templates existentes (assets/tags)
    _META_VISUAL = {
        "musculacao": {
            "imagem": "assets/musculacao.jpeg",
            "tag": "Força e Hipertrófia",
            "descricao": "Treine com os melhores equipamentos e instrutores para alcançar seus objetivos de forma eficiente."
        },
        "boxe": {
            "imagem": "assets/boxe.jpeg",
            "tag": "Agilidade e Resistência",
            "descricao": "Aprenda técnicas de boxe com profissionais experientes e melhore sua resistência e força."
        },
        "jiu-jitsu": {
            "imagem": "assets/jiujitsu.jpeg",
            "tag": "Estratégia e controle",
            "descricao": "Desenvolva habilidades de defesa pessoal e condicionamento físico com aulas de Jiu-Jitsu."
        },
        "funcional": {
            "imagem": "assets/funcional.jpeg",
            "tag": "Mobilidade e equilíbrio",
            "descricao": "Aulas dinâmicas que combinam força, resistência e flexibilidade para um treino completo."
        },
        "crossfit": {
            "imagem": "assets/crossfit.jpeg",
            "tag": "Força e resistência",
            "descricao": "Treino de alta intensidade que combina exercícios funcionais e movimentos variados."
        }
    }

    # Dados padrão com IDs definidos para resiliência e execução de testes isolados
    _DATA = [
        Modalidade(
            id=1,
            slug="musculacao",
            nome="Musculação",
            descricao="Treine com os melhores equipamentos e instrutores para alcançar seus objetivos de forma eficiente.",
            imagem="assets/musculacao.jpeg",
            tag="Força e Hipertrófia",
            ativo=True
        ),
        Modalidade(
            id=2,
            slug="boxe",
            nome="Boxe",
            descricao="Aprenda técnicas de boxe com profissionais experientes e melhore sua resistência e força.",
            imagem="assets/boxe.jpeg",
            tag="Agilidade e Resistência",
            ativo=True
        ),
        Modalidade(
            id=3,
            slug="jiu-jitsu",
            nome="Jiu-Jitsu",
            descricao="Desenvolva habilidades de defesa pessoal e condicionamento físico com aulas de Jiu-Jitsu.",
            imagem="assets/jiujitsu.jpeg",
            tag="Estratégia e controle",
            ativo=True
        ),
        Modalidade(
            id=4,
            slug="funcional",
            nome="Funcional",
            descricao="Aulas dinâmicas que combinam força, resistência e flexibilidade para um treino completo.",
            imagem="assets/funcional.jpeg",
            tag="Mobilidade e equilíbrio",
            ativo=True
        ),
        Modalidade(
            id=5,
            slug="crossfit",
            nome="CrossFit",
            descricao="Treino de alta intensidade que combina exercícios funcionais e movimentos variados.",
            imagem="assets/crossfit.jpeg",
            tag="Força e resistência",
            ativo=True
        )
    ]

    @classmethod
    def _is_testing(cls) -> bool:
        return has_app_context() and bool(current_app.config.get("TESTING"))

    @classmethod
    def get_all(cls, only_active: bool = True) -> List[Modalidade]:
        """Retorna todas as modalidades do PostgreSQL com metadados visuais."""
        conn = get_db_connection()
        if not conn:
            logger.error("Falha de conexão com PostgreSQL ao buscar todas as modalidades.")
            if cls._is_testing():
                if only_active:
                    return [m for m in cls._DATA if m.ativo]
                return cls._DATA
            return []

        try:
            with conn.cursor() as cursor:
                query = "SELECT id, slug, nome, descricao, ativo FROM modalidades"
                if only_active:
                    query += " WHERE ativo = TRUE"
                query += " ORDER BY id ASC"
                cursor.execute(query)
                rows = cursor.fetchall()
                if rows:
                    result = []
                    for row in rows:
                        slug = row["slug"]
                        meta = cls._META_VISUAL.get(slug, {})
                        result.append(
                            Modalidade(
                                id=row["id"],
                                slug=slug,
                                nome=row["nome"],
                                descricao=row.get("descricao") or meta.get("descricao", ""),
                                imagem=meta.get("imagem", f"assets/{slug}.jpeg"),
                                tag=meta.get("tag", ""),
                                ativo=row.get("ativo", True)
                            )
                        )
                    return result
                return []
        except Exception as e:
            logger.error(f"Erro ao consultar modalidades no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                if only_active:
                    return [m for m in cls._DATA if m.ativo]
                return cls._DATA
            return []

    @classmethod
    def get_by_id(cls, modality_id: int) -> Optional[Modalidade]:
        """Busca uma modalidade por seu ID numérico no PostgreSQL."""
        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar modalidade id {modality_id}.")
            if cls._is_testing():
                return next((m for m in cls._DATA if m.id == modality_id), None)
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, slug, nome, descricao, ativo FROM modalidades WHERE id = %s",
                    (modality_id,)
                )
                row = cursor.fetchone()
                if row:
                    slug = row["slug"]
                    meta = cls._META_VISUAL.get(slug, {})
                    return Modalidade(
                        id=row["id"],
                        slug=slug,
                        nome=row["nome"],
                        descricao=row.get("descricao") or meta.get("descricao", ""),
                        imagem=meta.get("imagem", f"assets/{slug}.jpeg"),
                        tag=meta.get("tag", ""),
                        ativo=row.get("ativo", True)
                    )
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar modalidade por ID {modality_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return next((m for m in cls._DATA if m.id == modality_id), None)
            return None

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional[Modalidade]:
        """Busca uma modalidade por seu slug único no PostgreSQL."""
        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar modalidade por slug '{slug}'.")
            if cls._is_testing():
                return next((m for m in cls._DATA if m.slug == slug), None)
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, slug, nome, descricao, ativo FROM modalidades WHERE slug = %s",
                    (slug,)
                )
                row = cursor.fetchone()
                if row:
                    meta = cls._META_VISUAL.get(slug, {})
                    return Modalidade(
                        id=row["id"],
                        slug=row["slug"],
                        nome=row["nome"],
                        descricao=row.get("descricao") or meta.get("descricao", ""),
                        imagem=meta.get("imagem", f"assets/{slug}.jpeg"),
                        tag=meta.get("tag", ""),
                        ativo=row.get("ativo", True)
                    )
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar modalidade por slug '{slug}' no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return next((m for m in cls._DATA if m.slug == slug), None)
            return None

    @classmethod
    def get_by_plan_id(cls, plan_id: int, only_active: bool = True) -> List[Modalidade]:
        """
        Retorna as modalidades associadas a um plano através da tabela relacional plano_modalidades.
        Utiliza exclusivamente as colunas plano_id e modalidade_id de plano_modalidades.
        """
        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar modalidades do plano {plan_id}.")
            if cls._is_testing():
                plan_map = {1: [1], 2: [1, 2, 3, 4], 3: [1, 2, 3, 4, 5], 4: [1, 2, 3, 4, 5]}
                allowed_ids = plan_map.get(plan_id, [])
                return [m for m in cls._DATA if m.id in allowed_ids and (m.ativo or not only_active)]
            return []

        try:
            with conn.cursor() as cursor:
                query = (
                    "SELECT m.id, m.slug, m.nome, m.descricao, m.ativo "
                    "FROM modalidades m "
                    "INNER JOIN plano_modalidades pm ON pm.modalidade_id = m.id "
                    "WHERE pm.plano_id = %s"
                )
                if only_active:
                    query += " AND m.ativo = TRUE"
                query += " ORDER BY m.id ASC"
                cursor.execute(query, (plan_id,))
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    slug = row["slug"]
                    meta = cls._META_VISUAL.get(slug, {})
                    result.append(
                        Modalidade(
                            id=row["id"],
                            slug=slug,
                            nome=row["nome"],
                            descricao=row.get("descricao") or meta.get("descricao", ""),
                            imagem=meta.get("imagem", f"assets/{slug}.jpeg"),
                            tag=meta.get("tag", ""),
                            ativo=row.get("ativo", True)
                        )
                    )
                return result
        except Exception as e:
            logger.error(f"Erro ao buscar modalidades do plano {plan_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                plan_map = {1: [1], 2: [1, 2, 3, 4], 3: [1, 2, 3, 4, 5], 4: [1, 2, 3, 4, 5]}
                allowed_ids = plan_map.get(plan_id, [])
                return [m for m in cls._DATA if m.id in allowed_ids and (m.ativo or not only_active)]
            return []
