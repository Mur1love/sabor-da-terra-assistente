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

def test_ped003_hipotese_documental_sem_historico():
    """PED-003 deve sugerir hipótese documental sem inventar histórico."""
    from sabor_da_terra.triagem.fila import triar_pendentes

    resultado = triar_pendentes("2026-10-29")

    pedido = next(
        item for item in resultado["fila"]
        if item["id"] == "PED-2026-003"
    )

    historico = pedido["historico"]

    assert historico is not None
    assert historico["hipoteses"] == []
    assert historico["requer_confirmacao"] is True

    hipotese = historico["hipotese_documental"]

    assert hipotese["produto"] == "queijo coalho"
    assert hipotese["tipo_evidencia"] == "ficha_tecnica"
    assert hipotese["historico_comprovado"] is False
    assert hipotese["confirmado"] is False
    assert hipotese["requer_confirmacao"] is True

    assert hipotese["fonte"] == (
        "data/fichas_tecnicas/queijo_coalho.txt"
    )

    assert pedido["status"] == "aguardando_confirmacao"

    assert all(
        not alocacao["alocacoes"]
        for alocacao in pedido["alocacoes"]
    )

    assert any(
        alerta["codigo"] == "HIPOTESE_DOCUMENTAL"
        and alerta["fonte"] == hipotese["fonte"]
        for alerta in pedido["alertas"]
    )


def test_ped003_sem_ficha_nao_inventa_hipotese(monkeypatch):
    """Sem evidência documental, nenhuma hipótese deve ser criada."""
    from pathlib import Path

    from sabor_da_terra.triagem.fila import (
        carregar_pedidos,
        sugerir_hipotese_documental,
    )

    registro = next(
        item for item in carregar_pedidos()
        if item["id"] == "PED-2026-003"
    )

    pedido = registro["pedido"]

    historico = {
        "hipoteses": [],
        "requer_confirmacao": True,
    }

    caminho_original = Path.is_file

    def simular_ficha_ausente(caminho):
        if str(caminho) == "data/fichas_tecnicas/queijo_coalho.txt":
            return False
        return caminho_original(caminho)

    monkeypatch.setattr(Path, "is_file", simular_ficha_ausente)

    hipotese = sugerir_hipotese_documental(
        pedido=pedido,
        historico=historico,
    )

    assert hipotese is None
