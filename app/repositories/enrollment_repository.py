import logging
from typing import List, Optional, Dict
from datetime import date, datetime
from decimal import Decimal
from flask import current_app, has_app_context
from app.db import get_db_connection
from app.models.enrollment import Matricula, MatriculaModalidade
from app.models.academy import Modalidade
from app.repositories.modality_repository import ModalityRepository

logger = logging.getLogger(__name__)

class EnrollmentRepository:
    """Repositório de persistência e consultas SQL para as tabelas matriculas e matricula_modalidades."""

    # Armazenamento em memória exclusivo para testes automatizados isolados quando TESTING=True e sem conexão DB
    _TEST_MATRICULAS: Dict[int, Matricula] = {}
    _TEST_MATRICULA_MODALIDADES: Dict[int, List[MatriculaModalidade]] = {}
    _TEST_ID_SEQ = 1

    @classmethod
    def _is_testing(cls) -> bool:
        return has_app_context() and bool(current_app.config.get("TESTING"))

    @classmethod
    def create_transactional(cls, cursor, matricula: Matricula, modality_ids: List[int]) -> Matricula:
        """
        Insere a matrícula e vincula suas modalidades liberadas em matricula_modalidades
        utilizando o cursor de uma transação ativa do PostgreSQL.

        Respeita rigorosamente o schema real das tabelas:
        - matriculas: aluno_id, plano_id, data_inicio, data_fim, status,
                      opcao_pagamento_id, tipo_cobranca, valor_cobranca,
                      valor_total_contratado, quantidade_parcelas
        - matricula_modalidades: matricula_id, plano_id, modalidade_id
        """
        if matricula.status not in Matricula.STATUS_PERMITIDOS:
            logger.warning(f"Status '{matricula.status}' inválido para matrícula. Ajustando para 'pendente'.")
            matricula.status = "pendente"

        cursor.execute(
            """
            INSERT INTO matriculas (
                aluno_id,
                plano_id,
                data_inicio,
                data_fim,
                status,
                opcao_pagamento_id,
                tipo_cobranca,
                valor_cobranca,
                valor_total_contratado,
                quantidade_parcelas
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, criado_em
            """,
            (
                matricula.aluno_id,
                matricula.plano_id,
                matricula.data_inicio,
                matricula.data_fim,
                matricula.status,
                matricula.opcao_pagamento_id,
                matricula.tipo_cobranca,
                matricula.valor_cobranca,
                matricula.valor_total_contratado,
                matricula.quantidade_parcelas or 1
            )
        )
        row = cursor.fetchone()
        matricula.id = row["id"]
        matricula.criado_em = row.get("criado_em")

        # Vincula cada modalidade liberada pelo plano na tabela matricula_modalidades,
        # respeitando a chave estrangeira composta (matricula_id, plano_id) e modalidade_id
        for mod_id in modality_ids:
            cursor.execute(
                """
                INSERT INTO matricula_modalidades (matricula_id, plano_id, modalidade_id)
                VALUES (%s, %s, %s)
                """,
                (matricula.id, matricula.plano_id, mod_id)
            )

        logger.info(
            f"Matrícula id={matricula.id} (plano_id={matricula.plano_id}) e "
            f"{len(modality_ids)} modalidades gravadas com sucesso no cursor transacional."
        )
        return matricula

    @classmethod
    def find_by_id(cls, matricula_id: int) -> Optional[Matricula]:
        """Busca uma matrícula por seu ID numérico no PostgreSQL com todas as colunas reais."""
        if not matricula_id:
            return None

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar matrícula id {matricula_id}.")
            if cls._is_testing():
                mat = cls._TEST_MATRICULAS.get(matricula_id)
                if mat:
                    mat.modalidades = cls.get_modalities_by_matricula_id(matricula_id)
                return mat
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, aluno_id, plano_id, data_inicio, data_fim, status,
                           opcao_pagamento_id, tipo_cobranca, valor_cobranca,
                           valor_total_contratado, quantidade_parcelas, criado_em
                    FROM matriculas
                    WHERE id = %s
                    """,
                    (matricula_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                matricula = cls._row_to_matricula(row)
                matricula.modalidades = cls.get_modalities_by_matricula_id(matricula.id)
                return matricula
        except Exception as e:
            logger.error(f"Erro ao buscar matrícula id {matricula_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                mat = cls._TEST_MATRICULAS.get(matricula_id)
                if mat:
                    mat.modalidades = cls.get_modalities_by_matricula_id(matricula_id)
                return mat
            return None

    @classmethod
    def find_active_by_aluno_id(cls, aluno_id: int) -> Optional[Matricula]:
        """
        Busca a matrícula ativa e vigente de um aluno.
        Garante que data_fim seja maior ou igual à data atual (CURRENT_DATE) e status seja 'ativa'.
        """
        if not aluno_id:
            return None

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar matrícula ativa para aluno id {aluno_id}.")
            if cls._is_testing():
                hoje = date.today()
                for mat in cls._TEST_MATRICULAS.values():
                    if mat.aluno_id == aluno_id and mat.status == "ativa" and mat.data_fim >= hoje:
                        mat.modalidades = cls.get_modalities_by_matricula_id(mat.id)
                        return mat
                return None
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, aluno_id, plano_id, data_inicio, data_fim, status,
                           opcao_pagamento_id, tipo_cobranca, valor_cobranca,
                           valor_total_contratado, quantidade_parcelas, criado_em
                    FROM matriculas
                    WHERE aluno_id = %s AND status = 'ativa' AND data_fim >= CURRENT_DATE
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (aluno_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                matricula = cls._row_to_matricula(row)
                matricula.modalidades = cls.get_modalities_by_matricula_id(matricula.id)
                return matricula
        except Exception as e:
            logger.error(f"Erro ao buscar matrícula ativa para aluno {aluno_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                hoje = date.today()
                for mat in cls._TEST_MATRICULAS.values():
                    if mat.aluno_id == aluno_id and mat.status == "ativa" and mat.data_fim >= hoje:
                        mat.modalidades = cls.get_modalities_by_matricula_id(mat.id)
                        return mat
                return None
            return None

    @classmethod
    def find_current_by_aluno_id(cls, aluno_id: int) -> Optional[Matricula]:
        """
        Busca a matrícula atual vigente de um aluno, priorizando:
        1. Matrícula com status 'ativa'.
        2. Matrícula com status 'pendente'.
        Garante que data_fim seja maior ou igual à data atual (CURRENT_DATE).
        """
        if not aluno_id:
            return None

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar matrícula atual para aluno id {aluno_id}.")
            if cls._is_testing():
                hoje = date.today()
                candidatos = [
                    m for m in cls._TEST_MATRICULAS.values()
                    if m.aluno_id == aluno_id and m.status in ("ativa", "pendente") and m.data_fim >= hoje
                ]
                if candidatos:
                    candidatos.sort(key=lambda m: (0 if m.status == "ativa" else 1, -(m.id or 0)))
                    mat = candidatos[0]
                    if not mat.modalidades:
                        mat.modalidades = cls.get_modalities_by_matricula_id(mat.id)
                    return mat
                return None
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, aluno_id, plano_id, data_inicio, data_fim, status,
                           opcao_pagamento_id, tipo_cobranca, valor_cobranca,
                           valor_total_contratado, quantidade_parcelas, criado_em
                    FROM matriculas
                    WHERE aluno_id = %s AND status IN ('ativa', 'pendente') AND data_fim >= CURRENT_DATE
                    ORDER BY CASE WHEN status = 'ativa' THEN 1 ELSE 2 END, id DESC
                    LIMIT 1
                    """,
                    (aluno_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                matricula = cls._row_to_matricula(row)
                matricula.modalidades = cls.get_modalities_by_matricula_id(matricula.id)
                return matricula
        except Exception as e:
            logger.error(f"Erro ao buscar matrícula atual para aluno {aluno_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                hoje = date.today()
                candidatos = [
                    m for m in cls._TEST_MATRICULAS.values()
                    if m.aluno_id == aluno_id and m.status in ("ativa", "pendente") and m.data_fim >= hoje
                ]
                if candidatos:
                    candidatos.sort(key=lambda m: (0 if m.status == "ativa" else 1, -(m.id or 0)))
                    mat = candidatos[0]
                    if not mat.modalidades:
                        mat.modalidades = cls.get_modalities_by_matricula_id(mat.id)
                    return mat
            return None

    @classmethod
    def lock_student_and_check_existing_matricula(cls, cursor, aluno_id: int) -> Optional[Matricula]:
        """
        Bloqueia a linha do aluno na tabela 'alunos' (SELECT ... FOR UPDATE) para garantir
        serialização estrita contra concorrência e verifica se já existe matrícula 'ativa' ou 'pendente'.
        Retorna a matrícula existente se houver, ou None se livre para contratação.
        """
        if not aluno_id:
            return None

        # 1. Bloqueio transacional por aluno via PostgreSQL
        cursor.execute("SELECT id FROM alunos WHERE id = %s FOR UPDATE", (aluno_id,))

        # 2. Verificação de matrícula ativa ou pendente
        cursor.execute(
            """
            SELECT id, aluno_id, plano_id, data_inicio, data_fim, status,
                   opcao_pagamento_id, tipo_cobranca, valor_cobranca,
                   valor_total_contratado, quantidade_parcelas, criado_em
            FROM matriculas
            WHERE aluno_id = %s AND status IN ('ativa', 'pendente') AND data_fim >= CURRENT_DATE
            ORDER BY CASE WHEN status = 'ativa' THEN 1 ELSE 2 END, id DESC
            LIMIT 1
            """,
            (aluno_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return cls._row_to_matricula(row)

    @classmethod
    def list_by_aluno_id(cls, aluno_id: int) -> List[Matricula]:
        """Retorna o histórico completo de matrículas de um aluno."""
        if not aluno_id:
            return []

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao listar matrículas do aluno {aluno_id}.")
            if cls._is_testing():
                mats = [m for m in cls._TEST_MATRICULAS.values() if m.aluno_id == aluno_id]
                for m in mats:
                    m.modalidades = cls.get_modalities_by_matricula_id(m.id)
                return sorted(mats, key=lambda x: x.id or 0, reverse=True)
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, aluno_id, plano_id, data_inicio, data_fim, status,
                           opcao_pagamento_id, tipo_cobranca, valor_cobranca,
                           valor_total_contratado, quantidade_parcelas, criado_em
                    FROM matriculas
                    WHERE aluno_id = %s
                    ORDER BY id DESC
                    """,
                    (aluno_id,)
                )
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    mat = cls._row_to_matricula(row)
                    mat.modalidades = cls.get_modalities_by_matricula_id(mat.id)
                    result.append(mat)
                return result
        except Exception as e:
            logger.error(f"Erro ao listar matrículas do aluno {aluno_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                mats = [m for m in cls._TEST_MATRICULAS.values() if m.aluno_id == aluno_id]
                for m in mats:
                    m.modalidades = cls.get_modalities_by_matricula_id(m.id)
                return sorted(mats, key=lambda x: x.id or 0, reverse=True)
            return []

    @classmethod
    def get_modalities_by_matricula_id(cls, matricula_id: int) -> List[Modalidade]:
        """
        Retorna as modalidades esportivas liberadas para determinada matrícula através de matricula_modalidades.
        Injeta os metadados visuais de ModalityRepository para compatibilidade completa com o frontend.
        """
        conn = get_db_connection()
        if not conn:
            if cls._is_testing():
                vms = cls._TEST_MATRICULA_MODALIDADES.get(matricula_id, [])
                mod_ids = [vm.modalidade_id for vm in vms]
                return [m for m in ModalityRepository.get_all() if m.id in mod_ids]
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT m.id, m.slug, m.nome, m.descricao, m.ativo
                    FROM modalidades m
                    INNER JOIN matricula_modalidades mm ON mm.modalidade_id = m.id
                    WHERE mm.matricula_id = %s
                    ORDER BY m.id ASC
                    """,
                    (matricula_id,)
                )
                rows = cursor.fetchall()
                modalidades = []
                for row in rows:
                    slug = row["slug"]
                    meta = ModalityRepository._META_VISUAL.get(slug, {})
                    modalidades.append(
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
                return modalidades
        except Exception as e:
            logger.error(f"Erro ao buscar modalidades da matrícula {matricula_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                vms = cls._TEST_MATRICULA_MODALIDADES.get(matricula_id, [])
                mod_ids = [vm.modalidade_id for vm in vms]
                return [m for m in ModalityRepository.get_all() if m.id in mod_ids]
            return []

    @classmethod
    def get_matricula_modalidades(cls, matricula_id: int) -> List[MatriculaModalidade]:
        """Retorna os registros de relacionamento direto matricula_modalidades (matricula_id, plano_id, modalidade_id)."""
        conn = get_db_connection()
        if not conn:
            if cls._is_testing():
                return cls._TEST_MATRICULA_MODALIDADES.get(matricula_id, [])
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT matricula_id, plano_id, modalidade_id
                    FROM matricula_modalidades
                    WHERE matricula_id = %s
                    ORDER BY modalidade_id ASC
                    """,
                    (matricula_id,)
                )
                rows = cursor.fetchall()
                return [
                    MatriculaModalidade(
                        matricula_id=r["matricula_id"],
                        plano_id=r["plano_id"],
                        modalidade_id=r["modalidade_id"]
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Erro ao consultar matricula_modalidades para id {matricula_id}: {e}", exc_info=True)
            if cls._is_testing():
                return cls._TEST_MATRICULA_MODALIDADES.get(matricula_id, [])
            return []

    @classmethod
    def update_status(cls, matricula_id: int, new_status: str) -> bool:
        """Atualiza o status de uma matrícula no PostgreSQL (exclusivamente status válidos)."""
        if new_status not in Matricula.STATUS_PERMITIDOS:
            logger.warning(
                f"Status '{new_status}' inválido para matrícula. "
                f"Valores permitidos: {Matricula.STATUS_PERMITIDOS}"
            )
            return False

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao atualizar status da matrícula {matricula_id}.")
            if cls._is_testing() and matricula_id in cls._TEST_MATRICULAS:
                cls._TEST_MATRICULAS[matricula_id].status = new_status
                return True
            return False

        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE matriculas SET status = %s WHERE id = %s",
                        (new_status, matricula_id)
                    )
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Erro ao atualizar status da matrícula {matricula_id} no PostgreSQL: {e}", exc_info=True)
            return False

    @staticmethod
    def _row_to_matricula(row: dict) -> Matricula:
        """Converte uma tupla/dicionário retornado do PostgreSQL em uma instância de Matricula."""
        valor_cobranca = row.get("valor_cobranca")
        if valor_cobranca is not None:
            valor_cobranca = Decimal(str(valor_cobranca))

        valor_total = row.get("valor_total_contratado")
        if valor_total is not None:
            valor_total = Decimal(str(valor_total))

        return Matricula(
            id=row["id"],
            aluno_id=row["aluno_id"],
            plano_id=row["plano_id"],
            data_inicio=row["data_inicio"],
            data_fim=row["data_fim"],
            status=row.get("status", "pendente"),
            opcao_pagamento_id=row.get("opcao_pagamento_id"),
            tipo_cobranca=row.get("tipo_cobranca"),
            valor_cobranca=valor_cobranca,
            valor_total_contratado=valor_total,
            quantidade_parcelas=row.get("quantidade_parcelas", 1),
            criado_em=row.get("criado_em")
        )
