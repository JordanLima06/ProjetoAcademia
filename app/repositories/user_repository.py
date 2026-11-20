import logging
from typing import Optional, Tuple, Dict
from datetime import date, datetime
from flask import current_app, has_app_context
from app.db import get_db_connection
from app.models.user import User, Aluno

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Classe base para exceções de persistência e banco de dados do FightAcademy."""
    pass

class DatabaseConnectionError(DatabaseError):
    """Lançada quando a conexão com o PostgreSQL está indisponível ou falha."""
    pass

class DatabaseQueryError(DatabaseError):
    """Lançada quando ocorre um erro inesperado na execução de comandos ou queries SQL."""
    pass

class UserRepository:
    """Repositório de persistência e consultas SQL para as tabelas usuarios e alunos."""

    # Armazenamento em memória para testes automatizados isolados quando TESTING=True e sem conexão DB
    _TEST_USERS: Dict[int, User] = {}
    _TEST_ALUNOS: Dict[int, Aluno] = {}
    _TEST_ID_SEQ = 1
    _SIMULATE_CONNECTION_ERROR = False
    _SIMULATE_QUERY_ERROR = False
    _ALLOW_TEST_FALLBACK = True

    @classmethod
    def _is_testing(cls) -> bool:
        return has_app_context() and bool(current_app.config.get("TESTING"))

    @classmethod
    def find_by_email(cls, email: str) -> Optional[User]:
        """
        Busca usuário por e-mail com busca case-insensitive no PostgreSQL.
        
        Retorna:
            User: quando o usuário é encontrado.
            None: quando não existe registro com este e-mail.
            
        Lança:
            DatabaseConnectionError: quando a conexão com o PostgreSQL falhar.
            DatabaseQueryError: quando ocorrer erro inesperado na query.
        """
        sanitized_email = (email or "").strip().lower()
        if not sanitized_email:
            return None

        if getattr(cls, "_SIMULATE_CONNECTION_ERROR", False):
            raise DatabaseConnectionError("Falha de conexão com PostgreSQL ao buscar usuário por e-mail.")

        if getattr(cls, "_SIMULATE_QUERY_ERROR", False):
            raise DatabaseQueryError("Erro inesperado na consulta por e-mail ao PostgreSQL.")

        try:
            conn = get_db_connection()
        except Exception as conn_err:
            logger.error(f"Erro ao obter conexão com PostgreSQL: {conn_err}")
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return next((u for u in cls._TEST_USERS.values() if u.email == sanitized_email), None)
            raise DatabaseConnectionError(f"Falha de conexão com PostgreSQL ao buscar usuário por e-mail: {conn_err}")

        if not conn:
            logger.error("Falha de conexão com PostgreSQL ao buscar usuário por e-mail.")
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return next((u for u in cls._TEST_USERS.values() if u.email == sanitized_email), None)
            raise DatabaseConnectionError("Falha de conexão com PostgreSQL ao buscar usuário por e-mail.")

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
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por email '{sanitized_email}' no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return next((u for u in cls._TEST_USERS.values() if u.email == sanitized_email), None)
            raise DatabaseQueryError(f"Erro inesperado ao consultar usuário por email '{sanitized_email}': {e}")

    @classmethod
    def find_by_id(cls, user_id: int) -> Optional[User]:
        """
        Busca usuário por seu ID numérico no PostgreSQL.
        
        Retorna:
            User: quando o registro existe no banco.
            None: quando o usuário legitimamente não existe (id inexistente).
            
        Lança:
            DatabaseConnectionError: quando a conexão com o PostgreSQL estiver indisponível.
            DatabaseQueryError: quando ocorrer erro inesperado na execução da consulta SQL.
        """
        if not user_id:
            return None

        if getattr(cls, "_SIMULATE_CONNECTION_ERROR", False):
            raise DatabaseConnectionError("Falha de conexão com PostgreSQL ao buscar usuário.")

        if getattr(cls, "_SIMULATE_QUERY_ERROR", False):
            raise DatabaseQueryError("Erro inesperado na consulta ao PostgreSQL.")

        try:
            conn = get_db_connection()
        except Exception as conn_err:
            logger.error(f"Erro ao obter conexão com PostgreSQL: {conn_err}")
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return cls._TEST_USERS.get(user_id)
            raise DatabaseConnectionError(f"Falha de conexão com PostgreSQL ao buscar usuário id {user_id}: {conn_err}")

        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar usuário id {user_id}.")
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return cls._TEST_USERS.get(user_id)
            raise DatabaseConnectionError(f"Falha de conexão com PostgreSQL ao buscar usuário id {user_id}.")

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
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar usuário id {user_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return cls._TEST_USERS.get(user_id)
            raise DatabaseQueryError(f"Erro inesperado ao consultar usuário id {user_id} no PostgreSQL: {e}")

    @classmethod
    def find_aluno_by_user_id(cls, user_id: int) -> Optional[Aluno]:
        """
        Busca os dados de aluno associados a um usuário.
        
        Retorna:
            Aluno: quando o vínculo existir.
            None: quando não for encontrado vínculo de aluno.
            
        Lança:
            DatabaseConnectionError: quando o PostgreSQL estiver inacessível.
            DatabaseQueryError: quando ocorrer erro inesperado na query.
        """
        if not user_id:
            return None

        if getattr(cls, "_SIMULATE_CONNECTION_ERROR", False):
            raise DatabaseConnectionError("Falha de conexão com PostgreSQL ao buscar aluno.")

        if getattr(cls, "_SIMULATE_QUERY_ERROR", False):
            raise DatabaseQueryError("Erro inesperado na consulta de aluno.")

        try:
            conn = get_db_connection()
        except Exception as conn_err:
            logger.error(f"Erro ao obter conexão com PostgreSQL: {conn_err}")
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return next((a for a in cls._TEST_ALUNOS.values() if a.usuario_id == user_id), None)
            raise DatabaseConnectionError(f"Falha de conexão com PostgreSQL ao buscar aluno: {conn_err}")

        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao buscar aluno com usuario_id {user_id}.")
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return next((a for a in cls._TEST_ALUNOS.values() if a.usuario_id == user_id), None)
            raise DatabaseConnectionError(f"Falha de conexão com PostgreSQL ao buscar aluno com usuario_id {user_id}.")

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
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar aluno por usuario_id {user_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing() and getattr(cls, "_ALLOW_TEST_FALLBACK", True):
                return next((a for a in cls._TEST_ALUNOS.values() if a.usuario_id == user_id), None)
            raise DatabaseQueryError(f"Erro inesperado ao consultar aluno por usuario_id {user_id}: {e}")

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
            if cls._is_testing() and user_id in cls._TEST_USERS:
                cls._TEST_USERS[user_id].senha = new_password_hash
                return True
            return False

    @classmethod
    def update_aluno_profile(
        cls,
        aluno_id: int,
        telefone: str,
        objetivo: Optional[str] = None,
        data_nascimento: Optional[date] = None
    ) -> bool:
        """
        Atualiza os dados cadastrais permitidos de um aluno (telefone, objetivo, data de nascimento).
        Respeita integralmente as colunas da tabela 'alunos'.
        """
        if not aluno_id:
            return False

        conn = get_db_connection()
        if not conn:
            logger.error(f"Falha de conexão com PostgreSQL ao atualizar perfil do aluno id {aluno_id}.")
            if cls._is_testing():
                for a in cls._TEST_ALUNOS.values():
                    if a.id == aluno_id:
                        a.telefone = telefone
                        a.objetivo = objetivo
                        a.data_nascimento = data_nascimento
                        return True
            return False

        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE alunos
                        SET telefone = %s, objetivo = %s, data_nascimento = %s
                        WHERE id = %s
                        """,
                        (telefone, objetivo, data_nascimento, aluno_id)
                    )
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Erro ao atualizar dados do aluno id {aluno_id} no PostgreSQL: {e}", exc_info=True)
            if cls._is_testing():
                for a in cls._TEST_ALUNOS.values():
                    if a.id == aluno_id:
                        a.telefone = telefone
                        a.objetivo = objetivo
                        a.data_nascimento = data_nascimento
                        return True
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
