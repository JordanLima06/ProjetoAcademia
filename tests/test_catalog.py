import unittest
from app import create_app
from app.config import TestingConfig, Config
from app.models.academy import Plano, Modalidade, OpcaoPagamento
from app.repositories.plan_repository import PlanRepository
from app.repositories.modality_repository import ModalityRepository
from app.services.academy_service import AcademyService
from unittest.mock import MagicMock, patch

class CatalogTestCase(unittest.TestCase):
    """Testes automatizados da Fase 1 — Fundação de Dados e Catálogo Relacional."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_opcao_pagamento_parcelamento_anual_exato(self):
        """
        Valida que o plano Anual em 12 parcelas calcula:
        - 11 parcelas de R$ 116,66
        - 1 última parcela de R$ 116,64
        - Soma total estritamente igual a R$ 1.399,90
        """
        opcao_12x = OpcaoPagamento(
            id=5,
            plano_id=4,
            codigo="anual_12x",
            nome="12 parcelas mensais sem juros",
            tipo_cobranca="mensal",
            valor_cobranca=116.66,
            valor_total_contratado=1399.90,
            quantidade_parcelas=12,
            periodicidade="mensal",
            ativo=True
        )

        parcelas = opcao_12x.calcular_parcelas_detalhadas()
        self.assertEqual(len(parcelas), 12)
        # As primeiras 11 parcelas devem ser de 116.66
        for p in parcelas[:11]:
            self.assertEqual(p, 116.66)
        # A última parcela ajusta a diferença de arredondamento
        self.assertEqual(parcelas[11], 116.64)
        # A soma total deve ser exatamente R$ 1.399,90
        soma_total = round(sum(parcelas), 2)
        self.assertEqual(soma_total, 1399.90)

    def test_opcao_pagamento_avista(self):
        """Valida que pagamento à vista retorna parcela única com valor contratado."""
        opcao_avista = OpcaoPagamento(
            id=4,
            plano_id=4,
            codigo="anual_avista",
            nome="Pagamento à vista",
            tipo_cobranca="unico",
            valor_cobranca=1399.90,
            valor_total_contratado=1399.90,
            quantidade_parcelas=1,
            periodicidade="unica",
            ativo=True
        )
        parcelas = opcao_avista.calcular_parcelas_detalhadas()
        self.assertEqual(len(parcelas), 1)
        self.assertEqual(parcelas[0], 1399.90)

    def test_plano_compatibilidade_template(self):
        """Garante que a entidade Plano possui todos os atributos esperados pelo Jinja2."""
        plano = Plano(
            id=1,
            slug="essencial",
            nome="Essencial",
            preco=79.90,
            beneficios=["Acesso à musculação", "Treino personalizado"]
        )
        self.assertEqual(plano.preco, 79.90)
        self.assertEqual(plano.nome, "Essencial")
        self.assertEqual(plano.slug, "essencial")
        self.assertIsInstance(plano.beneficios, list)
        self.assertEqual(len(plano.beneficios), 2)
        # Acesso por chave tipo dicionário
        self.assertEqual(plano["preco"], 79.90)
        self.assertEqual(plano["nome"], "Essencial")

    def test_plan_repository_get_all_e_por_slug(self):
        """Verifica busca de planos via PlanRepository."""
        planos = PlanRepository.get_all()
        self.assertGreaterEqual(len(planos), 4)

        plano_anual = PlanRepository.get_by_slug("anual")
        self.assertIsNotNone(plano_anual)
        self.assertEqual(plano_anual.nome, "Anual")
        self.assertEqual(plano_anual.preco, 1399.90)
        self.assertGreater(len(plano_anual.beneficios), 0)
        self.assertGreater(len(plano_anual.opcoes_pagamento), 0)

    def test_plan_repository_get_by_id(self):
        """Verifica busca por ID numérico de plano."""
        plano = PlanRepository.get_by_id(1)
        self.assertIsNotNone(plano)
        self.assertEqual(plano.slug, "essencial")
        self.assertEqual(plano.preco, 79.90)

    def test_modality_repository_get_by_plan_id(self):
        """Verifica consulta relacional de modalidades por plano."""
        # Plano 1 (Essencial) tem apenas Musculação
        modalidades_p1 = ModalityRepository.get_by_plan_id(1)
        self.assertGreaterEqual(len(modalidades_p1), 1)
        slugs_p1 = [m.slug for m in modalidades_p1]
        self.assertIn("musculacao", slugs_p1)

        # Plano 2 (Performance) tem Musculação, Boxe, Jiu-Jitsu, Funcional
        modalidades_p2 = ModalityRepository.get_by_plan_id(2)
        self.assertGreaterEqual(len(modalidades_p2), 4)

    def test_academy_service_metodos_adicionais(self):
        """Valida que o serviço AcademyService expõe as novas operações da Fase 1."""
        planos = AcademyService.list_plans()
        self.assertGreater(len(planos), 0)

        plano = AcademyService.get_plan_by_id(1)
        self.assertIsNotNone(plano)

        modalidades = AcademyService.list_modalities_by_plan(1)
        self.assertGreater(len(modalidades), 0)

        opcoes = AcademyService.get_payment_options(4)
        self.assertGreater(len(opcoes), 0)

    def test_falha_de_conexao_sem_dados_falsos_fora_de_teste(self):
        """
        Garante que, fora do ambiente de teste, falha de conexão com PostgreSQL
        NÃO retorna dados estáticos silenciosamente, registrando erro e retornando vazio.
        """
        with patch("app.repositories.plan_repository.get_db_connection", return_value=None), \
             patch("app.repositories.plan_repository.PlanRepository._is_testing", return_value=False):
            planos = PlanRepository.get_all()
            self.assertEqual(planos, [])
            plano = PlanRepository.get_by_id(1)
            self.assertIsNone(plano)
            plano_slug = PlanRepository.get_by_slug("essencial")
            self.assertIsNone(plano_slug)

        with patch("app.repositories.modality_repository.get_db_connection", return_value=None), \
             patch("app.repositories.modality_repository.ModalityRepository._is_testing", return_value=False):
            modalidades = ModalityRepository.get_all()
            self.assertEqual(modalidades, [])
            modalidade = ModalityRepository.get_by_id(1)
            self.assertIsNone(modalidade)
            modalidades_plano = ModalityRepository.get_by_plan_id(1)
            self.assertEqual(modalidades_plano, [])

    def test_sql_plano_modalidades_nao_utiliza_coluna_ativo(self):
        """
        Garante que a query SQL em get_by_plan_id NÃO inclui 'pm.ativo'
        ou 'plano_modalidades.ativo' no comando SQL executado.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"id": 1, "slug": "musculacao", "nome": "Musculação", "descricao": "Treino", "ativo": True}
        ]

        with patch("app.repositories.modality_repository.get_db_connection", return_value=mock_conn):
            ModalityRepository.get_by_plan_id(1)
            # Verifica a query executada
            args, _ = mock_cursor.execute.call_args
            query_sql = args[0]
            self.assertNotIn("pm.ativo", query_sql)
            self.assertNotIn("plano_modalidades.ativo", query_sql)

if __name__ == "__main__":
    unittest.main()
