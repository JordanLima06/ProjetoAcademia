# Guia de Configuração e Execução - FightAcademy

Instruções para configurar o ambiente e executar o projeto localmente.

---

## 1. Pré-requisitos
* Python 3.10+
* PostgreSQL (opcional para navegação básica, obrigatório para persistência de usuários)

---

## 2. Instalação de Dependências

Crie e ative o ambiente virtual (caso ainda não tenha):
```bash
python -m venv .venv
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1
# No Linux/Mac:
source .venv/bin/activate
```

Instale os requisitos:
```bash
pip install -r requirements.txt
# Para suporte ao PostgreSQL (se for utilizar o banco):
pip install psycopg2-binary
```

---

## 3. Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```
Ajuste suas credenciais de banco de dados (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).

---

## 4. Executando a Aplicação

Inicie o servidor de desenvolvimento:
```bash
python main.py
```
Acesse no navegador: `http://127.0.0.1:5000`

---

## 5. Executando os Testes Automatizados

Para rodar os testes:
```bash
pip install pytest
pytest
```


## SMTP -> Mailtrap