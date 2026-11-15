"""Fila consolidada de triagem de pedidos da cooperativa."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from sabor_da_terra.regras.fatos import obter_fatos
from sabor_da_terra.triagem.alocar import AlocadorSemanal
from sabor_da_terra.triagem.historico import identificar_historico
from sabor_da_terra.triagem.orcamento import consolidar_orcamento
from sabor_da_terra.triagem.priorizar import (
    classificar_prioridade,
    classificar_urgencia,
)
from sabor_da_terra.triagem.schema import (
    PedidoTriado,
    TipoMensagem,
)
from sabor_da_terra.triagem.validar import validar_item


CAMINHO_PEDIDOS = Path(
    "tests/fixtures/triagem_15_pedidos.json"
)

TIPOS_COMPRA = {
    TipoMensagem.COMPRA,
    TipoMensagem.COMPRA_URGENTE,
}

ORDEM_PRIORIDADE = {
    "alta": 0,
    "media": 1,
    "analise": 2,
    "baixa": 3,
}


def carregar_pedidos(
    caminho: Path = CAMINHO_PEDIDOS,
) -> list[dict[str, Any]]:
    """Carrega os pedidos estruturados da Issue #9."""

    with caminho.open(encoding="utf-8") as arquivo:
        registros = json.load(arquivo)

    if not isinstance(registros, list):
        raise ValueError(
            "O arquivo de pedidos deve conter uma lista."
        )

    pedidos = []

    for registro in registros:
        if "id" not in registro or "resultado" not in registro:
            raise ValueError(
                "Registro sem id ou resultado."
            )

        pedido = PedidoTriado.model_validate(
            registro["resultado"]
        )

        pedidos.append({
            "id": registro["id"],
            "pedido": pedido,
            "data_recebimento": registro.get(
                "data_recebimento"
            ),
            "mensagem_original": registro.get(
                "mensagem_original", ""
            ),
        })

    return pedidos


def identificar_referencia_historica(
    pedido: PedidoTriado,
) -> str | None:
    """Identifica referências implícitas ao histórico."""

    textos = [
        *pedido.ambiguidades,
        *pedido.observacoes,
    ]

    texto = " ".join(textos).casefold()

    if "de sempre" in texto:
        return "de_sempre"

    if "última vez" in texto or "ultima vez" in texto:
        return "ultima_vez"

    return None


def criar_alerta(
    codigo: str,
    mensagem: str,
    fonte: str,
) -> dict[str, str]:
    """Cria um alerta com fonte identificável."""

    return {
        "codigo": codigo,
        "mensagem": mensagem,
        "fonte": fonte,
    }


def identificar_contrato(
    comprador: str | None,
) -> dict[str, Any] | None:
    """Identifica contratos usando os fatos da Issue #5."""

    contrato = obter_fatos().contrato_do_comprador(
        comprador
    )

    if contrato is None:
        return None

    return {
        "numero": contrato.numero,
        "comprador": contrato.comprador,
        "inicio": contrato.inicio.isoformat(),
        "fim": (
            contrato.fim.isoformat()
            if contrato.fim
            else None
        ),
        "exige_dap_caf": contrato.exige_dap_caf,
        "exige_sie_origem_animal": (
            contrato.exige_sie_origem_animal
        ),
        "condicoes": list(contrato.condicoes),
        "fonte": contrato.fonte,
    }


def prioridade_do_registro(
    registro: dict[str, Any],
    data_referencia: date,
) -> dict[str, Any]:
    """Classifica prioridade considerando o contrato."""

    pedido: PedidoTriado = registro["pedido"]

    contrato = identificar_contrato(
        pedido.comprador
    )

    return classificar_prioridade(
        pedido,
        data_referencia=data_referencia,
        possui_contrato=contrato is not None,
    )


def calcular_urgencia(
    registro: dict[str, Any],
    pedido: PedidoTriado,
    possui_contrato: bool,
) -> dict[str, Any]:
    """Calcula urgência ou informa a ausência de dados.

    Não inventa data ou horário de recebimento.
    """

    data_recebimento = registro.get(
        "data_recebimento"
    )

    if not data_recebimento:
        return {
            "horas_restantes": None,
            "data_recebimento": None,
            "prazo_entrega": pedido.prazo_entrega,
            "urgencia_nao_calculada": True,
            "requer_confirmacao": True,
            "aviso": (
                "Data de recebimento não informada. "
                "Não é possível calcular a urgência "
                "em horas."
            ),
            "fonte": "registro.data_recebimento",
        }

    resultado = classificar_urgencia(
        pedido,
        data_recebimento=data_recebimento,
        mensagem_original=registro.get(
            "mensagem_original", ""
        ),
        possui_contrato=possui_contrato,
    )

    return {
        **resultado,
        "urgencia_nao_calculada": (
            resultado.get("horas_restantes") is None
        ),
    }


