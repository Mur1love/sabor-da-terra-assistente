# Etapa 3 — Ambiente de Desenvolvimento e Acesso à API Gemini — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualquer integrante clona o repositório e roda o projeto em minutos — com um cliente Gemini único que escolhe o modelo por papel, alterna AI Studio ↔ Vertex AI só por variável de ambiente, grava/reproduz respostas para testar sem gastar cota e nunca expõe a chave.

**Architecture:** Pacote `sabor_da_terra/` com um cliente fino (`llm/cliente.py`) sobre o SDK `google-genai`. O cliente lê a configuração do ambiente, resolve o modelo por papel, encapsula retry 429 com backoff e conta chamadas por modelo. O modo `fixture` grava respostas reais em `tests/fixtures/llm/` e as reproduz depois — a suíte roda 100% offline. A troca para Vertex AI não muda código: o SDK lê `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT` e `GOOGLE_CLOUD_LOCATION`.

**Tech Stack:** Python 3.11+, `google-genai==3.1.0`, `streamlit==1.67.0`, `pandas==3.1.1`, `pytest==9.2.0`, `python-dotenv==1.2.4`; seriação em JSON; `hashlib` para chave de fixture.

**Spec:** issue #3 (`https://github.com/Mur1love/sabor-da-terra-assistente/issues/3`), `docs/03-diretriz-arquitetura.md` §"Estratégia de custo — API do Gemini" (regras 1–4 e Plano B), `docs/04-arquitetura.md` §1 (stack por camada), §3 (divisão de modelos), §6 (padrão de troca).

## Global Constraints

