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


def test_resposta_sem_texto_falha_sem_gravar_fixture_nem_contar(tmp_path):
    fake = ClienteFake(ModeloFake(texto=None))
    cliente = LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    with pytest.raises(RuntimeError, match="sem texto"):
        cliente.gerar(Papel.RESPOSTA, "x")
    assert not list(tmp_path.rglob("*.json"))
    assert cliente.chamadas_por_modelo() == {}


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
