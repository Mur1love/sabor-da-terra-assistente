"""Testes do motor de regras (etapa 5). Rodam sobre os arquivos reais de data/, sem rede."""

import datetime as dt
import json
import re
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from google.genai import types

from sabor_da_terra.dados import obter_repositorio
from sabor_da_terra.regras import (
    FERRAMENTAS,
    Alerta,
    FatosInvalidos,
    ItemPedido,
    avaliar,
    carregar_fatos,
    obter_fatos,
    verificar_conformidade,
)
from sabor_da_terra.regras.alertas import ATENCAO, GRAVE, INFO, SEVERIDADES, ordenar
from sabor_da_terra.regras.fatos import ARQUIVO_FATOS

PASTA_DADOS = Path(__file__).resolve().parents[1] / "data"
REFERENCIA = "2026-10-29"  # dia do PED-006, o pedido urgente da SuperBom
PNAE = "Prefeitura de Garanhuns - PNAE"
SUPERBOM = "Rede SuperBom Atacado"
CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")


# Atalho para chamar a ferramenta com um item simples.
def verificar(produto, quantidade, entrega, comprador, organico=False, unidade=None, referencia=REFERENCIA):
    item = {"produto": produto, "quantidade": quantidade, "organico": organico, "unidade": unidade}
    return verificar_conformidade(item, entrega, comprador, data_referencia=referencia)


# Códigos dos alertas de um resultado.
def codigos(resultado):
    return [a["codigo"] for a in resultado["alertas"]]


# Primeiro alerta com o código pedido.
def alerta(resultado, codigo):
    return next(a for a in resultado["alertas"] if a["codigo"] == codigo)


# Ids dos produtores elegíveis.
def elegiveis(resultado):
    return {p["produtor_id"] for p in resultado["elegiveis"]}


# Motivos de exclusão por produtor.
def excluidos(resultado):
    return {p["produtor_id"]: p["motivos"] for p in resultado["excluidos"]}


# Fatos com a renovação da P008 concluída (novo certificado a partir de 20/11/2026).
def fatos_com_renovacao_da_p008():
    fatos = obter_fatos()
    p008 = next(c for c in fatos.certificacoes if c.produtor_id == "P008")
    renovada = replace(
        p008,
        renovacao=replace(p008.renovacao, concluida_em=dt.date(2026, 11, 20), nova_validade=dt.date(2028, 11, 20)),
    )
    return replace(fatos, certificacoes=tuple(renovada if c is p008 else c for c in fatos.certificacoes))


# --------------------------------------------------------------------------- #
# Critérios de aceite da issue #5                                             #
# --------------------------------------------------------------------------- #


def test_aceite_mel_organico_em_05_11_so_p002_e_p018_e_explica_a_p008():
    resultado = verificar("mel silvestre", 40, "2026-11-05", SUPERBOM, organico=True)
    assert elegiveis(resultado) == {"P002", "P018"}
    assert excluidos(resultado) == {"P008": ["CERTIFICACAO_VENCIDA"]}
    vencida = alerta(resultado, "CERTIFICACAO_VENCIDA")
    assert vencida["severidade"] == GRAVE
    assert vencida["fonte"] == "certificacoes/cert_organica_josefa_souza_P008.txt"
    assert "P008" in vencida["mensagem"] and "30/09/2026" in vencida["mensagem"]
    assert "REN-2026-0456" in vencida["mensagem"] and "15/11/2026" in vencida["mensagem"]


def test_aceite_vigencia_depende_da_data_e_renovacao_registrada_libera_a_p008():
    item = ItemPedido(produto="mel silvestre", quantidade=10, organico=True)
    fatos = fatos_com_renovacao_da_p008()
    repo = obter_repositorio()

    depois = avaliar(item, dt.date(2026, 11, 25), "Restaurante Raízes", dt.date(2026, 11, 20), fatos, repo)
    assert "P008" in elegiveis(depois)
    assert "CERTIFICACAO_VENCIDA" not in codigos(depois)

    antes = avaliar(item, dt.date(2026, 11, 18), "Restaurante Raízes", dt.date(2026, 11, 10), fatos, repo)
    assert excluidos(antes)["P008"] == ["CERTIFICACAO_VENCIDA"]
    assert "só vale a partir de 20/11/2026" in alerta(antes, "CERTIFICACAO_VENCIDA")["mensagem"]


