"""Etapa 14: a medição da avaliação ponta a ponta (gabarito, checagens, juiz e métricas).

Tudo offline: o assistente e o juiz rodam com respostas scriptadas
(`FilaControlada` da etapa 12), então o que se prova aqui é a régua — não a
nota do assistente, que vem da rodada real (`tests/test_gabarito.py`).
"""

import json

import pytest

from sabor_da_terra.avaliacao.execucao import (
    STATUS_ERRO_INFRA,
    STATUS_ERRO_JUIZ,
    STATUS_OK,
    avaliar_caso,
    checar_citacoes,
    checar_funcoes,
)
from sabor_da_terra.avaliacao.gabarito import (
    Caso,
    arquivos_de_fonte,
    caso_por_id,
    carregar_casos,
    data_referencia,
    requisitos_funcionais,
)
from sabor_da_terra.avaliacao.metricas import falhas, metricas, relatorio_markdown
from tests.dobles import Erro504
from tests.test_assistente import ROTEADOR, FilaControlada, Script, _fabrica, _fila_vazia


def _julgamento(n_deve: int, n_nao: int, *, deve_ok: bool = True, ocorreu: bool = False) -> Script:
    return Script(
        texto=json.dumps(
            {
                "deve_conter": [{"indice": i, "atendido": deve_ok, "evidencia": "trecho"} for i in range(n_deve)],
                "nao_deve_conter": [{"indice": i, "ocorreu": ocorreu, "evidencia": "—"} for i in range(n_nao)],
            }
        )
    )


def _caso_minimo(**campos) -> Caso:
    base = dict(
        id="DOC-900",
        arquivo="teste.yaml",
        desafio="Consulta documental",
        requisito="Consultar certificações",
        entrada="quem tem mel orgânico vigente?",
        esperado="P002 e P018.",
        funcoes_esperadas=("buscar_produtores",),
        deve_conter=("Identificação de P002", "Identificação de P018"),
        nao_deve_conter=("P008 como vigente",),
        fonte=("data/produtores.csv",),
        turnos=("quem tem mel orgânico vigente?",),
    )
    base.update(campos)
    return Caso(**base)


# ---------------------------------------------------------------------------
# Gabarito como dado
# ---------------------------------------------------------------------------


def test_gabarito_tem_os_37_casos_e_501_criterios():
    casos = carregar_casos()
    assert len(casos) == 37
    assert len({c.id for c in casos}) == 37
    assert sum(c.total_criterios for c in casos) == 501


def test_casos_de_contexto_viram_dois_turnos():
    caso = caso_por_id("CTX-001")
    assert caso.turnos == (
        "Quais produtores têm certificação orgânica vigente para mel silvestre?",
        "E o da Josefa?",
    )
    assert "RF5" in requisitos_funcionais(caso)


def test_mensagem_de_varias_linhas_continua_um_turno_so():
    caso = caso_por_id("TRI-014")  # notificação da ADAGRO, com lista em linhas
    assert len(caso.turnos) == 1 and "ADAGRO" in caso.turnos[0]


def test_desafios_normalizados_nos_tres_gargalos():
    assert {c.desafio for c in carregar_casos()} == {
        "Triagem de pedidos",
        "Consulta documental",
        "Comunicação com produtores",
    }


def test_anti_alucinacao_cobre_os_casos_do_criterio_de_aceite():
    """Lote inexistente (DOC-005), certificação internacional (ANTI-001), fora da base (ANTI-002)."""
    anti = {c.id for c in carregar_casos() if c.anti_alucinacao}
    assert {"ANTI-001", "ANTI-002", "ANTI-003", "DOC-005"} <= anti
    assert not any(c.documental for c in carregar_casos() if c.anti_alucinacao)  # recusa não exige citação


def test_data_referencia_do_caso_do_pedido_e_padrao():
    assert data_referencia(caso_por_id("TRI-003")) == "2026-10-28"  # data_recebimento do próprio caso
    assert data_referencia(caso_por_id("TRI-006")) == "2026-10-29"  # data do PED-2026-006
    assert data_referencia(caso_por_id("DOC-001")) == "2026-10-30"  # dia da demo


