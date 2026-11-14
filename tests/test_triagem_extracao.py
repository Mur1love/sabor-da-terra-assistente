"""Testes da Etapa 9 — Triagem I: classificação e extração estruturada."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.triagem import (
    ErroExtracaoTriagem,
    PedidoTriado,
    TipoMensagem,
    analisar_prazo_mensagem,
    extrair_pedido,
    normalizar_produto,
    normalizar_unidade,
    triar_pedido,
)
from tests.dobles import ClienteFake, ModeloFake

RAIZ = Path(__file__).resolve().parents[1]
ARQ_PEDIDOS = RAIZ / "data" / "pedidos.json"
ARQ_FIXTURE_CONSOLIDADA = RAIZ / "tests" / "fixtures" / "triagem_15_pedidos.json"

GABARITO_TIPOS: dict[str, TipoMensagem] = {
    "PED-2026-001": TipoMensagem.COMPRA,
    "PED-2026-002": TipoMensagem.COMPRA,
    "PED-2026-003": TipoMensagem.COMPRA_URGENTE,
    "PED-2026-004": TipoMensagem.COMPRA,
    "PED-2026-005": TipoMensagem.COMPRA,
    "PED-2026-006": TipoMensagem.COMPRA_URGENTE,
    "PED-2026-007": TipoMensagem.COTACAO,
    "PED-2026-008": TipoMensagem.CONSULTA,
    "PED-2026-009": TipoMensagem.COTACAO,
    "PED-2026-010": TipoMensagem.CONSULTA,
    "PED-2026-011": TipoMensagem.CONSULTA,
    "PED-2026-012": TipoMensagem.MENSAGEM_PRODUTOR,
    "PED-2026-013": TipoMensagem.COTACAO,
    "PED-2026-014": TipoMensagem.NOTIFICACAO_OFICIAL,
    "PED-2026-015": TipoMensagem.MENSAGEM_PRODUTOR,
}


class _ModeloSequencial:
    """Devolve respostas em sequência para testar retry de validação."""

    def __init__(self, respostas: list[str]) -> None:
        self._respostas = list(respostas)
        self.chamadas = 0

    def generate_content(self, *, model: str, contents: Any, config: Any = None):
        from google.genai import types

        texto = self._respostas[self.chamadas]
        self.chamadas += 1
        return types.GenerateContentResponse.model_validate(
            {"candidates": [{"content": {"role": "model", "parts": [{"text": texto}]}}]}
        )


def test_normalizacao_catalogo_e_unidades() -> None:
    assert normalizar_produto("mel (aquele silvestre mesmo)").base == "mel silvestre"
    assert normalizar_produto("queijo manteiga").base == "queijo manteiga"
    assert normalizar_produto("manteiga de garrafa").base == "manteiga de garrafa"
    assert normalizar_produto("passion fruit").base == "maracujá"
    assert normalizar_produto("manteiga").ambiguo is True

    assert normalizar_unidade("unid") == "unidade"
    assert normalizar_unidade("maços") == "maço"
    assert normalizar_unidade("dúzias") == "dúzia"
    assert normalizar_unidade("quilos") == "kg"


def test_resolucao_datas_relativas_e_conflitos() -> None:
    # PED-001: 01/11/2026 é domingo, mas mensagem diz "sexta (01/nov)"
    r1 = analisar_prazo_mensagem("Preciso pra essa sexta (01/nov)", "2026-10-28T09:15:00")
    assert r1.data_iso == "2026-11-01"
    assert r1.conflito is not None and "domingo" in r1.conflito.lower()

    # PED-002: 04/11/2026 é quarta, mas mensagem diz "terça 04/nov"
    r2 = analisar_prazo_mensagem("Entrega terça 04/nov no CD", "2026-10-28T10:32:00")
    assert r2.data_iso == "2026-11-04"
    assert r2.conflito is not None and "quarta" in r2.conflito.lower()

    # Datas relativas sem conflito
    assert analisar_prazo_mensagem("pra amanha", "2026-10-28T11:05:00").data_iso == "2026-10-29"
    assert analisar_prazo_mensagem("pra sabado", "2026-10-28T15:40:00").data_iso == "2026-10-31"
    assert analisar_prazo_mensagem("para HOJE (29/10)", "2026-10-29T08:00:00").data_iso == "2026-10-29"


def test_retry_validacao_schema_e_falha_explicita() -> None:
    # 1ª resposta inválida, 2ª válida -> recupera com 1 retry
    valido = json.dumps(
        {
            "tipo": "compra",
            "idioma": "pt",
            "comprador": "Padaria Teste",
            "canal": "whatsapp",
            "itens": [
                {"produto": "goiaba", "quantidade": 10, "unidade": "kg", "exige_organico": False, "opcional": False}
            ],
            "prazo_entrega": "2026-10-30",
            "prazo_original": "amanhã",
            "observacoes": [],
            "campos_faltantes": [],
            "ambiguidades": [],
        },
        ensure_ascii=False,
    )
    modelo_recupera = _ModeloSequencial(["{json quebrado", valido])
    llm_recupera = LLMClient(modo="real", cliente=ClienteFake(modelo_recupera))  # type: ignore[arg-type]

    res = extrair_pedido(
        "Manda 10kg de goiaba pra amanhã",
        data_recebimento="2026-10-29T09:00:00",
        llm=llm_recupera,
    )
    assert modelo_recupera.chamadas == 2
    assert res.tipo == TipoMensagem.COMPRA
    assert res.itens[0].produto == "goiaba paluma"

    # 2 respostas inválidas consecutivas -> levanta ErroExtracaoTriagem
    modelo_falha = _ModeloSequencial(['{"tipo": "inexistente"}', '{"tipo": "ainda_invalido"}'])
    llm_falha = LLMClient(modo="real", cliente=ClienteFake(modelo_falha))  # type: ignore[arg-type]
    with pytest.raises(ErroExtracaoTriagem):
        extrair_pedido("Mensagem teste", llm=llm_falha)
    assert modelo_falha.chamadas == 2


def test_triagem_15_pedidos_criterios_de_aceite() -> None:
    pedidos = json.loads(ARQ_PEDIDOS.read_text(encoding="utf-8"))
    assert len(pedidos) == 15

    llm_fixture = LLMClient(modo="fixture")
    resultados: dict[str, PedidoTriado] = {}

    for p in pedidos:
        triado = extrair_pedido(
            p["mensagem_original"],
            data_recebimento=p["data_recebimento"],
            canal=p["canal"],
            comprador=p["comprador"],
            remetente=p["remetente"],
            llm=llm_fixture,
        )
        # 100% das saídas validam contra o schema Pydantic
        assert isinstance(triado, PedidoTriado)
        resultados[p["id"]] = triado

    # Pelo menos 14 dos 15 registros classificados com o tipo do gabarito
    acertos = sum(1 for pid, esperado in GABARITO_TIPOS.items() if resultados[pid].tipo == esperado)
    assert acertos >= 14

    # Critérios explícitos de classificação
    for pid in ("PED-2026-008", "PED-2026-009", "PED-2026-010", "PED-2026-011", "PED-2026-013"):
        assert resultados[pid].tipo not in {TipoMensagem.COMPRA, TipoMensagem.COMPRA_URGENTE}

    assert resultados["PED-2026-012"].tipo == TipoMensagem.MENSAGEM_PRODUTOR
    assert resultados["PED-2026-015"].tipo == TipoMensagem.MENSAGEM_PRODUTOR
    assert resultados["PED-2026-014"].tipo == TipoMensagem.NOTIFICACAO_OFICIAL

    # PED-001 e PED-002 com conflito de data em ambiguidades
    assert any("conflito de data" in a.lower() for a in resultados["PED-2026-001"].ambiguidades)
    assert any("conflito de data" in a.lower() for a in resultados["PED-2026-002"].ambiguidades)

    # PED-003 e PED-005 com referência implícita em ambiguidades
    assert any("referência implícita" in a.lower() for a in resultados["PED-2026-003"].ambiguidades)
    assert any("referência implícita" in a.lower() for a in resultados["PED-2026-005"].ambiguidades)

    # Itens opcionais marcados corretamente
    ricota = next(i for i in resultados["PED-2026-001"].itens if "ricota" in i.produto.lower())
    assert ricota.opcional is True
    caja = next(i for i in resultados["PED-2026-007"].itens if "cajá" in i.produto.lower())
    assert caja.opcional is True

    # Normalização de produtos coloquiais e em inglês
    mel_ped1 = next(i for i in resultados["PED-2026-001"].itens if "mel" in i.produto.lower())
    assert mel_ped1.produto == "mel silvestre"
    produtos_en = {i.produto for i in resultados["PED-2026-011"].itens}
    assert {"manga tommy", "goiaba paluma", "maracujá"} <= produtos_en
    assert resultados["PED-2026-011"].idioma == "en"

    # CPFs mascarados em observações (LGPD/sigilo)
    for triado in resultados.values():
        for obs in triado.observacoes:
            assert "034.567.891-23" not in obs
            assert "876.543.210-98" not in obs

    # Confere integridade da fixture consolidada gravada
    assert ARQ_FIXTURE_CONSOLIDADA.exists()
    consolidado = json.loads(ARQ_FIXTURE_CONSOLIDADA.read_text(encoding="utf-8"))
    assert len(consolidado) == 15


def test_funcao_triar_pedido_function_calling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODO", "fixture")
    pedidos = json.loads(ARQ_PEDIDOS.read_text(encoding="utf-8"))
    p1 = pedidos[0]

    saida = triar_pedido(
        mensagem=p1["mensagem_original"],
        data_recebimento=p1["data_recebimento"],
        canal=p1["canal"],
        comprador=p1["comprador"],
        remetente=p1["remetente"],
    )
    assert isinstance(saida, dict)
    assert saida["tipo"] == "compra"
    assert saida["prazo_entrega"] == "2026-11-01"
