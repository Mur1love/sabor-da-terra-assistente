"""Testes de consolidação de orçamentos da triagem."""

from sabor_da_terra.triagem.orcamento import (
    consolidar_orcamento,
)


def avaliacao(
    produto,
    quantidade,
    preco,
    pode_atender=True,
):
    return {
        "encontrado": True,
        "item": {
            "produto": produto,
            "quantidade": quantidade,
            "unidade": "kg",
        },
        "pode_atender": pode_atender,
        "preco": preco,
        "alertas": [],
        "fontes": [],
    }


def test_orcamento_tabela_geral():
    resultado = consolidar_orcamento([
        avaliacao(
            "tomate",
            10,
            {
                "origem": "tabela",
                "disponivel": True,
                "preco_unitario": 6.0,
                "subtotal": 60.0,
                "total": 60.0,
                "fonte": "tabela_precos_outubro_2026.csv",
            },
        ),
    ])

    assert resultado["total_estimado"] == 60.0
    assert resultado["orcamento_completo"] is True
    assert resultado["confirmado"] is False


def test_orcamento_com_desconto_atacado():
    resultado = consolidar_orcamento([
        avaliacao(
            "banana prata",
            100,
            {
                "origem": "tabela",
                "disponivel": True,
                "preco_unitario": 3.5,
                "subtotal": 350.0,
                "desconto_atacado_aplicado": True,
                "desconto_atacado_pct": 10.0,
                "valor_desconto": 35.0,
                "total": 315.0,
                "fonte": "tabela_precos_outubro_2026.csv",
            },
        ),
    ])

    assert resultado["total_estimado"] == 315.0
    assert resultado["economia_atacado"] == 35.0
    assert (
        resultado["itens"][0]["desconto_atacado_aplicado"]
        is True
    )


def test_orcamento_contratual_pnae():
    resultado = consolidar_orcamento([
        avaliacao(
            "banana prata",
            200,
            {
                "origem": "contrato",
                "contrato": "045/2026-PNAE",
                "preco_unitario": 3.8,
                "total": 760.0,
                "fonte": "contratos/contrato_pnae_garanhuns.txt",
            },
        ),
    ])

    assert resultado["total_estimado"] == 760.0
    assert resultado["contratos"] == ["045/2026-PNAE"]
    assert resultado["itens"][0]["origem"] == "contrato"


def test_orcamento_parcial_sem_preco():
    resultado = consolidar_orcamento([
        avaliacao(
            "tomate",
            10,
            {
                "disponivel": True,
                "total": 60.0,
                "fonte": "tabela_precos_outubro_2026.csv",
            },
        ),
        avaliacao(
            "ovos caipira",
            10,
            None,
            pode_atender=False,
        ),
    ])

    assert resultado["total_estimado"] == 60.0
    assert resultado["itens_sem_preco"] == 1
    assert resultado["orcamento_completo"] is False
    assert resultado["itens"][1]["total"] is None


def test_orcamento_com_restricao():
    resultado = consolidar_orcamento([
        avaliacao(
            "mel silvestre",
            20,
            {
                "origem": "contrato",
                "contrato": "045/2026-PNAE",
                "total": 1160.0,
                "fonte": "contratos/contrato_pnae_garanhuns.txt",
            },
            pode_atender=False,
        ),
    ])

    assert resultado["itens_com_restricao"] == 1
    assert (
        resultado["itens"][0]["situacao"]
        == "estimado_com_restricao"
    )


def test_orcamento_vazio():
    resultado = consolidar_orcamento([])

    assert resultado["total_estimado"] == 0.0
    assert resultado["orcamento_completo"] is False


def test_orcamento_preserva_fontes():
    resultado = consolidar_orcamento([
        {
            **avaliacao(
                "tomate",
                10,
                {
                    "origem": "tabela",
                    "total": 60.0,
                    "fonte": "tabela_precos_outubro_2026.csv",
                },
            ),
            "fontes": ["fichas_tecnicas/hortalicas.txt"],
        },
    ])

    assert (
        "tabela_precos_outubro_2026.csv"
        in resultado["fontes"]
    )
    assert (
        "fichas_tecnicas/hortalicas.txt"
        in resultado["fontes"]
    )
