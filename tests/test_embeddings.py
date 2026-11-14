"""Testes da geração de embeddings com cache e sanitização."""

import pytest

from sabor_da_terra.rag.embeddings import GeradorEmbeddings
from sabor_da_terra.rag.indexar import preparar_nos


class ClienteSimulado:
    """Simula a geração de embeddings sem acessar o Gemini."""

    def __init__(self):
        self.chamadas = 0
        self.textos_recebidos = []

    def embedar(self, texto: str) -> list[float]:
        self.chamadas += 1
        self.textos_recebidos.append(texto)

        return [0.1, 0.2, 0.3]


@pytest.fixture
def cliente():
    return ClienteSimulado()


@pytest.fixture
def gerador(cliente, tmp_path):
    return GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=tmp_path / "embeddings.json",
    )


def test_gerar_embedding(gerador, cliente):
    vetor = gerador.gerar("Certificação orgânica válida")

    assert vetor == [0.1, 0.2, 0.3]
    assert cliente.chamadas == 1


def test_reutilizar_embedding_do_cache(gerador, cliente):
    primeiro = gerador.gerar("Certificação orgânica válida")
    segundo = gerador.gerar("Certificação orgânica válida")

    assert primeiro == segundo
    assert cliente.chamadas == 1


def test_cache_persistente_entre_instancias(cliente, tmp_path):
    caminho = tmp_path / "embeddings.json"

    primeiro_gerador = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=caminho,
    )

    primeiro_gerador.gerar("Frango caipira sem SIE")
    primeiro_gerador.cache.gravar()

    segundo_gerador = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=caminho,
    )

    segundo_gerador.gerar("Frango caipira sem SIE")

    assert cliente.chamadas == 1


def test_texto_diferente_gera_novo_embedding(gerador, cliente):
    gerador.gerar("Certificação válida")
    gerador.gerar("Certificação vencida")

    assert cliente.chamadas == 2


def test_sanitizar_antes_de_enviar(gerador, cliente):
    documento = {
        "arquivo": "contrato_teste.txt",
        "tipo_documento": "contrato",
        "caminho": "contratos/contrato_teste.txt",
        "texto": "FISCAIS DO CONTRATO:\n  Titular: Ana - CPF: 123.456.789-00",
    }

    nos = preparar_nos([documento], gerador)

    assert cliente.chamadas == 1
    assert "123.456.789-00" not in cliente.textos_recebidos[0]
    assert "123.456.789-00" not in nos[0].text


def test_texto_vazio_nao_gera_embedding(gerador, cliente):
    with pytest.raises(ValueError):
        gerador.gerar("   ")

    assert cliente.chamadas == 0


def test_cache_considera_modelo(cliente, tmp_path):
    caminho = tmp_path / "embeddings.json"

    gerador_a = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=caminho,
        modelo="modelo-a",
    )

    gerador_b = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=caminho,
        modelo="modelo-b",
    )

    gerador_a.gerar("Documento de teste")
    gerador_b.gerar("Documento de teste")

    assert cliente.chamadas == 2
