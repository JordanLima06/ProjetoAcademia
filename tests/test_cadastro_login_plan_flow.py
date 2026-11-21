import re
import unittest
from decimal import Decimal
from datetime import date, timedelta

from app import create_app
from app.config import TestingConfig
from app.repositories.user_repository import UserRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.enrollment_service import EnrollmentService


class CadastroFirstLoginPlanFlowTestCase(unittest.TestCase):
    """
    Suíte de testes ponta a ponta para:
    1. Fluxo real de CSRF desde /planos -> /cadastro -> primeiro /login -> /logout.
    2. Preservação do plano escolhido no cadastro até a contratação e exibição na Área do Aluno.
    3. Blindagem contra duplicidade de matrícula, manipulação de valores e opções inválidas.
    4. Proteção contra sobrescrita de sessão por rotas estáticas/404 e validação de headers anti-cache.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.test_request_context()
        self.ctx.push()

        UserRepository._TEST_USERS.clear()
        UserRepository._TEST_ALUNOS.clear()
        EnrollmentRepository._TEST_MATRICULAS.clear()
        EnrollmentRepository._TEST_MATRICULA_MODALIDADES.clear()
        PaymentRepository._TEST_PAGAMENTOS.clear()

        UserRepository._TEST_ID_SEQ = 1
        EnrollmentRepository._TEST_ID_SEQ = 1
        PaymentRepository._TEST_ID_SEQ = 1

    def tearDown(self):
        self.ctx.pop()

    @staticmethod
    def _extract_csrf(html: str) -> str:
        m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        assert m is not None, "Token CSRF não encontrado no HTML renderizado"
        return m.group(1)

    @staticmethod
    def _extract_hidden_input(html: str, name: str):
        m = re.search(rf'name="{re.escape(name)}"\s+value="([^"]*)"', html)
        return m.group(1) if m else None

    # ------------------------------------------------------------------
    # 1. AUTENTICAÇÃO E CSRF (CADASTRO -> PRIMEIRO LOGIN -> LOGOUT)
    # ------------------------------------------------------------------

    def test_01_fluxo_real_cadastro_seguido_do_primeiro_login_sem_erro_csrf(self):
        """
        Reproduz integralmente o cenário sem injeção manual de sessão:
        GET /planos -> GET /cadastro?plano=premium -> POST /cadastro ->
        GET /login -> POST /login -> GET /contratar/premium -> POST /logout.
        """
        # 1. Visitante escolhe o plano
        res_planos = self.client.get("/planos")
        self.assertEqual(res_planos.status_code, 200)
        self.assertIn('/cadastro?plano=premium', res_planos.get_data(as_text=True))

        # 2. Acessa o cadastro com o plano preservado
        res_cad_get = self.client.get("/cadastro?plano=premium")
        self.assertEqual(res_cad_get.status_code, 200)
        self.assertIn("no-store", res_cad_get.headers.get("Cache-Control", ""))
        self.assertTrue(res_cad_get.headers.getlist("Set-Cookie"))
        html_cad = res_cad_get.get_data(as_text=True)
        self.assertIn('value="premium" selected', html_cad)
        csrf_cad = self._extract_csrf(html_cad)

        # 3. Cria a conta (POST /cadastro)
        res_cad_post = self.client.post(
            "/cadastro",
            data={
                "csrf_token": csrf_cad,
                "nome": "Lucas Ferreira",
                "email": "lucas.ferreira@teste.com",
                "telefone": "(11) 99123-4567",
                "data_nascimento": "1997-08-14",
                "plano": "premium",
                "modalidade": "boxe",
                "senha": "SenhaSegura123",
                "confirmar": "SenhaSegura123",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_cad_post.status_code, 302)
        self.assertIn("/login", res_cad_post.headers["Location"])
        self.assertIn("next=/contratar/premium", res_cad_post.headers["Location"])
        self.assertIn("no-store", res_cad_post.headers.get("Cache-Control", ""))

        # 4. Segue o redirecionamento para GET /login
        res_login_get = self.client.get(res_cad_post.headers["Location"])
        self.assertEqual(res_login_get.status_code, 200)
        self.assertIn("no-store", res_login_get.headers.get("Cache-Control", ""))
        self.assertTrue(res_login_get.headers.getlist("Set-Cookie"))
        html_login = res_login_get.get_data(as_text=True)
        csrf_login = self._extract_csrf(html_login)
        next_hidden = self._extract_hidden_input(html_login, "next")
        self.assertEqual(next_hidden, "/contratar/premium")

        # 5. Primeiro login com o token real extraído do HTML
        res_login_post = self.client.post(
            "/login",
            data={
                "csrf_token": csrf_login,
                "next": next_hidden,
                "email": "lucas.ferreira@teste.com",
                "senha": "SenhaSegura123",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_login_post.status_code, 302)
        self.assertEqual(res_login_post.headers["Location"], "/contratar/premium")

        # Confirma sessão autenticada com HMAC fingerprint e novo CSRF token
        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get("user_id"))
            self.assertIn("auth_fingerprint", sess)
            self.assertEqual(len(sess["auth_fingerprint"]), 64)
            self.assertIn("csrf_token", sess)

        # 6. Logout via POST com token real da navbar continua funcionando
        res_contratar = self.client.get("/contratar/premium")
        self.assertEqual(res_contratar.status_code, 200)
        html_contratar = res_contratar.get_data(as_text=True)
        m_logout = re.search(
            r'action="/logout"[^>]*>.*?name="csrf_token"\s+value="([^"]+)"',
            html_contratar,
            re.DOTALL,
        )
        self.assertIsNotNone(m_logout)
        res_logout = self.client.post(
            "/logout",
            data={"csrf_token": m_logout.group(1)},
            follow_redirects=False,
        )
        self.assertEqual(res_logout.status_code, 302)
        self.assertEqual(res_logout.headers["Location"], "/")

    def test_02_estaticos_e_404_nao_geram_ou_sobrescrevem_cookie_de_sessao(self):
        """
        Garante que requisições para /static/* e 404 (como /favicon.ico ou script inexistente)
        NÃO criam token CSRF na sessão nem emitem Set-Cookie concorrente.
        """
        for path in ("/favicon.ico", "/static/js/script.js", "/static/css/login.css"):
            fresh_client = self.app.test_client()
            res = fresh_client.get(path)
            self.assertEqual(
                res.headers.getlist("Set-Cookie"),
                [],
                f"Rota {path} não deveria emitir Set-Cookie de sessão",
            )

    def test_03_get_login_sempre_emite_cookie_e_post_mesma_sessao_autentica(self):
        """GET /login sempre sincroniza Set-Cookie com o token do formulário e POST /login autentica."""
        # Cadastra usuário previamente
        res_cad = self.client.get("/cadastro")
        csrf_cad = self._extract_csrf(res_cad.get_data(as_text=True))
        self.client.post(
            "/cadastro",
            data={
                "csrf_token": csrf_cad,
                "nome": "Mariana Dias",
                "email": "mariana.dias@teste.com",
                "telefone": "(11) 98888-1234",
                "data_nascimento": "1994-03-10",
                "plano": "essencial",
                "modalidade": "musculacao",
                "senha": "MinhaSenha123",
                "confirmar": "MinhaSenha123",
            },
        )

        # Novo cliente anônimo acessa diretamente GET /login
        novo_client = self.app.test_client()
        res_get = novo_client.get("/login")
        self.assertEqual(res_get.status_code, 200)
        self.assertTrue(res_get.headers.getlist("Set-Cookie"))
        csrf_token = self._extract_csrf(res_get.get_data(as_text=True))

        # Segundo GET /login na mesma sessão também deve emitir Set-Cookie sincronizado
        res_get_2 = novo_client.get("/login")
        self.assertEqual(res_get_2.status_code, 200)
        self.assertTrue(res_get_2.headers.getlist("Set-Cookie"))
        csrf_token_2 = self._extract_csrf(res_get_2.get_data(as_text=True))

        # POST /login com token legítimo autentica com sucesso
        res_post = novo_client.post(
            "/login",
            data={
                "csrf_token": csrf_token_2,
                "email": "mariana.dias@teste.com",
                "senha": "MinhaSenha123",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_post.status_code, 302)
        self.assertEqual(csrf_token[:10], csrf_token_2[:10])

    def test_04_csrf_ausente_e_adulterado_continuam_rejeitados_400(self):
        """Proteção CSRF permanece ativa: token ausente ou adulterado retorna 400."""
        res_sem = self.client.post("/login", data={"email": "a@b.com", "senha": "123"})
        self.assertEqual(res_sem.status_code, 400)

        self.client.get("/login")
        res_adulterado = self.client.post(
            "/login",
            data={"email": "a@b.com", "senha": "123", "csrf_token": "invalido.adulterado.xyz"},
        )
        self.assertEqual(res_adulterado.status_code, 400)

    # ------------------------------------------------------------------
    # 2. PLANOS E MATRÍCULAS (PRESERVAÇÃO -> CONTRATAÇÃO -> PAINEL)
    # ------------------------------------------------------------------

    def test_05_fluxo_completo_plano_cadastro_login_contratacao_e_painel(self):
        """
        Valida o fluxo integral:
        1. Escolha do plano Anual -> cadastro preserva o plano (inclusive em erro 400).
        2. Cadastro concluído -> redireciona para login preservando contratação do plano Anual.
        3. Primeiro login -> conduz para /contratar/anual sem perder o plano.
        4. Aluno escolhe opção 12x e cartão -> EnrollmentService cria matrícula e 12 parcelas.
        5. Painel (/aluno/painel) exibe plano Anual, matrícula ativa, modalidades e parcelas.
        6. Novo login subsequente NÃO cria matrícula duplicada e NÃO redireciona para contratar.
        """
        # 1. GET /cadastro?plano=anual
        res_cad_get = self.client.get("/cadastro?plano=anual")
        html_cad = res_cad_get.get_data(as_text=True)
        self.assertIn('value="anual" selected', html_cad)
        csrf_cad = self._extract_csrf(html_cad)

        # 1b. Erro de validação (senha curta) preserva o plano selecionado no formulário
        res_cad_err = self.client.post(
            "/cadastro",
            data={
                "csrf_token": csrf_cad,
                "nome": "Rafael Costa",
                "email": "rafael@teste.com",
                "telefone": "(82) 99999-1111",
                "data_nascimento": "1993-04-20",
                "plano": "anual",
                "modalidade": "jiu-jitsu",
                "senha": "123",
                "confirmar": "123",
            },
        )
        self.assertEqual(res_cad_err.status_code, 400)
        html_err = res_cad_err.get_data(as_text=True)
        self.assertIn('value="anual" selected', html_err)
        self.assertIn('value="Rafael Costa"', html_err)

        # 2. Cadastro válido
        csrf_cad_2 = self._extract_csrf(html_err)
        res_cad_ok = self.client.post(
            "/cadastro",
            data={
                "csrf_token": csrf_cad_2,
                "nome": "Rafael Costa",
                "email": "rafael@teste.com",
                "telefone": "(82) 99999-1111",
                "data_nascimento": "1993-04-20",
                "plano": "anual",
                "modalidade": "jiu-jitsu",
                "senha": "SenhaValida123",
                "confirmar": "SenhaValida123",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_cad_ok.status_code, 302)
        self.assertIn("/login", res_cad_ok.headers["Location"])

        # Nenhuma matrícula criada apenas pelo cadastro
        user = UserRepository.find_by_email("rafael@teste.com")
        aluno = UserRepository.find_aluno_by_user_id(user.id)
        self.assertIsNone(EnrollmentService.obter_matricula_atual(aluno.id))

        # 3. Login conduz diretamente à contratação do plano Anual
        res_login_get = self.client.get(res_cad_ok.headers["Location"])
        html_login = res_login_get.get_data(as_text=True)
        csrf_login = self._extract_csrf(html_login)
        next_val = self._extract_hidden_input(html_login, "next")
        self.assertEqual(next_val, "/contratar/anual")

        res_login_post = self.client.post(
            "/login",
            data={
                "csrf_token": csrf_login,
                "next": next_val,
                "email": "rafael@teste.com",
                "senha": "SenhaValida123",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_login_post.status_code, 302)
        self.assertEqual(res_login_post.headers["Location"], "/contratar/anual")

        # Se o aluno visitar /aluno/painel antes de finalizar, ainda vê o atalho do plano escolhido
        res_painel_antes = self.client.get("/aluno/painel")
        self.assertEqual(res_painel_antes.status_code, 200)
        self.assertIn("Concluir Contratação — Anual", res_painel_antes.get_data(as_text=True))

        # 4. Tela de contratação do plano Anual exibe opções comerciais sem perder o plano
        res_contratar_get = self.client.get("/contratar/anual")
        self.assertEqual(res_contratar_get.status_code, 200)
        html_contratar = res_contratar_get.get_data(as_text=True)
        self.assertIn("Anual", html_contratar)
        self.assertIn("12 parcelas mensais sem juros", html_contratar)
        csrf_contratar = self._extract_csrf(html_contratar)

        # Contratação tentando adulterar preço via formulário (deve ser ignorado pelo servidor!)
        res_contratar_post = self.client.post(
            "/contratar/anual",
            data={
                "csrf_token": csrf_contratar,
                "opcao_pagamento_id": "5",  # 12x do plano anual
                "forma_pagamento": "cartao_credito",
                "valor_cobranca": "0.01",
                "valor_total_contratado": "0.12",
                "preco": "0.01",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_contratar_post.status_code, 302)
        self.assertEqual(res_contratar_post.headers["Location"], "/minha-matricula")

        # 5. Verifica matrícula criada com valores oficiais do servidor
        matricula = EnrollmentService.obter_matricula_atual(aluno.id)
        self.assertIsNotNone(matricula)
        self.assertEqual(matricula.plano.slug, "anual")
        self.assertEqual(matricula.status, "ativa")
        self.assertEqual(matricula.valor_total_contratado, Decimal("1399.90"))
        self.assertEqual(matricula.quantidade_parcelas, 12)

        # Painel do aluno exibe o plano e a matrícula ativa
        res_painel = self.client.get("/aluno/painel")
        self.assertEqual(res_painel.status_code, 200)
        html_painel = res_painel.get_data(as_text=True)
        self.assertIn("Anual", html_painel)
        self.assertIn("Acesso Liberado para Treinos", html_painel)
        self.assertIn("12x de R$ 116,66", html_painel)
        self.assertIn("1399,90", html_painel)

        # 6. Logout e novo login NÃO cria nova matrícula nem reabre contratação
        m_logout = re.search(
            r'action="/logout"[^>]*>.*?name="csrf_token"\s+value="([^"]+)"',
            html_painel,
            re.DOTALL,
        )
        self.client.post("/logout", data={"csrf_token": m_logout.group(1)})

        res_login2_get = self.client.get("/login?next=/contratar/anual")
        csrf_login2 = self._extract_csrf(res_login2_get.get_data(as_text=True))
        res_login2_post = self.client.post(
            "/login",
            data={
                "csrf_token": csrf_login2,
                "next": "/contratar/anual",
                "email": "rafael@teste.com",
                "senha": "SenhaValida123",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_login2_post.status_code, 302)
        self.assertEqual(res_login2_post.headers["Location"], "/aluno/painel")
        self.assertEqual(len(EnrollmentService.obter_historico_matriculas(aluno.id)), 1)

    def test_06_rejeita_plano_invalido_no_cadastro_e_opcao_pagamento_invalida_na_contratacao(self):
        """Valida rejeição de plano inexistente no cadastro e opção de pagamento cruzada/inválida."""
        res_cad = self.client.get("/cadastro")
        csrf_cad = self._extract_csrf(res_cad.get_data(as_text=True))

        # Plano inexistente no POST /cadastro -> 400
        res_plano_inv = self.client.post(
            "/cadastro",
            data={
                "csrf_token": csrf_cad,
                "nome": "Joao Teste",
                "email": "joao.inv@teste.com",
                "telefone": "(11) 99999-8888",
                "data_nascimento": "1995-01-10",
                "plano": "plano-forjado-gratis",
                "modalidade": "boxe",
                "senha": "SenhaValida123",
                "confirmar": "SenhaValida123",
            },
        )
        self.assertEqual(res_plano_inv.status_code, 400)
        self.assertIsNone(UserRepository.find_by_email("joao.inv@teste.com"))

        # Cadastra com plano premium válido e faz login
        csrf_cad2 = self._extract_csrf(res_plano_inv.get_data(as_text=True))
        res_ok = self.client.post(
            "/cadastro",
            data={
                "csrf_token": csrf_cad2,
                "nome": "Joao Teste",
                "email": "joao.ok@teste.com",
                "telefone": "(11) 99999-8888",
                "data_nascimento": "1995-01-10",
                "plano": "premium",
                "modalidade": "boxe",
                "senha": "SenhaValida123",
                "confirmar": "SenhaValida123",
            },
            follow_redirects=False,
        )
        res_lg = self.client.get(res_ok.headers["Location"])
        csrf_lg = self._extract_csrf(res_lg.get_data(as_text=True))
        self.client.post(
            "/login",
            data={
                "csrf_token": csrf_lg,
                "next": "/contratar/premium",
                "email": "joao.ok@teste.com",
                "senha": "SenhaValida123",
            },
        )

        # Tenta contratar premium usando opcao_pagamento_id=1 (que pertence ao plano Essencial!)
        res_cont = self.client.get("/contratar/premium")
        csrf_cont = self._extract_csrf(res_cont.get_data(as_text=True))
        res_bad_opt = self.client.post(
            "/contratar/premium",
            data={
                "csrf_token": csrf_cont,
                "opcao_pagamento_id": "1",  # Pertence ao Essencial (R$ 79,90), não ao Premium!
                "forma_pagamento": "pix",
            },
            follow_redirects=True,
        )
        self.assertEqual(res_bad_opt.status_code, 200)
        self.assertIn("Opção de pagamento inválida", res_bad_opt.get_data(as_text=True))

        user = UserRepository.find_by_email("joao.ok@teste.com")
        aluno = UserRepository.find_aluno_by_user_id(user.id)
        self.assertIsNone(EnrollmentService.obter_matricula_atual(aluno.id))

    def test_07_plano_pendente_nao_vaza_para_outro_usuario_no_mesmo_navegador(self):
        """
        Se Usuário A se cadastrar com plano Premium, mas Usuário B fizer login no mesmo navegador
        sem ?next=/contratar/..., o plano pendente de A não é aplicado a B.
        """
        # Cria Usuário B antes
        res_cad = self.client.get("/cadastro")
        csrf1 = self._extract_csrf(res_cad.get_data(as_text=True))
        self.client.post(
            "/cadastro",
            data={
                "csrf_token": csrf1,
                "nome": "Usuario B",
                "email": "userb@teste.com",
                "telefone": "(11) 91111-2222",
                "data_nascimento": "1990-01-01",
                "plano": "essencial",
                "modalidade": "musculacao",
                "senha": "SenhaValida123",
                "confirmar": "SenhaValida123",
            },
        )

        # Usuário A cadastra com plano Premium no mesmo client/browser
        res_cad_a = self.client.get("/cadastro?plano=premium")
        csrf2 = self._extract_csrf(res_cad_a.get_data(as_text=True))
        self.client.post(
            "/cadastro",
            data={
                "csrf_token": csrf2,
                "nome": "Usuario A",
                "email": "usera@teste.com",
                "telefone": "(11) 93333-4444",
                "data_nascimento": "1992-02-02",
                "plano": "premium",
                "modalidade": "boxe",
                "senha": "SenhaValida123",
                "confirmar": "SenhaValida123",
            },
        )

        # Usuário B acessa /login diretamente (sem next) e faz login
        res_login_b = self.client.get("/login")
        csrf_b = self._extract_csrf(res_login_b.get_data(as_text=True))
        res_post_b = self.client.post(
            "/login",
            data={
                "csrf_token": csrf_b,
                "email": "userb@teste.com",
                "senha": "SenhaValida123",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_post_b.status_code, 302)
        # Não deve redirecionar para o plano Premium do Usuário A
        self.assertNotIn("/contratar/premium", res_post_b.headers["Location"])


if __name__ == "__main__":
    unittest.main()
