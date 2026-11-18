---
trigger: always_on
---


# FIGHTACADEMY — REGRAS GERAIS DO PROJETO

## 1. Identidade do projeto

O FightAcademy é um sistema de gerenciamento de academia.

O objetivo é oferecer uma plataforma para alunos, professores e administradores, incluindo cadastro, autenticação, planos, modalidades, matrículas e acompanhamento dos alunos.

## 2. Tecnologias oficiais

### Back-end
- Python 3
- Flask 3
- Flask Blueprints
- PostgreSQL
- psycopg2
- Jinja2
- Werkzeug Security

### Front-end
- HTML5
- CSS3
- JavaScript
- Bootstrap 5
- Google Fonts — Montserrat

## 3. Arquitetura

O projeto utiliza arquitetura modular com separação de responsabilidades.

- app/routes: rotas e endpoints.
- app/services: regras de negócio.
- app/repositories: acesso e persistência de dados.
- app/models: representação das entidades.
- app/templates: páginas HTML e componentes Jinja2.
- app/static: CSS, JavaScript e imagens.
- app/config.py: configurações.
- app/db.py: conexão com PostgreSQL.
- tests/: testes automatizados.
- docs/: documentação.

Não misture responsabilidades entre as camadas.

## 4. Banco de dados

Banco utilizado: academia.

Tabelas existentes:
- usuarios
- alunos

### Regras importantes

- Utilizar PostgreSQL como banco principal.
- Respeitar o schema existente.
- Não recriar tabelas existentes.
- Não alterar colunas, tipos ou relacionamentos sem autorização.
- Utilizar consultas parametrizadas.
- Utilizar transações quando houver operações relacionadas.
- Nunca armazenar senhas em texto puro.
- Utilizar hash seguro de senhas.
- Não inserir dados fictícios no banco de produção.

## 5. Design System

Respeitar as cores oficiais:

- Primary: #1765ED
- Hover: #0D53CC
- Light: #78A9FF
- Dark: #080B12
- Dark Blue: #0D1424
- Surface: #121A2B
- Card: #172238
- Text: #F5F7FA
- Muted: #A7B2C5

Tipografia principal: Montserrat.

Manter consistência visual em todas as páginas.

## 6. Responsividade e acessibilidade

- Desenvolver pensando em dispositivos móveis e desktops.
- Manter contraste adequado.
- Utilizar labels nos formulários.
- Garantir navegação por teclado.
- Utilizar estados visuais de foco.
- Manter botões e controles acessíveis.
- Evitar interfaces confusas ou excessivamente complexas.

## 7. Regras de desenvolvimento

- Analisar o código existente antes de implementar.
- Reutilizar componentes existentes sempre que possível.
- Evitar duplicação de código.
- Não criar arquivos desnecessários.
- Utilizar nomes claros e padronizados.
- Preservar funcionalidades existentes.
- Não substituir tecnologias sem autorização.
- Não modificar arquivos fora do escopo da tarefa.

## 8. Trabalho entre agentes

### Front-end
Responsável por HTML, CSS, JavaScript, Jinja2, Bootstrap e experiência visual.

Não deve modificar regras de negócio Python, consultas SQL ou schema do banco.

### Back-end
Responsável por Flask, Python, rotas, services, repositories, PostgreSQL e segurança.

Não deve modificar a identidade visual ou folhas de estilo.

### Integração

Quando uma funcionalidade exigir trabalho dos dois agentes:

1. Definir primeiro o contrato de integração.
2. O Back-end define rotas, dados e respostas.
3. O Front-end implementa a interface que utilizará esses dados.
4. Validar a integração.
5. Executar testes.

## 9. Protocolo de alterações

Antes de mudanças estruturais:

1. Analisar os arquivos envolvidos.
2. Apresentar o problema identificado.
3. Explicar a solução proposta.
4. Informar quais arquivos serão modificados.
5. Aguardar aprovação.

Não realizar alterações destrutivas sem autorização.

## 10. Prioridade principal

A evolução do FightAcademy deve ser gradual.

Preservar o código existente, manter a arquitetura organizada e priorizar segurança, qualidade, acessibilidade e facilidade de manutenção.
