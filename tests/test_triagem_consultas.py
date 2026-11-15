"""Testes de cotações e consultas da Issue #10."""

from sabor_da_terra.triagem.fila import triar_pendentes


def buscar(fila, identificador):
    return next(
        pedido
        for pedido in fila
        if pedido["id"] == identificador
    )


def codigos(pedido):
    return {
        alerta["codigo"]
        for alerta in pedido["alertas"]
    }


def test_ped007_avalia_cotacao_com_data():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-007")

    analise = pedido["analise_comercial"]

    assert analise is not None
    assert analise["quantidade_itens"] == 9
    assert analise["quantidade_itens_avaliados"] == 9
    assert len(pedido["avaliacoes"]) == 9
    assert pedido["alocacoes"] == []
    assert pedido["orcamento"] is not None


def test_ped007_preserva_problemas_de_conformidade():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-007")

    avaliados = {
        avaliacao["item"]["produto"]: avaliacao
        for avaliacao in pedido["avaliacoes"]
        if avaliacao.get("encontrado")
    }

    assert "cajá" in avaliados
    assert "frango caipira" in avaliados

    assert avaliados["cajá"]["alertas"]
    assert avaliados["frango caipira"]["alertas"]

    assert all(
        alerta.get("fonte")
        for alerta in pedido["alertas"]
    )


def test_ped008_sem_prazo_nao_inventa_disponibilidade():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-008")

    assert "PRAZO_ENTREGA_AUSENTE" in codigos(pedido)
    assert pedido["avaliacoes"] == []
    assert pedido["orcamento"] is None
    assert pedido["alocacoes"] == []


def test_ped009_identifica_documentos_e_ambiguidades():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-009")

    analise = pedido["analise_comercial"]

    tipos = {
        documento["tipo"]
        for documento in analise["documentos_solicitados"]
    }

    assert "certificacao_organica" in tipos
    assert "rastreabilidade" in tipos
    assert "dap_caf" in tipos

    assert "AMBIGUIDADE" in codigos(pedido)
    assert pedido["alocacoes"] == []


def test_ped010_sem_itens_especificos():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-010")

    assert "ITENS_NAO_ESPECIFICADOS" in codigos(pedido)
    assert pedido["orcamento"] is None
    assert pedido["alocacoes"] == []


def test_ped011_certificacao_internacional_pendente():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-011")

    documentos = pedido[
        "analise_comercial"
    ]["documentos_solicitados"]

    assert any(
        documento["tipo"] == "certificacao_internacional"
        and documento["situacao"] == "comprovacao_pendente"
        for documento in documentos
    )

    assert pedido["orcamento"] is None
    assert pedido["alocacoes"] == []


def test_ped013_prazo_textual_nao_e_data():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-013")

    assert "PRAZO_ENTREGA_NAO_RESOLVIDO" in codigos(pedido)
    assert pedido["avaliacoes"] == []
    assert pedido["orcamento"] is None
    assert pedido["alocacoes"] == []


def test_consultas_nao_reservam_capacidade():
    resultado = triar_pendentes("2026-10-29")

    ids = {
        "PED-2026-007",
        "PED-2026-008",
        "PED-2026-009",
        "PED-2026-010",
        "PED-2026-011",
        "PED-2026-013",
    }

    for identificador in ids:
        pedido = buscar(
            resultado["fila"],
            identificador,
        )

        assert pedido["alocacoes"] == []
        assert pedido["analise_comercial"][
            "capacidade_reservada"
        ] is False
        assert pedido["analise_comercial"][
            "pedido_confirmado"
        ] is False


def test_todos_alertas_comerciais_possuem_fonte():
    resultado = triar_pendentes("2026-10-29")

    for pedido in resultado["fila"]:
        if pedido["tipo"] not in {"cotacao", "consulta"}:
            continue

        assert all(
            alerta.get("fonte")
            for alerta in pedido["alertas"]
        )


def test_fila_continua_com_15_registros():
    resultado = triar_pendentes("2026-10-29")

    assert resultado["total_registros"] == 15
    assert resultado["confirmacoes_realizadas"] is False
    assert resultado["notificacoes_enviadas"] is False


def test_ped010_retorna_catalogo_organico():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-010")

    catalogo = pedido["analise_comercial"]["catalogo_organico"]

    assert catalogo is not None
    assert catalogo["total_produtos"] > 0
    assert catalogo["produtos"]
    assert catalogo["capacidade_reservada"] is False


def test_ped010_produtores_ativos_e_certificados():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-010")

    produtos = pedido[
        "analise_comercial"
    ]["catalogo_organico"]["produtos"]

    for produto in produtos:
        assert produto["produtores"]

        for produtor in produto["produtores"]:
            assert produtor["certificacao_vigente"] is True
            assert produtor["validade_certificacao"]
            assert produtor["produtor_id"] not in {
                "P008",
                "P015",
            }


def test_ped010_precos_com_fontes():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-010")

    produtos = pedido[
        "analise_comercial"
    ]["catalogo_organico"]["produtos"]

    precos = [
        preco
        for produto in produtos
        for preco in produto["precos"]
    ]

    assert precos
    assert all(preco["fonte"] for preco in precos)

    for preco in precos:
        if preco["preco_disponivel"]:
            assert preco["preco_unitario"] is not None
            assert preco["preco_unitario"] > 0


def test_ped010_nao_confirma_disponibilidade():
    resultado = triar_pendentes("2026-10-29")
    pedido = buscar(resultado["fila"], "PED-2026-010")

    analise = pedido["analise_comercial"]
    catalogo = analise["catalogo_organico"]

    assert pedido["alocacoes"] == []
    assert pedido["orcamento"] is None
    assert analise["capacidade_reservada"] is False
    assert analise["pedido_confirmado"] is False
    assert catalogo["disponibilidade_futura_confirmada"] is False
    assert "DISPONIBILIDADE_FUTURA_A_CONFIRMAR" in codigos(
        pedido
    )
