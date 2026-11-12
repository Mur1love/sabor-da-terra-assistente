import pytest


@pytest.fixture(autouse=True)
def _forcar_modo_fixture(monkeypatch):
    """A suíte nunca fala com a API, mesmo que o .env local diga 'real'."""
    monkeypatch.setenv("LLM_MODO", "fixture")