- **Python 3.11+** (base do container em #15). O ambiente local tem 3.15; não usar sintaxe acima de 3.11.
- **Versões fixadas exatas** em `requirements.txt`: `google-genai==3.1.0`, `streamlit==1.67.0`, `pandas==3.1.1`, `pytest==9.2.0`, `python-dotenv==1.2.4`.
- **Nenhum segredo no repositório nem no histórico do git.** `.env` é ignorado; `.env.example` é versionado com valores vazios.
- **Modelos por papel** (tabela do `docs/03`, conferida em 10/11/2026): triagem/extração = `gemini-3.5-flash-lite`; resposta final = `gemini-3.8-flash`; embeddings = `gemini-embedding-001`.
- **`LLM_MODO=real|fixture`.** Com `fixture`, nenhuma chamada de rede é feita — nem para descobrir chave.
- **Troca AI Studio → Vertex AI só por ambiente:** `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` (+ ADC). Nenhuma linha de código muda.
- **Retry somente para 429**, backoff exponencial 1s, 2s, 4s… com teto de 30s e `max_tentativas` configurável (padrão 4). Erros não-429 sobem imediatamente.
- **Contador por modelo** conta chamadas **bem-sucedidas** à API; replay de fixture não conta.
- **Idioma:** código, mensagens e docs em português. Commits `Tema: descrição em português` (ver `CONTRIBUTING.md`).
- **Fora do escopo:** dados, RAG, triagem e produtores (#4–#12); Dockerfile/Terraform (#15); billing pago (#17).

## Entradas humanas obrigatórias (não executáveis pelo agente)

Estas três ações precisam de uma pessoa com acesso ao AI Studio/Gmail. O plano pausa e pede a entrada quando chegar nelas:

1. **Chave restrita:** criar no Google AI Studio, copiar para `.env` (nunca commitar). Regra 3 do `docs/03`.
2. **Limites reais:** copiar RPM/RPD/TPM de AI Studio → Usage and billing para a subseção nova do `docs/03`, com a data da consulta. Regra 4 do `docs/03`.
3. **E-mail à Sauter** pedindo créditos de parceiro (Plano B do `docs/03`) e registrar a resposta como comentário na issue #3.

Rascunho do e-mail (humano envia e cola a resposta na issue):

> **Assunto:** Projeto Sabor da Terra (UPE × Sauter) — solicitação de créditos de parceiro Google Cloud
>
> Olá, equipe Sauter. Somos o grupo do projeto intermediário de IA Generativa e Agentes (UPE Garanhuns). Estamos construindo o protótipo do assistente da Cooperativa Sabor da Terra com a Gemini API no free tier e queremos garantir a demonstração dos dias 20–21/11. A Sauter, como parceira Google Cloud do desafio, conseguiria créditos de parceiro para as equipes? O uso estimado é de centavos por demonstração (Flash/Flash-Lite + embeddings). Obrigado!

## Estrutura de arquivos

```
sabor-da-terra-assistente/
├── app.py                          # entrada Streamlit — tela "olá" (valida ambiente)
├── requirements.txt                # versões fixadas
├── .env.example                    # todas as chaves, sem valores secretos
├── pytest.ini                      # testpaths = tests
├── scripts/
│   ├── __init__.py
│   └── smoke_llm.py                # teste de fumaça real: Flash-Lite, Flash, embedding
├── sabor_da_terra/
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py             # exporta LLMClient, Papel
│   │   └── cliente.py              # cliente único: papéis, modelos, retry, fixtures, contador
│   ├── dados/__init__.py           # vazio nesta etapa (#4+)
│   ├── regras/__init__.py          # vazio nesta etapa (#5+)
│   ├── rag/__init__.py             # vazio nesta etapa (#7+)
│   ├── triagem/__init__.py         # vazio nesta etapa (#9+)
│   ├── produtores/__init__.py      # vazio nesta etapa (#11+)
│   └── assistente/__init__.py      # vazio nesta etapa (#12+)
└── tests/
    ├── __init__.py
    ├── conftest.py                 # força LLM_MODO=fixture na suíte
    ├── dobles.py                   # ClienteFake/ModeloFake para testes sem rede
    ├── fixtures/llm/<papel>/       # respostas gravadas (versionadas)
    ├── test_estrutura.py
    ├── test_cliente_config.py
    ├── test_cliente_fixture.py
    ├── test_cliente_retry.py
    ├── test_ambiente_local.py
    └── test_documentacao.py
```

**Setup (uma vez, antes da Task 1):**

- [ ] Criar a branch de trabalho a partir da `main` atualizada: `git switch -c etapa-3/ambiente-gemini`
- [ ] Criar o ambiente virtual. Neste harness, `python3 -m venv` aponta para um AppImage; usar: `env -u APPIMAGE /usr/bin/python3 -m venv .venv`
- [ ] Ativar e instalar: `source .venv/bin/activate && pip install -r requirements.txt` (após a Task 1 criar o arquivo)

---

### Task 1: Estrutura do projeto, dependências e configuração de ambiente

**Files:**
- Create: `requirements.txt`, `.env.example`, `pytest.ini`, `app.py`
- Create: `sabor_da_terra/__init__.py`, `sabor_da_terra/{llm,dados,regras,rag,triagem,produtores,assistente}/__init__.py`
- Create: `tests/__init__.py`, `tests/test_estrutura.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nada (primeira task).
- Produces: pacotes importáveis `sabor_da_terra.*`; `app.py` como entrada Streamlit; arquivos de configuração lidos pelas tasks seguintes e pelos testes de documentação.

- [ ] **Step 1: Escrever o teste que falha (estrutura + configuração)**

`tests/test_estrutura.py`:

```python
import importlib
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PACOTES = [
    "sabor_da_terra",
    "sabor_da_terra.llm",
    "sabor_da_terra.dados",
    "sabor_da_terra.regras",
    "sabor_da_terra.rag",
    "sabor_da_terra.triagem",
    "sabor_da_terra.produtores",
    "sabor_da_terra.assistente",
]

def test_pacotes_importaveis():
    for nome in PACOTES:
        assert importlib.import_module(nome) is not None

def test_requirements_tem_versoes_fixadas():
    linhas = [
        linha.strip()
        for linha in (RAIZ / "requirements.txt").read_text().splitlines()
        if linha.strip() and not linha.startswith("#")
    ]
    assert linhas
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+==\S+", linha) for linha in linhas)

def test_env_example_tem_chaves_obrigatorias():
    texto = (RAIZ / ".env.example").read_text()
    for chave in [
        "GEMINI_API_KEY",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "MODELO_TRIAGEM",
        "MODELO_RESPOSTA",
        "MODELO_EMBEDDING",
        "LLM_MODO",
    ]:
        assert f"{chave}=" in texto

def test_gitignore_ignora_env_e_indice_vetorial():
    texto = (RAIZ / ".gitignore").read_text()
    assert ".env" in texto
    assert ".llama_index/" in texto

def test_app_tem_tela_ola():
    texto = (RAIZ / "app.py").read_text()
    assert "st.title(" in texto
    assert "Sabor da Terra" in texto
```

- [ ] **Step 2: Rodar o teste para ver falhar**

Run: `pytest tests/test_estrutura.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sabor_da_terra'` (e arquivos ausentes).

- [ ] **Step 3: Criar os arquivos**

`requirements.txt`:

```
google-genai==3.1.0
streamlit==1.67.0
pandas==3.1.1
pytest==9.2.0
python-dotenv==1.2.4
```

`.env.example`:

```
# Copie para .env e preencha. NUNCA commite o .env.
# Chave restrita criada no Google AI Studio (regra 3 do docs/03).
GEMINI_API_KEY=

# FALSE = Gemini API (AI Studio) | TRUE = Vertex AI (ADC/IAM)
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=

# Modelos por papel — tabela "Divisão de trabalho entre modelos" do docs/03
MODELO_TRIAGEM=gemini-3.5-flash-lite
MODELO_RESPOSTA=gemini-3.8-flash
MODELO_EMBEDDING=gemini-embedding-001

# real = chama a API e grava fixtures | fixture = reutiliza respostas gravadas
LLM_MODO=real
```

`pytest.ini`:

```
[pytest]
testpaths = tests
```

`app.py`:

```python
"""Tela mínima para validar o ambiente (a interface conversacional vem na etapa 13)."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Sabor da Terra — Assistente", page_icon="🌱")
st.title("Sabor da Terra — Assistente")
st.write("Ambiente pronto. A interface conversacional chega na etapa 13.")
```

`__init__.py` de cada pacote: docstring de uma linha com o papel do pacote (ex.:
`sabor_da_terra/llm/__init__.py` → `"""Cliente único de LLM e embeddings."""`).
`tests/__init__.py`: vazio.

`.gitignore` — trocar o bloco Python e acrescentar o índice vetorial:

```gitignore
# ==== Python ====
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.ruff_cache/
.mypy_cache/

# ==== Índice vetorial local (LlamaIndex) ====
.llama_index/
storage/
```

- [ ] **Step 4: Rodar o teste para ver passar**

Run: `pytest tests/test_estrutura.py -v`
Expected: PASS (5 testes).

- [ ] **Step 5: Commitar**

```bash
git add requirements.txt .env.example pytest.ini app.py .gitignore sabor_da_terra tests
git commit -m "Ambiente: estrutura do projeto, dependências e configuração"
```

---

### Task 2: Cliente Gemini — papéis, modelos e validação de configuração

**Files:**
- Create: `sabor_da_terra/llm/cliente.py`
- Modify: `sabor_da_terra/llm/__init__.py`
- Create: `tests/conftest.py`, `tests/dobles.py`, `tests/test_cliente_config.py`

**Interfaces:**
- Consumes: pacote `sabor_da_terra.llm` (Task 1).
- Produces:
  - `class Papel(str, Enum)` com `TRIAGEM = "triagem"`, `RESPOSTA = "resposta"`, `EMBEDDING = "embedding"`.
  - `MODELOS_PADRAO: dict[Papel, str]` e `VARIAVEIS_MODELO: dict[Papel, str]`.
  - `class LLMClient` com `__init__(modo: str | None = None, pasta_fixtures: Path | None = None, cliente=None, dormir: Callable[[float], None] = time.sleep, max_tentativas: int = 4)`, `modo: str`, `modelo(papel: Papel) -> str` e `gerar(papel: Papel, prompt: str, **config_geracao) -> str`.
  - `class FixtureAusenteError(RuntimeError)` (definida aqui; usada na Task 3).

- [ ] **Step 1: Escrever o teste que falha (configuração e erros)**

`tests/conftest.py`:

```python
import pytest

@pytest.fixture(autouse=True)
def _forcar_modo_fixture(monkeypatch):
    """A suíte nunca fala com a API, mesmo que o .env local diga 'real'."""
    monkeypatch.setenv("LLM_MODO", "fixture")
```

`tests/dobles.py`:

```python
from types import SimpleNamespace


class ModeloFake:
    def __init__(self, texto: str = "resposta fake", embedding: list[float] | None = None):
        self.texto = texto
        self.embedding = embedding or [0.1, 0.2]
        self.chamadas: list[tuple[str, str, str]] = []

    def generate_content(self, *, model: str, contents: str, config=None):
        self.chamadas.append(("gerar", model, contents))
        return SimpleNamespace(text=self.texto)

    def embed_content(self, *, model: str, contents: str, config=None):
        self.chamadas.append(("embedar", model, contents))
        return SimpleNamespace(embeddings=[SimpleNamespace(values=self.embedding)])


class ClienteFake:
    def __init__(self, modelo: ModeloFake):
        self.models = modelo
```

`tests/test_cliente_config.py`:

```python
import pytest

from sabor_da_terra.llm.cliente import LLMClient, Papel


def test_modelos_padrao_por_papel(tmp_path):
    cliente = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    assert cliente.modelo(Papel.TRIAGEM) == "gemini-3.5-flash-lite"
    assert cliente.modelo(Papel.RESPOSTA) == "gemini-3.8-flash"
    assert cliente.modelo(Papel.EMBEDDING) == "gemini-embedding-001"


def test_modelo_respeita_variavel_de_ambiente(monkeypatch, tmp_path):
    monkeypatch.setenv("MODELO_RESPOSTA", "gemini-3.6-flash")
    cliente = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    assert cliente.modelo(Papel.RESPOSTA) == "gemini-3.6-flash"


def test_modo_invalido_falha(tmp_path):
    with pytest.raises(ValueError, match="LLM_MODO"):
        LLMClient(modo="talvez", pasta_fixtures=tmp_path)


def test_modo_real_sem_chave_falha_com_instrucao(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    cliente = LLMClient(modo="real", pasta_fixtures=tmp_path)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        cliente.gerar(Papel.TRIAGEM, "oi")


def test_vertexai_sem_projeto_falha_antes_da_chamada(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    cliente = LLMClient(modo="real", pasta_fixtures=tmp_path)
    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
        cliente.gerar(Papel.TRIAGEM, "oi")
```

- [ ] **Step 2: Rodar os testes para ver falhar**

Run: `pytest tests/test_cliente_config.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` de `cliente.py`.

- [ ] **Step 3: Implementar `sabor_da_terra/llm/cliente.py`**

Assinaturas e decisões (o corpo é seu, guiado pelos testes):

```python
"""Cliente único do Gemini: escolhe modelo por papel e alterna AI Studio/Vertex AI."""

class Papel(str, Enum):
    TRIAGEM = "triagem"
    RESPOSTA = "resposta"
    EMBEDDING = "embedding"

MODELOS_PADRAO = {
    Papel.TRIAGEM: "gemini-3.5-flash-lite",
    Papel.RESPOSTA: "gemini-3.8-flash",
    Papel.EMBEDDING: "gemini-embedding-001",
}

VARIAVEIS_MODELO = {
    Papel.TRIAGEM: "MODELO_TRIAGEM",
    Papel.RESPOSTA: "MODELO_RESPOSTA",
    Papel.EMBEDDING: "MODELO_EMBEDDING",
}

class FixtureAusenteError(RuntimeError):
    """Resposta não gravada para o par (papel, prompt, config)."""

class LLMClient:
    def __init__(self, modo=None, pasta_fixtures=None, cliente=None,
                 dormir=time.sleep, max_tentativas=4) -> None: ...
    @property
    def modo(self) -> str: ...
    def modelo(self, papel: Papel) -> str: ...
    def gerar(self, papel: Papel, prompt: str, **config_geracao) -> str: ...
```

Regras de implementação:

- `modo`: `None` → `os.getenv("LLM_MODO", "real")`; aceitar só `"real"`/`"fixture"`; caso contrário `ValueError` citando `LLM_MODO`.
- `modelo(papel)`: `os.getenv(VARIAVEIS_MODELO[papel]) or MODELOS_PADRAO[papel]`.
- `gerar` em modo real: obter cliente via `_cliente_google()` (lazy), chamar
  `self._cliente.models.generate_content(model=self.modelo(papel), contents=prompt, config=types.GenerateContentConfig(**config_geracao) if config_geracao else None)` e retornar `resposta.text`.
- `_cliente_google()` **só é criado no primeiro uso** e valida a configuração antes:
  - `_usar_vertexai()` = `os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().upper() in {"TRUE", "1", "YES"}`.
  - Vertex AI sem `GOOGLE_CLOUD_PROJECT` **ou** sem `GOOGLE_CLOUD_LOCATION` → `RuntimeError` citando `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` e o `gcloud auth application-default login`.
  - Gemini API sem `GEMINI_API_KEY` nem `GOOGLE_API_KEY` → `RuntimeError` citando `GEMINI_API_KEY`, `.env.example` e `LLM_MODO=fixture`.
  - Criar `genai.Client(http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)))` — **retry interno do SDK desligado**; o retry é nosso (Task 4).
- Em modo `fixture`, `gerar` ainda não tem implementação nesta task: levante `FixtureAusenteError` com mensagem "modo fixture será implementado na próxima task" (a Task 3 substitui). Nenhum cliente Google é criado em fixture.
- `dormir` e `cliente` são injetáveis para teste; não usar `time.sleep` direto no fluxo de retry.

`sabor_da_terra/llm/__init__.py`:

```python
"""Cliente único de LLM e embeddings."""

from sabor_da_terra.llm.cliente import LLMClient, Papel

__all__ = ["LLMClient", "Papel"]
```

- [ ] **Step 4: Rodar os testes para ver passar**

Run: `pytest tests/test_cliente_config.py -v`
Expected: PASS (5 testes).

- [ ] **Step 5: Commitar**

```bash
git add sabor_da_terra/llm tests/conftest.py tests/dobles.py tests/test_cliente_config.py
git commit -m "Cliente Gemini: papéis, modelos e validação de configuração"
```

---

### Task 3: Modo fixture — gravação e replay sem rede

**Files:**
- Modify: `sabor_da_terra/llm/cliente.py`
- Create: `tests/test_cliente_fixture.py`

**Interfaces:**
- Consumes: `LLMClient`, `Papel`, `FixtureAusenteError`, `ClienteFake`/`ModeloFake` (Task 2).
- Produces:
  - `LLMClient.embedar(texto: str) -> list[float]`.
  - `LLMClient.chamadas_por_modelo() -> dict[str, int]`.
  - Layout de fixture: `tests/fixtures/llm/<papel>/<hash16>.json`; JSON com `papel`, `modelo`, `prompt_sha256`, `resposta` (texto) **ou** `valores` (embedding).
  - Chave: SHA-256 de `json.dumps({"papel", "modelo", "prompt", "config"}, sort_keys=True, ensure_ascii=False)` truncado em 16 hex.

- [ ] **Step 1: Escrever os testes que falham (fixture e embeddings)**

`tests/test_cliente_fixture.py`:

```python
import pytest

from sabor_da_terra.llm.cliente import FixtureAusenteError, LLMClient, Papel
from tests.dobles import ClienteFake, ModeloFake


def test_modo_real_grava_fixture_e_replay_reproduz(tmp_path):
    fake = ClienteFake(ModeloFake(texto="resposta gravada"))
    real = LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    assert real.gerar(Papel.TRIAGEM, "pedido de teste") == "resposta gravada"
    assert len(list(tmp_path.rglob("*.json"))) == 1

    replay = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    assert replay.gerar(Papel.TRIAGEM, "pedido de teste") == "resposta gravada"
    assert replay.chamadas_por_modelo() == {}


def test_fixture_ausente_falha_com_instrucao(tmp_path):
    cliente = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    with pytest.raises(FixtureAusenteError, match="LLM_MODO=real"):
        cliente.gerar(Papel.RESPOSTA, "prompt nunca gravado")


def test_fixture_nao_instancia_cliente_google(tmp_path, monkeypatch):
    fake = ClienteFake(ModeloFake(texto="ok"))
    LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None).gerar(
        Papel.TRIAGEM, "x"
    )

    import sabor_da_terra.llm.cliente as mod

    def explode(*args, **kwargs):
        raise AssertionError("modo fixture não pode criar cliente Google")

    monkeypatch.setattr(mod.genai, "Client", explode)
    assert LLMClient(modo="fixture", pasta_fixtures=tmp_path).gerar(Papel.TRIAGEM, "x") == "ok"


def test_embedar_usa_modelo_de_embedding_e_retorna_vetor(tmp_path):
    fake = ClienteFake(ModeloFake(embedding=[0.1, 0.2, 0.3]))
    cliente = LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    assert cliente.embedar("texto") == [0.1, 0.2, 0.3]
    assert fake.models.chamadas[-1][1] == "gemini-embedding-001"


def test_embedding_grava_e_reproduz_fixture(tmp_path):
    fake = ClienteFake(ModeloFake(embedding=[0.5, 0.6]))
    LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None).embedar("abc")
    replay = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    assert replay.embedar("abc") == [0.5, 0.6]


def test_contador_por_modelo_conta_so_sucesso(tmp_path):
    fake = ClienteFake(ModeloFake(texto="ok", embedding=[0.0]))
    cliente = LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    cliente.gerar(Papel.TRIAGEM, "a")
    cliente.gerar(Papel.TRIAGEM, "b")
    cliente.gerar(Papel.RESPOSTA, "c")
    cliente.embedar("d")
    assert cliente.chamadas_por_modelo() == {
        "gemini-3.5-flash-lite": 2,
        "gemini-3.8-flash": 1,
        "gemini-embedding-001": 1,
    }
```

- [ ] **Step 2: Rodar os testes para ver falhar**

Run: `pytest tests/test_cliente_fixture.py -v`
Expected: FAIL — `embedar`/`chamadas_por_modelo` inexistentes e fixture não implementada.

- [ ] **Step 3: Implementar fixture e embeddings em `cliente.py`**

Regras:

- `pasta_fixtures` padrão: `Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "llm"`.
- `_caminho_fixture(papel, prompt, config)` → `<pasta>/<papel.value>/<hash16>.json`.
- `_ler_fixture` → `json.loads`; ausente → `FixtureAusenteError` com o caminho e a instrução "Rode uma vez com LLM_MODO=real para gravar.".
- `_gravar_fixture` → `mkdir(parents=True, exist_ok=True)` e `json.dump(..., ensure_ascii=False, indent=2)`.
- `gerar`: em `real`, chamar a API e **gravar** `{"papel", "modelo", "prompt_sha256", "resposta"}`; em `fixture`, ler e devolver `resposta`.
- `embedar(texto)`: `modelo = self.modelo(Papel.EMBEDDING)`; em `real`, `self._cliente_google().models.embed_content(model=modelo, contents=texto)` e `[float(v) for v in resposta.embeddings[0].values]`, gravando `{"...", "valores": [...]}`; em `fixture`, ler `valores`.
- Incrementar `self._chamadas[modelo] += 1` **somente após sucesso em modo real** (fixture não incrementa).
- `chamadas_por_modelo()` devolve uma **cópia** do dicionário.

- [ ] **Step 4: Rodar os testes para ver passar**

Run: `pytest tests/test_cliente_fixture.py -v`
Expected: PASS (6 testes).

- [ ] **Step 5: Commitar**

```bash
git add sabor_da_terra/llm/cliente.py tests/test_cliente_fixture.py
git commit -m "Cliente Gemini: modo fixture com gravação e replay"
```

---

### Task 4: Retry 429 com backoff e contador consistente

**Files:**
- Modify: `sabor_da_terra/llm/cliente.py`
- Modify: `tests/dobles.py` (adicionar `Erro429`)
- Create: `tests/test_cliente_retry.py`

**Interfaces:**
- Consumes: `LLMClient` (Tasks 2–3), `ClienteFake`/`ModeloFake`.
- Produces: `_executar_com_retry` interno; comportamento observável: 429 → espera 1s, 2s, 4s… (teto 30s, `max_tentativas` total), sucesso conta 1, falha persistente levanta o último erro, erro não-429 não espera.

- [ ] **Step 1: Escrever os testes que falham (retry)**

Adicionar a `tests/dobles.py`:

```python
class Erro429(Exception):
    code = 429
```

Estender `ModeloFake.__init__` com `falhas_429: int = 0` e, no início de `generate_content`:

```python
if self.falhas_429:
    self.falhas_429 -= 1
    raise Erro429()
```

`tests/test_cliente_retry.py`:

```python
import pytest

from sabor_da_terra.llm.cliente import LLMClient, Papel
from tests.dobles import ClienteFake, Erro429, ModeloFake


def test_retry_429_com_backoff_e_uma_chamada_contada(tmp_path):
    esperas = []
    fake = ClienteFake(ModeloFake(texto="ok", falhas_429=2))
    cliente = LLMClient(
        modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=esperas.append
    )
    assert cliente.gerar(Papel.TRIAGEM, "x") == "ok"
    assert esperas == [1.0, 2.0]
    assert cliente.chamadas_por_modelo() == {"gemini-3.5-flash-lite": 1}


def test_retry_esgotado_levanta_ultimo_erro_e_nao_conta(tmp_path):
    esperas = []
    fake = ClienteFake(ModeloFake(falhas_429=99))
    cliente = LLMClient(
        modo="real",
        pasta_fixtures=tmp_path,
        cliente=fake,
        dormir=esperas.append,
        max_tentativas=3,
    )
    with pytest.raises(Erro429):
        cliente.gerar(Papel.TRIAGEM, "x")
    assert esperas == [1.0, 2.0]
    assert cliente.chamadas_por_modelo() == {}


def test_erro_nao_429_nao_repete(tmp_path):
    esperas = []
    modelo = ModeloFake()

    class Erro400(Exception):
        code = 400

    def falha(**kwargs):
        raise Erro400()

    modelo.generate_content = falha
    cliente = LLMClient(
        modo="real", pasta_fixtures=tmp_path, cliente=ClienteFake(modelo), dormir=esperas.append
    )
    with pytest.raises(Erro400):
        cliente.gerar(Papel.TRIAGEM, "x")
    assert esperas == []
```

- [ ] **Step 2: Rodar os testes para ver falhar**

Run: `pytest tests/test_cliente_retry.py -v`
Expected: FAIL — nenhum retry; `esperas` vazio e `Erro429` propaga na primeira tentativa.

- [ ] **Step 3: Implementar o retry em `cliente.py`**

```python
from typing import Any, Callable

def _executar_com_retry(self, papel: Papel, acao: Callable[[], Any]) -> Any:
    tentativa = 1
    while True:
        try:
            return acao()
        except Exception as exc:
            if getattr(exc, "code", None) != 429 or tentativa >= self._max_tentativas:
                raise
            self._dormir(min(30.0, 1.0 * (2 ** (tentativa - 1))))
            tentativa += 1
```

- Envolver **apenas** a chamada HTTP (generate/embed) no retry; gravação de fixture e incremento do contador ficam **depois** do sucesso.
- Não capturar exceções de configuração (`RuntimeError` de chave/projeto) — elas não têm `.code`.
- Manter o retry interno do SDK desligado (`attempts=1`), para não duplicar tentativas.

- [ ] **Step 4: Rodar a suíte inteira**

Run: `pytest -v`
Expected: PASS (todos os testes das tasks 1–4).

- [ ] **Step 5: Commitar**

```bash
git add sabor_da_terra/llm/cliente.py tests/dobles.py tests/test_cliente_retry.py
git commit -m "Cliente Gemini: retry 429 com backoff e contador por modelo"
```

---

### Task 5: Script de fumaça e tela "olá" do Streamlit

**Files:**
- Create: `scripts/__init__.py`, `scripts/smoke_llm.py`
- Modify: `app.py`
- Create: `tests/test_ambiente_local.py`

**Interfaces:**
- Consumes: `LLMClient`, `Papel` (Tasks 2–4).
- Produces: `python -m scripts.smoke_llm` (3 chamadas reais: Flash-Lite, Flash, embedding) e `streamlit run app.py` (tela "Sabor da Terra — Assistente").

- [ ] **Step 1: Escrever os testes que falham (entradas locais)**

`tests/test_ambiente_local.py`:

```python
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_smoke_usa_os_tres_papeis():
    texto = (RAIZ / "scripts" / "smoke_llm.py").read_text()
    for papel in ["Papel.TRIAGEM", "Papel.RESPOSTA", "Papel.EMBEDDING"]:
        assert papel in texto
    assert "load_dotenv()" in texto


def test_app_streamlit_tem_titulo():
    texto = (RAIZ / "app.py").read_text()
    assert "st.set_page_config(" in texto
    assert "Sabor da Terra — Assistente" in texto
```

- [ ] **Step 2: Rodar os testes para ver falhar**

Run: `pytest tests/test_ambiente_local.py -v`
Expected: FAIL — `scripts/smoke_llm.py` não existe (e `app.py` ainda sem `set_page_config`).

- [ ] **Step 3: Implementar**

`scripts/__init__.py`: vazio.

`scripts/smoke_llm.py` — estrutura:

```python
"""Teste de fumaça real: Flash-Lite, Flash e embedding. Gasta cota mínima."""

def main() -> int:
    load_dotenv()
    os.environ["LLM_MODO"] = "real"
    cliente = LLMClient()
    try:
        triagem = cliente.gerar(Papel.TRIAGEM, "Responda apenas: ok")
        resposta = cliente.gerar(Papel.RESPOSTA, "Responda apenas: ok")
        vetor = cliente.embedar("teste de embedding")
    except RuntimeError as exc:
        print(f"FALHOU: {exc}")
        return 1
    print(f"Flash-Lite: {triagem!r}")
    print(f"Flash: {resposta!r}")
    print(f"Embedding: {len(vetor)} dimensões")
    print(f"Chamadas por modelo: {cliente.chamadas_por_modelo()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

`app.py` (versão final da etapa):

```python
"""Tela mínima para validar o ambiente (a interface conversacional vem na etapa 13)."""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Sabor da Terra — Assistente", page_icon="🌱")
st.title("Sabor da Terra — Assistente")
st.caption(f"LLM_MODO={os.getenv('LLM_MODO', 'real')}")
st.write("Ambiente pronto. A interface conversacional chega na etapa 13.")
```

- [ ] **Step 4: Rodar os testes para ver passar**

Run: `pytest tests/test_ambiente_local.py -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Teste de fumaça real (requer chave no `.env`)**

Run: `python -m scripts.smoke_llm`
Expected (com chave válida):

```
Flash-Lite: 'ok'          # ou variação curta
Flash: 'ok'               # ou variação curta
Embedding: 3072 dimensões  # gemini-embedding-001
Chamadas por modelo: {'gemini-3.5-flash-lite': 1, 'gemini-3.8-flash': 1, 'gemini-embedding-001': 1}
```

Depois, `streamlit run app.py` → navegador mostra "Sabor da Terra — Assistente" e `LLM_MODO=real`.
Se a chave ainda não existir, executar assim que a entrada humana 1 chegar; registrar a saída na issue.

- [ ] **Step 6: Commitar**

```bash
git add scripts app.py tests/test_ambiente_local.py
git commit -m "Ambiente: script de fumaça e app Streamlit de validação"
```

---

### Task 6: Documentação ("Como rodar"), limites confirmados e checagem de segredos

**Files:**
- Modify: `README.md`
- Modify: `docs/03-diretriz-arquitetura.md`
- Create: `tests/test_documentacao.py`

**Interfaces:**
- Consumes: tudo das tasks anteriores; **entrada humana 2** (números de RPM/RPD/TPM).
- Produces: README com seção "Como rodar", estrutura atualizada, documentação da troca para Vertex AI e do modo fixture; `docs/03` com a subseção "Limites confirmados no projeto".

- [ ] **Step 1: Escrever os testes que falham (documentação e segurança)**

`tests/test_documentacao.py`:

```python
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_readme_tem_como_rodar():
    texto = (RAIZ / "README.md").read_text()
    assert "## Como rodar" in texto
    for comando in ["python -m scripts.smoke_llm", "streamlit run app.py", "pytest"]:
        assert comando in texto
    assert "LLM_MODO=fixture" in texto


def test_docs03_registra_limites_com_data():
    texto = (RAIZ / "docs" / "03-diretriz-arquitetura.md").read_text()
    assert "Limites confirmados no projeto" in texto
    assert re.search(r"em \d{2}/\d{2}/\d{4}", texto)


def test_env_nao_e_rastreado_pelo_git():
    resultado = subprocess.run(
        ["git", "check-ignore", "-q", ".env"], cwd=RAIZ
    )
    assert resultado.returncode == 0


def test_historico_nao_tem_chave_gemini():
    saida = subprocess.run(
        ["git", "log", "-p", "--all"], cwd=RAIZ, capture_output=True, text=True
    ).stdout
    assert not re.search(r"AIza[0-9A-Za-z_-]{30,}", saida)
```

- [ ] **Step 2: Rodar os testes para ver falhar**

Run: `pytest tests/test_documentacao.py -v`
Expected: FAIL — README sem "Como rodar", `docs/03` sem a subseção, `.gitignore` sem `.llama_index/` (se a Task 1 não cobriu) etc.

- [ ] **Step 3: Atualizar o README**

Acrescentar a estrutura de arquivos real (a da seção "Estrutura de arquivos" deste plano) e a seção:

```markdown
## Como rodar

Requisitos: Python 3.11+ e Git. Nenhuma conta Google Cloud é necessária no protótipo.

1. Clone o repositório e entre na pasta.
2. Crie o ambiente virtual e instale as dependências:
   `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e preencha **GEMINI_API_KEY** com a chave
   restrita criada no [Google AI Studio](https://aistudio.google.com) (nunca commite o `.env`).
4. Valide o ambiente com o teste de fumaça (3 chamadas reais):
   `python -m scripts.smoke_llm`
5. Abra a tela de validação: `streamlit run app.py`
6. Rode os testes (100% offline, sem gastar cota): `pytest`

**Modo fixture:** com `LLM_MODO=fixture`, o cliente reutiliza as respostas gravadas em
`tests/fixtures/llm/` e não faz nenhuma chamada à API. Para regravar uma resposta,
rode uma vez com `LLM_MODO=real` — o cliente grava a fixture automaticamente.

**Vertex AI:** para trocar AI Studio por Vertex AI basta configurar no `.env`:
`GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT` e `GOOGLE_CLOUD_LOCATION`,
e autenticar com `gcloud auth application-default login`. Nenhuma linha de código muda.
```

- [ ] **Step 4: Registrar os limites confirmados no `docs/03`**

Pedir à pessoa responsável os números de **AI Studio → Usage and billing** e inserir, após a tabela "Divisão de trabalho entre modelos":

```markdown
### Limites confirmados no projeto

> Consulta em AI Studio → Usage and billing em **DD/MM/AAAA**. Limites variam por
> projeto e modelo; reconfirmar antes da semana de ajuste fino (#14).

| Modelo | RPM | RPD | TPM | Observação |
|---|---|---|---|---|
| Gemini Flash-Lite (`gemini-3.5-flash-lite`) | valor | valor | valor | valor |
| Gemini Flash (`gemini-3.8-flash`) | valor | valor | valor | valor |
| Gemini Embedding (`gemini-embedding-001`) | valor | valor | valor | valor |
```

Sem os números reais, a task **para** e pede a entrada humana 2 — não preencher com estimativas.

- [ ] **Step 5: Rodar os testes para ver passar**

Run: `pytest tests/test_documentacao.py -v`
Expected: PASS (4 testes).

- [ ] **Step 6: Commitar**

```bash
git add README.md docs/03-diretriz-arquitetura.md tests/test_documentacao.py
git commit -m "Documentação: como rodar, limites confirmados e checagem de segredos"
```

---

### Task 7: Evidências, issue e PR

**Files:**
- Modify: corpo da issue #3 (checkboxes), comentários.

**Interfaces:**
- Consumes: todas as tasks; entradas humanas 1–3.
- Produces: PR `etapa-3/ambiente-gemini` com `Closes #3`, evidências anexadas à issue.

- [ ] **Step 1: Rodar a suíte completa e capturar a saída**

Run: `pytest -v`
Expected: PASS, 0 falhas.

- [ ] **Step 2: Confirmar que a suíte não faz rede**

Run: `LLM_MODO=fixture pytest -v`
Expected: PASS, 0 falhas, sem tempo de espera de API.

- [ ] **Step 3: Confirmar ausência de chave no histórico**

Run: `git log -p --all | grep -E "AIza[0-9A-Za-z_-]{30,}" || echo "nenhuma chave no histórico"`
Expected: `nenhuma chave no histórico`.

- [ ] **Step 4: Comentar na issue #3 com as evidências**

Comentário com: saída do smoke real (`python -m scripts.smoke_llm`), resultado do `pytest`, confirmação da chave restrita, tabela de limites do `docs/03`, e a resposta da Sauter (ou "sem resposta até DD/MM").

- [ ] **Step 5: Validação por integrante independente**

Pedir a um integrante que **não participou da etapa** para seguir **somente o README** (clone → `.env` → `pip install` → `python -m scripts.smoke_llm`) e registrar o resultado na issue. Se falhar, corrigir o README e repetir.

- [ ] **Step 6: Criar o PR**

```bash
git push -u origin etapa-3/ambiente-gemini
gh pr create --title "Ambiente de desenvolvimento e acesso à API Gemini" \
  --body "Closes #3

- Estrutura, dependências fixadas e configuração (.env.example, .gitignore)
- Cliente Gemini por papel, retry 429, contador e modo fixture
- Teste de fumaça e tela Streamlit de validação
- README com 'Como rodar' e docs/03 com limites confirmados
- Nenhuma chave no histórico do git"
```

- [ ] **Step 7: Marcar as tarefas concluídas na issue e aguardar revisão**

Editar o corpo da issue marcando `[x]` nos itens verificados; deixar desmarcado apenas o que depender de resposta externa (ex.: resposta da Sauter).

---

## Review Focus

Os cinco modos de falha que o spec implica e que os testes das tasks precisam cobrir:

1. **Chave ausente/inválida em modo real** → erro claro com instrução (`GEMINI_API_KEY`, `.env`, `LLM_MODO=fixture`), nunca stack trace de autenticação. *Teste: `test_modo_real_sem_chave_falha_com_instrucao` (Task 2).*
2. **Fixture ausente em modo fixture** → `FixtureAusenteError` instrutivo; jamais cair silenciosamente para a API. *Teste: `test_fixture_ausente_falha_com_instrucao` (Task 3).*
3. **429 persistente** → backoff limitado, erro final claro e contador sem contar falha; nada de loop infinito. *Testes: `test_retry_esgotado_levanta_ultimo_erro_e_nao_conta` (Task 4).*
4. **Vertex AI ativado sem projeto/localização** → erro explícito antes da chamada, citando as variáveis e o ADC. *Teste: `test_vertexai_sem_projeto_falha_antes_da_chamada` (Task 2).*
5. **Chave acidental no repositório/histórico** → `.env` ignorado e varredura do histórico sem padrão `AIza…`. *Testes: `test_env_nao_e_rastreado_pelo_git` e `test_historico_nao_tem_chave_gemini` (Task 6).*
