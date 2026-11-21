import unittest
from app import create_app
from app.config import TestingConfig
from tests.csrf_helper import get_csrf_token

class RoutesTestCase(unittest.TestCase):
    """Testes automatizados das rotas do FightAcademy."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

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

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"FightAcademy", response.data)

    def test_planos_page(self):
        response = self.client.get("/planos")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Essencial", response.data)
        self.assertIn(b"Premium", response.data)

    def test_modalidades_page(self):
        response = self.client.get("/modalidades")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Muscula", response.data)
        self.assertIn(b"Boxe", response.data)

    def test_detalhe_modalidade_sucesso(self):
        response = self.client.get("/modalidades/boxe")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Boxe", response.data)

    def test_detalhe_modalidade_404(self):
        response = self.client.get("/modalidades/slug-inexistente")
        self.assertEqual(response.status_code, 404)

    def test_sobre_page(self):
        response = self.client.get("/sobre")
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    def test_cadastro_page(self):
        response = self.client.get("/cadastro")
        self.assertEqual(response.status_code, 200)

    def test_design_page(self):
        response = self.client.get("/design")
        self.assertEqual(response.status_code, 200)

    def test_aula_experimental_get(self):
        response = self.client.get("/aula-experimental")
        self.assertEqual(response.status_code, 200)
        self.assertIn("AGENDE SUA AULA EXPERIMENTAL".encode("utf-8"), response.data)
        self.assertIn(b"btn-voltar", response.data)

    def test_aula_experimental_get_com_parametro(self):
        response = self.client.get("/aula-experimental?modalidade=boxe")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-slug="boxe"', response.data)

    def test_aula_experimental_post_sucesso(self):
        response = self.client.post("/aula-experimental", data={
            "nome": "Fernando Souza",
            "telefone": "(82) 99321-1234",
            "modalidade_id": "1",
            "periodo_preferido": "noite"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Solicitação Recebida".encode("utf-8"), response.data)

    def test_aula_experimental_post_erro_repopula(self):
        response = self.client.post("/aula-experimental", data={
            "nome": "Nome Valido",
            "telefone": "",  # Telefone vazio gera erro 400
            "modalidade_id": "1"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Nome Valido", response.data)

if __name__ == "__main__":
    unittest.main()
