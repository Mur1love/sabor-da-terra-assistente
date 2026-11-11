# Sabor da Terra — Assistente Inteligente para Gestão de Cooperativa Agrícola

> Projeto intermediário da disciplina de **IA Generativa e Agentes**
> Universidade de Pernambuco (Campus Garanhuns) × **Sauter Tecnologia** — Novembro de 2026

**O que é:** um assistente de IA conversacional (texto, em português) que atua como apoio à operação da **Cooperativa dos Produtores Rurais Sabor da Terra**, cooperativa fictícia do Agreste Meridional de Pernambuco, resolvendo três gargalos:

| # | Gargalo | O que o assistente faz |
|---|---------|------------------------|
| 1 | **Triagem de pedidos** | Interpreta pedidos em linguagem natural coloquial (e-mail, WhatsApp, formulário web), extrai produtos/quantidades/prazos/comprador, classifica urgência e sinaliza problemas (fora de safra, acima da capacidade) |
| 2 | **Consulta documental** | Responde perguntas sobre certificações, rastreabilidade, sazonalidade e contratos **citando o documento de origem** — nada de resposta sem fundamento |
| 3 | **Comunicação com produtores** | Gera resumos personalizados (vendas, pendências, alocações) e notificações de novos pedidos por produtor |

## Regras do jogo (requisitos funcionais)

- Interface **conversacional** por texto para a equipe da cooperativa.
- Entende **português coloquial**: abreviações, erros de digitação, informação implícita.
- Toda resposta documental **indica de qual documento veio**.
- Gera **relatórios e notificações de forma autônoma** quando solicitado.
- Mantém o **contexto da conversa** durante a sessão.
- Quando **não souber a resposta**, diz claramente — **sem inventar**.

## Entregáveis e datas

| Data | Evento |
|------|--------|
| 05/11/2026 | Divulgação da formação dos grupos |
| **19/11/2026** | **Entrega obrigatória da arquitetura** — modificações após esta data são desconsideradas |
| 20–21/11/2026 | Apresentação e demonstração do protótipo funcional |

Entregas finais: **(1)** protótipo funcional com **demonstração ao vivo**; **(2)** apresentação de **10 minutos** explicando decisões técnicas, alternativas consideradas e limitações.

## Estrutura do repositório

```
sabor-da-terra-assistente/
├── README.md                ← este arquivo
├── INTEGRANTES.md           ← equipe do projeto
├── CONTRIBUTING.md          ← convenções de branch, commit e PR
├── app.py                   ← entrada Streamlit (validação do ambiente)
├── requirements.txt         ← dependências com versões fixadas
├── .env.example             ← modelo de configuração (copie para .env)
├── docs/
│   ├── 01-documento-base.md ← interpretação completa do documento do projeto
│   ├── 02-dataset.md        ← inventário detalhado dos dados + armadilhas
│   ├── 03-diretriz-arquitetura.md ← diretriz: arquitetura no ecossistema Google
│   └── 04-arquitetura.md    ← arquitetura de referência Google e decisões por componente
├── scripts/
│   └── smoke_llm.py         ← teste de fumaça real (Flash-Lite, Flash e embedding)
├── sabor_da_terra/
│   ├── llm/                 ← cliente único Gemini: modelo por papel, retry 429, modo fixture
│   ├── dados/               ← camada de dados estruturados (etapa 4)
│   ├── regras/              ← motor de regras de negócio (etapa 5)
│   ├── rag/                 ← consulta documental com citação (etapa 7)
│   ├── triagem/             ← triagem de pedidos (etapa 9)
│   ├── produtores/          ← comunicação com produtores (etapa 11)
│   └── assistente/          ← orquestração com function calling (etapa 12)
├── tests/                   ← suíte pytest (roda offline em LLM_MODO=fixture)
│   └── fixtures/llm/        ← respostas reais gravadas para os testes
└── data/                    ← base de dados da cooperativa (cópia de trabalho)
    ├── LEIA-ME.txt
    ├── produtores.csv · pedidos.json · financeiro.csv
    ├── sazonalidade.csv · tabela_precos_outubro_2026.csv · lotes.csv
    └── certificacoes/ (12 docs) · contratos/ (3) · fichas_tecnicas/ (5)
```

## Documentação

- **`docs/01-documento-base.md`** — tudo que o documento oficial define: cenário, problema, desafios, requisitos, entregáveis e datas.
- **`docs/02-dataset.md`** — descrição campo a campo dos 8 grupos de dados e das **armadilhas propositalmente escondidas** neles (certificação vencida, produtor sem registro sanitário, pedidos que não são pedidos de compra, pagamentos atrasados…).
- **`docs/03-diretriz-arquitetura.md`** — **diretriz permanente**: a arquitetura é desenhada no **ecossistema Google** — todo componente do protótipo é mapeado a um serviço Google Cloud com **justificativa e alternativa considerada**, mesmo que o protótipo execute local, sem GCP.
- **`docs/04-arquitetura.md`** — **arquitetura de referência** (rascunho da etapa 2): stack do protótipo por camada, tabela componente-a-componente (serviço Google Cloud, justificativa, alternativa considerada), divisão de modelos Gemini, princípios (dado estruturado por função, texto livre no RAG, o LLM não faz contas), padrão de troca local → Google e diagramas Mermaid.

## Como rodar

Requisitos: **Python 3.11+** e Git. Nenhuma conta Google Cloud é necessária no protótipo.

1. Clone o repositório e entre na pasta.
2. Crie o ambiente virtual e instale as dependências:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
   ```
3. Copie `.env.example` para `.env` e preencha **GEMINI_API_KEY** com a chave
   **restrita** criada no [Google AI Studio](https://aistudio.google.com)
   (regra 3 do `docs/03`; nunca commite o `.env`).
4. Valide o ambiente com o teste de fumaça (3 chamadas reais, custo mínimo):
   ```bash
   python -m scripts.smoke_llm
   ```
5. Abra a tela de validação: `streamlit run app.py`
6. Rode os testes (100% offline, sem gastar cota): `pytest`

**Modo fixture:** com `LLM_MODO=fixture`, o cliente reutiliza as respostas gravadas
em `tests/fixtures/llm/` e não faz **nenhuma** chamada à API. Para gravar ou
regravar uma resposta, rode uma vez com `LLM_MODO=real` — o cliente grava a
fixture automaticamente.

**Vertex AI:** para trocar AI Studio por Vertex AI basta configurar no `.env`:
`GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT` e `GOOGLE_CLOUD_LOCATION`,
e autenticar com `gcloud auth application-default login`. **Nenhuma linha de
código muda** — é o padrão de troca do `docs/04` §6.

## Como contribuir

Ver **[CONTRIBUTING.md](CONTRIBUTING.md)**: issues pelo template, branch
`etapa-N/descricao`, commit `Tema: descrição em português` e PR com
`Closes #N` revisado por ao menos 1 integrante — a `main` só recebe merge por PR.

## Dados

A base completa está em **`data/`** (cópia não-modificada do material fornecido em `~/Downloads/Facepe`). Todo o conteúdo é **fictício e simulado para avaliação** — porém contém CPFs, chaves PIX e dados bancários simulados: **mantenha este repositório PRIVADO**.

## Equipe

Ver **[INTEGRANTES.md](INTEGRANTES.md)**.
