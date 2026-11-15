"""Testes da classificação de prioridade."""

from datetime import date

from sabor_da_terra.triagem.priorizar import classificar_prioridade
from sabor_da_terra.triagem.schema import PedidoTriado


REFERENCIA = date(2026, 10, 29)


def criar_pedido(tipo, prazo=None, ambiguidades=None):
    return PedidoTriado(
        tipo=tipo,
        prazo_entrega=prazo,
        ambiguidades=ambiguidades or [],
    )


def test_compra_urgente():
    pedido = criar_pedido(
        "compra_urgente",
        "2026-10-29",
    )

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["prioridade"] == "alta"
    assert resultado["situacao_prazo"] == "proximo"


def test_compra_com_prazo_proximo():
    pedido = criar_pedido(
        "compra",
        "2026-10-30",
    )

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["prioridade"] == "alta"
    assert resultado["dias_restantes"] == 1


def test_compra_com_prazo_futuro():
    pedido = criar_pedido(
        "compra",
        "2026-11-20",
    )

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["prioridade"] == "media"
    assert resultado["situacao_prazo"] == "futuro"


def test_compra_contratual():
    pedido = criar_pedido(
        "compra",
        "2026-11-04",
    )

    resultado = classificar_prioridade(
        pedido,
        REFERENCIA,
        possui_contrato=True,
    )

    assert resultado["prioridade"] == "alta"


def test_notificacao_oficial():
    pedido = criar_pedido(
        "notificacao_oficial",
        "2026-11-12",
    )

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["prioridade"] == "alta"


def test_consulta_sem_prazo():
    pedido = criar_pedido("consulta")

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["prioridade"] == "baixa"
    assert resultado["situacao_prazo"] == "nao_informado"


def test_mensagem_produtor():
    pedido = criar_pedido(
        "mensagem_produtor",
        "2026-10-31",
    )

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["prioridade"] == "analise"


def test_prazo_vencido():
    pedido = criar_pedido(
        "compra",
        "2026-10-28",
    )

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["situacao_prazo"] == "vencido"
    assert resultado["requer_confirmacao"] is True


def test_prazo_textual():
    pedido = criar_pedido(
        "cotacao",
        "jan/2027",
    )

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["situacao_prazo"] == "nao_resolvido"
    assert resultado["requer_confirmacao"] is True


def test_ambiguidade_na_data():
    pedido = criar_pedido(
        "compra",
        "2026-11-01",
        ambiguidades=["Dia da semana não corresponde à data."],
    )

    resultado = classificar_prioridade(pedido, REFERENCIA)

    assert resultado["requer_confirmacao"] is True
