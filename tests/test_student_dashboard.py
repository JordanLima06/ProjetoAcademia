import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from werkzeug.security import generate_password_hash, check_password_hash

from app import create_app
from app.config import TestingConfig
from app.models.user import User, Aluno
from app.models.academy import Plano, Modalidade, OpcaoPagamento
from app.models.enrollment import Matricula, MatriculaModalidade
from app.models.payment import Pagamento
from app.repositories.user_repository import UserRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.modality_repository import ModalityRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.student_service import StudentService
from app.services.auth_service import AuthService
from tests.csrf_helper import get_csrf_token

class StudentDashboardTestCase(unittest.TestCase):
    """Suíte de testes automatizados para a Fase 4 — Área do Aluno Completa e Painel de Gestão."""

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
        PaymentRepository._TEST_ID_SEQ = 1

        # Criação de Aluno Principal (ID=1)
        self.user_aluno = User(
            id=1,
            nome="Carlos Silva",
            email="carlos@teste.com",
            senha=generate_password_hash("SenhaForte123"),
            tipo="aluno",
            ativo=True
        )
        UserRepository._TEST_USERS[1] = self.user_aluno

        self.aluno = Aluno(
            id=1,
            usuario_id=1,
            data_nascimento=date(1996, 4, 15),
            telefone="(11) 98765-4321",
            data_cadastro=date.today(),
            objetivo="Condicionamento físico e perda de peso",
            usuario=self.user_aluno
        )
        UserRepository._TEST_ALUNOS[1] = self.aluno

        # Criação de Segundo Aluno para testes de isolamento (ID=2)
        self.user_aluno_2 = User(
            id=2,
            nome="Mariana Costa",
            email="mariana@teste.com",
            senha=generate_password_hash("OutraSenha123"),
            tipo="aluno",
            ativo=True
        )
        UserRepository._TEST_USERS[2] = self.user_aluno_2

        self.aluno_2 = Aluno(
            id=2,
            usuario_id=2,
            data_nascimento=date(1998, 10, 22),
            telefone="(21) 97777-8888",
            data_cadastro=date.today(),
            objetivo="Hipertrofia e força",
            usuario=self.user_aluno_2
        )
        UserRepository._TEST_ALUNOS[2] = self.aluno_2

        # Usuário Professor para testes de permissão/role (ID=3)
        self.user_prof = User(
            id=3,
            nome="Professor Treinador",
            email="professor@teste.com",
            senha=generate_password_hash("ProfSenha123"),
            tipo="professor",
            ativo=True
        )
        UserRepository._TEST_USERS[3] = self.user_prof

        # Intercepta self.client.post para injetar automaticamente token CSRF válido se não informado
        orig_post = self.client.post
        def post_with_csrf(url, *args, **kwargs):
            if "data" in kwargs and isinstance(kwargs["data"], dict) and "csrf_token" not in kwargs["data"]:
                token = get_csrf_token(self.client, self.app)
                kwargs["data"]["csrf_token"] = token
            elif len(args) > 0 and isinstance(args[0], dict) and "csrf_token" not in args[0]:
                token = get_csrf_token(self.client, self.app)
                args[0]["csrf_token"] = token
            return orig_post(url, *args, **kwargs)
        self.client.post = post_with_csrf

    def tearDown(self):
        self.ctx.pop()

    def _login_as(self, user: User):
        """Helper para autenticar o cliente de testes na sessão."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_nome"] = user.nome
            sess["user_tipo"] = user.tipo
            sess["auth_fingerprint"] = AuthService.get_password_fingerprint(user.senha)

    def test_01_acesso_autenticado_dashboard(self):
        """Cenário 1: Aluno autenticado acessa GET /aluno/painel com sucesso (HTTP 200)."""
        self._login_as(self.user_aluno)
        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Área do Aluno", html)
        self.assertIn("Carlos Silva", html)
        self.assertIn("Condicionamento físico e perda de peso", html)

    def test_02_acesso_autenticado_perfil(self):
        """Cenário 2: Aluno autenticado acessa GET /aluno/perfil com sucesso (HTTP 200)."""
        self._login_as(self.user_aluno)
        res = self.client.get("/aluno/perfil")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Meus Dados Cadastrais", html)
        self.assertIn("Informações do Aluno", html)
        self.assertIn("carlos@teste.com", html)
        self.assertIn("Segurança da Conta", html)

    def test_03_redirecionamento_usuario_nao_autenticado(self):
        """Cenário 3: Visitante não autenticado é redirecionado para /login ao tentar acessar área do aluno."""
        res_painel = self.client.get("/aluno/painel")
        self.assertEqual(res_painel.status_code, 302)
        self.assertIn("/login", res_painel.headers["Location"])

        res_perfil = self.client.get("/aluno/perfil")
        self.assertEqual(res_perfil.status_code, 302)
        self.assertIn("/login", res_perfil.headers["Location"])

    def test_04_bloqueio_usuario_nao_aluno(self):
        """Cenário 4: Usuário com perfil diferente de 'aluno' recebe HTTP 403 Forbidden."""
        self._login_as(self.user_prof)
        res_painel = self.client.get("/aluno/painel")
        self.assertEqual(res_painel.status_code, 403)

        res_perfil = self.client.get("/aluno/perfil")
        self.assertEqual(res_perfil.status_code, 403)

    def test_05_isolamento_dados_entre_alunos(self):
        """
        Cenário 5: Isolamento estrito entre alunos.
        O aluno logado não visualiza dados de outro aluno, e tentativas de adulterar
        aluno_id ou usuario_id no formulário POST são ignoradas.
        """
        self._login_as(self.user_aluno)

        # 1. Painel deve exibir apenas os dados de Carlos
        res_painel = self.client.get("/aluno/painel")
        html_painel = res_painel.get_data(as_text=True)
        self.assertIn("carlos@teste.com", html_painel)
        self.assertNotIn("mariana@teste.com", html_painel)

        # 2. Tentativa maliciosa de enviar aluno_id=2 no POST de perfil
        res_post = self.client.post("/aluno/perfil", data={
            "aluno_id": "2",
            "usuario_id": "2",
            "telefone": "11999990000",
            "objetivo": "Tentativa de adulteração",
            "data_nascimento": "1996-04-15"
        }, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)

        # O aluno 1 (Carlos) teve seu perfil atualizado
        self.assertEqual(self.aluno.telefone, "(11) 99999-0000")
        self.assertEqual(self.aluno.objetivo, "Tentativa de adulteração")

        # O aluno 2 (Mariana) permaneceu intacto!
        self.assertEqual(self.aluno_2.telefone, "(21) 97777-8888")
        self.assertEqual(self.aluno_2.objetivo, "Hipertrofia e força")

    def test_06_atualizacao_perfil_sucesso(self):
        """Cenário 6: Atualização de telefone, objetivo e data de nascimento com normalização."""
        self._login_as(self.user_aluno)
        res = self.client.post("/aluno/perfil", data={
            "telefone": "11912345678",
            "data_nascimento": "1994-07-20",
            "objetivo": "Competição de Muay Thai e condicionamento"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Perfil atualizado com sucesso!", html)

        # Confere dados atualizados na entidade
        self.assertEqual(self.aluno.telefone, "(11) 91234-5678")
        self.assertEqual(self.aluno.data_nascimento, date(1994, 7, 20))
        self.assertEqual(self.aluno.objetivo, "Competição de Muay Thai e condicionamento")

    def test_07_rejeicao_telefone_invalido(self):
        """Cenário 7: Rejeição de telefone com formato inválido (letras, tamanho incorreto ou DDD com 0)."""
        self._login_as(self.user_aluno)

        # Telefone com menos de 10 dígitos
        res1 = self.client.post("/aluno/perfil", data={
            "telefone": "12345",
            "data_nascimento": "1996-04-15",
            "objetivo": "Treino"
        })
        self.assertEqual(res1.status_code, 400)
        self.assertIn("Telefone inválido", res1.get_data(as_text=True))

        # Telefone com DDD iniciado em 0
        res2 = self.client.post("/aluno/perfil", data={
            "telefone": "01998765432",
            "data_nascimento": "1996-04-15",
            "objetivo": "Treino"
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("DDD inválido", res2.get_data(as_text=True))

    def test_08_rejeicao_data_nascimento_futura_e_invalida(self):
        """Cenário 8: Rejeição de data de nascimento no futuro ou com idade irreal (> 120 anos)."""
        self._login_as(self.user_aluno)

        # Data futura
        amanha = (date.today() + timedelta(days=1)).isoformat()
        res_futuro = self.client.post("/aluno/perfil", data={
            "telefone": "11987654321",
            "data_nascimento": amanha,
            "objetivo": "Treino"
        })
        self.assertEqual(res_futuro.status_code, 400)
        self.assertIn("não pode ser no futuro", res_futuro.get_data(as_text=True))

        # Data com mais de 120 anos
        res_passado = self.client.post("/aluno/perfil", data={
            "telefone": "11987654321",
            "data_nascimento": "1890-01-01",
            "objetivo": "Treino"
        })
        self.assertEqual(res_passado.status_code, 400)
        self.assertIn("Data de nascimento inválida", res_passado.get_data(as_text=True))

    def test_09_alteracao_senha_sucesso(self):
        """Cenário 9: Alteração de senha bem-sucedida gera novo hash e permite autenticação."""
        self._login_as(self.user_aluno)
        res = self.client.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaForte123",
            "nova_senha": "NovaSenhaSegura456!",
            "confirmar_senha": "NovaSenhaSegura456!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Senha alterada com sucesso!", res.get_data(as_text=True))

        # Valida que o hash armazenado foi atualizado e confere com a nova senha
        self.assertTrue(check_password_hash(self.user_aluno.senha, "NovaSenhaSegura456!"))
        self.assertFalse(check_password_hash(self.user_aluno.senha, "SenhaForte123"))

    def test_10_rejeicao_alteracao_senha_atual_incorreta(self):
        """Cenário 10: Rejeição de alteração de senha quando a senha atual fornecida está errada."""
        self._login_as(self.user_aluno)
        res = self.client.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaErradaTotal",
            "nova_senha": "NovaSenhaSegura456!",
            "confirmar_senha": "NovaSenhaSegura456!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("A senha atual informada está incorreta", res.get_data(as_text=True))
        # Hash original preservado
        self.assertTrue(check_password_hash(self.user_aluno.senha, "SenhaForte123"))

    def test_11_rejeicao_alteracao_senha_confirmacao_divergente(self):
        """Cenário 11: Rejeição quando a confirmação da nova senha não confere."""
        self._login_as(self.user_aluno)
        res = self.client.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaForte123",
            "nova_senha": "NovaSenhaSegura456!",
            "confirmar_senha": "DivergenteDiferente!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("A confirmação da nova senha não confere", res.get_data(as_text=True))

    def test_12_rejeicao_alteracao_senha_curta(self):
        """Cenário 12: Rejeição quando a nova senha possui menos de 6 caracteres."""
        self._login_as(self.user_aluno)
        res = self.client.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaForte123",
            "nova_senha": "12345",
            "confirmar_senha": "12345"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("A nova senha deve possuir pelo menos 6 caracteres", res.get_data(as_text=True))

    def test_13_rejeicao_alteracao_senha_identica_a_atual(self):
        """Cenário 13: Rejeição obrigatória quando a nova senha for idêntica à senha atual."""
        self._login_as(self.user_aluno)
        res = self.client.post("/aluno/alterar-senha", data={
            "senha_atual": "SenhaForte123",
            "nova_senha": "SenhaForte123",
            "confirmar_senha": "SenhaForte123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("A nova senha deve ser diferente da senha atual", res.get_data(as_text=True))

    def test_14_dashboard_sem_matricula(self):
        """Cenário 14: Dashboard de aluno sem matrícula exibe aviso claro e botão para conhecer planos."""
        self._login_as(self.user_aluno)
        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Você ainda não possui uma matrícula ativa", html)
        self.assertIn("Conhecer Nossos Planos", html)
        self.assertNotIn("Resumo de Pagamentos (Demonstrativo)", html)

    def test_15_dashboard_com_matricula_pendente_nao_libera_modalidades(self):
        """
        Cenário 15: Matrícula com status 'pendente' exibe badge amarelo, aviso de aguardando pagamento,
        resumo financeiro com parcelas pendentes e NÃO libera modalidades esportivas.
        """
        self._login_as(self.user_aluno)

        plano = Plano(id=2, nome="Plano Combate Total", slug="combate-total", preco=Decimal("199.90"))
        mod_boxe = Modalidade(id=1, slug="boxe", nome="Boxe", descricao="Aulas de Boxe")
        mod_muay = Modalidade(id=2, slug="muay-thai", nome="Muay Thai", descricao="Aulas de Muay Thai")
        plano.modalidades = [mod_boxe, mod_muay]

        matricula_pendente = Matricula(
            id=10,
            aluno_id=1,
            plano_id=2,
            opcao_pagamento_id=1,
            data_inicio=date.today(),
            data_fim=date.today() + timedelta(days=30),
            status="pendente",
            tipo_cobranca="mensal",
            valor_cobranca=Decimal("199.90"),
            valor_total_contratado=Decimal("199.90"),
            quantidade_parcelas=1,
            plano=plano
        )
        EnrollmentRepository._TEST_MATRICULAS[10] = matricula_pendente

        # Cria pagamento demonstrativo pendente
        pag_pendente = Pagamento(
            id=101,
            matricula_id=10,
            numero_parcela=1,
            valor=Decimal("199.90"),
            vencimento=date.today() + timedelta(days=5),
            status="pendente",
            forma_pagamento="pix"
        )
        PaymentRepository._TEST_PAGAMENTOS[101] = pag_pendente

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Deve exibir status pendente
        self.assertIn("status-pendente", html)
        self.assertIn("Contratação Registrada (Aguardando Pagamento)", html)
        self.assertIn("As modalidades esportivas serão liberadas após a confirmação", html)

        # Regra obrigatória: Matrícula pendente NÃO libera modalidades
        self.assertNotIn("Acesso Liberado para Treinos", html)
        self.assertNotIn("Modalidades Liberadas para Você:", html)

        # Resumo financeiro demonstrativo exibe parcela pendente e próximo vencimento
        self.assertIn("Resumo de Pagamentos (Demonstrativo)", html)
        self.assertIn("Total Pendente", html)
        self.assertIn("199,90", html)

    def test_16_dashboard_com_matricula_ativa_libera_modalidades(self):
        """
        Cenário 16: Matrícula com status 'ativa' exibe badge verde, mensagem de acesso liberado
        e lista as modalidades esportivas previstas no plano.
        """
        self._login_as(self.user_aluno)

        plano = Plano(id=2, nome="Plano Combate Total", slug="combate-total", preco=Decimal("199.90"))
        mod_boxe = Modalidade(id=1, slug="boxe", nome="Boxe", descricao="Aulas de Boxe")
        mod_muay = Modalidade(id=2, slug="muay-thai", nome="Muay Thai", descricao="Aulas de Muay Thai")
        plano.modalidades = [mod_boxe, mod_muay]

        matricula_ativa = Matricula(
            id=20,
            aluno_id=1,
            plano_id=2,
            opcao_pagamento_id=1,
            data_inicio=date.today(),
            data_fim=date.today() + timedelta(days=365),
            status="ativa",
            tipo_cobranca="anual",
            valor_cobranca=Decimal("116.66"),
            valor_total_contratado=Decimal("1399.90"),
            quantidade_parcelas=12,
            plano=plano
        )
        matricula_ativa.modalidades = [mod_boxe, mod_muay]
        EnrollmentRepository._TEST_MATRICULAS[20] = matricula_ativa
        EnrollmentRepository._TEST_MATRICULA_MODALIDADES[20] = [
            MatriculaModalidade(matricula_id=20, plano_id=2, modalidade_id=1),
            MatriculaModalidade(matricula_id=20, plano_id=2, modalidade_id=2)
        ]

        # Pagamentos: 1 pago (histórico) e 11 pendentes
        pag_pago = Pagamento(
            id=201,
            matricula_id=20,
            numero_parcela=1,
            valor=Decimal("116.66"),
            vencimento=date.today(),
            pagamento_data=datetime.now(),
            status="pago",
            forma_pagamento="pix"
        )
        PaymentRepository._TEST_PAGAMENTOS[201] = pag_pago

        pag_pendente = Pagamento(
            id=202,
            matricula_id=20,
            numero_parcela=2,
            valor=Decimal("116.66"),
            vencimento=date.today() + timedelta(days=30),
            status="pendente",
            forma_pagamento="cartao_credito"
        )
        PaymentRepository._TEST_PAGAMENTOS[202] = pag_pendente

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Deve exibir status ativa e acesso liberado
        self.assertIn("status-ativa", html)
        self.assertIn("Acesso Liberado para Treinos", html)
        self.assertIn("Modalidades Liberadas para Você:", html)
        self.assertIn("Boxe", html)
        self.assertIn("Muay Thai", html)

        # Não deve exibir mensagem de pendência de liberação
        self.assertNotIn("As modalidades esportivas serão liberadas após a confirmação", html)

        # Resumo financeiro demonstrativo
        self.assertIn("Resumo de Pagamentos (Demonstrativo)", html)
        self.assertIn("12x de R$ 116,66", html)


if __name__ == "__main__":
    unittest.main()
