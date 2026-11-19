import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from app import create_app
from app.config import TestingConfig
from app.models.enrollment import Matricula, MatriculaModalidade
from app.models.payment import Pagamento
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.payment_repository import PaymentRepository

class EnrollmentModelsRepositoriesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_matricula_model_campos_reais_e_status(self):
        """Valida que Matricula mapeia todas as colunas reais e aceita status válidos."""
        hoje = date.today()
        fim = hoje + timedelta(days=365)
        mat = Matricula(
            id=1,
            aluno_id=10,
            plano_id=4,
            data_inicio=hoje,
            data_fim=fim,
            status="ativa",
            opcao_pagamento_id=7,
            tipo_cobranca="parcelado",
            valor_cobranca=Decimal("116.66"),
            valor_total_contratado=Decimal("1399.90"),
            quantidade_parcelas=12
        )

        self.assertEqual(mat.aluno_id, 10)
        self.assertEqual(mat.plano_id, 4)
        self.assertEqual(mat.status, "ativa")
        self.assertEqual(mat.opcao_pagamento_id, 7)
        self.assertEqual(mat.tipo_cobranca, "parcelado")
        self.assertEqual(mat.valor_cobranca, Decimal("116.66"))
        self.assertEqual(mat.valor_total_contratado, Decimal("1399.90"))
        self.assertEqual(mat.quantidade_parcelas, 12)
        self.assertTrue(mat.is_ativa())

        # Status 'expirada' não é permitido
        self.assertNotIn("expirada", Matricula.STATUS_PERMITIDOS)
        self.assertIn("pendente", Matricula.STATUS_PERMITIDOS)
        self.assertIn("ativa", Matricula.STATUS_PERMITIDOS)
        self.assertIn("suspensa", Matricula.STATUS_PERMITIDOS)
        self.assertIn("encerrada", Matricula.STATUS_PERMITIDOS)
        self.assertIn("cancelada", Matricula.STATUS_PERMITIDOS)

    def test_matricula_modalidade_chave_composta(self):
        """Valida que MatriculaModalidade inclui obrigatoriamente plano_id."""
        mm = MatriculaModalidade(matricula_id=1, plano_id=4, modalidade_id=3)
        self.assertEqual(mm.matricula_id, 1)
        self.assertEqual(mm.plano_id, 4)
        self.assertEqual(mm.modalidade_id, 3)
        d = mm.to_dict()
        self.assertEqual(d["matricula_id"], 1)
        self.assertEqual(d["plano_id"], 4)
        self.assertEqual(d["modalidade_id"], 3)

    def test_pagamento_model_colunas_reais_e_formas_permitidas(self):
        """Valida que Pagamento utiliza exclusivamente as colunas reais e formas de pagamento permitidas."""
        hoje = date.today()
        pag = Pagamento(
            id=1,
            matricula_id=1,
            numero_parcela=1,
            valor=Decimal("116.66"),
            vencimento=hoje,
            forma_pagamento="cartao_credito",
            status="pendente",
            pagamento_data=None
        )

        self.assertEqual(pag.matricula_id, 1)
        self.assertEqual(pag.numero_parcela, 1)
        self.assertEqual(pag.valor, Decimal("116.66"))
        self.assertEqual(pag.vencimento, hoje)
        self.assertIsNone(pag.pagamento_data)
        self.assertEqual(pag.status, "pendente")
        self.assertEqual(pag.forma_pagamento, "cartao_credito")

        # Verifica remoção do status 'simulado'
        self.assertNotIn("simulado", Pagamento.STATUS_PERMITIDOS)
        self.assertIn("pendente", Pagamento.STATUS_PERMITIDOS)

        # Formas de pagamento permitidas
        formas_esperadas = {"pix", "dinheiro", "cartao_credito", "cartao_debito", "boleto", "transferencia", "outro"}
        self.assertEqual(set(Pagamento.FORMAS_PAGAMENTO_PERMITIDAS), formas_esperadas)

    def test_parcelamento_anual_soma_exata_1399_90(self):
        """Valida que o plano anual de R$ 1.399,90 gera 11 parcelas de R$ 116,66 e 1 de R$ 116,64."""
        parcelas = Pagamento.gerar_parcelas(
            matricula_id=99,
            valor_total=Decimal("1399.90"),
            quantidade_parcelas=12,
            forma_pagamento="cartao_credito",
            data_base_vencimento=date(2026, 1, 15)
        )

        self.assertEqual(len(parcelas), 12)
        soma_total = sum(p.valor for p in parcelas)
        self.assertEqual(soma_total, Decimal("1399.90"))

        # As primeiras 11 devem ser R$ 116,66
        for i in range(11):
            self.assertEqual(parcelas[i].numero_parcela, i + 1)
            self.assertEqual(parcelas[i].valor, Decimal("116.66"))
            self.assertEqual(parcelas[i].status, "pendente")
            self.assertIsNone(parcelas[i].pagamento_data)

        # A 12ª deve ser R$ 116,64
        self.assertEqual(parcelas[11].numero_parcela, 12)
        self.assertEqual(parcelas[11].valor, Decimal("116.64"))
        self.assertEqual(parcelas[11].status, "pendente")
        self.assertIsNone(parcelas[11].pagamento_data)

    def test_enrollment_repository_create_transactional_com_plano_id_e_colunas(self):
        """Valida que EnrollmentRepository grava matricula com todas as colunas reais e matricula_modalidades com plano_id."""
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = {"id": 42, "criado_em": datetime.now()}

        hoje = date.today()
        matricula = Matricula(
            aluno_id=5,
            plano_id=2,
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=30),
            status="ativa",
            opcao_pagamento_id=3,
            tipo_cobranca="mensal",
            valor_cobranca=Decimal("89.90"),
            valor_total_contratado=Decimal("89.90"),
            quantidade_parcelas=1
        )

        salvo = EnrollmentRepository.create_transactional(cursor_mock, matricula, modality_ids=[1, 2])
        self.assertEqual(salvo.id, 42)

        # Verifica o INSERT em matriculas
        insert_mat_call = cursor_mock.execute.call_args_list[0]
        sql_mat = insert_mat_call[0][0]
        params_mat = insert_mat_call[0][1]

        self.assertIn("opcao_pagamento_id", sql_mat)
        self.assertIn("tipo_cobranca", sql_mat)
        self.assertIn("valor_cobranca", sql_mat)
        self.assertIn("valor_total_contratado", sql_mat)
        self.assertIn("quantidade_parcelas", sql_mat)
        self.assertEqual(params_mat[0], 5)  # aluno_id
        self.assertEqual(params_mat[1], 2)  # plano_id
        self.assertEqual(params_mat[4], "ativa")
        self.assertEqual(params_mat[5], 3)  # opcao_pagamento_id
        self.assertEqual(params_mat[6], "mensal")
        self.assertEqual(params_mat[7], Decimal("89.90"))
        self.assertEqual(params_mat[8], Decimal("89.90"))
        self.assertEqual(params_mat[9], 1)

        # Verifica o INSERT em matricula_modalidades contendo (matricula_id, plano_id, modalidade_id)
        insert_mod_1 = cursor_mock.execute.call_args_list[1]
        sql_mod_1 = insert_mod_1[0][0]
        params_mod_1 = insert_mod_1[0][1]

        self.assertIn("INSERT INTO matricula_modalidades (matricula_id, plano_id, modalidade_id)", sql_mod_1)
        self.assertEqual(params_mod_1, (42, 2, 1))

        insert_mod_2 = cursor_mock.execute.call_args_list[2]
        params_mod_2 = insert_mod_2[0][1]
        self.assertEqual(params_mod_2, (42, 2, 2))

    def test_payment_repository_create_transactional_seguranca_demonstrativa(self):
        """Valida que PaymentRepository ajusta status inadequados para pendente e mantém pagamento_data como None."""
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = {"id": 101, "criado_em": datetime.now()}

        # Tentativa com status 'pago' ou 'simulado'
        pagamento = Pagamento(
            matricula_id=42,
            numero_parcela=1,
            valor=Decimal("116.66"),
            vencimento=date.today(),
            forma_pagamento="pix",
            status="pago",
            pagamento_data=datetime.now()
        )

        salvo = PaymentRepository.create_transactional(cursor_mock, pagamento)
        # O repositório deve forçar para 'pendente' e pagamento_data para None
        self.assertEqual(salvo.status, "pendente")
        self.assertIsNone(salvo.pagamento_data)

        # Verifica a chamada SQL
        call_args = cursor_mock.execute.call_args[0]
        sql = call_args[0]
        params = call_args[1]

        self.assertIn("INSERT INTO pagamentos", sql)
        self.assertEqual(params[0], 42)  # matricula_id
        self.assertEqual(params[1], 1)   # numero_parcela
        self.assertEqual(params[2], Decimal("116.66"))
        self.assertIsNone(params[4])     # pagamento_data
        self.assertEqual(params[5], "pendente")
        self.assertEqual(params[6], "pix")

if __name__ == "__main__":
    unittest.main()
