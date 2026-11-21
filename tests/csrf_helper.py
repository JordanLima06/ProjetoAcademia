import os
import hashlib
from itsdangerous import URLSafeTimedSerializer

def get_csrf_token(client, app):
    """
    Gera um token CSRF válido para testes e sincroniza o segredo interno
    com a sessão do cliente de teste para validação bem-sucedida em qualquer requisição.
    """
    with client.session_transaction() as sess:
        if "csrf_token" not in sess:
            sess["csrf_token"] = hashlib.sha1(os.urandom(64)).hexdigest()
        raw_secret = sess["csrf_token"]

    serializer = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token")
    return serializer.dumps(raw_secret)
