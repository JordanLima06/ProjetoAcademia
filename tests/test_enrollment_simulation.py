import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from werkzeug.security import generate_password_hash

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
from app.services.enrollment_service import EnrollmentService
from app.services.payment_service import PaymentService

class EnrollmentSimulationTestCase(unittest.TestCase):
    """Suíte de testes para as Etapas 3 e 4 da Fase 3 — Matrículas e Pagamentos Simulados."""

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

        # Criação de usuário e aluno para testes
        self.user_aluno = User(
            id=1,
            nome="Aluno Teste",
            email="aluno@teste.com",
            senha=generate_password_hash("Senha123"),
            tipo="aluno",
            ativo=True
        )
        UserRepository._TEST_USERS[1] = self.user_aluno

        self.aluno = Aluno(
            id=1,
            usuario_id=1,
            data_nascimento=date(1995, 5, 20),
            telefone="11999998888",
            data_cadastro=date.today(),
            usuario=self.user_aluno
        )
        UserRepository._TEST_ALUNOS[1] = self.aluno

        # Usuário professor para testar controle de permissão
        self.user_professor = User(
            id=2,
            nome="Professor Teste",
            email="prof@teste.com",
            senha=generate_password_hash("Senha123"),
            tipo="professor",
            ativo=True
        )
        UserRepository._TEST_USERS[2] = self.user_professor

    def tearDown(self):
        self.ctx.pop()

    def test_contratacao_plano_anual_parcelamento_exato(self):
        """Valida contratação do plano anual com 12 parcelas exatas totalizando R$ 1.399,90."""
        # Opção anual 12x no cartão (id=5)
        sucesso, matricula, msg = EnrollmentService.contratar_plano_demonstrativo(
            aluno_id=1,
            plano_slug="anual",
            opcao_pagamento_id=5,  # 12x de R$ 116,66
            forma_pagamento="cartao_credito"
        )

        self.assertTrue(sucesso, f"Falha na contratação: {msg}")
        self.assertIsNotNone(matricula)
        self.assertEqual(matricula.status, "ativa")
        self.assertEqual(matricula.quantidade_parcelas, 12)
        self.assertEqual(matricula.valor_total_contratado, Decimal("1399.90"))

        # Recupera as parcelas geradas
        parcelas = PaymentService.listar_pagamentos_por_matricula(matricula.id)
        self.assertEqual(len(parcelas), 12)

        soma = sum(p.valor for p in parcelas)
        self.assertEqual(soma, Decimal("1399.90"))

        # 11 de R$ 116,66 e 12ª de R$ 116,64
        for i in range(11):
            self.assertEqual(parcelas[i].valor, Decimal("116.66"))
            self.assertEqual(parcelas[i].status, "pendente")
            self.assertIsNone(parcelas[i].pagamento_data)

        self.assertEqual(parcelas[11].valor, Decimal("116.64"))
        self.assertEqual(parcelas[11].status, "pendente")
        self.assertIsNone(parcelas[11].pagamento_data)

    def test_contratacao_planos_essencial_perfomance_premium_e_anual_avista(self):
        """Valida que todos os 4 planos podem ser contratados demonstrativamente."""
        planos_para_testar = [
            ("essencial", 1, "pix"),
            ("perfomance", 2, "cartao_credito"),
            ("premium", 3, "boleto"),
            ("anual", 4, "pix")  # Anual à vista
        ]

        for slug, op_id, forma in planos_para_testar:
            # Limpa matrícula anterior para permitir novo teste
            EnrollmentRepository._TEST_MATRICULAS.clear()

            sucesso, mat, msg = EnrollmentService.contratar_plano_demonstrativo(
                aluno_id=1,
                plano_slug=slug,
                opcao_pagamento_id=op_id,
                forma_pagamento=forma
            )
            self.assertTrue(sucesso, f"Falha ao contratar plano {slug}: {msg}")
            self.assertEqual(mat.status, "ativa")
            self.assertEqual(mat.plano_id, PlanRepository.get_by_slug(slug).id)

            parcelas = PaymentService.listar_pagamentos_por_matricula(mat.id)
            self.assertGreaterEqual(len(parcelas), 1)
            for p in parcelas:
                self.assertEqual(p.status, "pendente")
                self.assertIsNone(p.pagamento_data)

    def test_bloqueio_duplicidade_matricula_ativa(self):
        """Um aluno com matrícula ativa vigente não pode contratar outra matrícula simultânea."""
        # 1ª contratação: Sucesso
        sucesso1, mat1, _ = EnrollmentService.contratar_plano_demonstrativo(
            aluno_id=1,
            plano_slug="essencial",
            opcao_pagamento_id=1,
            forma_pagamento="pix"
        )
        self.assertTrue(sucesso1)

        # 2ª contratação: Bloqueada
        sucesso2, mat2, msg2 = EnrollmentService.contratar_plano_demonstrativo(
            aluno_id=1,
            plano_slug="anual",
            opcao_pagamento_id=5,
            forma_pagamento="cartao_credito"
        )
        self.assertFalse(sucesso2)
        self.assertIsNone(mat2)
        self.assertIn("já possui uma matrícula ativa", msg2)

    def test_validacao_forma_pagamento_invalida(self):
        """Rejeita formas de pagamento que não pertençam à constraint do PostgreSQL."""
        sucesso, mat, msg = EnrollmentService.contratar_plano_demonstrativo(
            aluno_id=1,
            plano_slug="essencial",
            opcao_pagamento_id=1,
            forma_pagamento="criptomoeda_invalida"
        )
        self.assertFalse(sucesso)
        self.assertIsNone(mat)
        self.assertIn("não permitida", msg)

    def test_cancelamento_matricula(self):
        """Valida fluxo de cancelamento de matrícula ativa."""
        sucesso_contrato, mat, _ = EnrollmentService.contratar_plano_demonstrativo(
            aluno_id=1,
            plano_slug="essencial",
            opcao_pagamento_id=1,
            forma_pagamento="pix"
        )
        self.assertTrue(sucesso_contrato)

        sucesso_canc, msg_canc = EnrollmentService.cancelar_matricula(aluno_id=1, matricula_id=mat.id)
        self.assertTrue(sucesso_canc)

        # Verifica se o status mudou para 'cancelada'
        mat_atualizada = EnrollmentRepository.find_by_id(mat.id)
        self.assertEqual(mat_atualizada.status, "cancelada")
        self.assertFalse(mat_atualizada.is_ativa())

        # Agora o aluno deve conseguir contratar outro plano normalmente
        sucesso_novo, mat_novo, _ = EnrollmentService.contratar_plano_demonstrativo(
            aluno_id=1,
            plano_slug="perfomance",
            opcao_pagamento_id=2,
            forma_pagamento="cartao_credito"
        )
        self.assertTrue(sucesso_novo)

    def test_rotas_bloqueio_usuario_nao_autenticado(self):
        """Rotas de contratação e matrícula exigem autenticação."""
        res_contratar = self.client.get("/contratar/essencial")
        self.assertEqual(res_contratar.status_code, 302)
        self.assertIn("/login", res_contratar.headers["Location"])

        res_matricula = self.client.get("/minha-matricula")
        self.assertEqual(res_matricula.status_code, 302)
        self.assertIn("/login", res_matricula.headers["Location"])

    def test_rotas_bloqueio_usuario_nao_aluno(self):
        """Usuário autenticado que não seja aluno (ex.: professor) recebe 403 Forbidden."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2  # Professor
            sess["user_nome"] = "Professor Teste"
            sess["user_tipo"] = "professor"

        res = self.client.get("/contratar/essencial")
        self.assertEqual(res.status_code, 403)

        res_minha = self.client.get("/minha-matricula")
        self.assertEqual(res_minha.status_code, 403)

    def test_rotas_aluno_autenticado_renderiza_contratar_e_minha_matricula(self):
        """Aluno autenticado acessa tela de contratação e área de matrícula com sucesso."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1  # Aluno
            sess["user_nome"] = "Aluno Teste"
            sess["user_tipo"] = "aluno"

        # GET /contratar/essencial
        res_contratar = self.client.get("/contratar/essencial")
        self.assertEqual(res_contratar.status_code, 200)
        self.assertIn("Contratação de Matrícula", res_contratar.get_data(as_text=True))
        self.assertIn("Simulação Demonstrativa", res_contratar.get_data(as_text=True))

        # POST /contratar/essencial
        res_post = self.client.post("/contratar/essencial", data={
            "opcao_pagamento_id": "1",
            "forma_pagamento": "pix"
        }, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn("Minha Matrícula", res_post.get_data(as_text=True))
        self.assertIn("Matrícula Ativa", res_post.get_data(as_text=True))

        # GET /minha-matricula
        res_minha = self.client.get("/minha-matricula")
        self.assertEqual(res_minha.status_code, 200)
        self.assertIn("Parcelas e Registros de Pagamento", res_minha.get_data(as_text=True))
        self.assertIn("pendente", res_minha.get_data(as_text=True))

    def test_transacao_rollback_em_falha(self):
        """Verifica que se ocorrer erro na gravação de pagamentos, a transação reverte sem deixar matrícula."""
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = {"id": 88, "criado_em": datetime.now()}

        conn_mock = MagicMock()
        conn_mock.cursor.return_value.__enter__.return_value = cursor_mock

        plano = PlanRepository.get_by_slug("essencial")
        opcao = PlanRepository.get_payment_option_by_id(1)

        with patch("app.services.enrollment_service.PlanRepository.get_by_slug", return_value=plano):
            with patch("app.services.enrollment_service.PlanRepository.get_payment_option_by_id", return_value=opcao):
                with patch("app.services.enrollment_service.get_db_connection", return_value=conn_mock):
                    with patch("app.services.enrollment_service.PaymentService.salvar_parcelas_transacional", side_effect=Exception("Falha forçada no pagamento")):
                        sucesso, mat, msg = EnrollmentService.contratar_plano_demonstrativo(
                            aluno_id=1,
                            plano_slug="essencial",
                            opcao_pagamento_id=1,
                            forma_pagamento="pix"
                        )
                        self.assertFalse(sucesso)
                        self.assertIsNone(mat)
                        self.assertIn("Falha forçada no pagamento", msg)

if __name__ == "__main__":
    unittest.main()