def processar_pedido(
    registro: dict[str, Any],
    data_referencia: date,
    alocador: AlocadorSemanal,
) -> dict[str, Any]:
    """Processa um registro sem confirmar pedidos ou produção."""

    pedido: PedidoTriado = registro["pedido"]
    identificador = registro["id"]

    # --------------------------------------------------
    # 1. Contrato e prioridade
    # --------------------------------------------------

    contrato = identificar_contrato(
        pedido.comprador
    )

    prioridade = classificar_prioridade(
        pedido,
        data_referencia=data_referencia,
        possui_contrato=contrato is not None,
    )

    # --------------------------------------------------
    # 2. Urgência
    # --------------------------------------------------

    urgencia = calcular_urgencia(
        registro=registro,
        pedido=pedido,
        possui_contrato=contrato is not None,
    )

    alertas: list[dict[str, Any]] = []
    avaliacoes: list[dict[str, Any]] = []
    alocacoes: list[dict[str, Any]] = []
    historico = None

    if not registro.get("data_recebimento"):
        alertas.append(
            criar_alerta(
                "DATA_RECEBIMENTO_AUSENTE",
                (
                    "Não foi possível calcular a "
                    "urgência em horas porque a data "
                    "de recebimento não foi informada."
                ),
                "registro.data_recebimento",
            )
        )

    # --------------------------------------------------
    # 3. Ambiguidades e campos faltantes
    # --------------------------------------------------

    for ambiguidade in pedido.ambiguidades:
        alertas.append(
            criar_alerta(
                "AMBIGUIDADE",
                ambiguidade,
                "pedido_estruturado.ambiguidades",
            )
        )

    for campo in pedido.campos_faltantes:
        alertas.append(
            criar_alerta(
                "CAMPO_FALTANTE",
                f"Campo pendente: {campo}",
                "pedido_estruturado.campos_faltantes",
            )
        )

    # --------------------------------------------------
    # 4. Prazo
    # --------------------------------------------------

    if prioridade["situacao_prazo"] == "vencido":
        alertas.append(
            criar_alerta(
                "PRAZO_VENCIDO",
                (
                    "Prazo vencido. Confirmar validade "
                    "da solicitação."
                ),
                "pedido_estruturado.prazo_entrega",
            )
        )

    if prioridade["situacao_prazo"] == "nao_resolvido":
        alertas.append(
            criar_alerta(
                "PRAZO_NAO_RESOLVIDO",
                "Prazo textual exige esclarecimento.",
                "pedido_estruturado.prazo_entrega",
            )
        )

    # --------------------------------------------------
    # 5. Histórico
    # --------------------------------------------------

    expressao = identificar_referencia_historica(
        pedido
    )

    if expressao and pedido.comprador:
        historico = identificar_historico(
            comprador=pedido.comprador,
            data_referencia=data_referencia.isoformat(),
            expressao=expressao,
        )

        alertas.append(
            criar_alerta(
                "CONFIRMAR_HISTORICO",
                historico["aviso"],
                "data/financeiro.csv; data/lotes.csv",
            )
        )

    # --------------------------------------------------
    # 6. Informações contratuais
    # --------------------------------------------------

    if contrato is not None:
        alertas.append(
            criar_alerta(
                "CONTRATO_IDENTIFICADO",
                (
                    "Comprador vinculado ao contrato "
                    f"{contrato['numero']}. "
                    "Verificar exigências contratuais."
                ),
                contrato["fonte"],
            )
        )

    # --------------------------------------------------
    # 7. Registros que não são compras
    # --------------------------------------------------

    if pedido.tipo not in TIPOS_COMPRA:
        return {
            "id": identificador,
            "tipo": pedido.tipo.value,
            "comprador": pedido.comprador,
            "prioridade": prioridade["prioridade"],
            "situacao_prazo": prioridade[
                "situacao_prazo"
            ],
            "prazo_entrega": pedido.prazo_entrega,
            "contrato": contrato,
            "urgencia": urgencia,
            "orcamento": None,
            "avaliacoes": [],
            "alocacoes": [],
            "historico": historico,
            "alertas": alertas,
            "status": "analise_sem_alocacao",
            "requer_confirmacao": (
                prioridade["requer_confirmacao"]
                or historico is not None
                or urgencia.get(
                    "requer_confirmacao", False
                )
            ),
        }

    # --------------------------------------------------
    # 8. Bloqueios de alocação
    # --------------------------------------------------

    bloqueio_alocacao = (
        prioridade["situacao_prazo"]
        in {"vencido", "nao_resolvido"}
        or bool(pedido.ambiguidades)
        or historico is not None
    )

    # --------------------------------------------------
    # 9. Avaliação e alocação dos itens
    # --------------------------------------------------

    for item in pedido.itens:
        avaliacao = validar_item(
            item=item,
            comprador=pedido.comprador,
            data_entrega=pedido.prazo_entrega,
            data_referencia=data_referencia.isoformat(),
        )

        avaliacoes.append(avaliacao)

        for alerta in avaliacao.get("alertas", []):
            alertas.append({
                "codigo": alerta.get(
                    "codigo", "CONFORMIDADE"
                ),
                "mensagem": alerta.get(
                    "mensagem", ""
                ),
                "severidade": alerta.get(
                    "severidade"
                ),
                "fonte": alerta.get(
                    "fonte",
                    "regras.conformidade",
                ),
            })

        if bloqueio_alocacao:
            alocacoes.append({
                "produto": item.produto,
                "status": "aguardando_confirmacao",
                "alocacoes": [],
            })
            continue

        if not avaliacao.get("encontrado"):
            alocacoes.append({
                "produto": item.produto,
                "status": "nao_alocavel",
                "alocacoes": [],
            })
            continue

        resultado = alocador.alocar_avaliacao(
            avaliacao
        )

        alocacoes.append(resultado)

    # --------------------------------------------------
    # 10. Orçamento consolidado
    # --------------------------------------------------

    orcamento = consolidar_orcamento(
        avaliacoes
    )

    # --------------------------------------------------
    # 11. Resultado consolidado
    # --------------------------------------------------

    return {
        "id": identificador,
        "tipo": pedido.tipo.value,
        "comprador": pedido.comprador,
        "prioridade": prioridade["prioridade"],
        "situacao_prazo": prioridade[
            "situacao_prazo"
        ],
        "prazo_entrega": pedido.prazo_entrega,
        "contrato": contrato,
        "urgencia": urgencia,
        "orcamento": orcamento,
        "avaliacoes": avaliacoes,
        "alocacoes": alocacoes,
        "historico": historico,
        "alertas": alertas,
        "status": (
            "aguardando_confirmacao"
            if bloqueio_alocacao
            else "sugestao_nao_confirmada"
        ),
        "requer_confirmacao": (
            prioridade["requer_confirmacao"]
            or historico is not None
            or urgencia.get(
                "requer_confirmacao", False
            )
        ),
    }


