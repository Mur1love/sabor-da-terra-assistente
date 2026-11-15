from sabor_da_terra.triagem.schema import ItemPedidoExtraido
from sabor_da_terra.triagem.validar import validar_item


def test_item_sem_quantidade():
    item = ItemPedidoExtraido(
        produto="queijo coalho",
        quantidade=None,
        unidade="kg",
    )

    resultado = validar_item(
        item=item,
        comprador="Restaurante Raízes",
        data_entrega="2026-11-15",
        data_referencia="2026-11-10",
    )

    assert resultado["pendente_confirmacao"] is True
    assert resultado["encontrado"] is False


def test_item_com_quantidade_consulta_regras():
    item = ItemPedidoExtraido(
        produto="mel silvestre",
        quantidade=50,
        unidade="kg",
        exige_organico=True,
    )

    resultado = validar_item(
        item=item,
        comprador="Restaurante Raízes",
        data_entrega="2026-11-15",
        data_referencia="2026-11-10",
    )

    assert resultado["encontrado"] is True
    assert "elegiveis" in resultado
    assert "excluidos" in resultado
    assert "alertas" in resultado

    for alerta in resultado["alertas"]:
        assert alerta["fonte"]
