"""Formatação da fila de triagem para a tela (etapa 13).

Funções puras sobre o resultado de `triar_pendentes` (etapa 10): nada aqui
reordena ou recalcula — a ordem de `chave_da_fila` (urgentes no topo) é regra
de negócio; a interface só apresenta e destaca.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

COLUNAS_FILA = ["Ordem", "Pedido", "Comprador", "Prioridade", "Status", "Prazo", "Produtos", "Problemas"]

PRAZO_OMISSO = "Não informado"


def formatar_fila(resultado: dict[str, Any]) -> pd.DataFrame:
    """A fila consolidada como DataFrame com colunas em português, ordem canônica preservada."""
    linhas: list[dict[str, Any]] = []
    for ordem, registro in enumerate(resultado.get("fila") or [], start=1):
        linhas.append(
            {
                "Ordem": ordem,
                "Pedido": registro.get("id") or "—",
                "Comprador": registro.get("comprador") or "—",
                "Prioridade": registro.get("prioridade") or "—",
                "Status": registro.get("status") or "—",
                "Prazo": registro.get("prazo_entrega") or PRAZO_OMISSO,
                "Produtos": _produtos_do_registro(registro),
                "Problemas": len(registro.get("alertas") or []),
            }
        )
    return pd.DataFrame(linhas, columns=COLUNAS_FILA)


def detalhes_da_fila(resultado: dict[str, Any]) -> list[tuple[str, str]]:
    """Um par (título, markdown) por registro da fila, com alertas e alocação sugerida."""
    detalhes: list[tuple[str, str]] = []
    for registro in resultado.get("fila") or []:
        titulo = f"{registro.get('id') or '—'} — {registro.get('comprador') or 'Comprador não identificado'}"
        linhas = [
            f"**Prioridade:** {registro.get('prioridade') or '—'} · **Status:** {registro.get('status') or '—'} · "
            f"**Prazo:** {registro.get('prazo_entrega') or PRAZO_OMISSO}"
        ]
        urgencia = registro.get("urgencia") or {}
        if urgencia.get("urgencia_nao_calculada"):
            linhas.append(f"{urgencia.get('aviso', 'Urgência não calculada.')}")
        elif urgencia.get("horas_restantes") is not None:
            linhas.append(f"{urgencia['horas_restantes']:g} h até o prazo.")
        alertas = registro.get("alertas") or []
        if alertas:
            linhas.append(f"**Alertas ({len(alertas)}):**")
            linhas += [f"- `{a['codigo']}` — {a['mensagem']} _(fonte: {a.get('fonte', '—')})_" for a in alertas]
        else:
            linhas.append("Sem alertas.")
        for alocacao in registro.get("alocacoes") or []:
            produtores = ", ".join(
                a.get("produtor_id") or "" for a in (alocacao.get("alocacoes") or [])
            )
            unidade = _unidade_da_alocacao(alocacao) or ""
            quantidade = alocacao.get("quantidade_sugerida")
            medida = f" {quantidade:g} {unidade}".rstrip() if isinstance(quantidade, (int, float)) else ""
            linhas.append(
                f"**Alocação sugerida:** {alocacao.get('produto')}{medida}"
                + (f": {produtores}" if produtores else ": sem produtor elegível")
            )
        detalhes.append((titulo, "\n".join(linhas)))
    return detalhes


def _produtos_do_registro(registro: dict[str, Any]) -> str:
    """Itens do pedido na forma `produto (quantidade unidade)`, de onde cada tipo os traz."""
    itens: list[tuple[str, float | None, str | None]] = []
    for item in (registro.get("orcamento") or {}).get("itens") or []:
        itens.append((item.get("produto"), item.get("quantidade"), item.get("unidade")))
    for avaliacao in registro.get("avaliacoes") or []:
        item = avaliacao.get("item") or {}
        if item.get("produto"):
            itens.append((item.get("produto"), item.get("quantidade"), item.get("unidade")))
    for alocacao in registro.get("alocacoes") or []:
        if alocacao.get("produto"):
            itens.append((alocacao.get("produto"), alocacao.get("quantidade_solicitada"), _unidade_da_alocacao(alocacao)))

    partes: list[str] = []
    vistos: set[str] = set()
    for produto, quantidade, unidade in itens:
        if not produto:
            continue
        parte = f"{produto} ({quantidade:g} {unidade or ''})".rstrip() if isinstance(quantidade, (int, float)) else str(produto)
        if parte not in vistos:
            vistos.add(parte)
            partes.append(parte)
    return "; ".join(partes)


def _unidade_da_alocacao(alocacao: dict[str, Any]) -> str | None:
    filhas = alocacao.get("alocacoes") or []
    return (filhas[0] or {}).get("unidade") if filhas else None
