# Arquitetura do FightAcademy

Este documento detalha o padrão arquitetural em camadas adotado pelo **FightAcademy**.

---

## 1. Visão Geral

A aplicação segue o padrão **Application Factory** com separação explícita de responsabilidades em camadas:

```
[ Cliente / Browser ]
        │
        ▼
[ Routes (Blueprints) ]
        │
        ▼
[ Services (Regras de Negócio) ]
   ├──▶ [ Models (Entidades) ]
   └──▶ [ Repositories (Persistência / SQL) ]
              │
              ▼
       [ PostgreSQL (db.py) ]
```

---

## 2. Responsabilidades por Camada

### `app/routes/`
* **Responsabilidade**: Gerenciamento de rotas e ciclo de requisição/resposta HTTP.
* **Componentes**:
  * `main.py`: Rotas institucionais e navegação (`/`, `/planos`, `/modalidades`, `/sobre`, etc.).
  * `auth.py`: Rotas de acesso (`/login`, `/cadastro`, `/logout`).
* **Regra**: As rotas **não** devem conter consultas SQL nem regras de negócio pesadas. Devem apenas receber parâmetros, delegar para a camada de serviços e renderizar templates ou redirecionar.

### `app/services/`
* **Responsabilidade**: Orquestração das regras de negócio do sistema.
* **Componentes**:
  * `auth_service.py`: Validação de formatos, verificação de duplicidade, hashing de senhas e autenticação.
  * `academy_service.py`: Lógica de planos, modalidades e dados da academia.
* **Regra**: Não acessa diretamente o banco via SQL; sempre interage através dos repositórios.

### `app/repositories/`
* **Responsabilidade**: Isolamento total do acesso a dados e consultas SQL.
* **Componentes**:
  * `user_repository.py`: Consultas SQL para inserção, busca por e-mail e busca por ID de usuários.
  * `plan_repository.py`: Acesso e recuperação dos planos de treinamento.
  * `modality_repository.py`: Acesso e recuperação das modalidades esportivas.
* **Regra**: Toda e qualquer instrução SQL (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) deve residir exclusivamente nesta camada.

### `app/models/`
* **Responsabilidade**: Representação estruturada das entidades de domínio.
* **Componentes**:
  * `user.py`: Entidade `User`.
  * `academy.py`: Entidades `Plano` e `Modalidade`.

### `app/db.py`
* **Responsabilidade**: Gerenciamento da conexão com o PostgreSQL, controle de cursores e encerramento seguro de conexões no encerramento da requisição (`teardown_appcontext`).

### `app/config.py`
* **Responsabilidade**: Centralização de variáveis e configurações por ambiente (`DevelopmentConfig`, `ProductionConfig`, `TestingConfig`).

### `app/templates/` e `app/static/`
* **Templates**: Páginas HTML Jinja2 e componentes reutilizáveis (`templates/_partials/navbar.html`, `footer.html`).
* **Static**: CSSs (`static/css/`), scripts (`static/js/`) e imagens (`static/assets/`).