def test_aceite_frango_para_revenda_e_grave_e_cita_a_adagro():
    resultado = verificar("frango caipira", 30, "2026-11-05", SUPERBOM)
    nc = alerta(resultado, "NAO_CONFORMIDADE_SANITARIA")
    assert nc["severidade"] == GRAVE
    assert nc["fonte"] == "certificacoes/inspecao_adagro_2026.txt"
    assert "NC-001" in nc["mensagem"] and "venda direta ao consumidor final" in nc["mensagem"]
    assert excluidos(resultado) == {"P017": ["NAO_CONFORMIDADE_SANITARIA"]}
    assert not resultado["pode_atender"]


def test_aceite_caja_em_novembro_tem_alerta_de_safra():
    resultado = verificar("cajá", 10, "2026-11-08", "Hotel Fazenda Serra Negra")
    safra = alerta(resultado, "SAFRA_BAIXA")
    assert safra["fonte"] == "sazonalidade.csv"
    assert "novembro" in safra["mensagem"]


def test_aceite_banana_do_pnae_sai_a_3_80_pelo_contrato():
    resultado = verificar("banana", 200, "2026-11-05", PNAE, referencia="2026-10-28")
    preco = resultado["preco"]
    assert preco["origem"] == "contrato"
    assert preco["preco_unitario"] == 3.80
    assert preco["total"] == 760.00
    assert preco["preco_tabela_geral"] == 3.50
    assert preco["fonte"] == "contratos/contrato_pnae_garanhuns.txt"
    assert alerta(resultado, "PRECO_CONTRATO")["fonte"] == "contratos/contrato_pnae_garanhuns.txt"


# Casos variados para os testes que valem para qualquer resultado.
def _resultados_variados():
    return [
        verificar("mel silvestre", 40, "2026-11-05", SUPERBOM, organico=True),
        verificar("mel silvestre", 20, "2026-11-05", PNAE, referencia="2026-10-28"),
        verificar("frango caipira", 30, "2026-11-05", SUPERBOM),
        verificar("ovos", 100, "2026-11-05", PNAE, referencia="2026-10-28"),
        verificar("queijo coalho", 200, "2026-10-29", SUPERBOM),
        verificar("queijo coalho", 50, "2026-11-05", PNAE, referencia="2026-10-28"),
        verificar("macaxeira", 150, "2026-11-05", PNAE, referencia="2026-10-28"),
        verificar("mirtilo", 5, "2026-11-10", "Sorveteria Tropical", organico=True),
        verificar("cajá", 10, "2026-11-05", PNAE, referencia="2026-10-28"),
        verificar("alface", 50, "2026-11-04", "Mercado Bom Preço", unidade="unid", referencia="2026-10-28"),
        verificar("coentro", 20, "2026-11-05", PNAE, unidade="kg", referencia="2026-10-28"),
        verificar("tomate cereja", 5, "2026-11-11", "Feira Orgânica do Recife", organico=True),
        verificar("banana", 3, "2026-11-05", "Restaurante Raízes", organico=True),
    ]


@pytest.mark.parametrize("resultado", _resultados_variados())
def test_aceite_todo_alerta_tem_os_quatro_campos_e_fonte_que_existe(resultado):
    assert resultado["alertas"]
    for a in resultado["alertas"]:
        assert set(a) == {"codigo", "severidade", "mensagem", "fonte"}
        assert a["severidade"] in SEVERIDADES and a["mensagem"]
        for arquivo in a["fonte"].split(";"):
            assert (PASTA_DADOS / arquivo.strip()).exists(), a


# --------------------------------------------------------------------------- #
# Regra: produtor inativo                                                     #
# --------------------------------------------------------------------------- #


def test_p015_inativo_nunca_e_elegivel():
    resultado = verificar("macaxeira", 150, "2026-11-05", PNAE, referencia="2026-10-28")
    assert elegiveis(resultado) == {"P005"}
    assert excluidos(resultado) == {"P015": ["PRODUTOR_INATIVO"]}
    assert alerta(resultado, "PRODUTOR_INATIVO")["fonte"] == "produtores.csv"


# --------------------------------------------------------------------------- #
# Regra: certificação vigente na data                                         #
# --------------------------------------------------------------------------- #


