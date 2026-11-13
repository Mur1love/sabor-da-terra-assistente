"""Testes da indexação documental persistente."""

from pathlib import Path

import pytest

from sabor_da_terra.rag.indexar import (
    construir_indice,
    indexar,
    preparar_nos,
)
from sabor_da_terra.rag.embeddings import GeradorEmbeddings


class ClienteSimulado:
    """Cliente de embeddings determinístico, sem chamadas externas."""

    def __init__(self):
        self.chamadas = 0

    def embedar(self, texto: str) -> list[float]:
        self.chamadas += 1

        return [
            float(len(texto) % 101) / 101,
            float(sum(map(ord, texto)) % 103) / 103,
            0.5,
        ]


@pytest.fixture
def documentos():
    return [
        {
            "arquivo": "cert_organica_P002.txt",
            "tipo_documento": "certificacao",
            "caminho": "certificacoes/cert_organica_P002.txt",
            "texto": (
                "CERTIFICAÇÃO ORGÂNICA\n\n"
                "Produtor: P002\n"
                "Produtos: Mel silvestre\n"
                "Data de Validade: 30/09/2026"
            ),
        }
    ]


@pytest.fixture
def cliente():
    return ClienteSimulado()


@pytest.fixture
def gerador(cliente, tmp_path):
    return GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=tmp_path / "embeddings.json",
    )


def test_preparar_nos(documentos, gerador):
    nos = preparar_nos(documentos, gerador)

    assert len(nos) > 0
    assert all(no.text.strip() for no in nos)
    assert all(no.embedding is not None for no in nos)


def test_preservar_metadados(documentos, gerador):
    nos = preparar_nos(documentos, gerador)

    for no in nos:
        assert no.metadata["arquivo"] == (
            "cert_organica_P002.txt"
        )
        assert no.metadata["tipo_documento"] == "certificacao"
        assert no.metadata["produtor_id"] == "P002"


def test_construir_indice(documentos, gerador, tmp_path):
    pasta = tmp_path / "indice"

    indice = construir_indice(
        documentos,
        gerador,
        pasta,
    )

    assert indice is not None
    assert (pasta / "docstore.json").exists()
    assert (pasta / "index_store.json").exists()


def test_reindexacao_reutiliza_cache(
    documentos,
    gerador,
    cliente,
    tmp_path,
):
    pasta = tmp_path / "indice"

    construir_indice(documentos, gerador, pasta)

    chamadas_primeira = cliente.chamadas

    construir_indice(documentos, gerador, pasta)

    assert chamadas_primeira > 0
    assert cliente.chamadas == chamadas_primeira


def test_cache_persistente_entre_execucoes(
    documentos,
    cliente,
    tmp_path,
):
    caminho_cache = tmp_path / "embeddings.json"
    pasta_indice = tmp_path / "indice"

    primeiro = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=caminho_cache,
    )

    construir_indice(
        documentos,
        primeiro,
        pasta_indice,
    )

    chamadas_anteriores = cliente.chamadas

    segundo = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=caminho_cache,
    )

    construir_indice(
        documentos,
        segundo,
        pasta_indice,
    )

    assert cliente.chamadas == chamadas_anteriores


def test_indexar_documentos_reais_sem_api(
    cliente,
    tmp_path,
):
    raiz = Path(__file__).resolve().parents[1]

    indice = indexar(
        cliente=cliente,
        pasta_dados=raiz / "data",
        pasta_indice=tmp_path / "indice",
        arquivo_cache=tmp_path / "embeddings.json",
    )

    assert len(indice.docstore.docs) > 0
    assert cliente.chamadas > 0
