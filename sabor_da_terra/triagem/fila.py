"""Fila consolidada de triagem de pedidos da cooperativa."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sabor_da_terra.triagem.alocar import AlocadorSemanal
from sabor_da_terra.triagem.historico import identificar_historico
from sabor_da_terra.triagem.priorizar import classificar_prioridade
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
    """Carrega os pedidos estruturados da Etapa 9."""

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
    """Identifica referências implícitas no pedido."""

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
    """Cria um alerta com origem identificável."""

    return {
        "codigo": codigo,
        "mensagem": mensagem,
        "fonte": fonte,
    }


def processar_pedido(
    registro: dict[str, Any],
    data_referencia: date,
    alocador: AlocadorSemanal,
) -> dict[str, Any]:
    """Processa um registro sem confirmar pedidos ou produção."""

    pedido: PedidoTriado = registro["pedido"]
    identificador = registro["id"]

    prioridade = classificar_prioridade(
        pedido,
        data_referencia=data_referencia,
    )

    alertas = []
    avaliacoes = []
    alocacoes = []
    historico = None

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

    if prioridade["situacao_prazo"] == "vencido":
        alertas.append(
            criar_alerta(
                "PRAZO_VENCIDO",
                "Prazo vencido. Confirmar validade da solicitação.",
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

    expressao = identificar_referencia_historica(pedido)

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

    # Ofertas, consultas e notificações não são
    # tratadas como demandas para alocação.
    if pedido.tipo not in TIPOS_COMPRA:
        return {
            "id": identificador,
            "tipo": pedido.tipo.value,
            "comprador": pedido.comprador,
            "prioridade": prioridade["prioridade"],
            "situacao_prazo": prioridade["situacao_prazo"],
            "prazo_entrega": pedido.prazo_entrega,
            "avaliacoes": [],
            "alocacoes": [],
            "historico": historico,
            "alertas": alertas,
            "status": "analise_sem_alocacao",
            "requer_confirmacao": (
                prioridade["requer_confirmacao"]
                or historico is not None
            ),
        }

    # Se o prazo venceu ou há ambiguidades,
    # não reservamos capacidade de produtores.
    bloqueio_alocacao = (
        prioridade["situacao_prazo"]
        in {"vencido", "nao_resolvido"}
        or bool(pedido.ambiguidades)
        or historico is not None
    )

    for item in pedido.itens:
        avaliacao = validar_item(
            item=item,
            comprador=pedido.comprador,
            data_entrega=pedido.prazo_entrega,
            data_referencia=data_referencia.isoformat(),
        )

        avaliacoes.append(avaliacao)

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

    return {
        "id": identificador,
        "tipo": pedido.tipo.value,
        "comprador": pedido.comprador,
        "prioridade": prioridade["prioridade"],
        "situacao_prazo": prioridade["situacao_prazo"],
        "prazo_entrega": pedido.prazo_entrega,
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

    # Primeiro prioriza; depois processa.
    # Isso permite que pedidos mais urgentes
    # utilizem a capacidade semanal primeiro.
    registros.sort(
        key=lambda registro: (
            ORDEM_PRIORIDADE[
                classificar_prioridade(
                    registro["pedido"],
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
