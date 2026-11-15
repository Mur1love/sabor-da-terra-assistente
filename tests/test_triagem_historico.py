"""Testes de desambiguação por histórico."""

from sabor_da_terra.triagem.historico import identificar_historico


def test_ped005_ultima_compra_cremilda():
    resultado = identificar_historico(
        comprador="Dona Cremilda - Lanchonete da Feira",
        data_referencia="2026-10-29",
        expressao="ultima_vez",
    )

    assert resultado["requer_confirmacao"] is True
    assert len(resultado["hipoteses"]) == 1

    hipotese = resultado["hipoteses"][0]

    assert hipotese["produto"] == "queijo coalho"
    assert hipotese["quantidade_kg"] == 20
    assert hipotese["registro_id"] == "FIN-2026-026"
    assert hipotese["confirmado"] is False


def test_ped005_historico_completo():
    resultado = identificar_historico(
        comprador="Dona Cremilda - Lanchonete da Feira",
        data_referencia="2026-10-29",
        expressao="de_sempre",
    )

    produtos = {
        hipotese["produto"]
        for hipotese in resultado["hipoteses"]
    }

    assert "queijo coalho" in produtos
    assert "banana prata" in produtos

    assert resultado["requer_confirmacao"] is True


def test_ped003_sem_historico():
    resultado = identificar_historico(
        comprador="Chef Amanda - Bistrô Sertão Gourmet",
        data_referencia="2026-10-29",
        expressao="de_sempre",
    )

    assert resultado["hipoteses"] == []
    assert resultado["requer_confirmacao"] is True
    assert "Nenhum histórico" in resultado["aviso"]


def test_historico_nao_consulta_registros_futuros():
    resultado = identificar_historico(
        comprador="Dona Cremilda - Lanchonete da Feira",
        data_referencia="2026-10-01",
        expressao="ultima_vez",
    )

    assert len(resultado["hipoteses"]) == 1
    assert resultado["hipoteses"][0]["produto"] == "banana prata"


def test_expressao_invalida():
    import pytest

    with pytest.raises(ValueError):
        identificar_historico(
            comprador="Lanchonete da Feira",
            data_referencia="2026-10-29",
            expressao="qualquer_coisa",
        )
