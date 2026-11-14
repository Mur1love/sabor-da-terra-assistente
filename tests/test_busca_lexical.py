"""Testes da busca lexical documental."""

from types import SimpleNamespace

from sabor_da_terra.rag.busca_lexical import (
    buscar_por_identificadores,
    calcular_score_lexical,
    extrair_identificadores,
)


def test_extrair_certificado_organico():
    texto = "Consultar ORG-PE-2024-003876"

    assert extrair_identificadores(texto) == [
        "ORG-PE-2024-003876"
    ]


def test_extrair_registro_adagro():
    texto = "Registro ADAGRO-AM-2026-0189"

    assert extrair_identificadores(texto) == [
        "ADAGRO-AM-2026-0189"
    ]


def test_extrair_numero_contrato():
    texto = "Contrato 045/2026-PNAE"

    assert extrair_identificadores(texto) == [
        "045/2026"
    ]


def test_identificadores_sem_duplicacao():
    texto = (
        "ORG-PE-2024-003876 e "
        "ORG-PE-2024-003876"
    )

    assert len(extrair_identificadores(texto)) == 1


def test_score_correspondencia_exata():
    score = calcular_score_lexical(
        "Consultar ORG-PE-2024-003876",
        "Certificado ORG-PE-2024-003876 válido.",
    )

    assert score == 1.0


def test_score_sem_correspondencia():
    score = calcular_score_lexical(
        "Consultar ORG-PE-2024-003876",
        "Certificado ORG-PE-2024-999999 válido.",
    )

    assert score == 0.0


def test_busca_respeita_filtro_produtor():
    nos = [
        SimpleNamespace(
            node_id="1",
            text="Certificado ORG-PE-2024-003876",
            metadata={
                "arquivo": "cert_P008.txt",
                "produtor_id": "P008",
            },
        ),
        SimpleNamespace(
            node_id="2",
            text="Certificado ORG-PE-2024-003876",
            metadata={
                "arquivo": "cert_P002.txt",
                "produtor_id": "P002",
            },
        ),
    ]

    resultados = buscar_por_identificadores(
        "ORG-PE-2024-003876",
        nos,
        filtros={"produtor_id": "P008"},
    )

    assert len(resultados) == 1
    assert resultados[0]["arquivo"] == "cert_P008.txt"


def test_contrato_com_sufixo_pnae():
    identificadores = extrair_identificadores(
        "Nº 045/2026-PNAE"
    )

    assert identificadores == ["045/2026"]


def test_correspondencia_contrato_sem_sufixo():
    score = calcular_score_lexical(
        "045/2026",
        "Contrato Nº 045/2026-PNAE",
    )

    assert score == 1.0
