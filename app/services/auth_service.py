import re
from typing import Tuple, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user import User
from app.repositories.user_repository import UserRepository

class AuthService:
    """Regras de negócio de autenticação, validação e registro de usuários."""

    EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

    @classmethod
    def register(cls, nome: str, email: str, senha: str, confirmar: str) -> Tuple[bool, str, Optional[User]]:
        """Valida e registra um novo usuário/aluno."""
        nome = (nome or "").strip()
        email = (email or "").strip().lower()

        if not nome or len(nome) < 2:
            return False, "Informe seu nome completo (mínimo 2 caracteres).", None

        if not email or not cls.EMAIL_REGEX.match(email):
            return False, "Informe um e-mail válido.", None

        if not senha or len(senha) < 8:
            return False, "A senha precisa ter pelo menos 8 caracteres.", None

        if senha != confirmar:
            return False, "As senhas não coincidem.", None

        existing_user = UserRepository.find_by_email(email)
        if existing_user:
            return False, "Este e-mail já está cadastrado.", None

        senha_hash = generate_password_hash(senha)
        novo_usuario = User(nome=nome, email=email, senha_hash=senha_hash)

        usuario_salvo = UserRepository.create(novo_usuario)
        return True, "Cadastro realizado com sucesso!", usuario_salvo

    @classmethod
    def authenticate(cls, email: str, senha: str) -> Tuple[bool, str, Optional[User]]:
        """Valida credenciais para login."""
        email = (email or "").strip().lower()

        if not email or not senha:
            return False, "E-mail e senha são obrigatórios.", None

        user = UserRepository.find_by_email(email)
        if not user or not check_password_hash(user.senha_hash, senha):
            return False, "E-mail ou senha incorretos.", None

        if not user.ativo:
            return False, "Esta conta está desativada. Contate a academia.", None

        return True, "Login realizado com sucesso!", user
