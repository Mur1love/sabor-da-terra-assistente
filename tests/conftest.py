import pytest


@pytest.fixture(autouse=True)
def _forcar_modo_fixture(monkeypatch):
    """A suíte nunca fala com a API, mesmo que o .env local diga 'real'."""
    monkeypatch.setenv("LLM_MODO", "fixture")
    # O smoke_llm carrega o .env no import (test_ambiente_local), e o .env da
    # máquina não pode trocar os modelos que a suíte espera por padrão.
    for variavel in (
        "GEMINI_MODELO_TRIAGEM",
        "GEMINI_MODELO_RESPOSTA",
        "GEMINI_MODEL_EMBEDDING",
        "GEMINI_MODELO_RESPOSTA_FALLBACK",
    ):
        monkeypatch.delenv(variavel, raising=False)
