from pathlib import Path

from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.rag.metadados import (
    extrair_produtor_id,
    extrair_data_validade,
    extrair_metadados,
)


BASE_DADOS = Path(__file__).resolve().parents[1] / "data"


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
    documentos = carregar_documentos(BASE_DADOS)

    josefa = next(
        doc for doc in documentos
        if doc["arquivo"]
        == "cert_organica_josefa_souza_P008.txt"
    )

    metadados = extrair_metadados(josefa)

    assert metadados["produtor_id"] == "P008"
    assert metadados["data_validade"] == "2026-09-30"
    assert metadados["tipo_documento"] == "certificacao"
    assert metadados["arquivo"] == josefa["arquivo"]


def test_contrato_sem_produtor():
    documentos = carregar_documentos(BASE_DADOS)

    contrato = next(
        doc for doc in documentos
        if doc["arquivo"] == "contrato_pnae_garanhuns.txt"
    )

    metadados = extrair_metadados(contrato)

    assert metadados["produtor_id"] is None
    assert metadados["tipo_documento"] == "contrato"
