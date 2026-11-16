"""Etapa 11: resumos e notificações para produtores (Desafio C).

Os números do resumo são conferidos contra o financeiro.csv lido direto do
arquivo, sem passar pela camada de dados: se as duas leituras divergirem, o
teste pega.
"""

import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pytest
from google.genai import types

from sabor_da_terra.dados import obter_repositorio
from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.produtores import (
    FERRAMENTAS,
    montar_resumo,
    notificacoes_da_fila,
    redigir,
    relatorio_pendencias_vencidas,
    responder_mensagem_produtor,
    resumo_produtor,
)
from sabor_da_terra.produtores.demanda import fila_da_triagem, produtores_com_alocacao
from sabor_da_terra.produtores.redacao import problemas_da_redacao
from sabor_da_terra.produtores.texto import dados_sensiveis_no_texto, reais
from sabor_da_terra.regras import alertas_do_produtor
from tests.dobles import ClienteFake, ModeloFake

RAIZ = Path(__file__).resolve().parents[1]
REFERENCIA = "2026-10-30"
PRODUTORES = [f"P{n:03d}" for n in range(1, 19)]
MESES = ["2026-09", "2026-10"]


def _financeiro() -> list[dict]:
    with (RAIZ / "data" / "financeiro.csv").open(encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def _d(valor) -> Decimal:
    return Decimal(str(valor))


@pytest.fixture(scope="module")
def fila():
    return fila_da_triagem(REFERENCIA)


@pytest.fixture(scope="module")
def lote(fila):
    return notificacoes_da_fila(fila)


# ---------------------------------------------------------------------------
# Resumo: valores iguais ao financeiro.csv
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mes", MESES)
@pytest.mark.parametrize("produtor_id", PRODUTORES)
def test_valores_do_resumo_batem_com_financeiro_csv(produtor_id, mes):
    linhas = [l for l in _financeiro() if l["produtor_id"] == produtor_id]
    vendas = [l for l in linhas if l["data"].startswith(mes)]
    recebidos = [l for l in linhas if l["status_pagamento"] == "pago" and l["data_pagamento"].startswith(mes)]
    pendentes = [l for l in linhas if l["status_pagamento"] == "pendente"]
    vencidas = [l for l in pendentes if l["data_vencimento"] < REFERENCIA]
    a_receber = [l for l in pendentes if l["data_vencimento"] >= REFERENCIA]

    resumo = montar_resumo(produtor_id, mes, REFERENCIA)
    assert resumo["encontrado"]
    totais = resumo["totais"]
    assert _d(totais["vendido_no_mes"]) == sum((_d(l["valor_total"]) for l in vendas), Decimal(0))
    assert _d(totais["recebido_no_mes"]) == sum((_d(l["valor_total"]) for l in recebidos), Decimal(0))
    assert _d(totais["vencido"]) == sum((_d(l["valor_total"]) for l in vencidas), Decimal(0))
    assert _d(totais["a_receber"]) == sum((_d(l["valor_total"]) for l in a_receber), Decimal(0))
    assert _d(totais["saldo_a_receber"]) == sum((_d(l["valor_total"]) for l in pendentes), Decimal(0))

    # Agrupamento por produto e comprador: kg e R$.
    esperado = defaultdict(lambda: [Decimal(0), Decimal(0), []])
    for l in vendas:
        grupo = esperado[(l["produto"], l["comprador"])]
        grupo[0] += _d(l["quantidade_kg"])
        grupo[1] += _d(l["valor_total"])
        grupo[2].append(l["id_transacao"])
    obtido = {(g["produto"], g["comprador"]): [_d(g["quantidade"]), _d(g["valor"]), g["transacoes"]] for g in resumo["vendas"]}
    assert obtido == {k: [v[0], v[1], v[2]] for k, v in esperado.items()}

    texto = resumo["texto"]
    for l in recebidos + vencidas + a_receber:
        assert f"{l['id_transacao']}: {reais(_d(l['valor_total']))}" in texto
    for grupo in esperado.values():
        assert reais(grupo[1]) in texto
    assert f"Saldo total a receber: {reais(_d(totais['saldo_a_receber']))}." in texto


def test_resumo_p003_mostra_fin_013_e_014_como_atrasados():
    resumo = montar_resumo("P003", "2026-10", REFERENCIA)
    assert [v["id_transacao"] for v in resumo["vencidas"]] == ["FIN-2026-013", "FIN-2026-014"]
    atrasados = resumo["texto"].split("PAGAMENTOS ATRASADOS")[1].split("A RECEBER")[0]
    assert "FIN-2026-013: R$ 4.500,00 de Rede SuperBom Atacado" in atrasados
    assert "FIN-2026-014: R$ 1.520,00 de Rede SuperBom Atacado" in atrasados
    assert atrasados.count('"ATRASADO - cobrar"') == 2
    assert "Total atrasado: R$ 6.020,00." in atrasados


def test_resumo_destaca_empenho_pnae_vencido_em_23_10():
    texto = montar_resumo("P004", "2026-10", REFERENCIA)["texto"]
    atrasados = texto.split("PAGAMENTOS ATRASADOS")[1].split("A RECEBER")[0]
    assert "FIN-2026-006: R$ 750,00" in atrasados and "FIN-2026-007: R$ 270,00" in atrasados
    assert "Venceu em 23/10/2026" in atrasados and "Empenho 2026NE00234" in atrasados


def test_resumo_produtor_inclui_pedidos_alocados_da_fila():
    resumo = resumo_produtor("P003", "2026-10", REFERENCIA)
    assert [a["pedido_id"] for a in resumo["pedidos_alocados"]] == ["PED-2026-006"]
    assert "PED-2026-006: 200 kg de queijo coalho para Rede SuperBom Atacado" in resumo["texto"]
    assert "Nenhum desses pedidos está fechado" in resumo["texto"]


def test_resumo_de_produtor_inexistente_nao_inventa():
    resumo = resumo_produtor("P099", "2026-10", REFERENCIA)
    assert resumo["encontrado"] is False and "não existe" in resumo["aviso"]


# ---------------------------------------------------------------------------
# Alertas de conformidade do produtor (#5)
# ---------------------------------------------------------------------------


def test_alerta_p008_certificacao_em_renovacao_com_auditoria_em_15_11():
    from datetime import date

    alerta = next(a for a in alertas_do_produtor("P008", date(2026, 10, 30)) if a["codigo"] == "CERTIFICACAO_VENCIDA")
    assert alerta["severidade"] == "grave"
    assert "venceu em 30/09/2026" in alerta["mensagem"]
    assert "REN-2026-0456" in alerta["mensagem"] and "auditoria está marcada para 15/11/2026" in alerta["mensagem"]
    assert alerta["fonte"] == "certificacoes/cert_organica_josefa_souza_P008.txt"
    assert "auditoria está marcada para 15/11/2026" in montar_resumo("P008", "2026-10", REFERENCIA)["texto"]


def test_alerta_p017_sem_sie_e_nao_conformidade():
    from datetime import date

    codigos = {a["codigo"]: a for a in alertas_do_produtor("P017", date(2026, 10, 30))}
    assert "NC-001" in codigos["NAO_CONFORMIDADE_SANITARIA"]["mensagem"]
    assert "Sem registro no SIE" in codigos["REGISTRO_SANITARIO"]["mensagem"]
    assert "ovos caipira" in codigos["REGISTRO_SANITARIO"]["mensagem"]


def test_produtor_em_dia_nao_tem_alerta():
    from datetime import date

    assert alertas_do_produtor("P002", date(2026, 10, 30)) == []


# ---------------------------------------------------------------------------
# Notificações
# ---------------------------------------------------------------------------


def test_lote_gera_exatamente_uma_notificacao_por_produtor_com_alocacao(fila, lote):
    com_alocacao = {
        s["produtor_id"]
        for registro in fila["fila"]
        for resultado in registro["alocacoes"]
        for s in resultado.get("alocacoes", [])
    }
    ids = [n["produtor"]["produtor_id"] for n in lote["notificacoes"]]
    assert len(ids) == len(set(ids)) == lote["total"]
    assert set(ids) == com_alocacao == set(produtores_com_alocacao(fila))
    assert lote["enviadas"] is False


def test_notificacao_lista_cada_alocacao_da_fila(fila, lote):
    for notificacao in lote["notificacoes"]:
        pid = notificacao["produtor"]["produtor_id"]
        esperado = sorted(
            (registro["id"], resultado["produto"], s["quantidade"])
            for registro in fila["fila"]
            for resultado in registro["alocacoes"]
            for s in resultado.get("alocacoes", [])
            if s["produtor_id"] == pid
        )
        obtido = sorted((a["pedido_id"], a["produto"], a["quantidade"]) for a in notificacao["pedidos_sugeridos"])
        assert obtido == esperado
        assert all(a["confirmado"] is False for a in notificacao["pedidos_sugeridos"])
        assert "Nada está fechado ainda" in notificacao["texto"]


def test_notificacao_traz_entrega_e_exigencias_do_contrato(lote):
    p005 = next(n for n in lote["notificacoes"] if n["produtor"]["produtor_id"] == "P005")
    texto = p005["texto"]
    pnae = texto.split("PED-2026-004 - Prefeitura de Garanhuns - PNAE")[1].split("\n2)")[0]
    assert "- 150 kg de macaxeira para você (preço do contrato R$ 3,50 por kg)." in pnae
    assert "- 80 kg de inhame para você (preço do contrato R$ 5,00 por kg)." in pnae
    assert "Prazo: 04/11/2026." in pnae
    assert "entrega semanal conforme o cardápio da nutricionista" in pnae
    assert "nota fiscal individual por produtor" in pnae and "DAP ou CAF vigente" in pnae
    assert pnae.count("Entrega:") == 1  # um bloco por pedido, não por produto
    bom_preco = texto.split("PED-2026-002 - Mercado Bom Preço")[1]
    assert "entrega das 6h às 10h no CD do Mercado Bom Preço" in bom_preco
    assert "entregas só às terças e sextas" in bom_preco
    assert "boleto com vencimento em 30 dias" in bom_preco






# ---------------------------------------------------------------------------
# Mensagens de produtor do dataset
# ---------------------------------------------------------------------------


def test_resposta_ped_012_pagamento_bom_preco_de_setembro():
    resposta = responder_mensagem_produtor("PED-2026-012")
    texto = resposta["texto"]
    assert resposta["produtor"]["produtor_id"] == "P001"
    assert "não há nenhuma venda registrada para você em outubro de 2026 (R$ 0,00)" in texto
    assert "Mercado Bom Preço (vendas de setembro de 2026): já entrou. Total de R$ 940,00, pago em 01/10/2026." in texto
    assert "FIN-2026-001: 120 kg de goiaba paluma, R$ 540,00, pago em 01/10/2026" in texto
    assert "FIN-2026-002: 80 kg de manga tommy, R$ 400,00, pago em 01/10/2026" in texto
    assert "Saldo a receber: R$ 0,00." in texto
    pagamento = resposta["dados"]["pagamentos"][0]
    assert pagamento["situacao"] == "pago" and pagamento["transacoes"] == ["FIN-2026-001", "FIN-2026-002"]
    assert "0437" not in texto  # agência citada na mensagem não volta na resposta


def test_resposta_ped_015_cruza_queijo_e_recusa_cadastro():
    resposta = responder_mensagem_produtor("PED-2026-015")
    texto = resposta["texto"]
    assert resposta["produtor"]["produtor_id"] == "P003"
    queijo = texto.split("Queijo coalho: pedidos em aberto")[1].split('"manteiga"')[0]
    for pedido in ("PED-2026-001", "PED-2026-005", "PED-2026-006", "PED-2026-007", "PED-2026-013"):
        assert pedido in queijo
    assert "PED-2026-007: Hotel Fazenda Serra Negra pediu 25 kg (cotação)" in texto
    assert "A triagem sugeriu 200 kg seus, aguardando confirmação." in texto
    assert '"manteiga": confirme qual é (manteiga de garrafa ou queijo manteiga)' in texto
    assert "PED-2026-006: Rede SuperBom Atacado pediu 50 kg (compra urgente)" in texto.split("Queijo manteiga:")[1]
    assert resposta["fora_do_escopo"] == ["cadastro_produtor"]
    assert "Cadastrar produtor novo não é algo que este assistente faz" in texto
    assert "432.198.765-01" not in texto and "Sebastião" not in texto
    assert "Nada foi alocado nem confirmado" in texto


def test_mensagem_que_nao_e_de_produtor_e_recusada():
    resposta = responder_mensagem_produtor("PED-2026-001")
    assert resposta["encontrado"] is False


# ---------------------------------------------------------------------------
# Relatório de pendências da cooperativa
# ---------------------------------------------------------------------------


def test_relatorio_de_pendencias_vencidas_separa_a_vencer():
    relatorio = relatorio_pendencias_vencidas(REFERENCIA)
    assert [v["id_transacao"] for v in relatorio["vencidas"]] == [
        "FIN-2026-013", "FIN-2026-014", "FIN-2026-005", "FIN-2026-006", "FIN-2026-007",
    ]
    assert _d(relatorio["total_vencido"]) == Decimal("8690.00")
    assert "Total vencido: R$ 8.690,00." in relatorio["texto"]
    assert {v["id_transacao"] for v in relatorio["a_vencer"]} == {
        "FIN-2026-023", "FIN-2026-024", "FIN-2026-025", "FIN-2026-027", "FIN-2026-030",
    }


# ---------------------------------------------------------------------------
# Dados sensíveis
# ---------------------------------------------------------------------------


def _todos_os_textos(lote) -> list[str]:
    textos = [montar_resumo(pid, mes, REFERENCIA)["texto"] for pid in PRODUTORES for mes in MESES]
    textos += [n["texto"] for n in lote["notificacoes"]]
    textos += [responder_mensagem_produtor(p)["texto"] for p in ("PED-2026-012", "PED-2026-015")]
    textos.append(relatorio_pendencias_vencidas(REFERENCIA)["texto"])
    return textos


def test_nenhum_texto_gerado_tem_cpf_ou_conta(lote):
    produtores = obter_repositorio().produtores()
    proibidos = set(produtores["cpf"]) | set(produtores["conta_corrente"])
    for texto in _todos_os_textos(lote):
        assert dados_sensiveis_no_texto(texto) == []
        assert not any(valor in texto for valor in proibidos)


def test_detector_de_dado_sensivel():
    assert dados_sensiveis_no_texto("CPF 432.198.765-01") == ["432.198.765-01"]
    assert "28901-3" in dados_sensiveis_no_texto("conta 28901-3")
    assert dados_sensiveis_no_texto("Minha conta é no BB agência 0437") == ["agência 0437"]
    assert dados_sensiveis_no_texto("FIN-2026-013 vence em 18/10/2026, LOT-2026-0089") == []


def test_reais_formata_milhar_e_centavos():
    assert reais(6020) == "R$ 6.020,00"
    assert reais(Decimal("0.005")) == "R$ 0,01"
    assert reais(1440.0) == "R$ 1.440,00"
    assert reais(0) == "R$ 0,00"


# ---------------------------------------------------------------------------
# Redação pelo Gemini: só reescreve
# ---------------------------------------------------------------------------

RASCUNHO = (
    "Olá, Cícero Romão de Almeida (P003)!\n"
    "- FIN-2026-013: R$ 4.500,00 de Rede SuperBom Atacado. Venceu em 18/10/2026.\n"
    "Fontes: data/financeiro.csv."
)


def _cliente(texto: str | None = None, erro: bool = False) -> LLMClient:
    modelo = ModeloFake(texto=texto)
    if erro:
        modelo.falhas_429 = 99
    return LLMClient(modo="real", cliente=ClienteFake(modelo), dormir=lambda _: None, max_tentativas=1)


def test_redacao_valida_usa_texto_do_gemini():
    novo = (
        "Oi, Cícero (P003)! A Rede SuperBom Atacado ainda não pagou a FIN-2026-013, de R$ 4.500,00. "
        "Ela venceu em 18/10/2026.\nFontes: data/financeiro.csv."
    )
    resultado = redigir(RASCUNHO, _cliente(novo))
    assert resultado["origem"] == "gemini" and resultado["texto"] == novo


@pytest.mark.parametrize(
    "texto, problema",
    [
        ("Você tem R$ 4.600,00 a receber (FIN-2026-013), desde 18/10/2026.", "valor que não está no rascunho"),
        ("A SuperBom deve R$ 4.500,00, vencido em 18/10/2026.", "código do rascunho que sumiu"),
        ("FIN-2026-013 e FIN-2026-099: R$ 4.500,00, 18/10/2026.", "código que não está no rascunho"),
        ("FIN-2026-013: R$ 4.500,00, venceu 18/10/2026. CPF 723.016.498-55.", "dado sensível"),
        ("FIN-2026-013: R$ 4.500,00, venceu em 20/10/2026.", "data que não está no rascunho"),
    ],
)
def test_redacao_que_mexe_em_numero_ou_vaza_dado_volta_ao_rascunho(texto, problema):
    resultado = redigir(RASCUNHO, _cliente(texto))
    assert resultado["origem"] == "modelo_fixo" and resultado["texto"] == RASCUNHO
    assert any(problema in p for p in resultado["problemas"])


def test_redacao_sem_api_usa_rascunho():
    resultado = redigir(RASCUNHO, _cliente(erro=True))
    assert resultado["origem"] == "modelo_fixo" and resultado["texto"] == RASCUNHO


def test_rascunhos_reais_passam_na_propria_validacao(lote):
    for texto in _todos_os_textos(lote):
        assert problemas_da_redacao(texto, texto) == []


# ---------------------------------------------------------------------------
# Function calling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("funcao", FERRAMENTAS, ids=lambda f: f.__name__)
def test_ferramentas_viram_declaracao_do_gemini(funcao):
    declaracao = types.FunctionDeclaration.from_callable_with_api_option(callable=funcao)
    assert declaracao.name == funcao.__name__
    assert declaracao.description


def test_saidas_das_ferramentas_sao_json():
    from sabor_da_terra.produtores import notificar_produtores

    saidas = [
        resumo_produtor("P001", "2026-10", REFERENCIA),
        notificar_produtores(REFERENCIA),
        notificar_produtores(REFERENCIA, "P002"),
        responder_mensagem_produtor("PED-2026-015"),
        relatorio_pendencias_vencidas(REFERENCIA),
    ]
    for saida in saidas:
        json.dumps(saida, ensure_ascii=False)


def test_notificar_produtores_valida_entrada():
    from sabor_da_terra.produtores import notificar_produtores

    assert notificar_produtores("30/10/2026")["encontrado"] is False
    assert notificar_produtores(REFERENCIA, "P099")["encontrado"] is False
    individual = notificar_produtores(REFERENCIA, "p008")
    assert individual["total"] == 1 and individual["notificacoes"][0]["pedidos_sugeridos"] == []


def test_repositorio_lista_produtos_do_produtor():
    assert obter_repositorio().produtos_do_produtor("P002") == ["mel de jandaíra", "mel silvestre", "própolis"]


# ---------------------------------------------------------------------------
# Correções da revisão
# ---------------------------------------------------------------------------








def test_relatorio_com_data_invalida_devolve_aviso():
    resultado = relatorio_pendencias_vencidas("30/10/2026")
    assert resultado["encontrado"] is False and "AAAA-MM-DD" in resultado["aviso"]


def test_meses_citados_na_ordem_do_texto():
    from sabor_da_terra.produtores.mensagens import _meses_citados

    assert _meses_citados("o pagamento de outubro e o de setembro") == [10, 9]


@pytest.mark.parametrize(
    "texto, problema",
    [
        ("FIN-2026-013: R$ 4.600, venceu em 18/10/2026.", "valor fora do formato"),
        ("FIN-2026-013: R$4500, venceu em 18/10/2026.", "valor fora do formato"),
        ("A FIN-2026-013 venceu em 18/10/2026.", "valor do rascunho que sumiu"),
    ],
)
def test_redacao_pega_valor_sem_centavos_ou_omitido(texto, problema):
    resultado = redigir(RASCUNHO, _cliente(texto))
    assert resultado["origem"] == "modelo_fixo"
    assert any(problema in p for p in resultado["problemas"])


def test_oferta_nao_lista_pedido_de_que_o_produtor_foi_excluido(fila):
    from sabor_da_terra.produtores.demanda import demanda_aberta

    # P008: certificação vencida. Mel orgânico (PED-006 avaliado na fila e cotações não avaliadas) fica de fora;
    # o mel convencional do PED-001 continua.
    ids = [d["pedido_id"] for d in demanda_aberta("P008", "mel silvestre", fila)]
    assert ids == ["PED-2026-001"]


def test_produtor_inativo_nao_recebe_pedido(fila):
    from sabor_da_terra.produtores import notificacao_produtor
    from sabor_da_terra.produtores.demanda import demanda_aberta

    assert demanda_aberta("P015", "macaxeira", fila) == []
    assert "Não há pedido novo para você até 30/10/2026." in notificacao_produtor("P015", fila)["texto"]


def test_ferramentas_sao_as_duas_da_issue():
    assert [f.__name__ for f in FERRAMENTAS] == ["resumo_produtor", "notificar_produtores"]
