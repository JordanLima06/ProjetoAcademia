import pytest
from app import create_app
from app.config import TestingConfig

@pytest.fixture
def app():
    """Cria e configura uma instância da aplicação para os testes."""
    app = create_app(TestingConfig)
    return app

@pytest.fixture
def client(app):
    """Cliente de testes do Flask."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Executor de comandos CLI para testes."""
    return app.test_cli_runner()
