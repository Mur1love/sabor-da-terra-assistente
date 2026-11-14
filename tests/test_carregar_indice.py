"""Testes do carregamento do índice vetorial persistido."""

import pytest

from sabor_da_terra.rag.embeddings import GeradorEmbeddings
from sabor_da_terra.rag.indexar import (
    carregar_indice,
    construir_indice,
    obter_indice,
)


class ClienteSimulado:
    """Gera vetores de teste sem acessar serviços externos."""

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
            "arquivo": "cert_organica_josefa_P008.txt",
            "tipo_documento": "certificacao",
            "caminho": "certificacoes/cert_organica_josefa_P008.txt",
            "texto": (
                "CERTIFICAÇÃO ORGÂNICA\n\n"
                "Produtor: P008\n"
                "Produtos: Mel silvestre\n"
                "Data de Validade: 30/09/2026"
            ),
        }
    ]


@pytest.fixture
def indice_persistido(tmp_path, documentos):
    cliente = ClienteSimulado()

    gerador = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=tmp_path / "embeddings.json",
    )

    pasta_indice = tmp_path / "indice"

    construir_indice(
        documentos=documentos,
        gerador=gerador,
        pasta_indice=pasta_indice,
    )

    return pasta_indice, cliente


def test_carregar_indice_existente(indice_persistido):
    pasta_indice, _ = indice_persistido

    indice = carregar_indice(pasta_indice)

    assert indice is not None


def test_obter_indice_carrega_uma_vez(indice_persistido):
    pasta_indice, _ = indice_persistido

    primeiro = obter_indice(pasta_indice)
    segundo = obter_indice(pasta_indice)

    assert primeiro is segundo


def test_preservar_quantidade_de_nos(indice_persistido):
    pasta_indice, _ = indice_persistido

    indice = carregar_indice(pasta_indice)

    # Os dois blocos do documento são curtos e viram um trecho só.
    assert len(indice.docstore.docs) == 1


def test_preservar_metadados(indice_persistido):
    pasta_indice, _ = indice_persistido

    indice = carregar_indice(pasta_indice)

    for no in indice.docstore.docs.values():
        assert no.metadata["arquivo"] == (
            "cert_organica_josefa_P008.txt"
        )
        assert no.metadata["produtor_id"] == "P008"
        assert no.metadata["tipo_documento"] == "certificacao"


def test_carregamento_nao_gera_embeddings(indice_persistido):
    pasta_indice, cliente = indice_persistido

    chamadas_antes = cliente.chamadas

    carregar_indice(pasta_indice)

    assert cliente.chamadas == chamadas_antes


def test_diretorio_inexistente(tmp_path):
    pasta = tmp_path / "indice_inexistente"

    with pytest.raises(FileNotFoundError):
        carregar_indice(pasta)


def test_indice_incompleto(tmp_path):
    pasta = tmp_path / "indice"
    pasta.mkdir()

    with pytest.raises(FileNotFoundError):
        carregar_indice(pasta)
