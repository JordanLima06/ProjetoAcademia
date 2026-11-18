from typing import Optional
from app.db import get_db_connection
from app.models.user import User

class UserRepository:
    """Repositório de persistência e consultas SQL para a entidade Usuário."""

    @staticmethod
    def find_by_email(email: str) -> Optional[User]:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, nome, email, senha_hash, criado_em, ativo FROM usuarios WHERE email = %s",
                    (email.lower().strip(),)
                )
                row = cursor.fetchone()
                if row:
                    return User(
                        id=row["id"],
                        nome=row["nome"],
                        email=row["email"],
                        senha_hash=row["senha_hash"],
                        criado_em=row.get("criado_em"),
                        ativo=row.get("ativo", True)
                    )
        return None

    @staticmethod
    def find_by_id(user_id: int) -> Optional[User]:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, nome, email, senha_hash, criado_em, ativo FROM usuarios WHERE id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return User(
                        id=row["id"],
                        nome=row["nome"],
                        email=row["email"],
                        senha_hash=row["senha_hash"],
                        criado_em=row.get("criado_em"),
                        ativo=row.get("ativo", True)
                    )
        return None

    @staticmethod
    def create(user: User) -> User:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO usuarios (nome, email, senha_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id, criado_em
                    """,
                    (user.nome, user.email.lower().strip(), user.senha_hash)
                )
                res = cursor.fetchone()
                conn.commit()
                user.id = res["id"]
                user.criado_em = res.get("criado_em")
        return user
