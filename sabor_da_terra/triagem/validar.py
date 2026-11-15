"""Integra a extração da Etapa 9 ao motor de regras da Etapa 5."""

from __future__ import annotations

from datetime import date
from typing import Any

from sabor_da_terra.regras.conformidade import (
    ItemPedido,
    verificar_conformidade,
)
from sabor_da_terra.triagem.schema import ItemPedidoExtraido


def validar_item(
    item: ItemPedidoExtraido,
    comprador: str | None,
    data_entrega: str | None,
    data_referencia: str,
) -> dict[str, Any]:
    """Valida um item extraído, preservando alertas e fontes."""

    if item.quantidade is None:
        return {
            "encontrado": False,
            "produto": item.produto,
            "pendente_confirmacao": True,
            "aviso": "Quantidade não informada. Confirmar com o comprador.",
            "fonte": "pedido_estruturado",
        }

    if not data_entrega:
        return {
            "encontrado": False,
            "produto": item.produto,
            "pendente_confirmacao": True,
            "aviso": "Prazo de entrega não informado.",
            "fonte": "pedido_estruturado",
        }

    try:
        date.fromisoformat(data_entrega)
    except ValueError:
        return {
            "encontrado": False,
            "produto": item.produto,
            "pendente_confirmacao": True,
            "aviso": "Prazo não resolvido para uma data válida.",
            "fonte": "pedido_estruturado",
        }

    pedido = ItemPedido(
        produto=item.produto,
        quantidade=item.quantidade,
        unidade=item.unidade,
        organico=item.exige_organico,
    )

    resultado = verificar_conformidade(
        item=pedido,
        data_entrega=data_entrega,
        comprador=comprador or "",
        data_referencia=data_referencia,
    )

    return resultado
