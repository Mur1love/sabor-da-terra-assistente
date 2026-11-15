"""Análise informativa de cotações e consultas da cooperativa."""

from __future__ import annotations

from datetime import date
from typing import Any

from sabor_da_terra.triagem.orcamento import consolidar_orcamento
from sabor_da_terra.triagem.schema import (
    PedidoTriado,
    TipoMensagem,
)
from sabor_da_terra.triagem.validar import validar_item


TIPOS_COMERCIAIS = {
    TipoMensagem.COTACAO,
    TipoMensagem.CONSULTA,
}

TERMOS_DOCUMENTAIS = {
    "dap_caf": (
        "dap/caf",
        "dap",
        "caf",
    ),
    "certificacao_organica": (
        "certificação orgânica",
        "certificacao organica",
    ),
    "certificacao_internacional": (
        "certificação internacional",
        "certificacao internacional",
        "equivalente internacional",
    ),
    "rastreabilidade": (
        "rastreabilidade",
    ),
    "laudo_sanitario": (
        "laudo sanitário",
        "laudo sanitario",
    ),
    "certificado_fitossanitario": (
        "certificados fitossanitários",
        "certificados fitossanitarios",
        "certificado fitossanitário",
        "certificado fitossanitario",
    ),
    "nota_fiscal": (
        "nota fiscal",
        "dados de nf",
    ),
}


def criar_pendencia(
    codigo: str,
    mensagem: str,
    fonte: str,
) -> dict[str, str]:
    """Cria pendência rastreável."""

    return {
        "codigo": codigo,
        "mensagem": mensagem,
        "fonte": fonte,
    }


def data_valida(
    valor: str | None,
) -> bool:
    """Verifica se a data está no formato ISO."""

    if not valor:
        return False

    try:
        date.fromisoformat(valor)
    except ValueError:
        return False

    return True


def identificar_documentos_solicitados(
    pedido: PedidoTriado,
) -> list[dict[str, Any]]:
    """Identifica exigências documentais mencionadas no pedido.

    Identificar uma exigência não comprova que o documento existe.
    """

    texto = " ".join(pedido.observacoes).casefold()
    documentos = []

    for codigo, termos in TERMOS_DOCUMENTAIS.items():
        if any(termo in texto for termo in termos):
            documentos.append({
                "tipo": codigo,
                "situacao": "comprovacao_pendente",
                "fonte": "pedido_estruturado.observacoes",
            })

    return documentos


