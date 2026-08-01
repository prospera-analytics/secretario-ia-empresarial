@'
# Secretário IA Empresarial

Aplicação desenvolvida em Python e Streamlit para consultar, analisar e relacionar dados operacionais de uma empresa varejista de smartphones.

O sistema combina banco de dados, ferramentas empresariais, consultas de preços concorrentes e um agente de inteligência artificial. Fluxos críticos são executados de forma determinística, reduzindo chamadas ao modelo e evitando respostas baseadas em dados não confirmados.

## Funcionalidades

- Consulta e pesquisa de produtos;
- Controle e análise de estoque;
- Consulta de fornecedores e compras;
- Registro e análise de vendas;
- Gestão de campanhas;
- Análises de margem, cobertura de estoque e riscos empresariais;
- Consulta de preços em concorrentes;
- Comparação entre preços internos e externos;
- Exibição da URL original da oferta concorrente;
- Memória factual da conversa;
- Roteamento seletivo de ferramentas;
- Interface conversacional com Streamlit.

## Arquitetura

O projeto separa as responsabilidades em módulos:

```text
challenge_alura/
├── agente/
│   ├── contexto.py
│   ├── executor.py
│   ├── ferramentas/
│   ├── memoria.py
│   ├── modelo.py
│   ├── orquestrador.py
│   ├── prompt.py
│   └── roteador.py
├── analises/
├── crud/
├── database/
├── servicos/
├── testes/
├── web/
├── app.py
├── config.py
├── requirements.txt
└── README.md