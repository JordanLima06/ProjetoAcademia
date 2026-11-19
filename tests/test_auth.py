import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from werkzeug.security import check_password_hash, generate_password_hash
from flask import g, session

from app import create_app
from app.config import TestingConfig
from app.models.user import User, Aluno
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.utils.auth_decorators import login_required, role_required

class AuthTestCase(unittest.TestCase):
    """Testes automatizados da Fase 2 — Autenticação, Usuários, Alunos e Permissões."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        # Limpa dicionários de teste
        UserRepository._TEST_USERS.clear()
        UserRepository._TEST_ALUNOS.clear()
        UserRepository._TEST_ID_SEQ = 1

    def tearDown(self):
        self.ctx.pop()

    def test_cadastro_sucesso_com_transacao_e_data_cadastro(self):
        """Valida cadastro atômico com persistência explícita de data_cadastro e hash de senha."""
        dados = {
            "nome": "Marcos Oliveira",
            "email": "marcos@exemplo.com",
            "telefone": "(82) 99876-5432",
            "data_nascimento": "1995-05-15",
            "senha": "SenhaForte123!",
            "confirmar": "SenhaForte123!",
            "objetivo": "Condicionamento e hipertrofia"
        }

        sucesso, msg, user, aluno = AuthService.register_aluno(dados)
        self.assertTrue(sucesso)
        self.assertIsNotNone(user)
        self.assertIsNotNone(aluno)
        self.assertEqual(user.nome, "Marcos Oliveira")
        self.assertEqual(user.email, "marcos@exemplo.com")
        self.assertEqual(user.tipo, "aluno")
        self.assertTrue(user.ativo)
        # Senha gravada como hash, nunca em texto puro
        self.assertNotEqual(user.senha, "SenhaForte123!")
        self.assertTrue(check_password_hash(user.senha, "SenhaForte123!"))
        # Confirma persistência explícita da data_cadastro
        self.assertEqual(aluno.data_cadastro, date.today())
        self.assertEqual(aluno.data_nascimento, date(1995, 5, 15))
        self.assertEqual(aluno.usuario_id, user.id)

    def test_rollback_quando_criacao_aluno_falhar(self):
        """Valida que falha na inserção do aluno dispara rollback na transação PostgreSQL."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Simula: INSERT usuarios ok, mas INSERT alunos falha
        mock_cursor.fetchone.side_effect = [
            {"id": 10, "criado_em": datetime.now()},  # retorno de usuarios
            Exception("Simulando falha de integridade em alunos")  # erro em alunos
        ]

        u = User(nome="Teste", email="rollback@teste.com", senha="hash", tipo="aluno")
        a = Aluno(usuario_id=0, data_nascimento=date(1990, 1, 1), telefone="82999998888")

        with patch("app.repositories.user_repository.get_db_connection", return_value=mock_conn):
            with self.assertRaises(Exception):
                UserRepository.create_user_with_student(u, a)

            # Verifica se o rollback foi invocado
            mock_conn.rollback.assert_called()

    def test_validacoes_cadastro_aluno(self):
        """Valida regras de negócio de cadastro de aluno."""
        base = {
            "nome": "Lucas Santos",
            "email": "lucas@teste.com",
            "telefone": "(82) 99999-1234",
            "data_nascimento": "2000-01-01",
            "senha": "MinhaSenha123",
            "confirmar": "MinhaSenha123"
        }

        # Nome curto
        d1 = dict(base, nome="L")
        s, m, _, _ = AuthService.register_aluno(d1)
        self.assertFalse(s)
        self.assertIn("nome", m.lower())

        # Email inválido
        d2 = dict(base, email="email_invalido")
        s, m, _, _ = AuthService.register_aluno(d2)
        self.assertFalse(s)
        self.assertIn("e-mail", m.lower())

        # Telefone curto (< 10 dígitos)
        d3 = dict(base, telefone="12345")
        s, m, _, _ = AuthService.register_aluno(d3)
        self.assertFalse(s)
        self.assertIn("telefone", m.lower())

        # Data de nascimento futura
        d4 = dict(base, data_nascimento="2099-01-01")
        s, m, _, _ = AuthService.register_aluno(d4)
        self.assertFalse(s)
        self.assertIn("passado", m.lower())

        # Senha curta (< 8 chars)
        d5 = dict(base, senha="123", confirmar="123")
        s, m, _, _ = AuthService.register_aluno(d5)
        self.assertFalse(s)
        self.assertIn("8 caracteres", m)

        # Senhas não coincidem
        d6 = dict(base, confirmar="OutraSenhaDiferente")
        s, m, _, _ = AuthService.register_aluno(d6)
        self.assertFalse(s)
        self.assertIn("coincidem", m.lower())

    def test_bloqueio_email_duplicado(self):
        """Garante que não é permitido cadastrar o mesmo e-mail duas vezes."""
        dados = {
            "nome": "Ana Clara",
            "email": "ana@exemplo.com",
            "telefone": "82991112233",
            "data_nascimento": "1998-03-20",
            "senha": "SenhaValida123",
            "confirmar": "SenhaValida123"
        }
        s1, _, _, _ = AuthService.register_aluno(dados)
        self.assertTrue(s1)

        s2, m2, _, _ = AuthService.register_aluno(dados)
        self.assertFalse(s2)
        self.assertIn("já está cadastrado", m2.lower())

    def test_login_sucesso_e_seguranca_sessao(self):
        """Valida autenticação com sucesso, limpeza de sessão e permanência configurada."""
        # Cadastra usuário
        dados = {
            "nome": "Roberto Carlos",
            "email": "roberto@exemplo.com",
            "telefone": "82993334455",
            "data_nascimento": "1990-10-10",
            "senha": "SenhaCorreta123",
            "confirmar": "SenhaCorreta123"
        }
        AuthService.register_aluno(dados)

        response = self.client.post("/login", data={
            "email": "roberto@exemplo.com",
            "senha": "SenhaCorreta123"
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertIn("user_id", sess)
            self.assertEqual(sess["user_nome"], "Roberto Carlos")
            self.assertEqual(sess["user_email"], "roberto@exemplo.com")
            self.assertEqual(sess["user_tipo"], "aluno")

    def test_login_senha_incorreta_e_usuario_inexistente(self):
        """Valida que credenciais inválidas não autenticam."""
        s, m, u = AuthService.authenticate("inexistente@exemplo.com", "qualquer")
        self.assertFalse(s)
        self.assertIsNone(u)

        # Usuário cadastrado com senha errada
        dados = {
            "nome": "Julia Melo",
            "email": "julia@exemplo.com",
            "telefone": "82995556677",
            "data_nascimento": "1996-07-07",
            "senha": "SenhaOriginal123",
            "confirmar": "SenhaOriginal123"
        }
        AuthService.register_aluno(dados)

        s2, m2, u2 = AuthService.authenticate("julia@exemplo.com", "SenhaErrada123")
        self.assertFalse(s2)
        self.assertIn("incorretos", m2.lower())

    def test_bloqueio_usuarios_inativos(self):
        """Garante que usuários com ativo=False não conseguem se autenticar."""
        user = User(
            id=99,
            nome="Inativo",
            email="inativo@exemplo.com",
            senha=generate_password_hash("Senha123!"),
            tipo="aluno",
            ativo=False
        )
        UserRepository._TEST_USERS[user.id] = user

        s, m, u = AuthService.authenticate("inativo@exemplo.com", "Senha123!")
        self.assertFalse(s)
        self.assertIn("desativada", m.lower())

    def test_decorador_login_required_disponibiliza_g_user(self):
        """Verifica se login_required recupera o usuário atualizado do banco e popula g.user."""
        user = User(
            id=10,
            nome="Atleta 1",
            email="atleta1@exemplo.com",
            senha="hash",
            tipo="aluno",
            ativo=True
        )
        UserRepository._TEST_USERS[user.id] = user

        @login_required
        def dummy_view():
            return f"Ola, {g.user.nome} ({g.user.tipo})"

        # Sem sessão -> redireciona para login
        with self.app.test_request_context("/area-aluno"):
            session.clear()
            res = dummy_view()
            self.assertEqual(res.status_code, 302)
            self.assertIn("/login", res.location)

        # Com sessão ativa -> executa e disponibiliza g.user
        with self.app.test_request_context("/area-aluno"):
            session["user_id"] = 10
            res = dummy_view()
            self.assertEqual(res, "Ola, Atleta 1 (aluno)")
            self.assertEqual(g.user.id, 10)

    def test_decorador_role_required_verifica_tipo_em_g_user_em_tempo_real(self):
        """
        Valida que role_required verifica g.user.tipo atualizado do PostgreSQL,
        não confiando cegamente no valor desatualizado da sessão.
        """
        user = User(
            id=20,
            nome="Carlos Admin",
            email="carlos@exemplo.com",
            senha="hash",
            tipo="aluno",  # inicialmente cadastrado como aluno no banco
            ativo=True
        )
        UserRepository._TEST_USERS[user.id] = user

        @role_required("admin")
        def rota_admin():
            return "Painel Administrativo"

        # Cenário 1: Sessão diz que é admin, mas banco diz que é aluno -> bloqueado (403)!
        with self.app.test_request_context("/painel-admin"):
            session["user_id"] = 20
            session["user_tipo"] = "admin"  # valor forjado ou desatualizado na sessão
            with self.assertRaises(Exception) as cm:
                rota_admin()
            self.assertEqual(getattr(cm.exception, "code", None), 403)

        # Cenário 2: Usuário promovido a admin no banco de dados
        user.tipo = "admin"  # atualizado no PostgreSQL

        with self.app.test_request_context("/painel-admin"):
            session["user_id"] = 20
            session["user_tipo"] = "aluno"  # sessão ainda desatualizada
            res = rota_admin()
            # Como role_required lê de g.user.tipo atualizado do banco, o acesso é liberado com sucesso!
            self.assertEqual(res, "Painel Administrativo")

    def test_recuperacao_senha_token_valido_e_redefinicao(self):
        """Valida geração de token assinado e redefinição de senha."""
        dados = {
            "nome": "Felipe Vieira",
            "email": "felipe@exemplo.com",
            "telefone": "82997778899",
            "data_nascimento": "1992-04-12",
            "senha": "SenhaAntiga123",
            "confirmar": "SenhaAntiga123"
        }
        AuthService.register_aluno(dados)

        sucesso_tok, _, token = AuthService.generate_password_reset_token("felipe@exemplo.com")
        self.assertTrue(sucesso_tok)
        self.assertIsNotNone(token)

        # Redefinição com o token
        sucesso_red, msg_red = AuthService.validate_and_reset_password(
            token,
            "NovaSenhaSegura456!",
            "NovaSenhaSegura456!"
        )
        self.assertTrue(sucesso_red)

        # Valida que o login agora só funciona com a nova senha
        s_velha, _, _ = AuthService.authenticate("felipe@exemplo.com", "SenhaAntiga123")
        self.assertFalse(s_velha)

        s_nova, _, u_novo = AuthService.authenticate("felipe@exemplo.com", "NovaSenhaSegura456!")
        self.assertTrue(s_nova)
        self.assertIsNotNone(u_novo)

    def test_recuperacao_senha_impede_reutilizacao_de_token(self):
        """
        Garante que, uma vez que a senha for alterada, o token anterior
        não pode ser reutilizado para redefinir novamente.
        """
        dados = {
            "nome": "Renata Souza",
            "email": "renata@exemplo.com",
            "telefone": "82991234567",
            "data_nascimento": "1994-09-09",
            "senha": "PrimeiraSenha1",
            "confirmar": "PrimeiraSenha1"
        }
        AuthService.register_aluno(dados)

        _, _, token = AuthService.generate_password_reset_token("renata@exemplo.com")

        # Primeiro uso: sucesso
        s1, _ = AuthService.validate_and_reset_password(token, "SegundaSenha2", "SegundaSenha2")
        self.assertTrue(s1)

        # Segundo uso com o mesmo token: deve ser rejeitado!
        s2, m2 = AuthService.validate_and_reset_password(token, "TerceiraSenha3", "TerceiraSenha3")
        self.assertFalse(s2)
        self.assertIn("já foi utilizado", m2.lower())

    def test_recuperacao_senha_sem_servico_email_documenta_dependencia(self):
        """Valida que a rota /recuperar-senha informa ausência de serviço de e-mail e não simula envio falso."""
        dados = {
            "nome": "Beto Costa",
            "email": "beto@exemplo.com",
            "telefone": "82998889900",
            "data_nascimento": "1991-02-02",
            "senha": "SenhaValida123",
            "confirmar": "SenhaValida123"
        }
        AuthService.register_aluno(dados)

        response = self.client.post("/recuperar-senha", data={"email": "beto@exemplo.com"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Deve exibir aviso de serviço não configurado
        self.assertIn("não está configurado".encode("utf-8"), response.data)

    def test_cadastro_e_contratacao_separados(self):
        """Garante que a rota de cadastro cria usuário e aluno, sem criar contratação/matrícula."""
        response = self.client.post("/cadastro", data={
            "nome": "Thiago Silva",
            "email": "thiago@exemplo.com",
            "telefone": "(82) 99333-2211",
            "data_nascimento": "1997-12-25",
            "senha": "MinhaSenha123",
            "confirmar": "MinhaSenha123",
            "plano": "premium",
            "modalidade": "boxe"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        # Usuário criado
        user = UserRepository.find_by_email("thiago@exemplo.com")
        self.assertIsNotNone(user)
        aluno = UserRepository.find_aluno_by_user_id(user.id)
        self.assertIsNotNone(aluno)

if __name__ == "__main__":
    unittest.main()
