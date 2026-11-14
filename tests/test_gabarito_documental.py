"""Etapa 8, tarefa 12: roda os casos documentais do gabarito (7 DOC + 3 ANTI) em modo fixture.

Cada caso do gabarito (`tests/gabarito/*.yaml`) é executado no pipeline com:
- buscador injetado que devolve exatamente os arquivos citados na `fonte` do caso
  (um retrieval perfeito para o caso — a qualidade do retrieval real é dívida da #7);
- resposta do Flash scriptada como fixture: para os casos DOC, o texto `esperado` do
  próprio gabarito citando as fontes; para os ANTI, a resposta de lacuna.

O que isso prova offline: o contrato do pipeline (citações ⊆ contexto, ao menos uma
citação para resposta com evidência, recusa sem inventar) sustenta TODOS os casos
documentais do gabarito. O que não prova: a qualidade da resposta do modelo real —
essa fica para a avaliação ponta a ponta da #14.
"""

from pathlib import Path

import pytest
import yaml

from sabor_da_terra.rag.responder import (
    Citacao,
    RespostaDocumental,
    TrechoRecuperado,
    _resposta_lacuna,
    listar_arquivos_data,
    responder_consulta_documental,
)
from tests.test_rag_responder import _LLMClientFixtureControlado

RAIZ = Path(__file__).resolve().parents[1]
PASTA_GABARITO = RAIZ / "tests" / "gabarito"
DATA_REFERENCIA = "2026-10-30"
LIMITE_DE_MARCAS = 6


def _casos_documentais() -> list[dict]:
    casos: list[dict] = []
    for nome in ("casos-consulta-documental.yaml", "anti-alucinacao.yaml"):
        casos.extend(yaml.safe_load((PASTA_GABARITO / nome).read_text(encoding="utf-8")))
    return casos


def _arquivos_de_data_do_caso(caso: dict) -> list[Path]:
    """Arquivos reais de data/ citados na fonte do caso; diretórios viram seus .txt."""
    arquivos: list[Path] = []
    vistos: set[Path] = set()
    for item in caso["fonte"]:
        base = item.split(" (")[0].strip()
        if not base.startswith("data/"):
            continue  # docs/ e afins não são recuperáveis pelo RAG
        caminho = RAIZ / base
        if caminho.is_dir():
            candidatos = sorted(caminho.glob("*.txt"))
        elif caminho.is_file():
            candidatos = [caminho]
        else:
            candidatos = []
        for arquivo in candidatos:
            if arquivo not in vistos:
                vistos.add(arquivo)
                arquivos.append(arquivo)
    return arquivos


def _buscador_do_caso(caso: dict):
    arquivos = _arquivos_de_data_do_caso(caso)

    def buscar(pergunta: str) -> list[TrechoRecuperado]:
        return [
            TrechoRecuperado(
                arquivo=caminho.relative_to(RAIZ / "data").as_posix(),
                conteudo=caminho.read_text(encoding="utf-8")[:400],
                score=1.0,
            )
            for caminho in arquivos
        ]

    return buscar, [caminho.relative_to(RAIZ / "data").as_posix() for caminho in arquivos]


def _resposta_do_caso(caso: dict, arquivos: list[str]) -> RespostaDocumental:
    if caso["id"].startswith("ANTI"):
        # Esperado dos casos anti-alucinação: recusa limpa, sem citação inventada.
        return _resposta_lacuna("pt", f"{caso['id']}: informação ausente na base documental.")

    citaveis = arquivos[:LIMITE_DE_MARCAS]
    trechos = []
    for rel in citaveis:
        primeira_linha = next(
            (linha.strip() for linha in (RAIZ / "data" / rel).read_text(encoding="utf-8").splitlines() if linha.strip()),
            "",
        )[:200]
        trechos.append(Citacao(arquivo=rel, trecho=primeira_linha))
    marcas = " ".join(f"[fonte: {rel}]" for rel in citaveis)
    return RespostaDocumental(
        resposta=f"{caso['esperado'].strip()} {marcas}".strip(),
        citacoes=trechos,
        lacunas=[],
    )


@pytest.mark.parametrize("caso", _casos_documentais(), ids=lambda caso: caso["id"])
def test_gabarito_documental_no_pipeline(tmp_path, caso: dict):
    assert caso["entrada"] and caso["esperado"] and caso["fonte"]  # gabarito completo

    buscador, arquivos = _buscador_do_caso(caso)
    llm = _LLMClientFixtureControlado(
        tmp_path,
        {"resposta": [_resposta_do_caso(caso, arquivos).model_dump_json()]},
    )

    resultado = responder_consulta_documental(
        caso["entrada"].strip(),
        data_referencia=DATA_REFERENCIA,
        cliente_llm=llm,
        buscador=buscador,
        usar_llm_auxiliar=False,
    )

    if caso["id"].startswith("ANTI"):
        # Recusa sem inventar: lacuna limpa, nenhuma citação.
        assert resultado.citacoes == []
        assert resultado.resposta.lower().startswith(("não encontrei", "i could not find"))
        assert resultado.lacunas
        return

    # Caso documental: ao menos uma citação (AC1), todas apontando arquivos reais
    # de data/ que estavam no contexto, e a resposta não foi rebaixada a lacuna.
    citaveis = set(arquivos[:LIMITE_DE_MARCAS])
    assert resultado.citacoes, f"{caso['id']}: resposta sem citação"
    assert {c.arquivo for c in resultado.citacoes} == citaveis
    assert all(c.arquivo in listar_arquivos_data() for c in resultado.citacoes)
    assert "não encontrei" not in resultado.resposta.lower()
    assert not any("fora do contexto" in lacuna for lacuna in resultado.lacunas)
