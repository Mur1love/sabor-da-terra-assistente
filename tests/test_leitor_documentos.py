
from pathlib import Path

from sabor_da_terra.rag.leitor import carregar_documentos


BASE_DADOS = Path(__file__).resolve().parents[1] / "data"


def test_carregar_20_documentos():
    documentos = carregar_documentos(BASE_DADOS)

    assert len(documentos) == 20


def test_todos_documentos_possuem_origem():
    documentos = carregar_documentos(BASE_DADOS)

    for documento in documentos:
        assert documento["texto"].strip()
        assert documento["arquivo"]
        assert documento["tipo_documento"]
        assert documento["caminho"]


def test_quantidade_por_tipo():
    documentos = carregar_documentos(BASE_DADOS)

    tipos = [
        documento["tipo_documento"]
        for documento in documentos
    ]

    assert tipos.count("certificacao") == 12
    assert tipos.count("contrato") == 3
    assert tipos.count("ficha_tecnica") == 5


def test_certificacao_josefa():
    documentos = carregar_documentos(BASE_DADOS)

    josefa = next(
        documento
        for documento in documentos
        if documento["arquivo"]
        == "cert_organica_josefa_souza_P008.txt"
    )

    assert "ORG-PE-2024-003876" in josefa["texto"]
    assert "30/09/2026" in josefa["texto"]
    assert "VENCIDA" in josefa["texto"]
