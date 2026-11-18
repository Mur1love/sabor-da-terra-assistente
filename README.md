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
├── app.py                   ← interface conversacional em Streamlit (etapa 13)
├── requirements.txt         ← dependências com versões fixadas
├── .env.example             ← modelo de configuração (copie para .env)
├── docs/
│   ├── 01-documento-base.md ← interpretação completa do documento do projeto
│   ├── 02-dataset.md        ← inventário detalhado dos dados + armadilhas
│   ├── 03-diretriz-arquitetura.md ← diretriz: arquitetura no ecossistema Google
│   └── 04-arquitetura.md    ← arquitetura de referência Google e decisões por componente
├── scripts/
│   ├── smoke_llm.py         ← teste de fumaça real (Flash-Lite, Flash e embedding)
│   └── exemplos_produtores.py ← gera os resumos e notificações de exemplo (etapa 11)
├── exemplos/
│   ├── fila_triagem.md      ← fila de triagem do dia 30/10/2026 (etapa 10)
│   └── produtores/          ← resumos, notificações e respostas a produtores (etapa 11)
├── sabor_da_terra/
│   ├── llm/                 ← cliente único Gemini: modelo por papel, retry 429, modo fixture
│   ├── dados/               ← camada de dados estruturados (etapa 4)
│   ├── regras/              ← motor de regras de negócio (etapa 5)
│   ├── rag/                 ← consulta documental com citação (etapa 7)
│   ├── triagem/             ← triagem de pedidos (etapa 9)
│   ├── produtores/          ← comunicação com produtores (etapa 11)
│   ├── assistente/          ← orquestração com function calling (etapa 12)
│   └── interface/           ← lógica da tela: fila para o st.dataframe, fontes, erros amigáveis (etapa 13)
├── tests/                   ← suíte pytest (roda offline em LLM_MODO=fixture)
│   └── fixtures/llm/        ← respostas reais gravadas para os testes
└── data/                    ← base de dados da cooperativa (cópia de trabalho)
    ├── LEIA-ME.txt
    ├── produtores.csv · pedidos.json · financeiro.csv
    ├── sazonalidade.csv · tabela_precos_outubro_2026.csv · lotes.csv
    └── certificacoes/ (12 docs) · contratos/ (3) · fichas_tecnicas/ (5)
