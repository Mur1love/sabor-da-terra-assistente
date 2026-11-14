"""Qualidade da recuperação: casos do gabarito (#22) no top-3."""

import os
from pathlib import Path

import pytest
import yaml

from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.rag.indexar import PASTA_INDICE
from sabor_da_terra.rag.recuperacao import buscar_documentos


PASTA_GABARITO = Path(__file__).parent / "gabarito"

# Casos de turno único do gabarito cuja fonte inclui um documento .txt.
CASOS_GABARITO = [
    "CERT-001",
    "CERT-002",
    "CERT-003",
    "CERT-004",
    "CERT-005",
    "DOC-001",
    "DOC-002",
    "DOC-004",
    "DOC-006",
    "ANTI-003",
]

# Critérios de aceite escritos na issue #7.
CRITERIOS_DA_ISSUE = [
    ("certificação da Josefa", "cert_organica_josefa_souza_P008.txt"),
    ("frango caipira SIE", "inspecao_adagro_2026.txt"),
]

EXECUTAR_REAL = pytest.mark.skipif(
    os.getenv("EXECUTAR_TESTES_RAG_REAL") != "1",
    reason=(
        "Teste de recuperação real desativado. "
        "Defina EXECUTAR_TESTES_RAG_REAL=1 para executar."
    ),
)


def carregar_casos() -> list[tuple[str, str, set[str]]]:
    """(id, pergunta, documentos aceitos) dos casos escolhidos."""

    todos = {}

    for arquivo in PASTA_GABARITO.glob("*.yaml"):
        for caso in yaml.safe_load(arquivo.read_text(encoding="utf-8")):
            todos[caso["id"]] = caso

    casos = []

    for id_caso in CASOS_GABARITO:
        caso = todos[id_caso]
        documentos = {
            Path(fonte).name
            for fonte in caso["fonte"]
            if str(fonte).endswith(".txt")
        }
        casos.append((id_caso, caso["entrada"].strip(), documentos))

    return casos


def test_casos_do_gabarito_carregam():
    casos = carregar_casos()

    assert len(casos) == 10
    assert all(documentos for _, _, documentos in casos)


@pytest.fixture(scope="module")
def cliente_real():
    assert PASTA_INDICE.is_dir(), (
        "Índice vetorial não encontrado. "
        "Execute 'python -m sabor_da_terra.rag.indexar'."
    )

    return LLMClient(modo="real")


@EXECUTAR_REAL
def test_recuperacao_top3_gabarito(cliente_real):
    """Pelo menos 9 dos 10 casos trazem um documento da fonte no top-3."""

    erros = []

    for id_caso, pergunta, documentos in carregar_casos():
        resultados = buscar_documentos(pergunta, k=3, cliente=cliente_real)
        encontrados = [resultado["arquivo"] for resultado in resultados]

        assert all(encontrados), f"{id_caso}: resultado sem arquivo."

        if not documentos & set(encontrados):
            erros.append(
                f"{id_caso}: esperado {sorted(documentos)}, veio {encontrados}"
            )

    acertos = len(CASOS_GABARITO) - len(erros)

    assert acertos >= 9, (
        f"{acertos}/10 no top-3. Falharam:\n" + "\n".join(erros)
    )


@EXECUTAR_REAL
@pytest.mark.parametrize("pergunta,arquivo_esperado", CRITERIOS_DA_ISSUE)
def test_criterios_da_issue(cliente_real, pergunta, arquivo_esperado):
    resultados = buscar_documentos(pergunta, k=3, cliente=cliente_real)

    assert arquivo_esperado in [r["arquivo"] for r in resultados]
