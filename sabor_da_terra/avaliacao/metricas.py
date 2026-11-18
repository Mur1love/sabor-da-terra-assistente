"""Métricas de uma rodada do gabarito e o relatório em Markdown do docs/05.

Definições (as mesmas do docs/05-avaliacao.md):
- acerto por critério: critérios cumpridos / critérios avaliados — cada item de
  `deve_conter` atendido e cada item de `nao_deve_conter` que NÃO ocorreu conta 1;
- caso aprovado: todos os critérios cumpridos, funções esperadas chamadas e
  citações válidas (quando o caso é documental);
- casos com erro de infraestrutura (cota/API fora) ficam fora das taxas e são
  listados à parte — não são acerto nem erro do assistente.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sabor_da_terra.avaliacao.gabarito import REQUISITOS_FUNCIONAIS
from sabor_da_terra.avaliacao.execucao import STATUS_OK


def _pct(parte: int, todo: int) -> float | None:
    return round(100.0 * parte / todo, 1) if todo else None


def _grupo(resultados: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in resultados if r.get("status") == STATUS_OK]
    criterios_ok = sum(r["criterios_ok"] for r in ok)
    criterios_total = sum(r["criterios_total"] for r in ok)
    return {
        "casos": len(resultados),
        "avaliados": len(ok),
        "aprovados": sum(1 for r in ok if r["aprovado"]),
        "criterios_ok": criterios_ok,
        "criterios_total": criterios_total,
        "acerto_criterios": _pct(criterios_ok, criterios_total),
        "taxa_aprovacao": _pct(sum(1 for r in ok if r["aprovado"]), len(ok)),
    }


def metricas(resultados: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in resultados if r.get("status") == STATUS_OK]
    por_desafio: dict[str, list] = defaultdict(list)
    por_rf: dict[str, list] = defaultdict(list)
    for r in resultados:
        por_desafio[r["desafio"]].append(r)
        for rf in r["requisitos_funcionais"]:
            por_rf[rf].append(r)

    documentais = [r for r in ok if r["documental"]]
    com_fonte_esperada = [r for r in documentais if r["citacoes"]["fonte_esperada_citada"] is not None]
    anti = [r for r in resultados if r["anti_alucinacao"]]
    return {
        "geral": _grupo(resultados),
        "por_desafio": {d: _grupo(rs) for d, rs in sorted(por_desafio.items())},
        "por_requisito_funcional": {rf: _grupo(por_rf[rf]) for rf in REQUISITOS_FUNCIONAIS if rf in por_rf},
        "anti_alucinacao": _grupo(anti) | {"ids": [r["id"] for r in anti]},
        "citacoes": {
            "documentais_avaliados": len(documentais),
            "com_citacao_valida": sum(1 for r in documentais if r["citacoes"]["ok"]),
            "taxa_citacao_valida": _pct(sum(1 for r in documentais if r["citacoes"]["ok"]), len(documentais)),
            "fonte_esperada_citada": _pct(
                sum(1 for r in com_fonte_esperada if r["citacoes"]["fonte_esperada_citada"]), len(com_fonte_esperada)
            ),
        },
        "funcoes": {
            "casos_com_funcoes_esperadas": sum(1 for r in ok if r["funcoes"]["ok"]),
            "taxa": _pct(sum(1 for r in ok if r["funcoes"]["ok"]), len(ok)),
        },
        "fora_da_conta": [{"id": r["id"], "status": r["status"], "erro": r.get("erro", "")} for r in resultados if r.get("status") != STATUS_OK],
    }


def falhas(resultados: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """O que reprovou cada caso avaliado — base da classificação por causa no docs/05."""
    saida = []
    for r in resultados:
        if r.get("status") != STATUS_OK or r["aprovado"]:
            continue
        saida.append(
            {
                "id": r["id"],
                "nao_atendidos": [c["criterio"] for c in r["criterios"]["deve_conter"] if not c["atendido"]],
                "ocorreram": [c["criterio"] for c in r["criterios"]["nao_deve_conter"] if c["ocorreu"]],
                "funcoes_faltando": r["funcoes"]["faltando"],
                "citacoes_invalidas": r["citacoes"]["invalidas"],
                "turnos_sem_fonte": r["citacoes"]["turnos_sem_fonte"],
            }
        )
    return saida


def _linha(nome: str, g: dict[str, Any]) -> str:
    acerto = "—" if g["acerto_criterios"] is None else f"{g['acerto_criterios']:.1f}%"
    aprov = "—" if g["taxa_aprovacao"] is None else f"{g['aprovados']}/{g['avaliados']} ({g['taxa_aprovacao']:.1f}%)"
    return f"| {nome} | {g['casos']} | {g['avaliados']} | {acerto} ({g['criterios_ok']}/{g['criterios_total']}) | {aprov} |"


def relatorio_markdown(rodada: dict[str, Any]) -> str:
    m = rodada["metricas"]
    cab = "| Recorte | Casos | Avaliados | Acerto por critério | Casos aprovados |\n|---|---|---|---|---|"
    linhas = [f"### Rodada {rodada['rodada']} — {rodada['data']}", "", cab, _linha("**Geral**", m["geral"])]
    linhas += [_linha(d, g) for d, g in m["por_desafio"].items()]
    linhas += ["", cab.replace("Recorte", "Requisito funcional (docs/01 §6)")]
    linhas += [_linha(f"{rf} — {REQUISITOS_FUNCIONAIS[rf]}", g) for rf, g in m["por_requisito_funcional"].items()]
    c = m["citacoes"]
    linhas += [
        "",
        f"- Anti-alucinação ({', '.join(m['anti_alucinacao']['ids'])}): "
        f"{m['anti_alucinacao']['aprovados']}/{m['anti_alucinacao']['avaliados']} aprovados.",
        f"- Respostas documentais com citação válida: {c['com_citacao_valida']}/{c['documentais_avaliados']}"
        + (f" ({c['taxa_citacao_valida']:.1f}%)" if c["taxa_citacao_valida"] is not None else "")
        + (f"; citam o arquivo que o gabarito dá como fonte: {c['fonte_esperada_citada']:.1f}%." if c["fonte_esperada_citada"] is not None else "."),
        f"- Funções esperadas chamadas: {m['funcoes']['casos_com_funcoes_esperadas']}/{m['geral']['avaliados']}.",
    ]
    consumo = rodada.get("consumo") or {}
    if consumo:
        reais = ", ".join(f"{modelo}: {n}" for modelo, n in consumo.get("chamadas_reais", {}).items()) or "nenhuma"
        linhas.append(f"- Consumo da rodada: chamadas reais ({reais}); replays: {consumo.get('replays', 0)}; failovers: {consumo.get('failovers', 0)}.")
    if m["fora_da_conta"]:
        linhas.append("- Fora da conta (infraestrutura): " + "; ".join(f"{f['id']} ({f['erro'][:80]})" for f in m["fora_da_conta"]) + ".")
    return "\n".join(linhas)
