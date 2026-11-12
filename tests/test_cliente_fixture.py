import pytest
from google.genai import types

from sabor_da_terra.llm.cliente import FixtureAusenteError, LLMClient, Papel
from tests.dobles import ClienteFake, ModeloFake


def test_modo_gravar_grava_resposta_completa_e_replay_reproduz(tmp_path):
    fake = ClienteFake(ModeloFake(texto="resposta gravada"))
    gravar = LLMClient(modo="gravar", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    assert gravar.gerar(Papel.TRIAGEM, "pedido de teste").text == "resposta gravada"
    assert len(list(tmp_path.rglob("*.json"))) == 1

    replay = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    assert replay.gerar(Papel.TRIAGEM, "pedido de teste").text == "resposta gravada"
    assert replay.chamadas_por_modelo() == {}


def test_modo_real_nao_grava_fixture(tmp_path):
    # demo e triagem chamam em modo real: nada pode sujar o repositório
    fake = ClienteFake(ModeloFake(texto="resposta real"))
    real = LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    assert real.gerar(Papel.TRIAGEM, "mensagem da demo").text == "resposta real"
    assert not list(tmp_path.rglob("*.json"))


def test_fixture_ausente_falha_com_instrucao(tmp_path):
    cliente = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    with pytest.raises(FixtureAusenteError, match="LLM_MODO=gravar"):
        cliente.gerar(Papel.RESPOSTA, "prompt nunca gravado")


def test_fixture_nao_instancia_cliente_google(tmp_path, monkeypatch):
    fake = ClienteFake(ModeloFake(texto="ok"))
    LLMClient(modo="gravar", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None).gerar(
        Papel.TRIAGEM, "x"
    )

    import sabor_da_terra.llm.cliente as mod

    def explode(*args, **kwargs):
        raise AssertionError("modo fixture não pode criar cliente Google")

    monkeypatch.setattr(mod.genai, "Client", explode)
    assert LLMClient(modo="fixture", pasta_fixtures=tmp_path).gerar(Papel.TRIAGEM, "x").text == "ok"


def test_gerar_aceita_historico_e_response_schema(tmp_path):
    """Etapas 9 e 12 dependem disso: histórico em lista e schema do SDK no config.

    Antes da correção, o hash do fixture quebrava com `types.Schema` e o
    prompt só aceitava string.
    """
    fake = ClienteFake(ModeloFake(texto='{"tipo": "pedido"}'))
    cliente = LLMClient(modo="gravar", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    historico = [
        types.Content(role="user", parts=[types.Part(text="bom dia")]),
        types.Content(role="model", parts=[types.Part(text="Olá! Como posso ajudar?")]),
        "novo pedido: 10 kg de banana",
    ]
    config = {
        "response_mime_type": "application/json",
        "response_schema": types.Schema(type="OBJECT"),
    }
    resposta = cliente.gerar(Papel.TRIAGEM, historico, **config)
    assert resposta.text == '{"tipo": "pedido"}'
    assert fake.models.chamadas[-1][2] == historico

    replay = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    assert replay.gerar(Papel.TRIAGEM, historico, **config).text == '{"tipo": "pedido"}'


def test_replay_preserva_function_call_da_resposta(tmp_path):
    """Etapa 12: resposta com function call não tem texto — e não pode virar erro."""
    fake = ClienteFake(
        ModeloFake(texto=None, function_call={"name": "registrar_pedido", "args": {"produto": "banana"}})
    )
    gravar = LLMClient(modo="gravar", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    assert gravar.gerar(Papel.RESPOSTA, "registrar").text is None

    replay = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    de_novo = replay.gerar(Papel.RESPOSTA, "registrar")
    assert de_novo.function_calls[0].name == "registrar_pedido"
    assert de_novo.function_calls[0].args == {"produto": "banana"}


def test_resposta_sem_texto_retorna_completa_e_grava(tmp_path):
    fake = ClienteFake(ModeloFake(texto=None))
    gravar = LLMClient(modo="gravar", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    assert gravar.gerar(Papel.RESPOSTA, "x").text is None

    # a resposta inteira foi gravada — nada de "None" perdido no arquivo
    replay = LLMClient(modo="fixture", pasta_fixtures=tmp_path)
    assert replay.gerar(Papel.RESPOSTA, "x").text is None


def test_embedar_usa_modelo_de_embedding_e_retorna_vetor(tmp_path):
    fake = ClienteFake(ModeloFake(embedding=[0.1, 0.2, 0.3]))
    cliente = LLMClient(modo="gravar", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None)
    assert cliente.embedar("texto") == [0.1, 0.2, 0.3]
    assert fake.models.chamadas[-1][1] == "gemini-embedding-001"


def test_embedding_grava_e_reproduz_fixture(tmp_path):
    fake = ClienteFake(ModeloFake(embedding=[0.5, 0.6]))
    LLMClient(modo="gravar", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda s: None).embedar(
        "abc"
    )
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
