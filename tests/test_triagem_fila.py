"""Testes da fila consolidada de triagem."""

import json
from datetime import date

from sabor_da_terra.triagem.alocar import AlocadorSemanal
from sabor_da_terra.triagem.fila import (
    CAMINHO_PEDIDOS,
    carregar_pedidos,
    identificar_referencia_historica,
    processar_pedido,
    recebido_ate,
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
    resultado = triar_pendentes("2026-10-30")

    assert resultado["total_registros"] == 15
    assert len(resultado["fila"]) == 15


def test_fila_ordenada_por_prioridade():
    resultado = triar_pendentes("2026-10-30")

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
    resultado = triar_pendentes("2026-10-30")

    pedido = buscar_registro(
        resultado["fila"],
        "PED-2026-015",
    )

    assert pedido["tipo"] == "mensagem_produtor"
    assert pedido["alocacoes"] == []
    assert pedido["status"] == "analise_sem_alocacao"


def test_ped014_notificacao_sem_alocacao():
    resultado = triar_pendentes("2026-10-30")

    pedido = buscar_registro(
        resultado["fila"],
        "PED-2026-014",
    )

    assert pedido["tipo"] == "notificacao_oficial"
    assert pedido["prioridade"] == "alta"
    assert pedido["alocacoes"] == []


def test_ped003_requer_confirmacao():
    resultado = triar_pendentes("2026-10-30")

    pedido = buscar_registro(
        resultado["fila"],
        "PED-2026-003",
    )

    assert pedido["requer_confirmacao"] is True
    # Nenhuma sugestão definitiva: só reserva condicionada à confirmação.
    assert all(
        sugestao["condicionada"]
        for alocacao in pedido["alocacoes"]
        for sugestao in alocacao["alocacoes"]
    )


def test_fila_so_inclui_mensagens_ja_recebidas():
    """Mensagens recebidas depois da data da triagem não entram na fila."""
    resultado = triar_pendentes("2026-10-29")

    ids = {registro["id"] for registro in resultado["fila"]}

    assert resultado["total_registros"] == 10
    assert not ids & {
        "PED-2026-011",
        "PED-2026-012",
        "PED-2026-013",
        "PED-2026-014",
        "PED-2026-015",
    }


def test_urgente_do_mesmo_dia_abre_a_fila():
    resultado = triar_pendentes("2026-10-30")

    ordem = [registro["id"] for registro in resultado["fila"]]

    assert ordem[0] == "PED-2026-006"
    assert ordem.index("PED-2026-003") < ordem.index("PED-2026-001")


def test_prioridade_da_fila_vem_da_urgencia():
    resultado = triar_pendentes("2026-10-30")

    for registro in resultado["fila"]:
        if not registro["urgencia"]["urgencia_nao_calculada"]:
            assert registro["prioridade"] == registro["urgencia"]["prioridade"]


def test_capacidade_soma_todos_os_pedidos_da_semana():
    """Pedidos aguardando confirmação também entram na soma da semana."""
    resultado = triar_pendentes("2026-10-30")

    queijo = next(
        linha for linha in resultado["demanda_semanal"]
        if linha["produto"] == "queijo coalho"
        and linha["semana_inicio"] == "2026-10-26"
    )

    assert queijo["pedidos"] == ["PED-2026-001", "PED-2026-005", "PED-2026-006"]
    assert queijo["demanda_total"] == 240

    p003 = next(
        linha for linha in resultado["capacidade_semanal_sugerida"]
        if linha["produtor_id"] == "P003" and linha["produto"] == "queijo coalho"
    )

    # O P003 chega ao máximo da ficha técnica (200 kg) e não passa dele.
    assert p003["quantidade"] == 200


def test_raizes_prefere_organico():
    """Contrato Raízes: produtor com orgânico vigente vem primeiro."""
    resultado = triar_pendentes("2026-10-30")

    pedido = buscar_registro(resultado["fila"], "PED-2026-001")
    queijo = next(
        alocacao for alocacao in pedido["alocacoes"]
        if alocacao["produto"] == "queijo coalho"
    )

    assert queijo["alocacoes"][0]["produtor_id"] == "P007"


def test_item_nao_alocavel_mantem_produto():
    resultado = triar_pendentes("2026-10-30")

    pedido = buscar_registro(resultado["fila"], "PED-2026-004")

    assert all(alocacao.get("produto") for alocacao in pedido["alocacoes"])


def test_triagem_roda_fora_da_raiz(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert triar_pendentes("2026-10-30")["total_registros"] == 15


def test_salvar_json(tmp_path):
    import json

    from sabor_da_terra.triagem.exportar import salvar_json

    caminho = salvar_json(triar_pendentes("2026-10-30"), tmp_path / "fila.json")
    dados = json.loads(caminho.read_text(encoding="utf-8"))

    assert dados["total_registros"] == 15
    assert dados["fila"][0]["id"] == "PED-2026-006"


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
    resultado = triar_pendentes("2026-10-30")

    pedido = buscar_registro(
        resultado["fila"],
        "PED-2026-006",
    )

    assert pedido["prioridade"] == "alta"


def test_capacidade_nao_confirmada():
    resultado = triar_pendentes("2026-10-30")

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


def codigos(registro):
    return {alerta["codigo"] for alerta in registro["alertas"]}


def test_capacidade_dentro_do_limite_nao_gera_alerta():
    """No dataset a semana de 26/10 pede 240 kg de queijo, abaixo dos 480 kg documentados."""
    resultado = triar_pendentes("2026-10-30")

    assert not any(linha["excede_capacidade"] for linha in resultado["demanda_semanal"])
    assert all(
        "CAPACIDADE_SEMANAL_EXCEDIDA" not in codigos(registro)
        for registro in resultado["fila"]
    )


def test_capacidade_semanal_excedida_gera_alerta(tmp_path):
    """Com o PED-006 pedindo 500 kg, a semana soma 540 kg e passa dos 480 kg."""
    registros = json.loads(CAMINHO_PEDIDOS.read_text(encoding="utf-8"))
    ped006 = buscar_registro(registros, "PED-2026-006")
    queijo = next(
        item for item in ped006["resultado"]["itens"]
        if item["produto"] == "queijo coalho"
    )
    queijo["quantidade"] = 500.0
    caminho = tmp_path / "pedidos.json"
    caminho.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")

    resultado = triar_pendentes("2026-10-30", caminho_pedidos=caminho)

    linha = next(
        linha for linha in resultado["demanda_semanal"]
        if linha["produto"] == "queijo coalho"
        and linha["semana_inicio"] == "2026-10-26"
    )
    assert linha["demanda_total"] == 540
    assert linha["capacidade_maxima_documentada"] == 480
    assert linha["excede_capacidade"] is True

    afetados = {"PED-2026-001", "PED-2026-005", "PED-2026-006"}
    for registro in resultado["fila"]:
        alertas = [
            alerta for alerta in registro["alertas"]
            if alerta["codigo"] == "CAPACIDADE_SEMANAL_EXCEDIDA"
        ]
        if registro["id"] not in afetados:
            assert alertas == []
            continue
        assert len(alertas) == 1
        assert "540 kg" in alertas[0]["mensagem"]
        assert "480 kg" in alertas[0]["mensagem"]
        assert "PED-2026-001, PED-2026-005, PED-2026-006" in alertas[0]["mensagem"]
        assert alertas[0]["fonte"] == "fichas_tecnicas/queijo_coalho.txt"


def test_alertas_de_prazo():
    resultado = triar_pendentes("2026-10-30")

    vencido = buscar_registro(resultado["fila"], "PED-2026-006")
    assert vencido["situacao_prazo"] == "vencido"
    assert "PRAZO_VENCIDO" in codigos(vencido)

    # "jan/2027" não vira data: o prazo fica para esclarecer.
    textual = buscar_registro(resultado["fila"], "PED-2026-013")
    assert textual["situacao_prazo"] == "nao_resolvido"
    assert "PRAZO_NAO_RESOLVIDO" in codigos(textual)

    no_prazo = buscar_registro(resultado["fila"], "PED-2026-004")
    assert not codigos(no_prazo) & {"PRAZO_VENCIDO", "PRAZO_NAO_RESOLVIDO"}


def test_contrato_identificado_cita_o_contrato():
    resultado = triar_pendentes("2026-10-30")

    esperado = {
        "PED-2026-001": "contratos/contrato_restaurante_raizes.txt",
        "PED-2026-002": "contratos/contrato_mercado_bom_preco.txt",
        "PED-2026-004": "contratos/contrato_pnae_garanhuns.txt",
    }
    for pedido_id, fonte in esperado.items():
        registro = buscar_registro(resultado["fila"], pedido_id)
        alerta = next(
            alerta for alerta in registro["alertas"]
            if alerta["codigo"] == "CONTRATO_IDENTIFICADO"
        )
        assert alerta["fonte"] == fonte
        assert registro["contrato"]["fonte"] == fonte

    # SuperBom não tem contrato registrado.
    superbom = buscar_registro(resultado["fila"], "PED-2026-006")
    assert superbom["contrato"] is None
    assert "CONTRATO_IDENTIFICADO" not in codigos(superbom)


def test_referencia_historica_pede_confirmacao():
    resultado = triar_pendentes("2026-10-30")

    for pedido_id in ("PED-2026-003", "PED-2026-005"):
        registro = buscar_registro(resultado["fila"], pedido_id)
        alerta = next(
            alerta for alerta in registro["alertas"]
            if alerta["codigo"] == "CONFIRMAR_HISTORICO"
        )
        assert alerta["fonte"] == "data/financeiro.csv; data/lotes.csv"
        assert registro["historico"] is not None
        assert registro["status"] == "aguardando_confirmacao"
        assert registro["requer_confirmacao"] is True


def test_campo_faltante_vira_alerta():
    resultado = triar_pendentes("2026-10-30")

    registro = buscar_registro(resultado["fila"], "PED-2026-009")
    faltantes = [
        alerta for alerta in registro["alertas"]
        if alerta["codigo"] == "CAMPO_FALTANTE"
    ]

    assert faltantes
    assert all(
        alerta["fonte"] == "pedido_estruturado.campos_faltantes"
        for alerta in faltantes
    )


def test_registro_sem_data_de_recebimento_fica_na_fila_com_alerta():
    registro = {
        "id": "TESTE-SEM-DATA",
        "pedido": PedidoTriado(tipo="mensagem_produtor", comprador="Produtor P001"),
    }

    # Sem data, não dá para provar que chegou depois: o registro fica na fila.
    assert recebido_ate(registro, date(2026, 10, 30)) is True

    resultado = processar_pedido(
        registro,
        data_referencia=date(2026, 10, 30),
        alocador=AlocadorSemanal(),
    )

    assert "DATA_RECEBIMENTO_AUSENTE" in codigos(resultado)
    assert resultado["urgencia"]["urgencia_nao_calculada"] is True
    assert resultado["urgencia"]["horas_restantes"] is None
    assert resultado["requer_confirmacao"] is True
