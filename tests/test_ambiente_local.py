from tests.dobles import ClienteFake, ModeloFake
from sabor_da_terra.llm.cliente import LLMClient


def test_fumaca_faz_as_tres_chamadas(tmp_path, capsys):
    """A fumaça é comportamento: 1 gerar por papel (triagem/resposta) + 1 embedar.

    Substitui o teste que só conferia strings dentro do arquivo — proteger
    pouco. O import do módulo garante que o script existe e roda de verdade.
    """
    from scripts.smoke_llm import rodar

    fake = ClienteFake(ModeloFake(texto="ok", embedding=[0.1, 0.2, 0.3]))
    cliente = LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    assert rodar(cliente) == 0

    acoes = [acao for acao, _, _ in fake.models.chamadas]
    modelos = [modelo for _, modelo, _ in fake.models.chamadas]
    assert acoes == ["gerar", "gerar", "embedar"]
    assert modelos == ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-embedding-001"]

    saida = capsys.readouterr().out
    assert "[1/3] triagem" in saida
    assert "[2/3] resposta" in saida
    assert "[3/3] embedding" in saida
    assert "Flash-Lite: 'ok'" in saida
    assert "Flash: 'ok'" in saida
    assert "Embedding: 3 dimensões" in saida
    assert "Chamadas por modelo" in saida


def test_fumaca_reporta_falha_da_api_sem_traceback(monkeypatch, capsys):
    """Erro da API do Google (chave inválida, cota) sai como FALHOU, sem traceback.

    O erro do SDK do Google não é RuntimeError — o except precisa ser genérico.
    """
    import scripts.smoke_llm as smoke

    class ChaveInvalida(Exception):
        pass

    def explode(_cliente):
        raise ChaveInvalida("API key not valid. Please check a valid API key.")

    monkeypatch.setattr(smoke, "rodar", explode)
    assert smoke.main() == 1
    saida = capsys.readouterr().out
    assert saida.startswith("FALHOU: ChaveInvalida")
    assert "API key not valid" in saida


def test_app_streamlit_importa_e_executa_sem_quebrar():
    """app.py roda de verdade na importação (bare mode) — não é só texto no arquivo."""
    import app  # noqa: F401 — executar st.set_page_config/st.title aqui é o teste