def test_p008_vale_no_dia_da_validade_e_nao_no_seguinte():
    no_dia = verificar("mel silvestre", 10, "2026-09-30", SUPERBOM, organico=True, referencia="2026-09-20")
    seguinte = verificar("mel silvestre", 10, "2026-10-01", SUPERBOM, organico=True, referencia="2026-09-20")
    assert "P008" in elegiveis(no_dia)
    assert "P008" in excluidos(seguinte)


def test_mel_convencional_nao_exige_certificacao():
    resultado = verificar("mel silvestre", 10, "2026-11-05", SUPERBOM)
    assert elegiveis(resultado) == {"P002", "P008", "P018"}
    assert "CERTIFICACAO_VENCIDA" not in codigos(resultado)


def test_organico_exclui_quem_nao_tem_certificacao():
    resultado = verificar("queijo coalho", 50, "2026-11-05", SUPERBOM, organico=True)
    assert elegiveis(resultado) == {"P007"}
    assert excluidos(resultado) == {"P003": ["SEM_CERTIFICACAO_ORGANICA"], "P011": ["SEM_CERTIFICACAO_ORGANICA"]}


def test_banana_organica_nao_tem_quem_atenda():
    resultado = verificar("banana", 3, "2026-11-05", "Restaurante Raízes", organico=True)
    assert not resultado["elegiveis"]
    assert not resultado["pode_atender"]
    assert "SEM_PRODUTOR_ELEGIVEL" in codigos(resultado)
    assert resultado["preco"] is None


def test_auditoria_da_p008_no_futuro_e_no_passado():
    antes = verificar("mel silvestre", 10, "2026-11-20", "Restaurante Raízes", organico=True, referencia="2026-11-05")
    depois = verificar("mel silvestre", 10, "2026-11-20", "Restaurante Raízes", organico=True, referencia="2026-11-18")
    assert "a auditoria está marcada para 15/11/2026" in alerta(antes, "CERTIFICACAO_VENCIDA")["mensagem"]
    mensagem = alerta(depois, "CERTIFICACAO_VENCIDA")["mensagem"]
    assert "a auditoria estava marcada para 15/11/2026" in mensagem
    assert "não há certificado renovado registrado" in mensagem


def test_p004_vigente_em_11_11_com_aviso_e_vencida_em_15_12():
    em_novembro = verificar("tomate cereja", 5, "2026-11-11", "Feira Orgânica do Recife", organico=True)
    assert elegiveis(em_novembro) == {"P004"}
    assert "01/12/2026" in alerta(em_novembro, "CERTIFICACAO_A_VENCER")["mensagem"]

    em_dezembro = verificar("tomate cereja", 5, "2026-12-15", "Feira Orgânica do Recife", organico=True, referencia="2026-12-10")
    assert excluidos(em_dezembro) == {"P004": ["CERTIFICACAO_VENCIDA"]}


# --------------------------------------------------------------------------- #
# Regra: SIE e não conformidade da ADAGRO                                     #
# --------------------------------------------------------------------------- #


def test_ovos_do_p017_saem_para_o_raizes_com_pendencia():
    resultado = verificar("ovos", 10, "2026-11-01", "Restaurante Raízes", referencia="2026-10-28")
    assert elegiveis(resultado) == {"P017"}
    assert resultado["elegiveis"][0]["pendencias"] == ["REGISTRO_SANITARIO"]
    assert "NAO_CONFORMIDADE_SANITARIA" not in codigos(resultado)
    assert "venda direta" in alerta(resultado, "REGISTRO_SANITARIO")["mensagem"]


def test_ovos_do_p017_nao_entram_no_pnae():
    resultado = verificar("ovos", 100, "2026-11-05", PNAE, unidade="dúzias", referencia="2026-10-28")
    assert excluidos(resultado) == {"P017": ["SIE_EXIGIDO"]}
    assert alerta(resultado, "SIE_EXIGIDO")["fonte"] == "certificacoes/inspecao_adagro_2026.txt"
    assert not resultado["pode_atender"]


def test_pnae_exclui_queijo_sem_sie_do_p011():
    resultado = verificar("queijo coalho", 50, "2026-11-05", PNAE, referencia="2026-10-28")
    assert elegiveis(resultado) == {"P003", "P007"}
    assert excluidos(resultado) == {"P011": ["SIE_EXIGIDO"]}
    assert alerta(resultado, "SIE_EXIGIDO")["fonte"] == "fichas_tecnicas/queijo_coalho.txt"


