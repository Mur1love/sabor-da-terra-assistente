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