def triar_pendentes(
    data_referencia: str,
    caminho_pedidos: Path = CAMINHO_PEDIDOS,
) -> dict[str, Any]:
    """Gera a fila consolidada para function calling."""

    referencia = date.fromisoformat(
        data_referencia
    )

    registros = carregar_pedidos(
        caminho_pedidos
    )

    alocador = AlocadorSemanal()

    # Ordena os pedidos antes da alocação.
    # Contratos também influenciam a prioridade.
    registros.sort(
        key=lambda registro: (
            ORDEM_PRIORIDADE[
                prioridade_do_registro(
                    registro,
                    data_referencia=referencia,
                )["prioridade"]
            ],
            registro["id"],
        )
    )

    fila = [
        processar_pedido(
            registro,
            data_referencia=referencia,
            alocador=alocador,
        )
        for registro in registros
    ]

    return {
        "data_referencia": referencia.isoformat(),
        "total_registros": len(fila),
        "fila": fila,
        "capacidade_semanal_sugerida": [
            {
                "produtor_id": chave[0],
                "produto": chave[1],
                "unidade": chave[2],
                "semana_inicio": chave[3].isoformat(),
                "quantidade": quantidade,
            }
            for chave, quantidade in alocador.utilizado.items()
        ],
        "confirmacoes_realizadas": False,
        "notificacoes_enviadas": False,
    }
