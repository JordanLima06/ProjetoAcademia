import logging
from typing import Optional, Tuple, Dict
from datetime import date, datetime
from flask import current_app, has_app_context
from app.db import get_db_connection
from app.models.user import User, Aluno

logger = logging.getLogger(__name__)

class UserRepository:
    """Repositório de persistência e consultas SQL para as tabelas usuarios e alunos."""

    # Armazenamento em memória para testes automatizados isolados quando TESTING=True e sem conexão DB
    _TEST_USERS: Dict[int, User] = {}
    _TEST_ALUNOS: Dict[int, Aluno] = {}
    _TEST_ID_SEQ = 1

    @classmethod
    def _is_testing(cls) -> bool:
        return has_app_context() and bool(current_app.config.get("TESTING"))

    @classmethod
    def find_by_email(cls, email: str) -> Optional[User]:
        """Busca usuário por e-mail com busca case-insensitive."""
        sanitized_email = (email or "").strip().lower()
        if not sanitized_email:
            return None

        conn = get_db_connection()
        if not conn:
            logger.error("Falha de conexão com PostgreSQL ao buscar usuário por e-mail.")
            if cls._is_testing():
                return next((u for u in cls._TEST_USERS.values() if u.email == sanitized_email), None)
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, nome, email, senha, tipo, ativo, criado_em "
                    "FROM usuarios WHERE email = %s",
                    (sanitized_email,)
                )
                row = cursor.fetchone()
                if row:
                    return User(
                        id=row["id"],
                        nome=row["nome"],
                        email=row["email"],
                        senha=row["senha"],
                        tipo=row.get("tipo", "aluno"),
                        ativo=row.get("ativo", True),
                        criado_em=row.get("criado_em")
                    )
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por email '{sanitized_email}' no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return next((u for u in cls._TEST_USERS.values() if u.email == sanitized_email), None)
            return None

    @classmethod
    def find_by_id(cls, user_id: int) -> Optional[User]:
        """Busca usuário por seu ID numérico no PostgreSQL."""
        if not user_id:
            return None

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar usuário id {user_id}.")
            if cls._is_testing():
                return cls._TEST_USERS.get(user_id)
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, nome, email, senha, tipo, ativo, criado_em "
                    "FROM usuarios WHERE id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return User(
                        id=row["id"],
                        nome=row["nome"],
                        email=row["email"],
                        senha=row["senha"],
                        tipo=row.get("tipo", "aluno"),
                        ativo=row.get("ativo", True),
                        criado_em=row.get("criado_em")
                    )
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar usuário id {user_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return cls._TEST_USERS.get(user_id)
            return None

    @classmethod
    def find_aluno_by_user_id(cls, user_id: int) -> Optional[Aluno]:
        """Busca os dados de aluno associados a um usuário."""
        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar aluno com usuario_id {user_id}.")
            if cls._is_testing():
                return next((a for a in cls._TEST_ALUNOS.values() if a.usuario_id == user_id), None)
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, usuario_id, data_nascimento, telefone, objetivo, data_cadastro "
                    "FROM alunos WHERE usuario_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return Aluno(
                        id=row["id"],
                        usuario_id=row["usuario_id"],
                        data_nascimento=row.get("data_nascimento"),
                        telefone=row.get("telefone", ""),
                        objetivo=row.get("objetivo"),
                        data_cadastro=row.get("data_cadastro")
                    )
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar aluno por usuario_id {user_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                return next((a for a in cls._TEST_ALUNOS.values() if a.usuario_id == user_id), None)
            return None

    @classmethod
    def is_user_active(cls, user_id: int) -> bool:
        """Verifica se o usuário existe e permanece ativo no banco."""
        user = cls.find_by_id(user_id)
        return bool(user and user.ativo)

    @classmethod
    def update_password(cls, user_id: int, new_password_hash: str) -> bool:
        """Atualiza a senha (hash) de um usuário."""
        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao atualizar senha do usuário {user_id}.")
            if cls._is_testing() and user_id in cls._TEST_USERS:
                cls._TEST_USERS[user_id].senha = new_password_hash
                return True
            return False

        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE usuarios SET senha = %s WHERE id = %s",
                        (new_password_hash, user_id)
                    )
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Erro ao atualizar senha no PostgreSQL para usuário {user_id}: {e}", exc_info=True)
            return False

    @classmethod
    def create_user_with_student(cls, user: User, aluno: Aluno) -> Tuple[User, Aluno]:
        """
        Cria um registro em 'usuarios' e o correspondente em 'alunos'
        dentro de uma transação atômica rigorosa. Se qualquer inserção falhar,
        a transação sofre rollback completo.
        Informa explicitamente 'data_cadastro' em alunos (DATE NOT NULL).
        """
        data_cad = aluno.data_cadastro or date.today()

        conn = get_db_connection()
        if not conn:
            logger.error("Falha de conexão com PostgreSQL ao criar usuário e aluno em transação.")
            if cls._is_testing():
                user.id = cls._TEST_ID_SEQ
                user.criado_em = datetime.now()
                cls._TEST_USERS[user.id] = user

                aluno.id = cls._TEST_ID_SEQ
                aluno.usuario_id = user.id
                aluno.data_cadastro = data_cad
                cls._TEST_ALUNOS[aluno.id] = aluno

                cls._TEST_ID_SEQ += 1
                return user, aluno
            raise RuntimeError("Banco de dados inacessível para cadastro.")

        try:
            with conn:
                with conn.cursor() as cursor:
                    # 1. Inserir na tabela usuarios
                    cursor.execute(
                        """
                        INSERT INTO usuarios (nome, email, senha, tipo, ativo)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, criado_em
                        """,
                        (user.nome, user.email.lower().strip(), user.senha, user.tipo, user.ativo)
                    )
                    u_row = cursor.fetchone()
                    user.id = u_row["id"]
                    user.criado_em = u_row.get("criado_em")

                    # 2. Inserir na tabela alunos com data_cadastro explícita
                    cursor.execute(
                        """
                        INSERT INTO alunos (usuario_id, data_nascimento, telefone, objetivo, data_cadastro)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, data_cadastro
                        """,
                        (user.id, aluno.data_nascimento, aluno.telefone, aluno.objetivo, data_cad)
                    )
                    a_row = cursor.fetchone()
                    aluno.id = a_row["id"]
                    aluno.usuario_id = user.id
                    aluno.data_cadastro = a_row.get("data_cadastro") or data_cad

            logger.info(f"Usuário id={user.id} e Aluno id={aluno.id} cadastrados com sucesso em transação atômica.")
            return user, aluno
        except Exception as e:
            conn.rollback()
            logger.error(f"Falha na transação atômica ao criar usuário/aluno: {e}", exc_info=True)
            raise
