"""Classificação de prioridade e urgência dos registros da triagem."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from sabor_da_terra.triagem.schema import (
    PedidoTriado,
    TipoMensagem,
)


TIPOS_COMPRA = {
    TipoMensagem.COMPRA,
    TipoMensagem.COMPRA_URGENTE,
}

SINAIS_URGENCIA = (
    "urgente",
    "hoje",
    "imediatamente",
    "o quanto antes",
    "pra ontem",
)


def classificar_prioridade(
    pedido: PedidoTriado,
    data_referencia: date,
    possui_contrato: bool = False,
) -> dict[str, Any]:
    """Classifica prioridade por tipo, prazo e contrato."""

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
        if data_entrega is not None
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
        motivos.append(
            "Notificação oficial exige análise."
        )

    elif pedido.tipo == TipoMensagem.COMPRA_URGENTE:
        prioridade = "alta"
        motivos.append(
            "Compra marcada como urgente."
        )

    elif pedido.tipo in TIPOS_COMPRA:
        if (
            dias_restantes is not None
            and dias_restantes <= 2
        ):
            prioridade = "alta"
            motivos.append(
                "Prazo de entrega próximo ou vencido."
            )

        elif (
            possui_contrato
            and dias_restantes is not None
            and dias_restantes <= 7
        ):
            prioridade = "alta"
            motivos.append(
                "Compra contratual com prazo de até sete dias."
            )

        else:
            prioridade = "media"
            motivos.append(
                "Compra aguardando processamento."
            )

    elif pedido.tipo == TipoMensagem.COTACAO:
        prioridade = "media"
        motivos.append(
            "Solicitação de cotação."
        )

    elif pedido.tipo == TipoMensagem.MENSAGEM_PRODUTOR:
        prioridade = "analise"
        motivos.append(
            "Mensagem de produtor requer tratamento específico."
        )

    else:
        prioridade = "baixa"
        motivos.append(
            "Consulta informativa."
        )

    if situacao_prazo == "vencido":
        motivos.append(
            "Prazo vencido: confirmar se a solicitação "
            "continua válida."
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
            situacao_prazo in {
                "vencido",
                "nao_resolvido",
            }
            or bool(pedido.ambiguidades)
        ),
    }


def classificar_urgencia(
    pedido: PedidoTriado,
    data_recebimento: str | datetime,
    mensagem_original: str = "",
    possui_contrato: bool = False,
) -> dict[str, Any]:
    """Calcula urgência por horas e sinais textuais."""

    recebimento = (
        datetime.fromisoformat(data_recebimento)
        if isinstance(data_recebimento, str)
        else data_recebimento
    )

    horas_restantes = None
    horario_estimado = False
    prazo_nao_resolvido = False
    motivos = []

    if pedido.prazo_entrega:
        try:
            data_prazo = date.fromisoformat(
                pedido.prazo_entrega
            )

            # O schema da Etapa 9 informa apenas a data.
            # Fim do dia é usado como limite provisório,
            # não como horário confirmado de entrega.
            prazo = datetime.combine(
                data_prazo,
                time(23, 59, 59),
                tzinfo=recebimento.tzinfo,
            )

            horario_estimado = True

            horas_restantes = round(
                (
                    prazo - recebimento
                ).total_seconds() / 3600,
                2,
            )

        except ValueError:
            prazo_nao_resolvido = True
            motivos.append(
                "Prazo não convertido para data exata."
            )

    texto = mensagem_original.casefold()

    sinais_textuais = [
        expressao
        for expressao in SINAIS_URGENCIA
        if expressao in texto
    ]

    # Aproveita a classificação produzida pelo Gemini
    # na extração estruturada da Etapa 9.
    urgencia_modelo = (
        pedido.tipo == TipoMensagem.COMPRA_URGENTE
    )

    prazo_vencido = (
        horas_restantes is not None
        and horas_restantes < 0
    )

    # Mensagens de produtores não são compras.
    if pedido.tipo == TipoMensagem.NOTIFICACAO_OFICIAL:
        prioridade = "alta"
        motivos.append(
            "Notificação oficial exige análise."
        )

    elif pedido.tipo == TipoMensagem.MENSAGEM_PRODUTOR:
        prioridade = "analise"
        motivos.append(
            "Mensagem de produtor requer tratamento específico."
        )

    elif pedido.tipo in TIPOS_COMPRA:
        if urgencia_modelo or sinais_textuais:
            prioridade = "alta"
            motivos.append(
                "Urgência identificada na mensagem."
            )

        elif (
            horas_restantes is not None
            and horas_restantes <= 48
        ):
            prioridade = "alta"
            motivos.append(
                "Prazo de até 48 horas ou vencido."
            )

        elif (
            possui_contrato
            and horas_restantes is not None
            and horas_restantes <= 168
        ):
            prioridade = "alta"
            motivos.append(
                "Contrato com prazo de até sete dias."
            )

        else:
            prioridade = "media"
            motivos.append(
                "Compra aguardando processamento."
            )

    elif pedido.tipo == TipoMensagem.COTACAO:
        prioridade = "media"
        motivos.append(
            "Solicitação de cotação."
        )

    else:
        prioridade = "baixa"
        motivos.append(
            "Consulta informativa."
        )

    if prazo_vencido:
        motivos.append(
            "Prazo vencido: confirmar se a solicitação "
            "continua válida."
        )

    if horario_estimado:
        motivos.append(
            "Horário de entrega não informado; "
            "cálculo provisório até o fim do dia."
        )

    if pedido.ambiguidades:
        motivos.append(
            "Existem ambiguidades que precisam "
            "ser esclarecidas."
        )

    requer_confirmacao = (
        prazo_vencido
        or prazo_nao_resolvido
        or bool(pedido.ambiguidades)
        or (
            pedido.tipo in TIPOS_COMPRA
            and horas_restantes is None
        )
    )

    fontes = ["pedido_estruturado"]

    if mensagem_original:
        fontes.append("mensagem_original")

    return {
        "prioridade": prioridade,
        "horas_restantes": horas_restantes,
        "prazo_vencido": prazo_vencido,
        "prazo_nao_resolvido": prazo_nao_resolvido,
        "horario_estimado": horario_estimado,
        "sinais_textuais": sinais_textuais,
        "urgencia_modelo": urgencia_modelo,
        "possui_contrato": possui_contrato,
        "motivos": motivos,
        "requer_confirmacao": requer_confirmacao,
        "fontes": fontes,
    }