def test_pnae_mel_so_p002_porque_contrato_exige_organico_e_sie():
    resultado = verificar("mel silvestre", 20, "2026-11-05", PNAE, referencia="2026-10-28")
    assert resultado["item"]["organico"]
    assert elegiveis(resultado) == {"P002"}
    assert excluidos(resultado) == {"P008": ["CERTIFICACAO_VENCIDA"], "P018": ["SIE_EXIGIDO"]}
    assert "CONTRATO_EXIGE_ORGANICO" in codigos(resultado)
    assert alerta(resultado, "SIE_EXIGIDO")["fonte"] == "fichas_tecnicas/mel_silvestre.txt"


def test_sie_pendente_so_e_pendencia_para_quem_nao_exige():
    resultado = verificar("mel silvestre", 10, "2026-11-05", "Restaurante Raízes")
    pendencias = {p["produtor_id"]: p["pendencias"] for p in resultado["elegiveis"]}
    assert pendencias == {"P002": [], "P008": ["REGISTRO_SANITARIO"], "P018": ["REGISTRO_SANITARIO"]}


def test_produtor_excluido_nao_acumula_alertas_de_outras_regras():
    # P008 já sai pela certificação; o SIE pendente dela não muda a decisão.
    resultado = verificar("mel silvestre", 40, "2026-11-05", SUPERBOM, organico=True)
    assert not any("P008" in a["mensagem"] for a in resultado["alertas"] if a["codigo"] == "REGISTRO_SANITARIO")


# --------------------------------------------------------------------------- #
# Regra: safra                                                                #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("produto", ["mirtilo", "framboesa"])
def test_fora_de_safra_em_novembro_bloqueia(produto):
    resultado = verificar(produto, 5, "2026-11-10", "Sorveteria Tropical", organico=True)
    assert alerta(resultado, "FORA_DE_SAFRA")["fonte"] == "sazonalidade.csv"
    assert not resultado["pode_atender"]


def test_goiaba_em_novembro_nao_tem_alerta_de_safra():
    resultado = verificar("goiaba extra", 50, "2026-11-05", "Restaurante Raízes")
    assert not {"FORA_DE_SAFRA", "SAFRA_BAIXA", "SAFRA_SEM_DADO"} & set(codigos(resultado))


def test_produto_sem_calendario_avisa_sem_inventar():
    resultado = verificar("tomate cereja", 5, "2026-11-11", "Feira Orgânica do Recife")
    assert "SAFRA_SEM_DADO" in codigos(resultado)


# --------------------------------------------------------------------------- #
# Regra: capacidade                                                           #
# --------------------------------------------------------------------------- #


def test_queijo_do_ped_006_cabe_mas_capacidade_nao_e_estoque():
    resultado = verificar("queijo coalho", 200, "2026-10-29", SUPERBOM)
    capacidade = resultado["capacidade"]
    assert capacidade["janela_dias"] == 7  # pedido para hoje compara com uma semana
    # P011 (sem SIE) sai da intermediação desde a #12: capacidade documentada dos elegíveis
    assert (capacidade["minimo"], capacidade["maximo"]) == (300, 400)
    assert "não é estoque" in alerta(resultado, "CAPACIDADE")["mensagem"]
    assert resultado["pode_atender"]


@pytest.mark.parametrize(
    "quantidade, codigo, pode",
    [(300, "CAPACIDADE", True), (400, "CAPACIDADE_NO_LIMITE", True), (500, "CAPACIDADE_EXCEDIDA", False)],
)
def test_capacidade_do_queijo_em_uma_semana(quantidade, codigo, pode):
    resultado = verificar("queijo coalho", quantidade, "2026-11-05", SUPERBOM)
    assert codigo in codigos(resultado)
    assert resultado["pode_atender"] is pode


def test_capacidade_cresce_com_o_prazo():
    resultado = verificar("queijo coalho", 500, "2026-11-12", SUPERBOM)  # 14 dias
    assert resultado["capacidade"]["maximo"] == 800  # P011 (sem SIE) fora da intermediação desde a #12
    assert "CAPACIDADE_EXCEDIDA" not in codigos(resultado)