```

## Interface conversacional (etapa 13)

`streamlit run app.py` abre o chat com o assistente orquestrado (etapa 12) —
`st.chat_input`/`st.chat_message`, histórico e estado da sessão no
`st.session_state`. O que aparece na tela:

- **Chat:** converse em português; o assistente chama as funções das etapas 4–11
  por function calling e mantém o contexto ("e o dela?", "esse lote") pela
  sessão. Toda resposta documental traz as citações `[fonte: arquivo]` e o
  rodapé **Fontes (N)** com os arquivos de origem.
- **Estado da sessão:** data de referência e os focos atuais
  (produtor, pedido e produto) — é o que resolve as referências vagas.
- **Barra lateral — Sessão:** **Modo do LLM** (`real` chama a API;
  `fixture` reproduz as respostas gravadas em `tests/fixtures/llm`, sem custo —
  trocar o modo inicia uma sessão nova), **data de referência** (o relógio da
  demo; por padrão vem de `DATA_REFERENCIA` do `.env`) e **Nova sessão**
  (apaga o histórico e os focos: o assistente não lembra da sessão anterior).
- **Barra lateral — Atalhos da demo:** chamam as funções reais direto, sem
  gastar cota — **Triar pedidos pendentes** (fila dos 15 registros em
  `st.dataframe`, urgentes e problemáticos no topo, com destaque por cor e
  detalhes por registro), **Resumo do produtor**, **Notificar produtores da
  fila** e **Relatório de pendências vencidas** (resumos e notificações em
  `st.code`, copiáveis; nada é enviado).
- **Barra lateral — Modelos:** o modelo de cada papel (roteamento, composição
  e embedding), as chamadas reais da sessão e o contador de failover. Com
  `GEMINI_MODELO_RESPOSTA_FALLBACK` configurado, a composição roda no Flash e,
  se a cota dele esgotar, retoma no fallback na mesma sessão — nada vira erro
  na tela. Medidor oficial: painel "Uso da API Gemini" do AI Studio.
- **Erros:** erro 429 (cota) e falhas de rede viram mensagem amigável na tela —
  nunca stack trace. Sem `GEMINI_API_KEY`, rode com `LLM_MODO=fixture`.

Capturas de tela em `docs/img/`.

## Documentação

- **`docs/01-documento-base.md`** — tudo que o documento oficial define: cenário, problema, desafios, requisitos, entregáveis e datas.
- **`docs/02-dataset.md`** — descrição campo a campo dos 8 grupos de dados e das **armadilhas propositalmente escondidas** neles (certificação vencida, produtor sem registro sanitário, pedidos que não são pedidos de compra, pagamentos atrasados…).
- **`docs/03-diretriz-arquitetura.md`** — **diretriz permanente**: a arquitetura é desenhada no **ecossistema Google** — todo componente do protótipo é mapeado a um serviço Google Cloud com **justificativa e alternativa considerada**, mesmo que o protótipo execute local, sem GCP.
- **`docs/04-arquitetura.md`** — **arquitetura de referência** (rascunho da etapa 2): stack do protótipo por camada, tabela componente-a-componente (serviço Google Cloud, justificativa, alternativa considerada), divisão de modelos Gemini, princípios (dado estruturado por função, texto livre no RAG, o LLM não faz contas), padrão de troca local → Google e diagramas Mermaid.

## Como rodar

Requisitos: **Python 3.11 ou mais novo** e Git. Nenhuma conta Google Cloud é necessária no protótipo.

1. Clone o repositório e entre na pasta.
2. Crie o ambiente virtual com o Python 3.11+ da máquina e instale as dependências:
   ```bash
   python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
   ```
   - **Sem `python3.11`?** Se o `python3` da máquina já for 3.11+ (`python3 --version`), use `python3 -m venv .venv` no lugar.
   - **Instalar o 3.11 no Ubuntu/WSL** (ex.: 22.04 vem com 3.10):
     ```bash
     sudo apt update && sudo apt install -y python3.11 python3.11-venv
     ```
     Sem o pacote nos repositórios da sua versão (ex.: 24.04, que vem com 3.12)? Use o PPA:
     ```bash
     sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update && \
       sudo apt install -y python3.11 python3.11-venv
     ```
     Se `python3 -m venv` reclamar de `ensurepip`, falta o `python3.*-venv` — instale o pacote acima e repita.
   - **Windows/macOS:** instalador em <https://www.python.org/downloads/>.
3. Copie `.env.example` para `.env` e preencha **GEMINI_API_KEY** com a chave
   **restrita** criada no [Google AI Studio](https://aistudio.google.com)
   (regra 3 do `docs/03`; nunca commite o `.env`).
4. Valide o ambiente com o teste de fumaça (3 chamadas reais, custo mínimo):
   ```bash
   python -m scripts.smoke_llm
   ```
5. Abra a interface conversacional:
   ```bash
   streamlit run app.py
   ```
   Converse no chat ("Que certificações a cooperativa tem?", "Triar pedidos pendentes",
   "E o dela?") e use os atalhos da barra lateral. Detalhes na seção
   [Interface conversacional](#interface-conversacional-etapa-13).
6. Rode os testes (100% offline, sem gastar cota): `pytest`
7. Gere os exemplos de comunicação com produtores em `exemplos/produtores/`:
   `python -m scripts.exemplos_produtores` (sem API) ou
   `python -m scripts.exemplos_produtores --gemini` (o Gemini Flash reescreve o
   texto; se mexer em algum valor, data ou código, fica o texto original).

**Modos do LLM (`LLM_MODO` no `.env`):**
- `real` — chama a API de verdade e **não grava nada**: a demo e a triagem
  rodam assim, sem sujar `tests/fixtures/llm/` a cada mensagem.
- `gravar` — chama a API e grava a resposta completa em `tests/fixtures/llm/`.
  Para gravar ou regravar uma resposta, rode uma vez:
  `LLM_MODO=gravar python -m scripts.smoke_llm`.
- `fixture` — reproduz as respostas gravadas em `tests/fixtures/llm/` e não
  faz **nenhuma** chamada à API (é o modo em que os testes rodam).

**Vertex AI:** para trocar AI Studio por Vertex AI basta configurar no `.env`:
`GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT` e `GOOGLE_CLOUD_LOCATION`,
e autenticar com `gcloud auth application-default login`. **Nenhuma linha de
código muda** — é o padrão de troca do `docs/04` §6.

**Solução de problemas:** se o comando do passo 2 falhar citando um AppImage
(ex.: `Vicinae-x86_64.AppImage ... ensurepip`), é o ambiente de sessão da
máquina interferindo no resolvedor de caminho do Python — o AppImage de
um app na sessão é tomado como executável-base. Neutralize nesta sessão
e repita o passo 2:

```bash
unset APPIMAGE APPDIR OWD
```

Para valer em todo terminal novo, adicione o mesmo `unset` ao final do
`~/.zshrc` (ou `~/.bashrc`).

**Importante:** neste tipo de sessão, o mesmo `unset` vale para **usar** o
`.venv` — sem ele, o Python ignora o `site-packages` do venv e roda os pacotes
de `~/.local` do usuário (hoje com as mesmas versões, mas fora do controle do
`requirements.txt`). Se um comando `python` se comportar de forma estranha
(módulo que deveria existir "não encontrado", caminho do AppImage em
tracebacks), rode `unset APPIMAGE APPDIR OWD` e repita.

## Como contribuir

Ver **[CONTRIBUTING.md](CONTRIBUTING.md)**: issues pelo template, branch
`etapa-N/descricao`, commit `Tema: descrição em português` e PR com
`Closes #N` revisado por ao menos 1 integrante — a `main` só recebe merge por PR.

## Dados

A base completa está em **`data/`** (cópia não-modificada do material fornecido em `~/Downloads/Facepe`). Todo o conteúdo é **fictício e simulado para avaliação** — porém contém CPFs, chaves PIX e dados bancários simulados: **mantenha este repositório PRIVADO**.

## Equipe

Ver **[INTEGRANTES.md](INTEGRANTES.md)**.
