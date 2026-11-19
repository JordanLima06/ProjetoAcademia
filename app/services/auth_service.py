import re
import hashlib
import logging
from datetime import datetime, date
from typing import Tuple, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app
from app.models.user import User, Aluno
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

class AuthService:
    """Regras de negócio de autenticação, cadastro e recuperação de credenciais."""

    EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
    PASSWORD_RESET_SALT = "fightacademy-password-reset-salt"
    TOKEN_MAX_AGE_SECONDS = 1800  # 30 minutos

    @classmethod
    def register_aluno(cls, dados: dict) -> Tuple[bool, str, Optional[User], Optional[Aluno]]:
        """
        Valida os dados e cadastra um novo aluno no FightAcademy.
        Cria atomicamente o registro em 'usuarios' e em 'alunos'.
        Não cria matrículas nem pagamentos nesta fase.
        """
        nome = (dados.get("nome") or "").strip()
        email = (dados.get("email") or "").strip().lower()
        telefone = (dados.get("telefone") or "").strip()
        data_nascimento_raw = (dados.get("data_nascimento") or "").strip()
        senha = dados.get("senha") or ""
        confirmar = dados.get("confirmar") or ""
        objetivo = (dados.get("objetivo") or "").strip() or None

        # 1. Validação de Nome
        if not nome or len(nome) < 2:
            return False, "Informe seu nome completo (mínimo de 2 caracteres).", None, None
        if len(nome) > 100:
            return False, "O nome não pode exceder 100 caracteres.", None, None

        # 2. Validação de E-mail
        if not email or not cls.EMAIL_REGEX.match(email):
            return False, "Informe um endereço de e-mail válido.", None, None
        if len(email) > 150:
            return False, "O e-mail não pode exceder 150 caracteres.", None, None

        # 3. Validação de Telefone (DDD + 8 ou 9 dígitos)
        digitos_tel = re.sub(r"\D", "", telefone)
        if len(digitos_tel) < 10 or len(digitos_tel) > 11:
            return False, "Informe um telefone válido com DDD (10 ou 11 dígitos).", None, None

        # 4. Validação de Data de Nascimento
        if not data_nascimento_raw:
            return False, "A data de nascimento é obrigatória.", None, None

        try:
            data_nasc = datetime.strptime(data_nascimento_raw, "%Y-%m-%d").date()
        except ValueError:
            return False, "Formato de data de nascimento inválido. Use AAAA-MM-DD.", None, None

        hoje = date.today()
        if data_nasc >= hoje:
            return False, "A data de nascimento deve estar no passado.", None, None

        idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
        if idade < 12 or idade > 120:
            return False, "A idade deve estar entre 12 e 120 anos para cadastro.", None, None

        # 5. Validação de Senha
        if not senha or len(senha) < 8:
            return False, "A senha precisa ter pelo menos 8 caracteres.", None, None

        if senha != confirmar:
            return False, "As senhas não coincidem.", None, None

        # 6. Unicidade de E-mail no PostgreSQL
        usuario_existente = UserRepository.find_by_email(email)
        if usuario_existente:
            return False, "Este e-mail já está cadastrado no sistema.", None, None

        # 7. Criptografia Segura da Senha
        senha_hash = generate_password_hash(senha)

        novo_usuario = User(
            nome=nome,
            email=email,
            senha=senha_hash,
            tipo="aluno",
            ativo=True
        )

        novo_aluno = Aluno(
            usuario_id=0,
            data_nascimento=data_nasc,
            telefone=telefone,
            objetivo=objetivo,
            data_cadastro=hoje
        )

        # 8. Persistência em Transação Atômica (PostgreSQL)
        try:
            user_criado, aluno_criado = UserRepository.create_user_with_student(novo_usuario, novo_aluno)
            return True, "Cadastro realizado com sucesso! Faça login para começar.", user_criado, aluno_criado
        except Exception as e:
            logger.error(f"Erro no serviço de autenticação ao registrar aluno: {e}", exc_info=True)
            return False, "Erro ao registrar cadastro. Tente novamente mais tarde.", None, None

    @classmethod
    def authenticate(cls, email: str, senha: str) -> Tuple[bool, str, Optional[User]]:
        """
        Valida credenciais para login.
        Verifica formato, hash da senha e se o usuário está ativo.
        """
        email = (email or "").strip().lower()
        senha = senha or ""

        if not email or not senha:
            return False, "E-mail e senha são obrigatórios.", None

        user = UserRepository.find_by_email(email)
        if not user or not check_password_hash(user.senha, senha):
            return False, "E-mail ou senha incorretos.", None

        if not user.ativo:
            return False, "Esta conta está desativada. Entre em contato com a academia.", None

        return True, "Login realizado com sucesso!", user

    @classmethod
    def _get_password_fingerprint(cls, senha_hash: str) -> str:
        """Gera um identificador criptográfico curto do hash atual da senha para invalidar tokens após redefinição."""
        return hashlib.sha256(senha_hash.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def generate_password_reset_token(cls, email: str) -> Tuple[bool, str, Optional[str]]:
        """
        Gera um token assinado com validade de 30 minutos.
        Incorpora a digital da senha atual para impedir reutilização do token após a alteração.
        """
        email = (email or "").strip().lower()
        if not email:
            return False, "Informe seu e-mail.", None

        user = UserRepository.find_by_email(email)
        if not user or not user.ativo:
            # Mensagem genérica para não revelar existência de contas
            return False, "Se o e-mail estiver cadastrado, as instruções serão processadas.", None

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        payload = {
            "user_id": user.id,
            "email": user.email,
            "p_fingerprint": cls._get_password_fingerprint(user.senha)
        }
        token = serializer.dumps(payload, salt=cls.PASSWORD_RESET_SALT)
        return True, "Token de recuperação gerado com sucesso.", token

    @classmethod
    def validate_and_reset_password(cls, token: str, nova_senha: str, confirmar: str) -> Tuple[bool, str]:
        """
        Valida o token temporário, verifica expiração (30 min) e impede reutilização.
        Atualiza a senha do usuário no banco com hash seguro.
        """
        if not token:
            return False, "Token de recuperação ausente."

        if not nova_senha or len(nova_senha) < 8:
            return False, "A nova senha deve ter pelo menos 8 caracteres."

        if nova_senha != confirmar:
            return False, "A confirmação de senha não coincide."

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            payload = serializer.loads(
                token,
                salt=cls.PASSWORD_RESET_SALT,
                max_age=cls.TOKEN_MAX_AGE_SECONDS
            )
        except SignatureExpired:
            return False, "O link de recuperação expirou (validade máxima de 30 minutos). Solicite um novo."
        except BadSignature:
            return False, "Link de recuperação inválido ou corrompido."
        except Exception as e:
            logger.error(f"Erro ao decodificar token de recuperação: {e}")
            return False, "Link de recuperação inválido."

        user_id = payload.get("user_id")
        token_fingerprint = payload.get("p_fingerprint")

        user = UserRepository.find_by_id(user_id)
        if not user or not user.ativo:
            return False, "Usuário não localizado ou conta inativa."

        # Validação contra reutilização do token:
        # Se a senha já foi alterada, a digital do hash atual será diferente da gravada no token!
        current_fingerprint = cls._get_password_fingerprint(user.senha)
        if current_fingerprint != token_fingerprint:
            return False, "Este link de recuperação já foi utilizado. Solicite um novo se necessário."

        nova_senha_hash = generate_password_hash(nova_senha)
        sucesso = UserRepository.update_password(user.id, nova_senha_hash)
        if sucesso:
            return True, "Senha redefinida com sucesso! Faça login com sua nova senha."
        return False, "Erro ao atualizar senha no banco de dados. Tente novamente."