def test_goiaba_tem_capacidade_de_safra_e_de_entressafra():
    safra = verificar("goiaba extra", 300, "2026-11-05", "Restaurante Raízes")
    entressafra = verificar("goiaba extra", 300, "2027-07-10", "Restaurante Raízes", referencia="2027-07-03")
    assert safra["capacidade"]["maximo"] == 800
    assert entressafra["capacidade"]["maximo"] == 180
    assert "CAPACIDADE_EXCEDIDA" in codigos(entressafra)


def test_capacidade_em_kg_nao_e_comparada_com_alface_em_unidade():
    resultado = verificar("alface", 50, "2026-11-06", "Mercado Bom Preço", referencia="2026-10-28")
    assert resultado["capacidade"] is None
    assert "CAPACIDADE_SEM_DADO" in codigos(resultado)


# --------------------------------------------------------------------------- #
# Regra: exclusividade                                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "produto, unico",
    [("mel de jandaíra", "P002"), ("própolis", "P002"), ("pólen", "P018"), ("cera de abelha", "P018"), ("tomate cereja", "P004")],
)
def test_itens_de_um_so_produtor(produto, unico):
    resultado = verificar(produto, 1, "2026-11-05", "Restaurante Raízes")
    exclusivo = alerta(resultado, "PRODUTOR_EXCLUSIVO")
    assert unico in exclusivo["mensagem"]
    assert exclusivo["fonte"] == "produtores.csv"


def test_produto_com_varios_produtores_nao_e_exclusivo():
    assert "PRODUTOR_EXCLUSIVO" not in codigos(verificar("queijo coalho", 10, "2026-11-05", SUPERBOM))


# --------------------------------------------------------------------------- #
# Regras: preço por contrato e exigências                                     #
# --------------------------------------------------------------------------- #


def test_queijo_do_pnae_sai_pelo_contrato_e_nao_pela_tabela():
    resultado = verificar("queijo coalho", 50, "2026-11-05", PNAE, referencia="2026-10-28")
    assert resultado["preco"]["preco_unitario"] == 34.00
    assert resultado["preco"]["preco_tabela_geral"] == 32.00


def test_bom_preco_usa_a_tabela_geral():
    resultado = verificar("banana", 40, "2026-11-06", "Mercado Bom Preço", referencia="2026-10-28")
    assert resultado["preco"]["origem"] == "tabela"
    assert resultado["preco"]["preco_unitario"] == 3.50


def test_item_fora_do_contrato_pnae():
    resultado = verificar("cajá", 10, "2026-11-05", PNAE, referencia="2026-10-28")
    assert "ITEM_FORA_DO_CONTRATO" in codigos(resultado)
    assert resultado["preco"] is None


def test_ped_002_entrega_na_quarta_04_11_fura_o_contrato_do_bom_preco():
    # O pedido diz "terça 04/nov", mas 04/11/2026 é quarta; o contrato só aceita terça e sexta.
    quarta = verificar("alface", 50, "2026-11-04", "Mercado Bom Preço", referencia="2026-10-28")
    terca = verificar("alface", 50, "2026-11-03", "Mercado Bom Preço", referencia="2026-10-28")
    assert "só às terças e sextas" in alerta(quarta, "ENTREGA_FORA_DO_DIA")["mensagem"]
    assert "é quarta" in alerta(quarta, "ENTREGA_FORA_DO_DIA")["mensagem"]
    assert "ENTREGA_FORA_DO_DIA" not in codigos(terca)


def test_pnae_cobra_dap_caf_comprovada():
    queijo = verificar("queijo coalho", 50, "2026-11-05", PNAE, referencia="2026-10-28")
    pendencias = {p["produtor_id"]: p["pendencias"] for p in queijo["elegiveis"]}
    assert pendencias == {"P003": ["DAP_CAF_NAO_COMPROVADA"], "P007": ["DAP_CAF_NAO_COMPROVADA"]}

    macaxeira = verificar("macaxeira", 150, "2026-11-05", PNAE, referencia="2026-10-28")
    assert "DAP_CAF_NAO_COMPROVADA" not in codigos(macaxeira)  # P005: DAP/CAF vigente na inspeção da ADAGRO