def test_arquivos_de_fonte_tiram_prefixo_e_anotacao():
    assert arquivos_de_fonte(caso_por_id("CTX-003")) == ("financeiro.csv", "lotes.csv")


# ---------------------------------------------------------------------------
# Checagens determinísticas
# ---------------------------------------------------------------------------


def _turno(resposta="ok", funcoes=("buscar_produtores",), fontes_do_turno=("produtores.csv",), fontes=None):
    return {
        "mensagem": "m",
        "resposta": resposta,
        "funcoes": list(funcoes),
        "fontes_do_turno": list(fontes_do_turno),
        "fontes": list(fontes if fontes is not None else fontes_do_turno),
    }


def test_citacao_valida_quando_a_fonte_existe_e_saiu_da_funcao():
    resultado = checar_citacoes(_caso_minimo(), [_turno()])
    assert resultado["ok"] and resultado["fonte_esperada_citada"] is True


def test_citacao_invalida_quando_o_modelo_cita_arquivo_que_as_funcoes_nao_devolveram():
    turno = _turno(resposta="Vigentes [fonte: certificacoes/inventado.txt].")
    resultado = checar_citacoes(_caso_minimo(), [turno])
    assert not resultado["ok"]
    assert "certificacoes/inventado.txt" in resultado["invalidas"]


def test_caso_documental_sem_fonte_no_turno_reprova_a_citacao():
    resultado = checar_citacoes(_caso_minimo(), [_turno(fontes_do_turno=(), fontes=())])
    assert not resultado["ok"] and resultado["turnos_sem_fonte"] == [1]


def test_recusa_anti_alucinacao_nao_precisa_de_fonte():
    caso = _caso_minimo(id="ANTI-900", requisito="Não inventar informações")
    resultado = checar_citacoes(caso, [_turno(fontes_do_turno=(), fontes=())])
    assert resultado["aplicavel"] is False and resultado["ok"]


def test_funcoes_esperadas_somam_os_turnos():
    caso = _caso_minimo(funcoes_esperadas=("buscar_produtores", "identificar_produtor"))
    turnos = [_turno(funcoes=("buscar_produtores",)), _turno(funcoes=("identificar_produtor",))]
    assert checar_funcoes(caso, turnos)["ok"]
    assert checar_funcoes(caso, turnos[:1])["faltando"] == ["identificar_produtor"]


# ---------------------------------------------------------------------------
# Caso inteiro: assistente + juiz scriptados
# ---------------------------------------------------------------------------


def test_avaliar_caso_aprovado_de_ponta_a_ponta(tmp_path):
    caso = _caso_minimo()
    fila = FilaControlada({
        "triagem": [
            ROTEADOR("buscar_produtores", {"produto": "mel silvestre", "organico": True}),
            Script(texto="ok"),
            _julgamento(2, 1),  # o juiz também é Flash-Lite (papel de triagem)
        ],
        "resposta": [Script(texto="P002 e P018 têm certificação vigente.")],
    })
    resultado = avaliar_caso(caso, _fabrica(tmp_path, fila)())
    _fila_vazia(fila)
    assert resultado["status"] == STATUS_OK
    assert resultado["aprovado"] is True
    assert resultado["criterios_ok"] == resultado["criterios_total"] == 3
    assert resultado["turnos"][0]["fontes"] == ["produtores.csv"]  # o rodapé que a interface mostraria
    assert resultado["data_referencia"] == "2026-10-30"


def test_criterio_nao_atendido_reprova_e_aparece_nas_falhas(tmp_path):
    caso = _caso_minimo()
    fila = FilaControlada({
        "triagem": [ROTEADOR("buscar_produtores", {"produto": "mel silvestre"}), Script(texto="ok"), _julgamento(2, 1, ocorreu=True)],
        "resposta": [Script(texto="P008 está vigente.")],
    })
    resultado = avaliar_caso(caso, _fabrica(tmp_path, fila)())
    assert resultado["status"] == STATUS_OK and resultado["aprovado"] is False
    assert resultado["criterios_ok"] == 2
    assert falhas([resultado])[0]["ocorreram"] == ["P008 como vigente"]


