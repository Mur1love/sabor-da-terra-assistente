import pytest

from sabor_da_terra.llm.cliente import LLMClient, Papel


def test_modelos_padrao_por_papel(tmp_path):
    cliente = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    assert cliente.modelo(Papel.TRIAGEM) == "gemini-3.5-flash-lite"
    assert cliente.modelo(Papel.RESPOSTA) == "gemini-3.8-flash"
    assert cliente.modelo(Papel.EMBEDDING) == "gemini-embedding-001"


def test_modelo_respeita_variavel_de_ambiente(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_MODELO_RESPOSTA", "gemini-3.6-flash")
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
