import unittest
from datetime import date
from werkzeug.security import generate_password_hash

from app import create_app
from app.config import TestingConfig
from app.models.user import User, Aluno
from app.repositories.user_repository import (
    UserRepository,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError
)
from app.services.auth_service import AuthService

class PostgreSQLResilienceTestCase(unittest.TestCase):
    """
    Testes automatizados para validação do tratamento de indisponibilidade
    e falhas do PostgreSQL na camada de persistência e decoradores de autenticação.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.test_request_context()
        self.ctx.push()

        # Limpeza e reset de flags de teste
        UserRepository._TEST_USERS.clear()
        UserRepository._TEST_ALUNOS.clear()
        UserRepository._TEST_ID_SEQ = 1
        UserRepository._SIMULATE_CONNECTION_ERROR = False
        UserRepository._SIMULATE_QUERY_ERROR = False
        UserRepository._ALLOW_TEST_FALLBACK = True

        # Criação de usuários de teste
        self.user_ativo = User(
            id=1,
            nome="Carlos Ativo",
            email="carlos@teste.com",
            senha=generate_password_hash("SenhaValida123"),
            tipo="aluno",
            ativo=True
        )
        UserRepository._TEST_USERS[1] = self.user_ativo

        self.aluno_ativo = Aluno(
            id=1,
            usuario_id=1,
            data_nascimento=date(1990, 5, 20),
            telefone="(11) 97777-6666",
            data_cadastro=date.today(),
            objetivo="Boxe",
            usuario=self.user_ativo
        )
        UserRepository._TEST_ALUNOS[1] = self.aluno_ativo

        self.user_inativo = User(
            id=2,
            nome="Marcos Inativo",
            email="marcos@teste.com",
            senha=generate_password_hash("SenhaInativo123"),
            tipo="aluno",
            ativo=False
        )
        UserRepository._TEST_USERS[2] = self.user_inativo

    def tearDown(self):
        UserRepository._SIMULATE_CONNECTION_ERROR = False
        UserRepository._SIMULATE_QUERY_ERROR = False
        UserRepository._ALLOW_TEST_FALLBACK = True
        self.ctx.pop()

    def _login_client(self, client, user):
        """Inicializa a sessão autenticada com user_id e auth_fingerprint atualizados."""
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_nome"] = user.nome
            sess["user_tipo"] = user.tipo
            sess["auth_fingerprint"] = AuthService.get_password_fingerprint(user.senha)

    def test_01_usuario_existente_e_ativo_recuperado_com_sucesso(self):
        """Valida busca de usuário existente e ativo no repositório."""
        user = UserRepository.find_by_id(1)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, 1)
        self.assertTrue(user.ativo)
        self.assertEqual(user.email, "carlos@teste.com")

    def test_02_usuario_inexistente_retorna_none_e_invalida_sessao(self):
        """Valida que usuário inexistente retorna None e causa limpeza da sessão em rota protegida."""
        user = UserRepository.find_by_id(9999)
        self.assertIsNone(user)

        with self.client.session_transaction() as sess:
            sess["user_id"] = 9999
            sess["auth_fingerprint"] = "qualquer_fingerprint"

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_03_usuario_inativo_invalida_sessao(self):
        """Valida que usuário inativo no banco causa invalidação e limpeza da sessão."""
        user = UserRepository.find_by_id(2)
        self.assertIsNotNone(user)
        self.assertFalse(user.ativo)

        self._login_client(self.client, self.user_inativo)

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_04_falha_de_conexao_lanca_database_connection_error(self):
        """Valida que indisponibilidade do banco lança DatabaseConnectionError explicitamente."""
        UserRepository._SIMULATE_CONNECTION_ERROR = True

        with self.assertRaises(DatabaseConnectionError):
            UserRepository.find_by_id(1)

        with self.assertRaises(DatabaseConnectionError):
            UserRepository.find_by_email("carlos@teste.com")

        with self.assertRaises(DatabaseConnectionError):
            UserRepository.find_aluno_by_user_id(1)

    def test_05_erro_inesperado_sql_lanca_database_query_error(self):
        """Valida que erro inesperado na execução SQL lança DatabaseQueryError explicitamente."""
        UserRepository._SIMULATE_QUERY_ERROR = True

        with self.assertRaises(DatabaseQueryError):
            UserRepository.find_by_id(1)

        with self.assertRaises(DatabaseQueryError):
            UserRepository.find_by_email("carlos@teste.com")

    def test_06_http_503_sem_limpeza_de_sessao_em_indisponibilidade_banco(self):
        """
        Valida que rota protegida por @login_required retorna HTTP 503 durante falha
        de conexão com o PostgreSQL, sem executar session.clear().
        """
        self._login_client(self.client, self.user_ativo)

        # Simula indisponibilidade de conexão do PostgreSQL
        UserRepository._SIMULATE_CONNECTION_ERROR = True

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 503)
        self.assertIn("Serviço temporariamente indisponível", res.get_data(as_text=True))

        # A sessão NÃO pode ter sido apagada!
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), 1)
            self.assertIsNotNone(sess.get("auth_fingerprint"))

    def test_07_sessao_preservada_e_funciona_apos_recuperacao_do_banco(self):
        """
        Valida o ciclo completo de resiliência:
        1. Acesso durante indisponibilidade -> 503, sessão preservada.
        2. Banco recupera conexão.
        3. Próximo acesso do mesmo cliente autenticado -> 200 OK sem necessidade de novo login.
        """
        self._login_client(self.client, self.user_ativo)

        # 1. Banco fica indisponível
        UserRepository._SIMULATE_CONNECTION_ERROR = True
        res_falha = self.client.get("/aluno/painel")
        self.assertEqual(res_falha.status_code, 503)

        # Sessão legítima foi preservada
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), 1)

        # 2. Banco restabelece a conexão
        UserRepository._SIMULATE_CONNECTION_ERROR = False

        # 3. Usuário tenta novamente -> autenticação funciona sem pedir novo login!
        res_recuperado = self.client.get("/aluno/painel")
        self.assertEqual(res_recuperado.status_code, 200)
        self.assertIn("Meu Painel", res_recuperado.get_data(as_text=True))

    def test_08_erro_inesperado_sql_retorna_500_sem_limpeza_de_sessao(self):
        """Valida que erro inesperado na query SQL retorna HTTP 500 sem apagar a sessão."""
        self._login_client(self.client, self.user_ativo)

        UserRepository._SIMULATE_QUERY_ERROR = True

        res = self.client.get("/aluno/painel")
        self.assertEqual(res.status_code, 500)
        self.assertIn("Erro interno do servidor", res.get_data(as_text=True))

        # Sessão permanece preservada
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), 1)

    def test_09_auth_service_resiliente_a_indisponibilidade_de_banco(self):
        """Valida que AuthService.authenticate retorna mensagem apropriada sem crash em caso de banco offline."""
        UserRepository._SIMULATE_CONNECTION_ERROR = True

        sucesso, mensagem, usuario = AuthService.authenticate("carlos@teste.com", "SenhaValida123")
        self.assertFalse(sucesso)
        self.assertIsNone(usuario)
        self.assertIn("Serviço temporariamente indisponível", mensagem)

    def test_10_role_required_retorna_503_sem_limpeza_de_sessao(self):
        """Valida que o decorador @role_required também responde 503 sem limpar sessão na queda do banco."""
        # Configura sessão com tipo aluno mas sem g.user preenchido previamente
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["auth_fingerprint"] = AuthService.get_password_fingerprint(self.user_ativo.senha)

        UserRepository._SIMULATE_CONNECTION_ERROR = True

        res = self.client.get("/aluno/perfil")
        self.assertEqual(res.status_code, 503)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), 1)

    # -------------------------------------------------------------------------
    # TESTES DE CONEXÃO MULTI-AMBIENTE: NEON + VERCEL VS DESENVOLVIMENTO LOCAL
    # -------------------------------------------------------------------------

    def test_11_conexao_modo_uri_prioriza_database_url_com_realdictcursor(self):
        """Valida que a conexão via URI prioriza DATABASE_URL, preserva RealDictCursor e parâmetros Neon."""
        from unittest.mock import patch, MagicMock
        from app.db import get_db_connection
        from psycopg2.extras import RealDictCursor
        from flask import g

        neon_url = "postgresql://academia_owner:segredo123@ep-cool-sun-12345.sa-east-1.aws.neon.tech/academia?sslmode=require&channel_binding=require"

        with patch("app.db._get_config_value", return_value=neon_url):
            with patch("psycopg2.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn

                # Força limpeza de conexão em g
                g.pop("db", None)

                conn = get_db_connection()

                self.assertIsNotNone(conn)
                mock_connect.assert_called_once()
                args, kwargs = mock_connect.call_args

                # Primeiro argumento deve ser a URL preservada
                self.assertEqual(args[0], neon_url)
                self.assertIn("sslmode=require", args[0])
                self.assertIn("channel_binding=require", args[0])
                # RealDictCursor obrigatório
                self.assertEqual(kwargs.get("cursor_factory"), RealDictCursor)

    def test_12_conexao_modo_uri_usa_postgres_url_como_alternativa(self):
        """Valida que POSTGRES_URL é utilizada como alternativa quando DATABASE_URL não estiver definida."""
        from unittest.mock import patch, MagicMock
        from app.db import get_db_connection
        from psycopg2.extras import RealDictCursor
        from flask import g

        neon_postgres_url = "postgres://academia_owner:segredo123@ep-cool-sun-12345.sa-east-1.aws.neon.tech/academia?sslmode=require"

        # Simula ausência de DATABASE_URL e presença de POSTGRES_URL no ambiente
        with patch.dict("os.environ", {"DATABASE_URL": "", "POSTGRES_URL": neon_postgres_url}, clear=False):
            with patch("app.db._get_config_value", return_value=None):
                with patch("psycopg2.connect") as mock_connect:
                    mock_conn = MagicMock()
                    mock_connect.return_value = mock_conn

                    g.pop("db", None)
                    conn = get_db_connection()

                    self.assertIsNotNone(conn)
                    mock_connect.assert_called_once()
                    args, kwargs = mock_connect.call_args

                    # O prefixo 'postgres://' deve ter sido normalizado para 'postgresql://'
                    self.assertTrue(args[0].startswith("postgresql://"))
                    self.assertIn("sslmode=require", args[0])
                    self.assertEqual(kwargs.get("cursor_factory"), RealDictCursor)

    def test_13_conexao_modo_local_usa_parametros_individuais_com_realdictcursor(self):
        """Valida que em desenvolvimento local sem URL, a conexão utiliza os parâmetros individuais e RealDictCursor."""
        from unittest.mock import patch, MagicMock
        from app.db import get_db_connection
        from psycopg2.extras import RealDictCursor
        from flask import g

        # Simula ambiente local (sem DATABASE_URL nem POSTGRES_URL)
        with patch.dict("os.environ", {"DATABASE_URL": "", "POSTGRES_URL": "", "VERCEL": "", "APP_ENV": "", "FLASK_ENV": "development"}):
            with patch("app.db._get_config_value") as mock_cfg:
                def config_side_effect(key, default=None):
                    configs = {
                        "DATABASE_URL": None,
                        "DB_HOST": "127.0.0.1",
                        "DB_PORT": "5432",
                        "DB_NAME": "academia_local",
                        "DB_USER": "postgres_local",
                        "DB_PASSWORD": "admin_local"
                    }
                    return configs.get(key, default)
                mock_cfg.side_effect = config_side_effect

                with patch("psycopg2.connect") as mock_connect:
                    mock_conn = MagicMock()
                    mock_connect.return_value = mock_conn

                    g.pop("db", None)
                    conn = get_db_connection()

                    self.assertIsNotNone(conn)
                    mock_connect.assert_called_once_with(
                        host="127.0.0.1",
                        port="5432",
                        dbname="academia_local",
                        user="postgres_local",
                        password="admin_local",
                        cursor_factory=RealDictCursor
                    )

    def test_14_producao_sem_url_gera_erro_explicito_e_proibe_localhost(self):
        """Valida que em produção a ausência de DATABASE_URL/POSTGRES_URL gera erro explícito e proíbe localhost."""
        from unittest.mock import patch
        from app.db import get_db_connection
        from app.config import ProductionConfig
        from flask import g

        # 1. Validação na classe de configuração
        with patch.dict("os.environ", {"DATABASE_URL": "", "POSTGRES_URL": ""}):
            with self.assertRaises(RuntimeError) as ctx_cfg:
                ProductionConfig.validate_production_config()
            self.assertIn("DATABASE_URL ou POSTGRES_URL não configurada", str(ctx_cfg.exception))
            self.assertIn("É estritamente proibido utilizar localhost como fallback", str(ctx_cfg.exception))

        # 2. Validação no método get_db_connection durante produção
        with patch.dict("os.environ", {"DATABASE_URL": "", "POSTGRES_URL": "", "VERCEL": "1"}):
            with patch("app.db._get_config_value", return_value=None):
                g.pop("db", None)
                with self.assertRaises(RuntimeError) as ctx_db:
                    get_db_connection()
                self.assertIn("É estritamente proibido utilizar localhost como fallback em ambiente de produção", str(ctx_db.exception))

    def test_15_selecao_ambiente_vercel_app_env_e_flask_env(self):
        """Valida a seleção dinâmica da configuração para VERCEL=1, APP_ENV=production, FLASK_ENV=production e dev."""
        from unittest.mock import patch
        from app.config import get_config_class, ProductionConfig, DevelopmentConfig, TestingConfig

        # VERCEL=1
        with patch.dict("os.environ", {"VERCEL": "1", "APP_ENV": "", "FLASK_ENV": ""}):
            self.assertEqual(get_config_class(), ProductionConfig)

        # APP_ENV=production
        with patch.dict("os.environ", {"VERCEL": "", "APP_ENV": "production", "FLASK_ENV": ""}):
            self.assertEqual(get_config_class(), ProductionConfig)

        # FLASK_ENV=production
        with patch.dict("os.environ", {"VERCEL": "", "APP_ENV": "", "FLASK_ENV": "production"}):
            self.assertEqual(get_config_class(), ProductionConfig)

        # Padrão desenvolvimento
        with patch.dict("os.environ", {"VERCEL": "", "APP_ENV": "", "FLASK_ENV": ""}):
            self.assertEqual(get_config_class(), DevelopmentConfig)

        # Testes
        with patch.dict("os.environ", {"FLASK_ENV": "testing"}):
            self.assertEqual(get_config_class(), TestingConfig)

    def test_16_tratamento_erros_e_mascaramento_credenciais_em_logs(self):
        """Valida que credenciais e senhas não aparecem em mensagens de erro ou logs."""
        from app.db import _sanitize_db_error

        # Erro contendo URI com senha
        err_uri = Exception("could not connect to postgresql://academia_owner:minhaSenhaSecreta123@ep-xyz.neon.tech/academia")
        msg_uri_sanitizada = _sanitize_db_error(err_uri)
        self.assertNotIn("minhaSenhaSecreta123", msg_uri_sanitizada)
        self.assertIn(":*****@", msg_uri_sanitizada)

        # Erro contendo password=
        err_kv = Exception("FATAL: password authentication failed for user academia_owner password=segredoSuperForte!")
        msg_kv_sanitizada = _sanitize_db_error(err_kv)
        self.assertNotIn("segredoSuperForte!", msg_kv_sanitizada)
        self.assertIn("password=*****", msg_kv_sanitizada)

    def test_17_preservacao_parametros_neon(self):
        """Valida que normalize_database_url converte o scheme e preserva 100% dos parâmetros de query Neon."""
        from app.db import normalize_database_url

        url_original = "postgres://academia_owner:pwd@ep-xyz.sa-east-1.aws.neon.tech/academia?sslmode=require&channel_binding=require&endpoint=ep-xyz"
        url_normalizada = normalize_database_url(url_original)

        self.assertTrue(url_normalizada.startswith("postgresql://"))
        self.assertIn("sslmode=require", url_normalizada)
        self.assertIn("channel_binding=require", url_normalizada)
        self.assertIn("endpoint=ep-xyz", url_normalizada)

if __name__ == "__main__":
    unittest.main()