def analisar_consulta(
    pedido: PedidoTriado,
    data_referencia: str,
) -> dict[str, Any]:
    """Analisa cotação ou consulta sem reservar capacidade.

    A conformidade completa só é calculada quando há uma data
    de entrega válida. Nenhuma avaliação confirma estoque,
    certificação documental ou disponibilidade futura.
    """

    if pedido.tipo not in TIPOS_COMERCIAIS:
        raise ValueError(
            "A análise comercial aceita apenas cotação ou consulta."
        )

    referencia = date.fromisoformat(data_referencia)
    prazo_valido = data_valida(pedido.prazo_entrega)

    data_entrega = (
        date.fromisoformat(pedido.prazo_entrega)
        if prazo_valido
        else None
    )

    prazo_utilizavel = (
        data_entrega is not None
        and data_entrega >= referencia
    )

    informacoes_disponiveis: list[dict[str, Any]] = []
    pendencias: list[dict[str, str]] = []
    avaliacoes: list[dict[str, Any]] = []

    documentos = identificar_documentos_solicitados(
        pedido
    )

    # 1. Verificar data e prazo.
    if not pedido.prazo_entrega:
        pendencias.append(
            criar_pendencia(
                "PRAZO_ENTREGA_AUSENTE",
                (
                    "Informar a data de entrega para avaliar "
                    "safra, capacidade e certificações na data."
                ),
                "pedido_estruturado.prazo_entrega",
            )
        )

    elif not prazo_valido:
        pendencias.append(
            criar_pendencia(
                "PRAZO_ENTREGA_NAO_RESOLVIDO",
                (
                    f"O prazo '{pedido.prazo_entrega}' "
                    "precisa ser convertido em uma data exata."
                ),
                "pedido_estruturado.prazo_entrega",
            )
        )

    elif not prazo_utilizavel:
        pendencias.append(
            criar_pendencia(
                "PRAZO_ENTREGA_VENCIDO",
                "A data de entrega é anterior à referência.",
                "pedido_estruturado.prazo_entrega",
            )
        )

    # 2. Registrar campos faltantes.
    for campo in pedido.campos_faltantes:
        pendencias.append(
            criar_pendencia(
                "CAMPO_FALTANTE",
                f"Confirmar campo: {campo}.",
                "pedido_estruturado.campos_faltantes",
            )
        )

    # 3. Registrar ambiguidades.
    for ambiguidade in pedido.ambiguidades:
        pendencias.append(
            criar_pendencia(
                "AMBIGUIDADE",
                ambiguidade,
                "pedido_estruturado.ambiguidades",
            )
        )

    # 4. Consultas sem itens específicos.
    if not pedido.itens:
        pendencias.append(
            criar_pendencia(
                "ITENS_NAO_ESPECIFICADOS",
                (
                    "É necessário definir quais produtos "
                    "serão consultados ou cotados."
                ),
                "pedido_estruturado.itens",
            )
        )

    # 5. Identificar exigências documentais.
    for documento in documentos:
        pendencias.append(
            criar_pendencia(
                "DOCUMENTO_A_COMPROVAR",
                (
                    "Verificar a documentação exigida: "
                    f"{documento['tipo']}."
                ),
                documento["fonte"],
            )
        )

    # 6. Avaliar cada item.
    for item in pedido.itens:
        informacao = {
            "produto": item.produto,
            "quantidade": item.quantidade,
            "unidade": item.unidade,
            "exige_organico": item.exige_organico,
            "opcional": item.opcional,
            "fonte": "pedido_estruturado.itens",
        }

        informacoes_disponiveis.append(informacao)

        if item.quantidade is None:
            pendencias.append(
                criar_pendencia(
                    "QUANTIDADE_A_CONFIRMAR",
                    (
                        f"Informar quantidade de "
                        f"{item.produto}."
                    ),
                    "pedido_estruturado.itens",
                )
            )
            continue

        if not prazo_utilizavel:
            pendencias.append(
                criar_pendencia(
                    "AVALIACAO_DEPENDE_DO_PRAZO",
                    (
                        f"A disponibilidade de {item.produto} "
                        "depende da data de entrega."
                    ),
                    "pedido_estruturado.prazo_entrega",
                )
            )
            continue

        avaliacao = validar_item(
            item=item,
            comprador=pedido.comprador,
            data_entrega=data_entrega.isoformat(),
            data_referencia=data_referencia,
        )

        avaliacoes.append(avaliacao)

        # Preservar alertas e fontes da Issue #5.
        for alerta in avaliacao.get("alertas", []):
            fontes = alerta.get("fontes", [])
            fonte = alerta.get("fonte")

            if not fonte and fontes:
                fonte = "; ".join(str(f) for f in fontes)

            pendencias.append({
                "codigo": alerta.get(
                    "codigo", "CONFORMIDADE"
                ),
                "mensagem": alerta.get(
                    "mensagem", ""
                ),
                "fonte": fonte or "regras.conformidade",
            })

        if not avaliacao.get("encontrado"):
            pendencias.append(
                criar_pendencia(
                    "ITEM_NAO_AVALIADO",
                    avaliacao.get(
                        "aviso",
                        f"Não foi possível avaliar {item.produto}.",
                    ),
                    "catalogo; pedido_estruturado.itens",
                )
            )

    # 7. Orçamento apenas para itens efetivamente avaliados.
    orcamento = (
        consolidar_orcamento(avaliacoes)
        if avaliacoes
        else None
    )

    # Um orçamento com itens não avaliados não é completo.
    if orcamento is not None:
        orcamento["orcamento_completo"] = (
            orcamento["orcamento_completo"]
            and len(avaliacoes) == len(pedido.itens)
            and all(
                avaliacao.get("encontrado", False)
                for avaliacao in avaliacoes
            )
            and all(
                avaliacao.get("pode_atender", False)
                for avaliacao in avaliacoes
            )
            and not pedido.ambiguidades
        )

    return {
        "tipo": pedido.tipo.value,
        "comprador": pedido.comprador,
        "prazo_entrega": pedido.prazo_entrega,
        "data_referencia": data_referencia,
        "informacoes_disponiveis": informacoes_disponiveis,
        "documentos_solicitados": documentos,
        "avaliacoes": avaliacoes,
        "orcamento": orcamento,
        "pendencias": pendencias,
        "quantidade_itens": len(pedido.itens),
        "quantidade_itens_avaliados": len(avaliacoes),
        "pode_responder_parcialmente": bool(
            informacoes_disponiveis or documentos
        ),
        "requer_confirmacao": bool(
            pendencias
            or not prazo_utilizavel
        ),
        "capacidade_reservada": False,
        "pedido_confirmado": False,
        "aviso": (
            "Análise informativa. Não representa reserva "
            "de capacidade, disponibilidade garantida "
            "ou confirmação de venda."
        ),
    }
