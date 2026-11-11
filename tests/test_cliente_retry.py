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
