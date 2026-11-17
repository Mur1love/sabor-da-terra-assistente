from types import SimpleNamespace

import pytest

from sabor_da_terra.llm.cliente import LLMClient, Papel
from tests.dobles import ClienteFake, Erro429, Erro503, Erro504, ModeloFake


def test_retry_429_com_backoff_e_uma_chamada_contada(tmp_path):
    esperas = []
    fake = ClienteFake(ModeloFake(texto="ok", falhas_429=2))
    cliente = LLMClient(
        modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=esperas.append
    )
    assert cliente.gerar(Papel.TRIAGEM, "x").text == "ok"
    assert esperas == [10.0, 20.0]
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
    assert esperas == [10.0, 20.0]
    assert cliente.chamadas_por_modelo() == {}


def test_erro_400_nao_repete(tmp_path):
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


def test_retry_503_com_backoff(tmp_path):
    esperas = []
    fake = ClienteFake(ModeloFake(texto="ok", falhas_429=2))
    fake.models.falhas_429 = 0  # o 503 é simulado por instável próprio abaixo

    class ModeloInstavel:
        def __init__(self):
            self.falhas = 2

        def generate_content(self, *, model, contents, config=None):
            if self.falhas:
                self.falhas -= 1
                raise Erro503()
            return SimpleNamespace(text="ok")

    fake = ClienteFake(ModeloInstavel())
    cliente = LLMClient(
        modo="real", pasta_fixtures=tmp_path, cliente=fake, dormir=esperas.append
    )
    assert cliente.gerar(Papel.TRIAGEM, "x").text == "ok"
    assert esperas == [10.0, 20.0]
    assert cliente.chamadas_por_modelo() == {"gemini-3.5-flash-lite": 1}


def test_retry_504_com_backoff(tmp_path):
    """504 DEADLINE_EXCEEDED é transitório como 503 (visto na fumaça de 16/11)."""
    esperas = []

    class ModeloInstavel:
        def __init__(self):
            self.falhas = 2

        def generate_content(self, *, model, contents, config=None):
            if self.falhas:
                self.falhas -= 1
                raise Erro504()
            return SimpleNamespace(text="ok")

    cliente = LLMClient(
        modo="real", pasta_fixtures=tmp_path, cliente=ClienteFake(ModeloInstavel()), dormir=esperas.append
    )
    assert cliente.gerar(Papel.RESPOSTA, "x").text == "ok"
    assert esperas == [10.0, 20.0]
    assert cliente.chamadas_por_modelo() == {"gemini-3.8-flash": 1}
