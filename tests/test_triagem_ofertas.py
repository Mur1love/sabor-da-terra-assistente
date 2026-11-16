"""Testes de correspondência entre ofertas e demandas."""

from sabor_da_terra.triagem.fila import (
    carregar_pedidos,
    triar_pendentes,
)
from sabor_da_terra.triagem.ofertas import (
    cruzar_ofertas,
    identificar_ofertas,
)


def test_identificar_oferta_queijo_coalho_p003():
    registros = carregar_pedidos()
    ofertas = identificar_ofertas(registros)

    oferta = next(
        oferta for oferta in ofertas
        if oferta["pedido_oferta"] == "PED-2026-015"
        and oferta["produto"] == "queijo coalho"
    )

    assert oferta["produtor_id"] == "P003"
    assert oferta["quantidade"] == 200.0
    assert oferta["unidade"] == "kg"
    assert oferta["confirmada"] is False


def test_nao_interpretar_manteiga_ambigua():
    registros = carregar_pedidos()
    ofertas = identificar_ofertas(registros)

    assert not any(
        oferta["pedido_oferta"] == "PED-2026-015"
        and oferta["produto"] == "manteiga"
        for oferta in ofertas
    )


def test_cruzamento_ped006_ped015():
    registros = carregar_pedidos()
    ofertas = identificar_ofertas(registros)

    demanda = next(
        registro for registro in registros
        if registro["id"] == "PED-2026-006"
    )

    correspondencias = cruzar_ofertas(demanda, ofertas)

    correspondencia = next(
        item for item in correspondencias
        if item["pedido_oferta"] == "PED-2026-015"
    )

    assert correspondencia["produto"] == "queijo coalho"
    assert correspondencia["produtor_id"] == "P003"
    assert correspondencia["quantidade_potencial"] == 200.0
    assert correspondencia["compatibilidade_temporal"] is False
    assert correspondencia["disponibilidade_confirmada"] is False
    assert correspondencia["requer_confirmacao"] is True

def test_fila_nao_utiliza_oferta_futura():
    """Uma oferta futura não pode influenciar a triagem."""

    resultado = triar_pendentes("2026-10-29")

    pedido = next(
        item for item in resultado["fila"]
        if item["id"] == "PED-2026-006"
    )

    assert pedido["correspondencias_ofertas"] == []

    assert not any(
        alerta["codigo"] == "OFERTA_POSTERIOR_AO_PRAZO"
        for alerta in pedido["alertas"]
    )

    assert resultado["confirmacoes_realizadas"] is False
    assert resultado["notificacoes_enviadas"] is False


def test_fila_registra_oferta_sem_confirmar():
    """Uma oferta conhecida pode ser relacionada, mas não confirmada."""

    resultado = triar_pendentes("2026-10-30")

    pedido = next(
        item for item in resultado["fila"]
        if item["id"] == "PED-2026-006"
    )

    correspondencias = pedido["correspondencias_ofertas"]

    oferta = next(
        item for item in correspondencias
        if item["pedido_oferta"] == "PED-2026-015"
    )

    assert oferta["produtor_id"] == "P003"
    assert oferta["produto"] == "queijo coalho"
    assert oferta["quantidade_potencial"] == 200.0
    assert oferta["compatibilidade_temporal"] is False
    assert oferta["disponibilidade_confirmada"] is False
    assert oferta["requer_confirmacao"] is True

    assert any(
        alerta["codigo"] == "OFERTA_POSTERIOR_AO_PRAZO"
        for alerta in pedido["alertas"]
    )

    assert resultado["confirmacoes_realizadas"] is False
    assert resultado["notificacoes_enviadas"] is False