def test_exigencias_do_raizes_aparecem():
    resultado = verificar("queijo coalho", 10, "2026-11-05", "Restaurante Raízes")
    exigencias = alerta(resultado, "EXIGENCIAS_CONTRATO")
    assert "PIX" in exigencias["mensagem"] and "10h" in exigencias["mensagem"]
    assert exigencias["fonte"] == "contratos/contrato_restaurante_raizes.txt"


def test_contrato_fora_da_vigencia_com_tabela_mantem_o_preco_da_tabela():
    resultado = verificar("banana", 40, "2027-01-05", "Mercado Bom Preço", referencia="2026-12-28")
    assert "CONTRATO_FORA_DA_VIGENCIA" in codigos(resultado)
    assert resultado["preco"]["origem"] == "tabela"


def test_pnae_fora_da_vigencia_nao_tem_preco_contratado():
    resultado = verificar("banana", 200, "2027-03-10", PNAE, referencia="2027-03-01")
    assert resultado["preco"] is None
    assert "Não há preço contratado válido" in alerta(resultado, "CONTRATO_FORA_DA_VIGENCIA")["mensagem"]
    assert "PRECO_CONTRATO" not in codigos(resultado)


@pytest.mark.parametrize(
    "comprador, contrato",
    [
        ("Prefeitura de Garanhuns - PNAE", "045/2026-PNAE"),
        ("PNAE", "045/2026-PNAE"),
        ("Mercado Bom Preço", "012/2026"),
        ("Bom Preço", "012/2026"),
        ("Restaurante Raízes", "008/2026"),
        ("Raízes", "008/2026"),
        ("Raízes Distribuidora de Frutas", None),
        ("Supermercado Bom Preço do Recife", None),
        ("Rede SuperBom Atacado", None),
        ("", None),
    ],
)
def test_comprador_so_ganha_contrato_quando_e_ele_mesmo(comprador, contrato):
    achado = obter_fatos().contrato_do_comprador(comprador)
    assert (achado.numero if achado else None) == contrato


def test_comprador_sem_contrato_usa_a_tabela():
    resultado = verificar("queijo coalho", 10, "2026-11-05", SUPERBOM)
    assert resultado["contrato"] is None
    assert alerta(resultado, "SEM_CONTRATO")["fonte"] == "tabela_precos_outubro_2026.csv"


# --------------------------------------------------------------------------- #
# Entrada da ferramenta                                                       #
# --------------------------------------------------------------------------- #


def test_unidade_diferente_nao_calcula_preco_nem_capacidade():
    resultado = verificar("coentro", 20, "2026-11-05", PNAE, unidade="kg", referencia="2026-10-28")
    assert "UNIDADE_DIFERENTE" in codigos(resultado)
    assert resultado["preco"] is None and resultado["capacidade"] is None


def test_unidade_escrita_de_outro_jeito_e_aceita():
    resultado = verificar("coentro", 20, "2026-11-05", PNAE, unidade="maços", referencia="2026-10-28")
    assert "UNIDADE_DIFERENTE" not in codigos(resultado)
    assert resultado["preco"]["total"] == 40.00


def test_produto_parecido_vira_sugestao_sem_dados():
    resultado = verificar("melão", 10, "2026-11-05", SUPERBOM)
    assert not resultado["encontrado"]
    assert resultado["opcoes"] == ["melado"]
    assert "alertas" not in resultado


@pytest.mark.parametrize(
    "item, entrega, referencia",
    [
        ({"produto": "alface", "quantidade": 0}, "2026-11-05", REFERENCIA),
        ({"produto": "alface", "quantidade": float("nan")}, "2026-11-05", REFERENCIA),
        ({"produto": "alface", "quantidade": float("inf")}, "2026-11-05", REFERENCIA),
        ({"quantidade": 3}, "2026-11-05", REFERENCIA),
        ({"produto": "alface", "quantidade": 3}, "amanhã", REFERENCIA),
        ({"produto": "alface", "quantidade": 3}, "2026-11-05", "ontem"),
        ({"produto": "alface", "quantidade": 3}, "2026-10-01", REFERENCIA),
    ],
)
def test_entradas_invalidas_viram_aviso(item, entrega, referencia):
    resultado = verificar_conformidade(item, entrega, SUPERBOM, data_referencia=referencia)
    assert not resultado["encontrado"]
    assert resultado["aviso"]


