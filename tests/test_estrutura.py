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
        "GEMINI_MODEL_FLASH_LITE",
        "GEMINI_MODEL_FLASH",
        "GEMINI_MODEL_EMBEDDING",
        "LLM_MODO",
        "RAG_INDEX_DIR",
    ]:
        assert f"{chave}=" in texto


def test_gitignore_ignora_env_e_indice_vetorial():
    texto = (RAIZ / ".gitignore").read_text()
    assert ".env" in texto
    assert ".llama_index/" in texto
    assert ".rag_index/" in texto


def test_app_tem_tela_ola():
    texto = (RAIZ / "app.py").read_text()
    assert "st.title(" in texto
    assert "Sabor da Terra" in texto
