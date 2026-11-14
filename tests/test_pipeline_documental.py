"""Testes de integração do processamento documental."""

from pathlib import Path

from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.rag.chunking import dividir_em_trechos
from sabor_da_terra.rag.sanitizacao import sanitizar_trechos


BASE_DADOS = Path(__file__).resolve().parents[1] / "data"


def processar_documentos():
    documentos = carregar_documentos(BASE_DADOS)
    trechos = []

    for documento in documentos:
        partes = dividir_em_trechos(documento)
        trechos.extend(sanitizar_trechos(partes))

    return documentos, trechos


def test_processar_20_documentos():
    documentos, trechos = processar_documentos()

    assert len(documentos) == 20
    assert len(trechos) >= 20


def test_quantidade_de_trechos_estavel():
    _, trechos = processar_documentos()

    # 133 trechos na correção do PR 25 (era 204 antes da junção dos
    # trechos curtos). A faixa evita regressão silenciosa do chunking:
    # se TAMANHO_MINIMO for zerado, volta para 204; se duplicar a junção,
    # despenca para 40.
    assert 120 <= len(trechos) <= 145


def test_todos_trechos_possuem_origem():
    _, trechos = processar_documentos()

    for trecho in trechos:
        assert trecho["texto"].strip()
        assert trecho["metadados"]["arquivo"]
        assert trecho["metadados"]["tipo_documento"]
        assert trecho["metadados"]["secao"]


def test_todos_documentos_geram_trechos():
    documentos, trechos = processar_documentos()

    arquivos_indexaveis = {
        trecho["metadados"]["arquivo"]
        for trecho in trechos
    }

    for documento in documentos:
        assert documento["arquivo"] in arquivos_indexaveis


def test_preservar_identificadores():
    _, trechos = processar_documentos()

    texto = "\n".join(t["texto"] for t in trechos)

    assert "ORG-PE-2024-003876" in texto
    assert "ADAGRO-AM-2026-0189" in texto
    assert "045/2026-PNAE" in texto


def test_nao_expor_cpf_ou_cnpj():
    _, trechos = processar_documentos()

    texto = "\n".join(t["texto"] for t in trechos)

    import re

    assert not re.search(
        r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
        texto,
    )

    assert not re.search(
        r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
        texto,
    )
