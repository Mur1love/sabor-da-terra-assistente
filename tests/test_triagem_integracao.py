"""Testes de integração de contratos, orçamento e urgência."""

from sabor_da_terra.triagem.fila import triar_pendentes


def buscar(fila, identificador):
    return next(
        pedido for pedido in fila
        if pedido["id"] == identificador
    )


def test_pnae_identifica_contrato():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-004")

    assert pedido["contrato"] is not None
    assert pedido["contrato"]["numero"] == "045/2026-PNAE"
    assert pedido["contrato"]["exige_dap_caf"] is True


def test_pnae_orcamento_parcial():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-004")

    orcamento = pedido["orcamento"]

    assert orcamento["total_estimado"] == 4475.0
    assert orcamento["itens_com_preco"] == 8
    assert orcamento["itens_sem_preco"] == 1
    assert orcamento["orcamento_completo"] is False


def test_pnae_restricao_sem_preco():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-004")

    assert pedido["orcamento"]["itens_com_restricao"] >= 1


def test_pnae_preserva_alertas_documentais():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-004")

    codigos = {
        alerta["codigo"]
        for alerta in pedido["alertas"]
    }

    assert "DAP_CAF_NAO_COMPROVADA" in codigos
    assert "SIE_EXIGIDO" in codigos

    assert all(
        alerta.get("fonte")
        for alerta in pedido["alertas"]
    )


def test_ped006_possui_urgencia():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-006")

    assert pedido["urgencia"] is not None
    assert isinstance(pedido["urgencia"], dict)


def test_oferta_produtor_sem_orcamento():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-015")

    assert pedido["orcamento"] is None
    assert pedido["alocacoes"] == []


def test_fila_mantem_15_registros():
    resultado = triar_pendentes("2026-10-29")

    assert resultado["total_registros"] == 15
    assert resultado["confirmacoes_realizadas"] is False
    assert resultado["notificacoes_enviadas"] is False
