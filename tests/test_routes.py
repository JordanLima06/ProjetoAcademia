import unittest
from app import create_app
from app.config import TestingConfig

class RoutesTestCase(unittest.TestCase):
    """Testes automatizados das rotas do FightAcademy."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

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

if __name__ == "__main__":
    unittest.main()
