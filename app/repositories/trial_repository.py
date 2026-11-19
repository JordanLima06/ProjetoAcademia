import logging
from typing import List, Optional
from app.db import get_db_connection
from app.models.trial_class import SolicitacaoAulaExperimental

logger = logging.getLogger(__name__)

class TrialRepository:
    """Repositório de persistência para a tabela solicitacoes_aula_experimental no PostgreSQL."""

    @staticmethod
    def create(solicitacao: SolicitacaoAulaExperimental) -> SolicitacaoAulaExperimental:
        """
        Insere uma nova solicitação de aula experimental no banco utilizando consulta parametrizada (%s).
        Retorna a instância com id e criado_em preenchidos.
        """
        conn = get_db_connection()
        if not conn:
            # Fallback seguro para testes unitários ou ambientes sem banco conectado
            logger.warning("Conexão PostgreSQL indisponível. Simulando persistência da solicitação.")
            solicitacao.id = 1
            return solicitacao

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO solicitacoes_aula_experimental (
                        nome, email, telefone, modalidade_id,
                        dia_preferido, periodo_preferido, objetivo, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, criado_em, status;
                    """,
                    (
                        solicitacao.nome,
                        solicitacao.email.lower().strip() if solicitacao.email else None,
                        solicitacao.telefone,
                        solicitacao.modalidade_id,
                        solicitacao.dia_preferido,
                        solicitacao.periodo_preferido,
                        solicitacao.objetivo,
                        solicitacao.status or "nova"
                    )
                )
                row = cursor.fetchone()
                conn.commit()
                if row:
                    solicitacao.id = row["id"]
                    solicitacao.criado_em = row.get("criado_em")
                    solicitacao.status = row.get("status", solicitacao.status)
                return solicitacao
        except Exception as e:
            conn.rollback()
            logger.error(f"Erro ao persistir solicitacao_aula_experimental no PostgreSQL: {e}")
            raise

    @staticmethod
    def find_by_id(solicitacao_id: int) -> Optional[SolicitacaoAulaExperimental]:
        """Busca uma solicitação pelo ID no PostgreSQL."""
        conn = get_db_connection()
        if not conn:
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, nome, email, telefone, modalidade_id,
                           dia_preferido, periodo_preferido, objetivo, status, criado_em
                    FROM solicitacoes_aula_experimental
                    WHERE id = %s;
                    """,
                    (solicitacao_id,)
                )
                row = cursor.fetchone()
                if row:
                    return SolicitacaoAulaExperimental(
                        id=row["id"],
                        nome=row["nome"],
                        email=row.get("email"),
                        telefone=row["telefone"],
                        modalidade_id=row.get("modalidade_id"),
                        dia_preferido=row.get("dia_preferido"),
                        periodo_preferido=row.get("periodo_preferido"),
                        objetivo=row.get("objetivo"),
                        status=row.get("status", "nova"),
                        criado_em=row.get("criado_em")
                    )
        except Exception as e:
            logger.error(f"Erro ao buscar solicitacao por ID: {e}")

        return None

    @staticmethod
    def list_all(status: Optional[str] = None) -> List[SolicitacaoAulaExperimental]:
        """Lista as solicitações de aula experimental com filtro opcional por status."""
        conn = get_db_connection()
        if not conn:
            return []

        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT id, nome, email, telefone, modalidade_id,
                           dia_preferido, periodo_preferido, objetivo, status, criado_em
                    FROM solicitacoes_aula_experimental
                """
                params = ()
                if status:
                    query += " WHERE status = %s"
                    params = (status,)
                query += " ORDER BY criado_em DESC;"

                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [
                    SolicitacaoAulaExperimental(
                        id=r["id"],
                        nome=r["nome"],
                        email=r.get("email"),
                        telefone=r["telefone"],
                        modalidade_id=r.get("modalidade_id"),
                        dia_preferido=r.get("dia_preferido"),
                        periodo_preferido=r.get("periodo_preferido"),
                        objetivo=r.get("objetivo"),
                        status=r.get("status", "nova"),
                        criado_em=r.get("criado_em")
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Erro ao listar solicitações: {e}")
            return []
