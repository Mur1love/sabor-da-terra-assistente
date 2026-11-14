"""Testes da recuperação documental com filtros."""

import pytest

from sabor_da_terra.rag.embeddings import GeradorEmbeddings
from sabor_da_terra.rag.indexar import construir_indice
from sabor_da_terra.rag.recuperacao import buscar_documentos


class ClienteSimulado:
    """Gera embeddings determinísticos para os testes."""

    def __init__(self):
        self.chamadas = 0

    def embedar(self, texto: str) -> list[float]:
        self.chamadas += 1
        texto = texto.lower()

        if "frango" in texto:
            return [0.0, 1.0, 0.0]

        if "mel" in texto or "josefa" in texto:
            return [1.0, 0.0, 0.0]

        return [0.0, 0.0, 1.0]


@pytest.fixture
def ambiente_rag(tmp_path):
    cliente = ClienteSimulado()

    documentos = [
        {
            "arquivo": "cert_organica_josefa_P008.txt",
            "tipo_documento": "certificacao",
            "caminho": "certificacoes/cert_organica_josefa_P008.txt",
            "texto": (
                "CERTIFICAÇÃO ORGÂNICA\n\n"
                "Produtor: P008\n"
                "Produtos: Mel silvestre\n"
                "Certificação de Josefa vencida."
            ),
        },
        {
            "arquivo": "inspecao_adagro_2026.txt",
            "tipo_documento": "certificacao",
            "caminho": "certificacoes/inspecao_adagro_2026.txt",
            "texto": (
                "PRODUTORES VISTORIADOS\n\n"
                "P017 - Wellington\n"
                "Produtos: Frango caipira\n"
                "Registro SIE: NÃO POSSUI."
            ),
        },
    ]

    pasta_indice = tmp_path / "indice"
    arquivo_cache = tmp_path / "embeddings.json"

    gerador = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=arquivo_cache,
    )

    construir_indice(
        documentos,
        gerador,
        pasta_indice,
    )

    return {
        "cliente": cliente,
        "pasta_indice": pasta_indice,
    }


def test_buscar_documentos(ambiente_rag):
    resultados = buscar_documentos(
        "Qual a situação da certificação da Josefa?",
        k=3,
        **ambiente_rag,
    )

    assert resultados
    assert all(
        {"arquivo", "trecho", "metadados", "score"}
        <= resultado.keys()
        for resultado in resultados
    )


def test_busca_certificacao_josefa(ambiente_rag):
    resultados = buscar_documentos(
        "Qual a situação da certificação da Josefa?",
        k=3,
        **ambiente_rag,
    )

    assert any(
        resultado["arquivo"] == "cert_organica_josefa_P008.txt"
        for resultado in resultados
    )


def test_busca_frango_caipira(ambiente_rag):
    resultados = buscar_documentos(
        "O frango caipira possui SIE?",
        k=3,
        **ambiente_rag,
    )

    assert any(
        resultado["arquivo"] == "inspecao_adagro_2026.txt"
        for resultado in resultados
    )


def test_filtro_produtor(ambiente_rag):
    resultados = buscar_documentos(
        "Qual a situação da certificação?",
        filtros={"produtor_id": "P008"},
        k=3,
        **ambiente_rag,
    )

    assert resultados
    assert all(
        resultado["metadados"]["produtor_id"] == "P008"
        for resultado in resultados
    )


def test_filtro_tipo_documento(ambiente_rag):
    resultados = buscar_documentos(
        "Certificação orgânica",
        filtros={"tipo_documento": "certificacao"},
        k=3,
        **ambiente_rag,
    )

    assert resultados
    assert all(
        resultado["metadados"]["tipo_documento"] == "certificacao"
        for resultado in resultados
    )


def test_pergunta_vazia(ambiente_rag):
    with pytest.raises(ValueError):
        buscar_documentos(
            "   ",
            **ambiente_rag,
        )


def test_k_invalido(ambiente_rag):
    with pytest.raises(ValueError):
        buscar_documentos(
            "Certificação",
            k=0,
            **ambiente_rag,
        )
