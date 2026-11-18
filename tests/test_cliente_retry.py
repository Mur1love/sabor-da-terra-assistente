from types import SimpleNamespace

import httpx

import pytest

from sabor_da_terra.llm.cliente import LLMClient, Papel
from tests.dobles import ClienteFake, Erro429, Erro503, Erro504, ModeloFake

VARIAVEL_FALLBACK = "GEMINI_MODELO_RESPOSTA_FALLBACK"


class ModeloCotaPorModelo:
    """Falha 429 apenas para o modelo principal; o fallback responde."""

    def generate_content(self, *, model, contents, config=None):
        if model == "gemini-3.8-flash":
            raise Erro429()
        return SimpleNamespace(text="ok do fallback")


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


# ---------------------------------------------------------------------------
# Failover: cota do principal esgotou → retoma no modelo de fallback
# ---------------------------------------------------------------------------


def test_failover_resposta_quando_a_cota_do_principal_acaba(tmp_path, monkeypatch):
    monkeypatch.setenv(VARIAVEL_FALLBACK, "gemini-3.5-flash-lite")
    esperas = []
    cliente = LLMClient(
        modo="real",
        pasta_fixtures=tmp_path,
        cliente=ClienteFake(ModeloCotaPorModelo()),
        dormir=esperas.append,
    )
    resposta = cliente.gerar(Papel.RESPOSTA, "x")
    assert resposta.text == "ok do fallback"
    assert esperas == [10.0, 20.0, 40.0]  # o principal esgotou as 4 tentativas
    assert cliente.chamadas_por_modelo() == {"gemini-3.5-flash-lite": 1}
    assert cliente.failovers() == 1


def test_sem_fallback_configurado_o_erro_propaga(tmp_path, monkeypatch):
    monkeypatch.delenv(VARIAVEL_FALLBACK, raising=False)
    esperas = []
    cliente = LLMClient(
        modo="real",
        pasta_fixtures=tmp_path,
        cliente=ClienteFake(ModeloFake(falhas_429=99)),
        dormir=esperas.append,
        max_tentativas=2,
    )
    with pytest.raises(Erro429):
        cliente.gerar(Papel.RESPOSTA, "x")
    assert cliente.failovers() == 0


def test_failover_nao_dispara_em_erro_nao_transitorio(tmp_path, monkeypatch):
    monkeypatch.setenv(VARIAVEL_FALLBACK, "gemini-3.5-flash-lite")

    class Erro400(Exception):
        code = 400

    class Modelo400:
        def generate_content(self, *, model, contents, config=None):
            raise Erro400()

    esperas = []
    cliente = LLMClient(
        modo="real", pasta_fixtures=tmp_path, cliente=ClienteFake(Modelo400()), dormir=esperas.append
    )
    with pytest.raises(Erro400):
        cliente.gerar(Papel.RESPOSTA, "x")
    assert esperas == []  # 400 não é nem repetido
    assert cliente.failovers() == 0


def test_failover_e_exclusivo_do_papel_resposta(tmp_path, monkeypatch):
    """O fallback é da composição: a triagem esgotada propaga o erro."""
    monkeypatch.setenv(VARIAVEL_FALLBACK, "gemini-3.5-flash-lite")

    class ModeloSempre429:
        def generate_content(self, *, model, contents, config=None):
            raise Erro429()

    cliente = LLMClient(
        modo="real",
        pasta_fixtures=tmp_path,
        cliente=ClienteFake(ModeloSempre429()),
        dormir=lambda _s: None,
        max_tentativas=2,
    )
    with pytest.raises(Erro429):
        cliente.gerar(Papel.TRIAGEM, "x")
    assert cliente.failovers() == 0


class ModeloTimeoutNoPrincipal:
    """O principal trava até o timeout do cliente (ReadTimeout, sem código HTTP)."""

    def __init__(self):
        self.modelos: list[str] = []

    def generate_content(self, *, model, contents, config=None):
        self.modelos.append(model)
        if model == "gemini-3.8-flash":
            raise httpx.ReadTimeout("The read operation timed out")
        return SimpleNamespace(text="ok do fallback")


def test_failover_resposta_quando_o_principal_estoura_o_timeout(tmp_path, monkeypatch):
    """Visto ao vivo em 18/11/2026: ReadTimeout no Flash fechava o turno sem resposta."""
    monkeypatch.setenv(VARIAVEL_FALLBACK, "gemini-3.5-flash-lite")
    esperas = []
    modelo = ModeloTimeoutNoPrincipal()
    cliente = LLMClient(modo="real", pasta_fixtures=tmp_path, cliente=ClienteFake(modelo), dormir=esperas.append)
    assert cliente.gerar(Papel.RESPOSTA, "x").text == "ok do fallback"
    assert esperas == []  # timeout não repete no mesmo modelo: já custou o prazo inteiro
    assert modelo.modelos == ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
    assert cliente.failovers() == 1


def test_timeout_sem_fallback_propaga(tmp_path, monkeypatch):
    monkeypatch.delenv(VARIAVEL_FALLBACK, raising=False)
    cliente = LLMClient(
        modo="real", pasta_fixtures=tmp_path, cliente=ClienteFake(ModeloTimeoutNoPrincipal()), dormir=lambda _s: None
    )
    with pytest.raises(httpx.ReadTimeout):
        cliente.gerar(Papel.RESPOSTA, "x")
    assert cliente.failovers() == 0
