"""Etapa 14: o gabarito inteiro (tests/gabarito/*.yaml) contra o assistente integrado.

Comando único: `pytest tests/test_gabarito.py`.

Cada caso roda no `Assistente` de verdade (roteamento, ferramentas, composição)
e é conferido em três frentes:
- funções esperadas (`funcoes_esperadas`) chamadas na conversa;
- citações válidas: arquivos de `data/` que saíram das funções do turno, e ao
  menos uma fonte por turno nos casos documentais;
- cada critério de `deve_conter` / `nao_deve_conter`, decidido pelo juiz
  (Flash-Lite com saída estruturada).

Roda 100% offline: repete as respostas gravadas na rodada real
(`python -m scripts.avaliar_gabarito`). Caso sem gravação é pulado com a
instrução — não finge passar. Os números por desafio e por requisito estão
no `docs/05-avaliacao.md`.
"""

import pytest

from sabor_da_terra.avaliacao.clientes import FALLBACK_DA_AVALIACAO
from sabor_da_terra.avaliacao.execucao import STATUS_OK, avaliar_caso
from sabor_da_terra.avaliacao.gabarito import carregar_casos
from sabor_da_terra.avaliacao.metricas import falhas
from sabor_da_terra.llm.cliente import VARIAVEL_FALLBACK, FixtureAusenteError, LLMClient

# Falhas conhecidas que ficaram como limitação registrada no docs/05 (id → motivo).
# `strict=True`: se um caso desses passar a acertar, o teste avisa para tirar daqui.
LIMITACOES_CONHECIDAS: dict[str, str] = {}


def _parametros(conjunto: str):
    for caso in carregar_casos(conjunto):
        marcas = []
        if caso.id in LIMITACOES_CONHECIDAS:
            marcas.append(pytest.mark.xfail(reason=LIMITACOES_CONHECIDAS[caso.id], strict=True))
        yield pytest.param(caso, id=caso.id, marks=marcas)


def _avaliar(caso, monkeypatch):
    monkeypatch.setenv(VARIAVEL_FALLBACK, FALLBACK_DA_AVALIACAO)
    try:
        resultado = avaliar_caso(caso, LLMClient(modo="fixture"))
    except FixtureAusenteError as erro:
        pytest.skip(f"{caso.id} sem gravação ({erro}) — rode python -m scripts.avaliar_gabarito")

    assert resultado["status"] == STATUS_OK, resultado.get("erro")
    detalhe = falhas([resultado])
    assert resultado["aprovado"], f"{caso.id} reprovado: {detalhe[0] if detalhe else resultado}"


@pytest.mark.parametrize("caso", list(_parametros("gabarito")))
def test_caso_do_gabarito(caso, monkeypatch):
    _avaliar(caso, monkeypatch)


@pytest.mark.parametrize("caso", list(_parametros("robustez")))
def test_variacao_coloquial_de_robustez(caso, monkeypatch):
    """5 variações coloquiais novas, fora do gabarito (tests/robustez/)."""
    _avaliar(caso, monkeypatch)
