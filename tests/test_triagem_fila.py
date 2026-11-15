"""Testes da fila consolidada de triagem."""

from datetime import date

from sabor_da_terra.triagem.alocar import AlocadorSemanal
from sabor_da_terra.triagem.fila import (
    carregar_pedidos,
    identificar_referencia_historica,
    processar_pedido,
    triar_pendentes,
)
from sabor_da_terra.triagem.schema import PedidoTriado


def buscar_registro(registros, identificador):
    return next(
        registro
        for registro in registros
        if registro["id"] == identificador
    )


def test_carregar_15_pedidos():
    registros = carregar_pedidos()

    assert len(registros) == 15
    assert registros[0]["id"] == "PED-2026-001"


def test_fila_contem_15_registros():
    resultado = triar_pendentes("2026-10-29")

    assert resultado["total_registros"] == 15
    assert len(resultado["fila"]) == 15


def test_fila_ordenada_por_prioridade():
    resultado = triar_pendentes("2026-10-29")

    ordem = {
        "alta": 0,
        "media": 1,
        "analise": 2,
        "baixa": 3,
    }

    prioridades = [
        ordem[registro["prioridade"]]
        for registro in resultado["fila"]
    ]

    assert prioridades == sorted(prioridades)


def test_ped015_nao_e_demanda():
    resultado = triar_pendentes("2026-10-29")

    pedido = buscar_registro(
        resultado["fila"],
        "PED-2026-015",
    )

    assert pedido["tipo"] == "mensagem_produtor"
    assert pedido["alocacoes"] == []
    assert pedido["status"] == "analise_sem_alocacao"


def test_ped014_notificacao_sem_alocacao():
    resultado = triar_pendentes("2026-10-29")

    pedido = buscar_registro(
        resultado["fila"],
        "PED-2026-014",
    )

    assert pedido["tipo"] == "notificacao_oficial"
    assert pedido["prioridade"] == "alta"
    assert pedido["alocacoes"] == []


def test_ped003_requer_confirmacao():
    resultado = triar_pendentes("2026-10-29")

    pedido = buscar_registro(
        resultado["fila"],
        "PED-2026-003",
    )

    assert pedido["requer_confirmacao"] is True
    assert pedido["alocacoes"] == [] or all(
        not alocacao["alocacoes"]
        for alocacao in pedido["alocacoes"]
    )


def test_ped005_referencia_historica():
    registros = carregar_pedidos()

    registro = buscar_registro(
        registros,
        "PED-2026-005",
    )

    expressao = identificar_referencia_historica(
        registro["pedido"]
    )

    assert expressao in {
        "ultima_vez",
        "de_sempre",
    }


def test_ped006_prioridade_alta():
    resultado = triar_pendentes("2026-10-29")

    pedido = buscar_registro(
        resultado["fila"],
        "PED-2026-006",
    )

    assert pedido["prioridade"] == "alta"


def test_capacidade_nao_confirmada():
    resultado = triar_pendentes("2026-10-29")

    assert resultado["confirmacoes_realizadas"] is False
    assert resultado["notificacoes_enviadas"] is False


def test_consulta_nao_consome_capacidade():
    pedido = PedidoTriado(
        tipo="consulta",
        comprador="Cliente Teste",
    )

    registro = {
        "id": "TESTE-CONSULTA",
        "pedido": pedido,
    }

    alocador = AlocadorSemanal()

    resultado = processar_pedido(
        registro,
        data_referencia=date(2026, 10, 29),
        alocador=alocador,
    )

    assert resultado["alocacoes"] == []
    assert alocador.utilizado == {}
