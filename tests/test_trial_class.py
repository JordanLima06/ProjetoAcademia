import unittest
from datetime import date
from app import create_app
from app.config import TestingConfig
from app.models.trial_class import SolicitacaoAulaExperimental
from app.services.trial_service import TrialService
from app.repositories.modality_repository import ModalityRepository

class TrialClassTestCase(unittest.TestCase):
    """Testes automatizados para as regras de negócio e validações de Aula Experimental."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_model_instantiation(self):
        solicitacao = SolicitacaoAulaExperimental(
            nome="Carlos Silva",
            telefone="(11) 98765-4321",
            modalidade_id=2,
            email="carlos@exemplo.com",
            dia_preferido=date(2026, 12, 1),
            periodo_preferido="noite",
            objetivo="Melhorar condicionamento"
        )
        self.assertEqual(solicitacao.nome, "Carlos Silva")
        self.assertEqual(solicitacao.status, "nova")
        self.assertEqual(solicitacao.modalidade_id, 2)
        dados = solicitacao.to_dict()
        self.assertEqual(dados["status"], "nova")
        self.assertEqual(dados["dia_preferido"], "2026-12-01")

    def test_service_solicitar_aula_sucesso_completo(self):
        dados = {
            "nome": "Mariana Ferreira",
            "telefone": "(82) 99123-4567",
            "email": "mariana@exemplo.com",
            "modalidade_id": 1,
            "dia_preferido": "2026-11-25",
            "periodo_preferido": "manha",
            "objetivo": "Perda de peso e ganho de resistência"
        }
        sucesso, msg, item = TrialService.solicitar_aula(dados)
        self.assertTrue(sucesso)
        self.assertIn("sucesso", msg.lower())
        self.assertIsNotNone(item)
        self.assertEqual(item.status, "nova")
        self.assertEqual(item.modalidade_id, 1)

    def test_service_solicitar_aula_sucesso_opcionais_vazios(self):
        # E-mail, dia, período e objetivo são opcionais
        dados = {
            "nome": "João Santos",
            "telefone": "82988887777",
            "modalidade_id": 2,
            "email": "",
            "dia_preferido": "",
            "periodo_preferido": "",
            "objetivo": ""
        }
        sucesso, msg, item = TrialService.solicitar_aula(dados)
        self.assertTrue(sucesso)
        self.assertEqual(item.status, "nova")
        self.assertIsNone(item.email)
        self.assertIsNone(item.dia_preferido)
        self.assertIsNone(item.periodo_preferido)
        self.assertIsNone(item.objetivo)

    def test_service_validacao_nome_invalido(self):
        # Nome vazio
        sucesso, msg, item = TrialService.solicitar_aula({"nome": "", "telefone": "11988887777", "modalidade_id": 1})
        self.assertFalse(sucesso)
        self.assertIn("nome", msg.lower())

        # Nome > 100 caracteres
        sucesso, msg, item = TrialService.solicitar_aula({"nome": "A" * 105, "telefone": "11988887777", "modalidade_id": 1})
        self.assertFalse(sucesso)
        self.assertIn("100", msg)

    def test_service_validacao_telefone_whatsapp(self):
        # Telefone vazio
        sucesso, msg, item = TrialService.solicitar_aula({"nome": "Lucas", "telefone": "", "modalidade_id": 1})
        self.assertFalse(sucesso)
        self.assertIn("whatsapp", msg.lower())

        # Telefone curto (< 10 dígitos)
        sucesso, msg, item = TrialService.solicitar_aula({"nome": "Lucas", "telefone": "12345", "modalidade_id": 1})
        self.assertFalse(sucesso)

    def test_service_validacao_modalidade_inexistente(self):
        sucesso, msg, item = TrialService.solicitar_aula({
            "nome": "Lucas",
            "telefone": "82999998888",
            "modalidade_id": 9999
        })
        self.assertFalse(sucesso)
        self.assertIn("modalidade", msg.lower())

    def test_service_validacao_email_invalido(self):
        sucesso, msg, item = TrialService.solicitar_aula({
            "nome": "Lucas",
            "telefone": "82999998888",
            "modalidade_id": 1,
            "email": "email_invalido_sem_arroba"
        })
        self.assertFalse(sucesso)
        self.assertIn("e-mail", msg.lower())

    def test_service_validacao_periodo_invalido_check(self):
        # Apenas 'manha', 'tarde', 'noite' são aceitos pelo CHECK
        sucesso, msg, item = TrialService.solicitar_aula({
            "nome": "Lucas",
            "telefone": "82999998888",
            "modalidade_id": 1,
            "periodo_preferido": "madrugada"
        })
        self.assertFalse(sucesso)
        self.assertIn("período", msg.lower())

    def test_service_nao_bloqueia_telefone_duplicado(self):
        # Regra 10: não bloquear solicitações legítimas por duplicidade de telefone
        dados1 = {"nome": "Paula Lima", "telefone": "82991112222", "modalidade_id": 1}
        dados2 = {"nome": "Paula Lima", "telefone": "82991112222", "modalidade_id": 2}
        
        sucesso1, _, item1 = TrialService.solicitar_aula(dados1)
        sucesso2, _, item2 = TrialService.solicitar_aula(dados2)
        
        self.assertTrue(sucesso1)
        self.assertTrue(sucesso2)

    def test_modality_repository_compatibility(self):
        modalidades = ModalityRepository.get_all()
        self.assertGreater(len(modalidades), 0)
        primeira = modalidades[0]
        # Atributos exigidos pelos templates existentes
        self.assertTrue(hasattr(primeira, "id"))
        self.assertTrue(hasattr(primeira, "slug"))
        self.assertTrue(hasattr(primeira, "nome"))
        self.assertTrue(hasattr(primeira, "descricao"))
        self.assertTrue(hasattr(primeira, "imagem"))
        self.assertTrue(hasattr(primeira, "tag"))

if __name__ == "__main__":
    unittest.main()