def test_turno_sem_composicao_vira_erro_de_infra_e_nao_e_julgado(tmp_path):
    caso = _caso_minimo()
    fila = FilaControlada({
        "triagem": [ROTEADOR("buscar_produtores", {"produto": "mel silvestre"}), Script(texto="ok")],
        "resposta": [Script(erro=Erro504())],
    })
    resultado = avaliar_caso(caso, _fabrica(tmp_path, fila)())
    _fila_vazia(fila)  # nenhum julgamento consumido
    assert resultado["status"] == STATUS_ERRO_INFRA and resultado["aprovado"] is False


def test_juiz_que_pula_criterio_vira_erro_de_juiz(tmp_path):
    caso = _caso_minimo()
    fila = FilaControlada({
        "triagem": [ROTEADOR("buscar_produtores", {"produto": "mel silvestre"}), Script(texto="ok"), _julgamento(1, 1)],
        "resposta": [Script(texto="P002 e P018.")],
    })
    resultado = avaliar_caso(caso, _fabrica(tmp_path, fila)())
    assert resultado["status"] == STATUS_ERRO_JUIZ


# ---------------------------------------------------------------------------
# Métricas e relatório
# ---------------------------------------------------------------------------


def _resultado(id_, desafio, rfs, ok, total, aprovado, *, documental=False, anti=False, status=STATUS_OK):
    r = {
        "id": id_, "desafio": desafio, "requisitos_funcionais": rfs, "documental": documental,
        "anti_alucinacao": anti, "status": status, "aprovado": aprovado,
    }
    if status == STATUS_OK:
        r.update(
            criterios_ok=ok, criterios_total=total,
            funcoes={"ok": True, "faltando": []},
            citacoes={"ok": aprovado or not documental, "invalidas": [], "turnos_sem_fonte": [], "fonte_esperada_citada": True},
            criterios={"deve_conter": [], "nao_deve_conter": []},
        )
    else:
        r["erro"] = "cota"
    return r


def test_metricas_por_criterio_por_desafio_e_por_requisito():
    resultados = [
        _resultado("DOC-1", "Consulta documental", ["RF1", "RF3"], 9, 10, False, documental=True),
        _resultado("ANTI-1", "Consulta documental", ["RF1", "RF3", "RF6"], 4, 4, True, anti=True),
        _resultado("TRI-1", "Triagem de pedidos", ["RF1", "RF2"], 6, 6, True),
        _resultado("TRI-2", "Triagem de pedidos", ["RF1", "RF2"], 0, 0, False, status=STATUS_ERRO_INFRA),
    ]
    m = metricas(resultados)
    assert m["geral"]["avaliados"] == 3
    assert m["geral"]["acerto_criterios"] == pytest.approx(95.0)  # 19/20
    assert m["geral"]["aprovados"] == 2
    assert m["por_desafio"]["Triagem de pedidos"]["avaliados"] == 1  # o erro de infra fica fora
    assert m["por_requisito_funcional"]["RF6"]["aprovados"] == 1
    assert m["citacoes"]["documentais_avaliados"] == 1 and m["citacoes"]["com_citacao_valida"] == 0
    assert [f["id"] for f in m["fora_da_conta"]] == ["TRI-2"]

    md = relatorio_markdown({"rodada": 1, "data": "2026-11-18", "metricas": m, "consumo": {"chamadas_reais": {"m": 3}}})
    assert "| **Geral** | 4 | 3 | 95.0% (19/20) | 2/3 (66.7%) |" in md
    assert "RF6 — Dizer que não sabe" in md
    assert "Fora da conta" in md


def test_robustez_tem_5_variacoes_coloquiais_fora_do_gabarito():
    robustez = carregar_casos("robustez")
    assert [c.id for c in robustez] == ["ROB-001", "ROB-002", "ROB-003", "ROB-004", "ROB-005"]
    assert all("RF2" in requisitos_funcionais(c) for c in robustez)
    assert not {c.id for c in robustez} & {c.id for c in carregar_casos()}  # fora do gabarito
    assert all(c.funcoes_esperadas and c.deve_conter and c.fonte for c in robustez)
