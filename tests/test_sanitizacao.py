from pathlib import Path

from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.rag.chunking import dividir_em_trechos
from sabor_da_terra.rag.sanitizacao import (
    sanitizar_texto,
    sanitizar_trechos,
)


BASE_DADOS = Path(__file__).resolve().parents[1] / "data"


def test_remover_cpf():
    texto = "CPF: 345.678.912-34"

    resultado = sanitizar_texto(texto)

    assert "345.678.912-34" not in resultado
    assert "[CPF REMOVIDO]" in resultado


def test_remover_cnpj():
    texto = "CNPJ: 45.678.901/0001-23"

    resultado = sanitizar_texto(texto)

    assert "45.678.901/0001-23" not in resultado
    assert "[CNPJ REMOVIDO]" in resultado


def test_remover_dados_bancarios():
    texto = "Banco do Brasil - Ag. 0437 - C/C 55.678-9"

    resultado = sanitizar_texto(texto)

    assert "55.678-9" not in resultado
    assert "[DADOS BANCÁRIOS REMOVIDOS]" in resultado


def test_preservar_certificado():
    texto = (
        "Certificado Nº: ORG-PE-2024-003876\n"
        "Data de Validade: 30/09/2026"
    )

    assert sanitizar_texto(texto) == texto


def test_sanitizar_documento_josefa():
    documentos = carregar_documentos(BASE_DADOS)

    josefa = next(
        doc for doc in documentos
        if doc["arquivo"]
        == "cert_organica_josefa_souza_P008.txt"
    )

    trechos = dividir_em_trechos(josefa)
    sanitizados = sanitizar_trechos(trechos)

    texto_final = "\n".join(
        trecho["texto"] for trecho in sanitizados
    )

    assert "345.678.912-34" not in texto_final
    assert "ORG-PE-2024-003876" in texto_final


def test_nao_alterar_trechos_originais():
    trecho = {
        "texto": "CPF: 345.678.912-34",
        "metadados": {"arquivo": "teste.txt"},
    }

    sanitizados = sanitizar_trechos([trecho])

    assert trecho["texto"] == "CPF: 345.678.912-34"
    assert "345.678.912-34" not in sanitizados[0]["texto"]
