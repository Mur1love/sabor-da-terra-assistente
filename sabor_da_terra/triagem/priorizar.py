"""Classificação de prioridade dos registros da triagem."""

from __future__ import annotations

from datetime import date
from typing import Any

from sabor_da_terra.triagem.schema import PedidoTriado, TipoMensagem


def classificar_prioridade(
    pedido: PedidoTriado,
    data_referencia: date,
    possui_contrato: bool = False,
) -> dict[str, Any]:
    """Classifica prioridade sem confundir urgência e prazo vencido."""

    tipos_compra = {
        TipoMensagem.COMPRA,
        TipoMensagem.COMPRA_URGENTE,
    }

    data_entrega = None
    prazo_nao_resolvido = False

    if pedido.prazo_entrega:
        try:
            data_entrega = date.fromisoformat(
                pedido.prazo_entrega
            )
        except ValueError:
            prazo_nao_resolvido = True

    dias_restantes = (
        (data_entrega - data_referencia).days
        if data_entrega
        else None
    )

    if dias_restantes is None:
        situacao_prazo = (
            "nao_resolvido"
            if prazo_nao_resolvido
            else "nao_informado"
        )
    elif dias_restantes < 0:
        situacao_prazo = "vencido"
    elif dias_restantes <= 2:
        situacao_prazo = "proximo"
    else:
        situacao_prazo = "futuro"

    motivos = []

    if pedido.tipo == TipoMensagem.NOTIFICACAO_OFICIAL:
        prioridade = "alta"
        motivos.append("Notificação oficial exige análise.")

    elif pedido.tipo == TipoMensagem.COMPRA_URGENTE:
        prioridade = "alta"
        motivos.append("Compra marcada como urgente.")

    elif pedido.tipo in tipos_compra:
        if (
            dias_restantes is not None
            and dias_restantes <= 2
        ):
            prioridade = "alta"
            motivos.append("Prazo de entrega próximo ou vencido.")

        elif possui_contrato and (
            dias_restantes is not None
            and dias_restantes <= 7
        ):
            prioridade = "alta"
            motivos.append(
                "Compra contratual com prazo de até sete dias."
            )

        else:
            prioridade = "media"
            motivos.append("Compra aguardando processamento.")

    elif pedido.tipo == TipoMensagem.COTACAO:
        prioridade = "media"
        motivos.append("Solicitação de cotação.")

    elif pedido.tipo == TipoMensagem.MENSAGEM_PRODUTOR:
        prioridade = "analise"
        motivos.append(
            "Mensagem de produtor requer tratamento específico."
        )

    else:
        prioridade = "baixa"
        motivos.append("Consulta informativa.")

    if situacao_prazo == "vencido":
        motivos.append(
            "Prazo vencido: confirmar se a solicitação continua válida."
        )

    if prazo_nao_resolvido:
        motivos.append(
            "Prazo textual não convertido para uma data exata."
        )

    if pedido.ambiguidades:
        motivos.append(
            "Existem ambiguidades que precisam ser esclarecidas."
        )

    return {
        "prioridade": prioridade,
        "situacao_prazo": situacao_prazo,
        "dias_restantes": dias_restantes,
        "possui_contrato": possui_contrato,
        "motivos": motivos,
        "requer_confirmacao": (
            situacao_prazo in {"vencido", "nao_resolvido"}
            or bool(pedido.ambiguidades)
        ),
    }
