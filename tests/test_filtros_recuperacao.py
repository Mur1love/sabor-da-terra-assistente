"""Testes dos filtros de metadados da recuperação documental."""

import pytest

from sabor_da_terra.rag.indexar import indexar
from sabor_da_terra.rag.recuperacao import buscar_documentos


class ClienteEmbeddingSimulado:
    """Simula embeddings sem realizar chamadas à API Gemini."""

    def embedar(self, texto: str) -> list[float]:
        return [0.01] * 3072


@pytest.fixture(scope="module")
def pasta_indice(tmp_path_factory):
    """Índice dos 20 documentos reais, montado sem chamar a API."""

    pasta = tmp_path_factory.mktemp("rag")

    indexar(
        cliente=ClienteEmbeddingSimulado(),
        pasta_indice=pasta / "indice",
        arquivo_cache=pasta / "embeddings.json",
    )

    return pasta / "indice"


@pytest.mark.parametrize(
    "pergunta,filtros",
    [
        (
            "certificação orgânica",
            {"tipo_documento": "certificacao"},
        ),
        (
            "documentos do produtor P002",
            {"produtor_id": "P002"},
        ),
        (
            "certificação do produtor P002",
            {
                "tipo_documento": "certificacao",
                "produtor_id": "P002",
            },
        ),
        (
            "mel silvestre",
            {"produto": "mel silvestre"},
        ),
    ],
)
def test_filtros_metadados(
    pergunta,
    filtros,
    pasta_indice,
):
    cliente = ClienteEmbeddingSimulado()

    resultados = buscar_documentos(
        pergunta=pergunta,
        filtros=filtros,
        k=3,
        cliente=cliente,
        pasta_indice=pasta_indice,
    )

    assert resultados, "A busca não retornou documentos."

    for resultado in resultados:
        assert resultado["arquivo"]
        assert resultado["trecho"]

        for chave, valor in filtros.items():
            atual = resultado["metadados"][chave]

            if isinstance(atual, list):
                assert valor in atual
            else:
                assert atual == valor