def test_aceita_item_pedido_e_dict():
    como_modelo = verificar_conformidade(ItemPedido(produto="alface", quantidade=10), "2026-11-05", SUPERBOM, REFERENCIA)
    como_dict = verificar_conformidade({"produto": "alface", "quantidade": 10}, "2026-11-05", SUPERBOM, REFERENCIA)
    assert como_modelo == como_dict


# --------------------------------------------------------------------------- #
# Saída                                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("resultado", _resultados_variados())
def test_todo_motivo_de_exclusao_tem_alerta(resultado):
    gerados = set(codigos(resultado))
    for produtor in resultado["excluidos"]:
        assert set(produtor["motivos"]) <= gerados


@pytest.mark.parametrize("resultado", _resultados_variados())
def test_alertas_vem_do_mais_grave_para_o_menos(resultado):
    ordem = [SEVERIDADES.index(a["severidade"]) for a in resultado["alertas"]]
    assert ordem == sorted(ordem)


@pytest.mark.parametrize("resultado", _resultados_variados())
def test_fontes_listam_os_arquivos_citados(resultado):
    citados = {parte.strip() for a in resultado["alertas"] for parte in a["fonte"].split(";")}
    assert citados <= set(resultado["fontes"])


def test_saidas_nao_tem_dado_pessoal_ou_bancario():
    produtores = obter_repositorio().produtores()
    proibidos = [v for coluna in ("telefone", "email", "endereco", "conta_corrente", "chave_pix") for v in produtores[coluna] if v]
    for resultado in _resultados_variados():
        texto = json.dumps(resultado, ensure_ascii=False)
        assert not CPF.search(texto)
        assert not any(valor in texto for valor in proibidos)


@pytest.mark.parametrize("resultado", _resultados_variados())
def test_saidas_sao_json(resultado):
    json.dumps(resultado)


def test_ferramenta_vira_declaracao_do_gemini_com_os_campos_do_item():
    assert FERRAMENTAS == [verificar_conformidade]
    declaracao = types.FunctionDeclaration.from_callable_with_api_option(callable=verificar_conformidade)
    assert declaracao.name == "verificar_conformidade"
    assert declaracao.description
    item = declaracao.parameters.properties["item"]
    assert {"produto", "quantidade", "organico"} <= set(item.properties)
    assert set(declaracao.parameters.required) == {"item", "data_entrega", "comprador"}


# --------------------------------------------------------------------------- #
# Base de fatos                                                               #
# --------------------------------------------------------------------------- #


def _todas_as_fontes(fatos):
    grupos = [fatos.certificacoes, fatos.registros_sanitarios, fatos.nao_conformidades, fatos.dap_caf, fatos.capacidades, fatos.contratos]
    return {f.fonte for grupo in grupos for f in grupo} | {fatos.fonte_origem_animal}


def test_toda_fonte_dos_fatos_existe_em_data():
    for fonte in _todas_as_fontes(obter_fatos()):
        assert (PASTA_DADOS / fonte).is_file(), fonte


def test_certificacoes_batem_com_o_cadastro():
    produtores = obter_repositorio().produtores().set_index("produtor_id")
    certificados = {c.produtor_id: c for c in obter_fatos().certificacoes}
    assert set(certificados) == set(produtores.index[produtores["certificacao_organica"]])
    for pid, cert in certificados.items():
        assert cert.validade == produtores.loc[pid, "validade_certificacao"], pid


def test_produtos_dos_fatos_existem_no_catalogo():
    fatos = obter_fatos()
    catalogo = set(obter_repositorio().catalogo.bases)
    nomes = (
        {p for c in fatos.certificacoes for p in c.produtos}
        | {p for c in fatos.capacidades for p in c.produtos}
        | {p for nc in fatos.nao_conformidades for p in nc.produtos}
        | {i.produto for c in fatos.contratos for i in c.itens}
        | set(fatos.origem_animal)
    )
    assert nomes <= catalogo, nomes - catalogo


def test_produtores_dos_fatos_existem_no_cadastro():
    fatos = obter_fatos()
    cadastro = set(obter_repositorio().produtores()["produtor_id"])
    grupos = [fatos.certificacoes, fatos.registros_sanitarios, fatos.nao_conformidades, fatos.dap_caf, fatos.capacidades]
    assert {f.produtor_id for grupo in grupos for f in grupo} <= cadastro


