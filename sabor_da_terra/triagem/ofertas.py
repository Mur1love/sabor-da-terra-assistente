"""Correspondência informativa entre ofertas de produtores e demandas."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from sabor_da_terra.triagem.schema import PedidoTriado, TipoMensagem


def _data_recebimento(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


def _identificar_produtor(comprador: str | None) -> str | None:
    """Extrai identificador explícito, sem deduzir produtor pelo nome."""
    if not comprador:
        return None

    resultado = re.search(r"\bP\d{3}\b", comprador.upper())
    return resultado.group(0) if resultado else None



def identificar_ofertas(
    registros: list[dict[str, Any]],
    data_referencia: date | None = None,
) -> list[dict[str, Any]]:
    """Extrai ofertas conhecidas até a data de referência."""
    ofertas = []

    for registro in registros:
        pedido: PedidoTriado = registro["pedido"]

        if pedido.tipo != TipoMensagem.MENSAGEM_PRODUTOR:
            continue

        recebimento = _data_recebimento(
            registro.get("data_recebimento")
        )

        if data_referencia is not None:
            # Uma oferta futura não pode influenciar a triagem.
            # Sem data verificável, também não é possível
            # comprovar que a oferta já era conhecida.
            if (
                recebimento is None
                or recebimento.date() > data_referencia
            ):
                continue

        produtor_id = _identificar_produtor(pedido.comprador)
        if produtor_id is None:
            continue

        for item in pedido.itens:
            if item.quantidade is None or not item.unidade:
                continue

            if item.produto.casefold().strip() == "manteiga":
                continue

            ofertas.append({
                "pedido_oferta": registro["id"],
                "produtor_id": produtor_id,
                "produto": item.produto,
                "quantidade": float(item.quantidade),
                "unidade": item.unidade,
                "recebida_em": registro.get("data_recebimento"),
                "prazo_resposta": pedido.prazo_entrega,
                "fonte": (
                    "tests/fixtures/triagem_15_pedidos.json:"
                    f"{registro['id']}"
                ),
                "confirmada": False,
            })

    return ofertas



def cruzar_ofertas(
    registro_demanda: dict[str, Any],
    ofertas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Relaciona ofertas e demandas sem reservar ou confirmar estoque."""

    pedido: PedidoTriado = registro_demanda["pedido"]

    if pedido.tipo not in {
        TipoMensagem.COMPRA,
        TipoMensagem.COMPRA_URGENTE,
    }:
        return []

    prazo = None

    if pedido.prazo_entrega:
        try:
            prazo = date.fromisoformat(pedido.prazo_entrega)
        except ValueError:
            pass

    correspondencias = []

    for item in pedido.itens:
        if item.quantidade is None or not item.unidade:
            continue

        for oferta in ofertas:
            if (
                item.produto.casefold().strip()
                != oferta["produto"].casefold().strip()
                or item.unidade != oferta["unidade"]
            ):
                continue

            recebimento = _data_recebimento(
                oferta.get("recebida_em")
            )

            # Verifica a compatibilidade temporal.
            if prazo is None or recebimento is None:
                compativel = None
                observacao = (
                    "Não foi possível verificar a compatibilidade "
                    "temporal. Confirmar prazo e disponibilidade."
                )

            elif recebimento.date() <= prazo:
                compativel = True
                observacao = (
                    "Oferta recebida até a data-limite da demanda; "
                    "confirmar disponibilidade e condições."
                )

            else:
                compativel = False
                observacao = (
                    "Oferta posterior ao prazo original. "
                    "Confirmar se a demanda continua aberta "
                    "e se o comprador aceita renegociar."
                )

            correspondencias.append({
                "pedido_demanda": registro_demanda["id"],
                "pedido_oferta": oferta["pedido_oferta"],
                "produtor_id": oferta["produtor_id"],
                "produto": item.produto,
                "quantidade_solicitada": float(item.quantidade),
                "quantidade_ofertada": oferta["quantidade"],
                "quantidade_potencial": min(
                    float(item.quantidade),
                    oferta["quantidade"],
                ),
                "unidade": item.unidade,
                "compatibilidade_temporal": compativel,
                "disponibilidade_confirmada": False,
                "requer_confirmacao": True,
                "fonte": oferta["fonte"],
                "observacao": observacao,
            })

    return correspondencias
