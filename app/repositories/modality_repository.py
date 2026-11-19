import logging
from typing import List, Optional
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
    def get_all(cls, only_active: bool = True) -> List[Modalidade]:
        """Retorna todas as modalidades ativas do PostgreSQL com fallback seguro."""
        conn = get_db_connection()
        if conn:
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
            except Exception as e:
                logger.warning(f"Erro ao consultar modalidades do banco: {e}")

        # Fallback para os dados existentes preservando compatibilidade
        if only_active:
            return [m for m in cls._DATA if m.ativo]
        return cls._DATA

    @classmethod
    def get_by_id(cls, modality_id: int) -> Optional[Modalidade]:
        """Busca uma modalidade por seu ID numérico no PostgreSQL."""
        conn = get_db_connection()
        if conn:
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
            except Exception as e:
                logger.warning(f"Erro ao buscar modalidade por ID no banco: {e}")

        return next((m for m in cls._DATA if m.id == modality_id), None)

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional[Modalidade]:
        """Busca uma modalidade por seu slug único."""
        conn = get_db_connection()
        if conn:
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
            except Exception as e:
                logger.warning(f"Erro ao buscar modalidade por slug no banco: {e}")

        return next((m for m in cls._DATA if m.slug == slug), None)