def test_todo_produtor_de_origem_animal_tem_registro_sanitario():
    fatos = obter_fatos()
    repo = obter_repositorio()
    for produto in fatos.origem_animal:
        for pid in repo.produtores_do_produto(produto).query("ativo")["produtor_id"]:
            assert fatos.registro_sanitario(pid) is not None, (produto, pid)


def test_unidades_do_contrato_batem_com_a_tabela():
    repo = obter_repositorio()
    for contrato in obter_fatos().contratos:
        for item in contrato.itens:
            variante = repo.catalogo.variantes(item.produto)[0]
            assert repo.preco_da_variante(variante)["unidade"] == item.unidade, item.produto


def test_capacidades_usam_a_unidade_da_tabela_ou_kg_das_fichas():
    repo = obter_repositorio()
    for capacidade in obter_fatos().capacidades:
        unidades = {repo.preco_da_variante(repo.catalogo.variantes(p)[0])["unidade"] for p in capacidade.produtos}
        assert capacidade.unidade in unidades | {"kg"}, capacidade


# Grava uma cópia do YAML com uma alteração e tenta carregar.
def _carregar_alterado(tmp_path, alterar):
    dados = yaml.safe_load(ARQUIVO_FATOS.read_text(encoding="utf-8"))
    alterar(dados)
    caminho = tmp_path / "fatos.yaml"
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return carregar_fatos(caminho)


@pytest.mark.parametrize(
    "alterar",
    [
        lambda d: d["certificacoes_organicas"][0].pop("fonte"),
        lambda d: d["certificacoes_organicas"][0].update(validade="31/12/2027"),
        lambda d: d["registros_sanitarios"][0].update(situacao="talvez"),
        lambda d: d["capacidades"][0].update(minimo=300, maximo=200),
        lambda d: d["capacidades"][0].update(periodo="quinzena"),
        lambda d: d["contratos"][1].update(dias_entrega=["feriado"]),
        lambda d: d["certificacoes_organicas"][4]["renovacao"].update(concluida_em=dt.date(2026, 11, 20)),
        lambda d: d.pop("origem_animal"),
        lambda d: d["registros_sanitarios"].append(dict(d["registros_sanitarios"][0])),
        lambda d: d["dap_caf"].append(dict(d["dap_caf"][0])),
        lambda d: d["capacidades"].append(dict(d["capacidades"][0])),
        lambda d: d["capacidades"][12].update(meses=[True]),
        lambda d: d["contratos"][0]["itens"].append(dict(d["contratos"][0]["itens"][0])),
        lambda d: d["contratos"][2].update(apelidos=["bom preco"]),
    ],
    ids=[
        "sem-fonte", "data-em-texto", "situacao-invalida", "minimo-maior-que-maximo",
        "periodo-desconhecido", "dia-de-entrega-desconhecido", "renovacao-sem-nova-validade", "sem-origem-animal",
        "sie-repetido", "dap-caf-repetida", "capacidade-sobreposta", "mes-booleano", "item-de-contrato-repetido",
        "apelido-em-dois-contratos",
    ],
)
def test_fatos_invalidos_sao_recusados(tmp_path, alterar):
    with pytest.raises(FatosInvalidos):
        _carregar_alterado(tmp_path, alterar)


def test_yaml_atual_carrega_igual_ao_cache():
    assert carregar_fatos() == obter_fatos()


# --------------------------------------------------------------------------- #
# Alerta                                                                      #
# --------------------------------------------------------------------------- #


def test_alerta_sem_fonte_ou_com_severidade_errada_e_recusado():
    with pytest.raises(ValueError):
        Alerta("X", GRAVE, "mensagem", "")
    with pytest.raises(ValueError):
        Alerta("X", "urgente", "mensagem", "produtores.csv")


def test_ordenar_poe_grave_primeiro_e_tira_repetidos():
    info = Alerta("A", INFO, "a", "produtores.csv")
    grave = Alerta("B", GRAVE, "b", "produtores.csv")
    atencao = Alerta("C", ATENCAO, "c", "produtores.csv")
    assert ordenar([info, grave, atencao, grave]) == [grave, atencao, info]
