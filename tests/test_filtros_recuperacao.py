"""Testes dos filtros de metadados da recuperação documental."""

import pytest

from sabor_da_terra.rag.recuperacao import buscar_documentos


class ClienteEmbeddingSimulado:
    """Simula embeddings sem realizar chamadas à API Gemini."""

    def embedar(self, texto: str) -> list[float]:
        return [0.01] * 3072


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
    ],
)
def test_filtros_metadados(
    pergunta,
    filtros,
    tmp_path,
):
    cliente = ClienteEmbeddingSimulado()

    resultados = buscar_documentos(
        pergunta=pergunta,
        filtros=filtros,
        k=3,
        cliente=cliente,
        arquivo_cache=tmp_path / "embeddings_teste.json",
    )

    assert resultados, "A busca não retornou documentos."

    for resultado in resultados:
        assert resultado["arquivo"]
        assert resultado["trecho"]

        for chave, valor in filtros.items():
            assert resultado["metadados"][chave] == valor
