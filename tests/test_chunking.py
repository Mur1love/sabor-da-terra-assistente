from pathlib import Path

from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.rag.chunking import dividir_em_trechos


BASE_DADOS = Path(__file__).resolve().parents[1] / "data"


def obter_documento(nome):
    documentos = carregar_documentos(BASE_DADOS)
    return next(doc for doc in documentos if doc["arquivo"] == nome)


def test_divisao_certificacao():
    documento = obter_documento(
        "cert_organica_josefa_souza_P008.txt"
    )

    trechos = dividir_em_trechos(documento)

    assert len(trechos) > 1
    assert all(t["texto"] for t in trechos)


def test_preservar_origem():
    documento = obter_documento(
        "cert_organica_josefa_souza_P008.txt"
    )

    trechos = dividir_em_trechos(documento)

    for trecho in trechos:
        assert trecho["metadados"]["arquivo"] == documento["arquivo"]
        assert trecho["metadados"]["produtor_id"] == "P008"


def test_preservar_nao_conformidade():
    documento = obter_documento("inspecao_adagro_2026.txt")

    trechos = dividir_em_trechos(documento)

    assert any(
        "NC-001" in trecho["texto"]
        and "P017" in trecho["texto"]
        for trecho in trechos
    )


def test_preservar_condicoes_contrato():
    documento = obter_documento("contrato_pnae_garanhuns.txt")

    trechos = dividir_em_trechos(documento)

    assert any(
        "CONDIÇÕES OBRIGATÓRIAS" in trecho["texto"]
        and "certificação válida" in trecho["texto"]
        for trecho in trechos
    )
