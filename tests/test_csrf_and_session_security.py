import unittest
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash

from app import create_app
from app.config import TestingConfig
from app.models.user import User, Aluno
from app.models.academy import Plano, Modalidade
from app.models.enrollment import Matricula
from app.repositories.user_repository import UserRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.auth_service import AuthService
from tests.csrf_helper import get_csrf_token

class CSRFAndSessionSecurityTestCase(unittest.TestCase):
    """
    Suíte de testes automatizados pós-auditoria da Fase 4:
    Valida rigorosamente:
    1. Proteção CSRF global (rejeição de POST sem token, token inválido, aceitação com token válido, presença em formulários).
    2. Revogação de sessões antigas após alteração ou redefinição de senha via credencial fingerprint.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.test_request_context()
        self.ctx.push()

        # Limpeza de fixtures em memória
        UserRepository._TEST_USERS.clear()
        UserRepository._TEST_ALUNOS.clear()
        EnrollmentRepository._TEST_MATRICULAS.clear()
        EnrollmentRepository._TEST_MATRICULA_MODALIDADES.clear()
        PaymentRepository._TEST_PAGAMENTOS.clear()

        UserRepository._TEST_ID_SEQ = 1
        EnrollmentRepository._TEST_ID_SEQ = 1
        PaymentRepository._TEST_PAGAMENTOS.clear()

        # Aluno de teste principal
        self.user_aluno = User(
            id=1,
            nome="Rodrigo Alves",
            email="rodrigo@teste.com",
            senha=generate_password_hash("SenhaInicial123"),
            tipo="aluno",
            ativo=True
        )
        UserRepository._TEST_USERS[1] = self.user_aluno

        self.aluno = Aluno(
            id=1,
            usuario_id=1,
            data_nascimento=date(1995, 6, 10),
            telefone="(11) 98888-7777",
            data_cadastro=date.today(),
            objetivo="Boxe e condicionamento",
            usuario=self.user_aluno
        )
        UserRepository._TEST_ALUNOS[1] = self.aluno

    def tearDown(self):
        self.ctx.pop()

    def _login_client(self, client, user):
        """Autentica o cliente na sessão com auth_fingerprint atualizado."""
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_nome"] = user.nome
            sess["user_tipo"] = user.tipo
            sess["auth_fingerprint"] = AuthService.get_password_fingerprint(user.senha)

    # -------------------------------------------------------------
    # 1. TESTES DE PROTEÇÃO CSRF
    # -------------------------------------------------------------

    def test_01_post_sem_token_csrf_rejeitado_400(self):
        """Valida que qualquer requisição POST sem token CSRF é rejeitada com HTTP 400 Bad Request."""
        res = self.client.post("/login", data={
            "email": "rodrigo@teste.com",
            "senha": "SenhaInicial123"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("The CSRF token is missing", res.get_data(as_text=True))

    def test_02_post_com_token_csrf_invalido_rejeitado_400(self):
        """Valida que requisição POST com token CSRF falso/adulterado é rejeitada com HTTP 400."""
        # Inicializa a sessão do cliente visitando uma página
        self.client.get("/login")

        # Fornece token adulterado
        res = self.client.post("/login", data={
            "email": "rodrigo@teste.com",
            "senha": "SenhaInicial123",
            "csrf_token": "token-forjado-e-invalido-12345"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("The CSRF token is invalid", res.get_data(as_text=True))

    def test_03_post_com_token_csrf_valido_autentica_sucesso(self):
        """Valida que requisição POST com token CSRF legítimo é processada com sucesso."""
        token = get_csrf_token(self.client, self.app)
        res = self.client.post("/login", data={
            "email": "rodrigo@teste.com",
            "senha": "SenhaInicial123",
            "csrf_token": token
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/", res.headers["Location"])

    def test_04_todos_os_formularios_html_renderizam_campo_csrf(self):
        """Verifica se todos os formulários públicos e autenticados contêm o campo oculto csrf_token."""
        # 1. Formulário de Login e Recuperação de Senha
        res_login = self.client.get("/login")
        self.assertEqual(res_login.status_code, 200)
        html_login = res_login.get_data(as_text=True)
        self.assertIn('name="csrf_token"', html_login)
        tokens_encontrados = re.findall(r'name="csrf_token"\s+value="([^"]+)"', html_login)
        self.assertGreaterEqual(len(tokens_encontrados), 2)  # login-form e recuperar-form

        # 2. Formulário de Cadastro
        res_cad = self.client.get("/cadastro")
        self.assertEqual(res_cad.status_code, 200)
        self.assertIn('name="csrf_token"', res_cad.get_data(as_text=True))

        # 3. Formulário de Aula Experimental
        res_aula = self.client.get("/aula-experimental")
        self.assertEqual(res_aula.status_code, 200)
        self.assertIn('name="csrf_token"', res_aula.get_data(as_text=True))

        # 4. Formulários autenticados de Perfil e Alteração de Senha
        self._login_client(self.client, self.user_aluno)
        res_perfil = self.client.get("/aluno/perfil")
        self.assertEqual(res_perfil.status_code, 200)
        html_perfil = res_perfil.get_data(as_text=True)
        tokens_perfil = re.findall(r'name="csrf_token"\s+value="([^"]+)"', html_perfil)
        self.assertGreaterEqual(len(tokens_perfil), 2)  # perfil form e alterar_senha form

        # 5. Formulário de Contratação
        res_contratar = self.client.get("/contratar/essencial")
        self.assertEqual(res_contratar.status_code, 200)
        self.assertIn('name="csrf_token"', res_contratar.get_data(as_text=True))

    def test_05_rotas_post_sensiveis_rejeitam_requisicoes_sem_csrf(self):
        """Valida que todas as rotas POST de alteração de estado rejeitam sem token CSRF."""
        self._login_client(self.client, self.user_aluno)

        # POST /aluno/perfil sem CSRF
        res1 = self.client.post("/aluno/perfil", data={"telefone": "11988887777"})
        self.assertEqual(res1.status_code, 400)

        # POST /aluno/alterar-senha sem CSRF
        res2 = self.client.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaInicial123",
            "nova_senha": "NovaSenhaSegura123",
            "confirmar_senha": "NovaSenhaSegura123"
        })
        self.assertEqual(res2.status_code, 400)

        # POST /cadastro sem CSRF
        res3 = self.client.post("/cadastro", data={"email": "novo@teste.com"})
        self.assertEqual(res3.status_code, 400)

        # POST /aula-experimental sem CSRF
        res4 = self.client.post("/aula-experimental", data={"nome": "Teste", "telefone": "11999998888"})
        self.assertEqual(res4.status_code, 400)

        # POST /recuperar-senha sem CSRF
        res5 = self.client.post("/recuperar-senha", data={"email": "rodrigo@teste.com"})
        self.assertEqual(res5.status_code, 400)

    # -------------------------------------------------------------
    # 2. TESTES DE REVOGAÇÃO DE SESSÕES APÓS ALTERAÇÃO DE SENHA
    # -------------------------------------------------------------

    def test_06_sessao_atual_preservada_apos_alteracao_senha(self):
        """
        Valida que o cliente que efetuou a alteração de senha autenticada
        permanece logado (sua sessão é atualizada com a nova credencial fingerprint).
        """
        self._login_client(self.client, self.user_aluno)

        # Altera a senha com token CSRF válido
        token = get_csrf_token(self.client, self.app)
        res = self.client.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaInicial123",
            "nova_senha": "NovaSenhaForte789!",
            "confirmar_senha": "NovaSenhaForte789!",
            "csrf_token": token
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Senha alterada com sucesso!", res.get_data(as_text=True))

        # A sessão atual continua ativa e consegue acessar o painel normalmente
        res_painel = self.client.get("/aluno/painel")
        self.assertEqual(res_painel.status_code, 200)
        self.assertIn("Rodrigo Alves", res_painel.get_data(as_text=True))

    def test_07_sessao_antiga_em_outro_dispositivo_revogada_imediatamente(self):
        """
        Valida que uma sessão prévia aberta em outro dispositivo/cliente é revogada
        imediatamente na primeira requisição após a senha do aluno ser alterada.
        """
        # Dispositivo 1 (Navegador A) e Dispositivo 2 (Navegador B) logados com a senha inicial
        client_a = self.app.test_client()
        client_b = self.app.test_client()

        self._login_client(client_a, self.user_aluno)
        self._login_client(client_b, self.user_aluno)

        # Ambos os navegadores conseguem acessar o painel
        self.assertEqual(client_a.get("/aluno/painel").status_code, 200)
        self.assertEqual(client_b.get("/aluno/painel").status_code, 200)

        # Dispositivo 1 altera a senha
        token_a = get_csrf_token(client_a, self.app)
        res_troca = client_a.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaInicial123",
            "nova_senha": "SenhaDispositivo1!",
            "confirmar_senha": "SenhaDispositivo1!",
            "csrf_token": token_a
        }, follow_redirects=True)
        self.assertEqual(res_troca.status_code, 200)

        # Dispositivo 1 permanece ativo
        self.assertEqual(client_a.get("/aluno/painel").status_code, 200)

        # Dispositivo 2 tenta acessar o painel -> DETECTA FINGERPRINT DESATUALIZADO!
        res_b = client_b.get("/aluno/painel")
        # Deve ser redirecionado para /login com HTTP 302
        self.assertEqual(res_b.status_code, 302)
        self.assertIn("/login", res_b.headers["Location"])

        # Segue o redirecionamento e confere a mensagem de segurança
        res_b_redirect = client_b.get("/aluno/painel", follow_redirects=True)
        html_b = res_b_redirect.get_data(as_text=True)
        self.assertIn("Sua senha foi alterada recentemente ou sua sessão expirou", html_b)

        # Confirma que a sessão no Dispositivo 2 foi totalmente limpa
        with client_b.session_transaction() as sess_b:
            self.assertNotIn("user_id", sess_b)
            self.assertNotIn("auth_fingerprint", sess_b)

    def test_08_login_com_nova_senha_e_rejeicao_senha_antiga(self):
        """Valida que após alteração, a senha antiga é rejeitada e a nova aceita com novo fingerprint."""
        # 1. Altera a senha
        token = get_csrf_token(self.client, self.app)
        self._login_client(self.client, self.user_aluno)
        self.client.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaInicial123",
            "nova_senha": "SuperNovaSenha321!",
            "confirmar_senha": "SuperNovaSenha321!",
            "csrf_token": token
        })

        # 2. Desloga via POST com CSRF
        token_logout = get_csrf_token(self.client, self.app)
        self.client.post("/logout", data={"csrf_token": token_logout})

        # 3. Tenta login com a senha antiga -> deve falhar
        token_login1 = get_csrf_token(self.client, self.app)
        res_antiga = self.client.post("/login", data={
            "email": "rodrigo@teste.com",
            "senha": "SenhaInicial123",
            "csrf_token": token_login1
        })
        self.assertEqual(res_antiga.status_code, 200)
        self.assertIn("E-mail ou senha incorretos", res_antiga.get_data(as_text=True))

        # 4. Login com a nova senha -> sucesso e armazena novo fingerprint
        token_login2 = get_csrf_token(self.client, self.app)
        res_nova = self.client.post("/login", data={
            "email": "rodrigo@teste.com",
            "senha": "SuperNovaSenha321!",
            "csrf_token": token_login2
        }, follow_redirects=False)
        self.assertEqual(res_nova.status_code, 302)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], 1)
            novo_fp_esperado = AuthService.get_password_fingerprint(self.user_aluno.senha)
            self.assertEqual(sess["auth_fingerprint"], novo_fp_esperado)

    def test_09_sessao_antiga_revogada_apos_redefinicao_por_token(self):
        """Valida que sessões ativas são revogadas quando a senha é redefinida via token de recuperação."""
        client_ativo = self.app.test_client()
        self._login_client(client_ativo, self.user_aluno)
        self.assertEqual(client_ativo.get("/aluno/painel").status_code, 200)

        # Gera token de recuperação e redefine a senha externamente
        _, _, token_reset = AuthService.generate_password_reset_token("rodrigo@teste.com")
        sucesso, msg = AuthService.validate_and_reset_password(token_reset, "RedefinidaToken999!", "RedefinidaToken999!")
        self.assertTrue(sucesso)

        # O cliente previamente logado tenta fazer uma requisição -> detecta revogação
        res = client_ativo.get("/aluno/painel")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

        # Sessão limpa
        with client_ativo.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_10_sessao_sem_fingerprint_invalida_e_limpa(self):
        """Valida que cookies legados sem o campo auth_fingerprint são tratados como inválidos e limpos."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_nome"] = "Rodrigo Alves"
            sess["user_tipo"] = "aluno"
            # Sem auth_fingerprint

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    # -------------------------------------------------------------
    # 3. TESTES DE LOGOUT VIA POST COM CSRF
    # -------------------------------------------------------------

    def test_11_logout_get_nao_executa_logout_e_retorna_405(self):
        """Valida que requisição GET /logout é rejeitada com HTTP 405 Method Not Allowed e a sessão é preservada."""
        self._login_client(self.client, self.user_aluno)

        res = self.client.get("/logout")
        self.assertEqual(res.status_code, 405)

        # Sessão permanece ativa
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), 1)

    def test_12_logout_post_sem_csrf_rejeitado_400(self):
        """Valida que POST /logout sem token CSRF é rejeitado com HTTP 400 e não efetua logout."""
        self._login_client(self.client, self.user_aluno)

        res = self.client.post("/logout")
        self.assertEqual(res.status_code, 400)

        # Sessão permanece ativa
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), 1)

    def test_13_logout_post_com_csrf_valido_encerra_sessao(self):
        """Valida que POST /logout com token CSRF válido encerra a sessão com sucesso e redireciona."""
        self._login_client(self.client, self.user_aluno)
        csrf_token = get_csrf_token(self.client, self.app)

        res = self.client.post("/logout", data={"csrf_token": csrf_token}, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers["Location"], "/")

        # Sessão foi limpa
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)
            self.assertNotIn("auth_fingerprint", sess)

    def test_14_navbar_contem_formulario_post_com_token_csrf(self):
        """Valida que a barra de navegação renderiza o botão de Sair em formulário POST com token CSRF."""
        self._login_client(self.client, self.user_aluno)

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('action="/logout"', html)
        self.assertIn('method="POST"', html)
        self.assertIn('name="csrf_token"', html)
        self.assertIn("btn btn-outline-light btn-sm", html)
        self.assertIn("Sair</button>", html)

    # -------------------------------------------------------------
    # 4. TESTES DE FINGERPRINT HMAC-SHA256 (64 CARACTERES)
    # -------------------------------------------------------------

    def test_15_fingerprint_hmac_sha256_formato_e_tamanho(self):
        """Valida que o fingerprint gerado utiliza HMAC-SHA256 com SECRET_KEY e possui 64 caracteres hexadecimais."""
        import hmac
        import hashlib

        fp = AuthService.get_password_fingerprint(self.user_aluno.senha)
        self.assertEqual(len(fp), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in fp))

        # Confere o cálculo exato utilizando a SECRET_KEY configurada
        expected_fp = hmac.new(
            self.app.config["SECRET_KEY"].encode("utf-8"),
            self.user_aluno.senha.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        self.assertEqual(fp, expected_fp)

    def test_16_cookie_antigo_com_fingerprint_truncado_exige_novo_login(self):
        """Valida que cookies legados com fingerprints de 16 caracteres são rejeitados com segurança."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_nome"] = "Rodrigo Alves"
            sess["user_tipo"] = "aluno"
            sess["auth_fingerprint"] = "a1b2c3d4e5f60718"  # 16 caracteres (formato anterior)

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

        # Sessão foi limpa
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)


if __name__ == "__main__":
    unittest.main()
