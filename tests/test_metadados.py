"""Testes da extração e enriquecimento de metadados."""

from pathlib import Path

from sabor_da_terra.rag.metadados import enriquecer_metadados_trecho
from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.rag.metadados import (
    extrair_produtor_id,
    extrair_data_validade,
    extrair_metadados,
    enriquecer_metadados_trecho,
)


BASE_DADOS = Path(__file__).resolve().parents[1] / "data"


def obter_documento(nome: str) -> dict:
    documentos = carregar_documentos(BASE_DADOS)

    return next(
        documento
        for documento in documentos
        if documento["arquivo"] == nome
    )


def test_extrair_produtor_id():
    assert extrair_produtor_id(
        "cert_organica_josefa_souza_P008.txt"
    ) == "P008"

    assert extrair_produtor_id(
        "contrato_pnae_garanhuns.txt"
    ) is None


def test_extrair_data_validade():
    texto = "Data de Validade: 30/09/2026"

    assert extrair_data_validade(texto) == "2026-09-30"


def test_documento_sem_validade():
    texto = "Documento sem data de validade."

    assert extrair_data_validade(texto) is None


def test_metadados_josefa():
    josefa = obter_documento(
        "cert_organica_josefa_souza_P008.txt"
    )

    metadados = extrair_metadados(josefa)

    assert metadados["arquivo"] == josefa["arquivo"]
    assert metadados["tipo_documento"] == "certificacao"
    assert metadados["produtor_id"] == "P008"
    assert metadados["data_validade"] == "2026-09-30"


def test_contrato_sem_produtor():
    contrato = obter_documento(
        "contrato_pnae_garanhuns.txt"
    )

    metadados = extrair_metadados(contrato)

    assert metadados["produtor_id"] is None
    assert metadados["tipo_documento"] == "contrato"


def test_identificar_produtor_no_trecho():
    texto = """
    5. P017 - Wellington da Silva Monteiro
    Produtos: Frango caipira, ovos caipira
    Registro SIE: NÃO POSSUI
    """

    metadados = enriquecer_metadados_trecho(
        texto,
        {
            "arquivo": "inspecao_adagro_2026.txt",
            "produtor_id": None,
        },
    )

    assert metadados["produtor_id"] == "P017"
    assert metadados["produto"] == [
        "frango caipira",
        "ovos caipira",
    ]


def test_trecho_sem_produtor():
    metadados = enriquecer_metadados_trecho(
        "RESULTADO GERAL: APROVADO COM RESTRIÇÕES",
        {
            "arquivo": "inspecao_adagro_2026.txt",
            "produtor_id": None,
        },
    )

    assert metadados["produtor_id"] is None
    assert metadados["produto"] == []


def test_trecho_com_multiplos_produtores():
    metadados = enriquecer_metadados_trecho(
        "Produtores P001 e P002 participaram da inspeção.",
        {
            "arquivo": "inspecao_adagro_2026.txt",
            "produtor_id": None,
        },
    )

    assert metadados["produtor_id"] is None
    assert metadados["produto"] == []


def test_preservar_metadados_originais():
    originais = {
        "arquivo": "inspecao_adagro_2026.txt",
        "tipo_documento": "certificacao",
        "produtor_id": None,
        "data_validade": None,
        "secao": "produtores_vistoriados",
    }

    enriquecidos = enriquecer_metadados_trecho(
        "P017\nProdutos: Frango caipira, ovos caipira",
        originais,
    )

    assert enriquecidos["arquivo"] == originais["arquivo"]
    assert enriquecidos["tipo_documento"] == "certificacao"
    assert enriquecidos["secao"] == "produtores_vistoriados"

    # A função não deve modificar o dicionário recebido.
    assert originais["produtor_id"] is None
    assert enriquecidos["produtor_id"] == "P017"


def test_reconhecer_produto_singular():
    metadados = {"produtor_id": None}

    resultado = enriquecer_metadados_trecho(
        "Produto: Queijo coalho",
        metadados,
    )

    assert resultado["produto"] == ["queijo coalho"]


def test_multiplos_produtores_sem_id_unico():
    metadados = {"produtor_id": None}

    resultado = enriquecer_metadados_trecho(
        "Produtores P002 e P017 foram vistoriados.",
        metadados,
    )

    assert resultado["produtor_id"] is None
