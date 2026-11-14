"""Testes da recuperação por identificadores documentais exatos."""

import pytest

from sabor_da_terra.rag.recuperacao import buscar_documentos


class ClienteEmbeddingSimulado:
    """Evita chamadas à API Gemini nos testes."""

    def embedar(self, texto: str) -> list[float]:
        return [0.01] * 3072


@pytest.mark.parametrize(
    "pergunta,arquivo_esperado",
    [
        (
            "ORG-PE-2025-003198",
            "inspecao_adagro_2026.txt",
        ),
        (
            "ADAGRO-AM-2026-0189",
            "inspecao_adagro_2026.txt",
        ),
        (
            "045/2026",
            "contrato_pnae_garanhuns.txt",
        ),
    ],
)
def test_identificadores_exatos(
    pergunta,
    arquivo_esperado,
    tmp_path,
):
    resultados = buscar_documentos(
        pergunta=pergunta,
        k=3,
        cliente=ClienteEmbeddingSimulado(),
        arquivo_cache=tmp_path / "embeddings_teste.json",
    )

    arquivos = [item["arquivo"] for item in resultados]

    assert arquivo_esperado in arquivos, (
        f"Documento {arquivo_esperado} não encontrado "
        f"no top-3 para o identificador {pergunta}. "
        f"Resultados: {arquivos}"
    )
