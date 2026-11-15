"""Consolidação de orçamentos da triagem de pedidos."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def _dinheiro(valor: Any) -> Decimal:
    """Converte valores monetários sem usar aritmética float."""
    return Decimal(str(valor)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def consolidar_orcamento(
    avaliacoes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Consolida preços retornados pelo motor de conformidade.

    Os valores são estimativas comerciais, não pedidos
    confirmados nem garantias de disponibilidade.
    """

    itens = []
    fontes = set()
    total = Decimal("0.00")
    total_sem_desconto = Decimal("0.00")
    itens_sem_preco = 0
    itens_com_restricao = 0
    contratos = set()

    for avaliacao in avaliacoes:
        item = avaliacao.get("item") or {}
        preco = avaliacao.get("preco")
        alertas = avaliacao.get("alertas") or []

        produto = item.get(
            "produto",
            avaliacao.get("produto", "não identificado"),
        )

        quantidade = item.get("quantidade")
        unidade = item.get("unidade")

        fontes.update(
            fonte
            for fonte in avaliacao.get("fontes", [])
            if fonte
        )

        if not preco or not preco.get("disponivel", True):
            itens_sem_preco += 1

            itens.append({
                "produto": produto,
                "quantidade": quantidade,
                "unidade": unidade,
                "situacao": "sem_preco",
                "total": None,
                "fonte": None,
                "alertas": alertas,
            })
            continue

        valor_total = preco.get("total")

        if valor_total is None:
            itens_sem_preco += 1

            itens.append({
                "produto": produto,
                "quantidade": quantidade,
                "unidade": unidade,
                "situacao": "sem_preco",
                "total": None,
                "fonte": preco.get("fonte"),
                "alertas": alertas,
            })
            continue

        origem = preco.get("origem", "tabela")
        contrato = preco.get("contrato")

        if contrato:
            contratos.add(contrato)

        valor = _dinheiro(valor_total)
        total += valor

        subtotal = preco.get("subtotal")
        if subtotal is not None:
            total_sem_desconto += _dinheiro(subtotal)
        else:
            total_sem_desconto += valor

        pode_atender = avaliacao.get(
            "pode_atender", False
        )

        if not pode_atender:
            itens_com_restricao += 1

        fonte_preco = preco.get("fonte")
        if fonte_preco:
            fontes.add(fonte_preco)

        itens.append({
            "produto": produto,
            "quantidade": quantidade,
            "unidade": unidade,
            "situacao": (
                "estimado_com_restricao"
                if not pode_atender
                else "estimado"
            ),
            "origem": origem,
            "contrato": contrato,
            "preco_unitario": preco.get(
                "preco_unitario"
            ),
            "desconto_atacado_aplicado": preco.get(
                "desconto_atacado_aplicado", False
            ),
            "desconto_atacado_pct": preco.get(
                "desconto_atacado_pct", 0.0
            ),
            "valor_desconto": preco.get(
                "valor_desconto", 0.0
            ),
            "total": float(valor),
            "fonte": fonte_preco,
            "alertas": alertas,
        })

    completo = (
        len(avaliacoes) > 0
        and itens_sem_preco == 0
    )

    return {
        "itens": itens,
        "quantidade_itens": len(avaliacoes),
        "itens_com_preco": len(avaliacoes) - itens_sem_preco,
        "itens_sem_preco": itens_sem_preco,
        "itens_com_restricao": itens_com_restricao,
        "total_estimado": float(total),
        "total_sem_desconto": float(
            total_sem_desconto
        ),
        "economia_atacado": float(
            total_sem_desconto - total
        ),
        "orcamento_completo": completo,
        "contratos": sorted(contratos),
        "fontes": sorted(fontes),
        "confirmado": False,
        "aviso": (
            "Estimativa baseada nos preços disponíveis. "
            "Não representa confirmação de compra, "
            "estoque ou atendimento."
        ),
    }
