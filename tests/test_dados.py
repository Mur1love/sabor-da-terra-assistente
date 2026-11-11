"""Testes da camada de dados (etapa 4). Rodam sobre os arquivos reais de data/, sem rede."""

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from google.genai import types

import sabor_da_terra.dados as pacote_dados
from sabor_da_terra.dados import (
    FERRAMENTAS,
    DadosRepository,
    buscar_produtores,
    disponibilidade,
    extrato_produtor,
    identificar_produtor,
    obter_repositorio,
    preco,
    rastrear_lote,
)
from sabor_da_terra.dados import normalizacao as n
from sabor_da_terra.dados.carregamento import carregar, obter_base
from sabor_da_terra.dados.consultas import _valor
from sabor_da_terra.dados.esquema import TABELAS, colunas

PASTA_DADOS = Path(__file__).resolve().parents[1] / "data"
REFERENCIA = "2026-10-30"  # último dia dos pedidos do dataset
CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")


# --------------------------------------------------------------------------- #
# Normalização                                                                #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "bruto, esperado",
    [("4.50", 4.5), ("4,50", 4.5), ("1.234,56", 1234.56), ("R$ 32,00", 32.0), ("n/d", None), ("", None)],
)
def test_numero_aceita_ponto_virgula_e_nd(bruto, esperado):
    assert n.numero(bruto) == esperado


def test_data_iso_e_brasileira():
    assert n.data("2026-10-02") == date(2026, 10, 2)
    assert n.data("02/10/2026") == date(2026, 10, 2)
    assert n.data("") is None


def test_chave_ignora_acento_caixa_e_hifen():
    assert n.chave("Maracujá") == n.chave("maracuja")
    assert n.chave("Batata-Doce") == "batata doce"


@pytest.mark.parametrize("bruto, esperado", [("11", 11), ("nov", 11), ("Novembro", 11), ("2026-11", 11), ("13", None)])
def test_mes_em_varios_formatos(bruto, esperado):
    assert n.mes(bruto) == esperado


# --------------------------------------------------------------------------- #
# Carregamento e esquema                                                      #
# --------------------------------------------------------------------------- #


def _hash_pasta() -> str:
    h = hashlib.sha256()
    for arquivo in sorted(PASTA_DADOS.rglob("*")):
        if arquivo.is_file():
            h.update(arquivo.read_bytes())
    return h.hexdigest()


def test_carregar_nao_modifica_data():
    antes = _hash_pasta()
    carregar(PASTA_DADOS)
    assert _hash_pasta() == antes


@pytest.mark.parametrize("tabela", list(TABELAS))
def test_tabelas_seguem_o_esquema(tabela):
    df = getattr(obter_base(), tabela)
    assert list(df.columns) == colunas(tabela)
    for coluna in TABELAS[tabela]:
        if coluna.obrigatoria:
            assert df[coluna.nome].notna().all(), f"{tabela}.{coluna.nome} tem nulo"


# Tipo do Python que cada tipo do BigQuery vira (contrato do DadosRepository).
_TIPOS = {
    "STRING": lambda v: isinstance(v, str),
    "DATE": lambda v: isinstance(v, date) and not isinstance(v, datetime),
    "DATETIME": lambda v: isinstance(v, datetime),
    "NUMERIC": lambda v: isinstance(v, float),
    "INT64": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "BOOL": lambda v: isinstance(v, bool),
}


@pytest.mark.parametrize("tabela", list(TABELAS))
def test_valores_seguem_o_contrato_de_tipos(tabela):
    df = getattr(obter_base(), tabela)
    for coluna in TABELAS[tabela]:
        for valor in df[coluna.nome].tolist():
            assert valor is None or _TIPOS[coluna.tipo](valor), f"{tabela}.{coluna.nome}: {valor!r}"


@pytest.mark.parametrize(
    "tabela, coluna, permitidos",
    [
        ("sazonalidade", "nivel", {"alta", "media", "baixa", "nenhuma"}),
        ("produtos", "unidade", {"kg", "unidade", "maço", "dúzia", "litro"}),
        ("transacoes", "status_pagamento", {"pago", "pendente"}),
        ("produtores", "status", {"ativo", "inativo"}),
    ],
)
def test_valores_dentro_do_dominio(tabela, coluna, permitidos):
    assert set(getattr(obter_base(), tabela)[coluna]) <= permitidos


def test_integridade_entre_tabelas():
    base = obter_base()
    produtores = set(base.produtores["produtor_id"])
    produtos = set(base.catalogo.bases)
    assert set(base.transacoes["produtor_id"]) <= produtores
    assert set(base.lotes["produtor_id"]) <= produtores
    assert set(base.produtor_produtos["produtor_id"]) <= produtores
    assert set(base.transacoes["produto"]) <= produtos
    assert set(base.lotes["produto"]) <= produtos
    assert set(base.lotes["id_transacao"]) <= set(base.transacoes["id_transacao"])


def test_volumes_carregados():
    base = obter_base()
    assert len(base.produtores) == 18
    assert len(base.pedidos) == 15
    assert len(base.transacoes) == 30
    assert len(base.lotes) == 20
    assert len(base.produtos) == 53  # 53 linhas: goiaba paluma e pimentão têm duas variantes
    assert len(base.sazonalidade) == 50 * 12


def test_agencia_mantem_zero_a_esquerda():
    produtores = obter_base().produtores
    assert produtores.loc[produtores["produtor_id"] == "P001", "agencia"].item() == "0437"


def test_p015_inativo():
    produtores = obter_base().produtores.set_index("produtor_id")
    assert produtores.loc["P015", "status"] == "inativo"
    assert not produtores.loc["P015", "ativo"]
    assert produtores.drop("P015")["ativo"].all()


def test_preco_organico_nd_vira_sem_oferta_e_nao_zero():
    banana = obter_base().produtos.set_index("produto").loc["banana prata"]
    assert banana["preco_organico"] is None
    assert not banana["tem_oferta_organica"]


def test_unidades_ovos_em_duzia_alface_em_unidade_coentro_em_maco():
    transacoes = obter_base().transacoes.set_index("id_transacao")
    assert transacoes.loc["FIN-2026-019", "unidade"] == "dúzia"  # ovos, "Preço por dúzia"
    assert transacoes.loc["FIN-2026-006", "unidade"] == "unidade"  # alface
    assert transacoes.loc["FIN-2026-007", "unidade"] == "maço"  # coentro


def test_transporte_ambiente_vira_flag():
    lote = obter_base().lotes.set_index("lote_id").loc["LOT-2026-0090"]
    assert lote["transporte_ambiente"]
    assert lote["temperatura_transporte_c"] is None


def test_produtores_ligados_ao_catalogo():
    ligacoes = obter_base().produtor_produtos
    p001 = set(ligacoes.loc[ligacoes["produtor_id"] == "P001", "produto"])
    assert p001 == {"goiaba paluma", "acerola", "manga tommy"}
    # Produto fora do catálogo não é chutado: "feijão" do P015 fica sem ligação.
    feijao = ligacoes[ligacoes["produto_cadastrado"] == "feijão"]
    assert feijao["produto"].isna().all()


def test_todo_lote_ligado_a_uma_transacao():
    lotes = obter_base().lotes
    assert lotes["id_transacao"].notna().all()
    assert lotes.set_index("lote_id").loc["LOT-2026-0089", "id_transacao"] == "FIN-2026-003"


# --------------------------------------------------------------------------- #
# buscar_produtores                                                           #
# --------------------------------------------------------------------------- #


def _ids(resultado):
    return {p["produtor_id"] for p in resultado["produtores"]}


def test_buscar_produtores_por_nome_do_cadastro_e_da_tabela():
    assert _ids(buscar_produtores("goiaba")) == {"P001", "P010"}
    assert _ids(buscar_produtores("queijo coalho")) == {"P003", "P007", "P011"}


def test_buscar_produtores_filtra_organico():
    assert _ids(buscar_produtores("queijo coalho", organico=True, data_referencia=REFERENCIA)) == {"P007"}
    assert _ids(buscar_produtores("queijo coalho", organico=False, data_referencia=REFERENCIA)) == {"P003", "P011"}


def test_buscar_produtores_ignora_inativo_e_avisa():
    resultado = buscar_produtores("macaxeira")
    assert _ids(resultado) == {"P005"}
    assert resultado["inativos_ignorados"] == ["P015"]


def test_buscar_produtores_tolera_acento_caixa_plural_e_apelido():
    assert _ids(buscar_produtores("maracuja")) == {"P006"}
    assert _ids(buscar_produtores("QUEIJO DE COALHO")) == {"P003", "P007", "P011"}
    assert _ids(buscar_produtores("ovos")) == {"P017"}
    assert buscar_produtores("goiabas")["aviso"] is None


def test_buscar_produtores_digitacao_vira_sugestao_sem_dados():
    resultado = buscar_produtores("queijo coalio")
    assert not resultado["encontrado"]
    assert resultado["opcoes"] == ["queijo coalho"]
    assert "produtores" not in resultado
    assert "confirme" in resultado["aviso"]


@pytest.mark.parametrize(
    "termo, sugestao",
    [("melão", "melado"), ("pimenta", "pimentão"), ("batata", "batata doce")],
)
def test_produto_parecido_nao_e_trocado_por_outro(termo, sugestao):
    for resultado in (buscar_produtores(termo), preco(termo, organico=False, quantidade=10), disponibilidade(termo, "11")):
        assert not resultado["encontrado"]
        assert resultado["opcoes"] == [sugestao]
        assert "total" not in resultado and "produtores" not in resultado and "nivel" not in resultado


def test_buscar_produtores_ambiguo_devolve_opcoes():
    resultado = buscar_produtores("mel")
    assert not resultado["encontrado"]
    assert set(resultado["opcoes"]) == {"mel silvestre", "mel de jandaíra"}


def test_buscar_produtores_organico_exclui_certificacao_vencida():
    # P008 tem "sim" no cadastro, mas a certificação venceu em 30/09/2026 (docs/02 §10, armadilha 1).
    resultado = buscar_produtores("mel silvestre", organico=True, data_referencia="2026-11-05")
    assert _ids(resultado) == {"P002", "P018"}
    assert all(p["certificacao_vigente"] for p in resultado["produtores"])
    assert [p["produtor_id"] for p in resultado["certificacao_vencida"]] == ["P008"]
    assert "P008" in resultado["aviso"] and "2026-09-30" in resultado["aviso"]


def test_buscar_produtores_vigencia_depende_da_data():
    antes = buscar_produtores("mel silvestre", organico=True, data_referencia="2026-09-30")
    assert _ids(antes) == {"P002", "P008", "P018"}  # o dia da validade ainda vale
    assert antes["certificacao_vencida"] == []


def test_buscar_produtores_sem_certificacao_vigente_inclui_vencida():
    resultado = buscar_produtores("mel silvestre", organico=False, data_referencia="2026-11-05")
    assert _ids(resultado) == {"P008"}


def test_buscar_produtores_sem_filtro_marca_vigencia():
    resultado = buscar_produtores("mel silvestre", data_referencia="2026-11-05")
    vigencia = {p["produtor_id"]: p["certificacao_vigente"] for p in resultado["produtores"]}
    assert vigencia == {"P002": True, "P008": False, "P018": True}


def test_buscar_produtores_data_invalida():
    assert not buscar_produtores("mel silvestre", data_referencia="ontem")["encontrado"]


def test_buscar_produtores_inexistente():
    resultado = buscar_produtores("caviar")
    assert not resultado["encontrado"]
    assert resultado["aviso"]


# --------------------------------------------------------------------------- #
# disponibilidade                                                             #
# --------------------------------------------------------------------------- #


def test_disponibilidade_caja_em_novembro_e_baixa():
    resultado = disponibilidade("cajá", "novembro")
    assert resultado["nivel"] == "baixa"
    assert resultado["disponivel"]


def test_disponibilidade_nenhuma_nao_esta_disponivel():
    resultado = disponibilidade("mirtilo", "2026-11")
    assert resultado["nivel"] == "nenhuma"
    assert not resultado["disponivel"]


def test_disponibilidade_sem_dado_nao_inventa():
    resultado = disponibilidade("tomate cereja", "11")
    assert not resultado["encontrado"]
    assert "Não há dado de sazonalidade" in resultado["aviso"]


def test_disponibilidade_mes_invalido():
    assert not disponibilidade("goiaba", "mês 13")["encontrado"]


# --------------------------------------------------------------------------- #
# preco                                                                       #
# --------------------------------------------------------------------------- #


def test_preco_queijo_coalho_150kg_aplica_atacado_5_por_cento():
    resultado = preco("queijo coalho", organico=False, quantidade=150)
    assert resultado["desconto_atacado_aplicado"]
    assert resultado["desconto_atacado_pct"] == 5.0
    assert resultado["subtotal"] == 4800.0
    assert resultado["valor_desconto"] == 240.0
    assert resultado["total"] == 4560.0


def test_preco_desconto_vale_a_partir_do_volume_minimo_inclusive():
    assert preco("queijo coalho", organico=False, quantidade=100)["desconto_atacado_aplicado"]
    assert not preco("queijo coalho", organico=False, quantidade=99.9)["desconto_atacado_aplicado"]


def test_preco_abaixo_do_minimo_sem_desconto():
    resultado = preco("queijo coalho", organico=False, quantidade=50)
    assert not resultado["desconto_atacado_aplicado"]
    assert resultado["total"] == 1600.0


def test_preco_organico_nd_e_sem_oferta_e_nao_zero():
    resultado = preco("banana", organico=True, quantidade=10)
    assert resultado["encontrado"]
    assert not resultado["disponivel"]
    assert "total" not in resultado


def test_preco_com_mais_de_uma_variante_pergunta():
    resultado = preco("goiaba", organico=False, quantidade=10)
    assert not resultado["encontrado"]
    assert set(resultado["opcoes"]) == {"goiaba paluma extra", "goiaba paluma especial"}


def test_preco_variante_pelo_termo():
    resultado = preco("goiaba extra", organico=True, quantidade=120)
    assert resultado["produto"] == "goiaba paluma extra"
    assert resultado["total"] == 594.0  # 120 × 5,50 = 660, menos 10%


def test_preco_ovos_em_duzia_traz_observacao_da_tabela():
    resultado = preco("ovos", organico=False, quantidade=10)
    assert resultado["unidade"] == "dúzia"
    assert resultado["total"] == 180.0


def test_preco_quantidade_invalida():
    assert not preco("alface", organico=False, quantidade=0)["encontrado"]


# --------------------------------------------------------------------------- #
# rastrear_lote                                                               #
# --------------------------------------------------------------------------- #


def test_rastrear_lote_exato_liga_produtor_e_transacao():
    resultado = rastrear_lote("LOT-2026-0089")
    assert resultado["encontrado"] and resultado["exato"]
    assert resultado["produtor"]["produtor_id"] == "P003"
    assert resultado["transacao"]["id_transacao"] == "FIN-2026-003"
    assert resultado["aviso"] is None


def test_rastrear_lote_forma_solta_avisa_que_nao_e_exato():
    resultado = rastrear_lote("lote 089")
    assert resultado["encontrado"]
    assert not resultado["exato"]
    assert resultado["lote"]["lote_id"] == "LOT-2026-0089"
    assert "LOT-2026-0089" in resultado["aviso"]


def test_rastrear_lote_ignora_pontuacao_nas_pontas():
    resultado = rastrear_lote("LOT-2026-0089.")
    assert resultado["exato"] and resultado["aviso"] is None


def test_rastrear_lote_mostra_certificacao_na_data_da_entrega():
    # LOT-2026-0104: mel da P008 entregue em 01/10 com "Certificação orgânica anexa", mas venceu em 30/09.
    assert not rastrear_lote("LOT-2026-0104")["produtor"]["certificacao_vigente_na_entrega"]
    assert rastrear_lote("LOT-2026-0093")["produtor"]["certificacao_vigente_na_entrega"]


def test_rastrear_lote_2024_089_nao_inventa_e_sugere():
    resultado = rastrear_lote("2024-089")
    assert not resultado["encontrado"]
    assert "lote" not in resultado  # nenhum dado de outro lote
    assert resultado["sugestoes"] == ["LOT-2026-0089"]
    assert "não existe" in resultado["aviso"]


def test_rastrear_lote_inexistente():
    resultado = rastrear_lote("LOT-2026-0500")
    assert not resultado["encontrado"]
    assert "LOT-2026-0089 a LOT-2026-0108" in resultado["aviso"]


# --------------------------------------------------------------------------- #
# extrato_produtor                                                            #
# --------------------------------------------------------------------------- #


def _ids_tx(itens):
    return {t["id_transacao"] for t in itens}


def test_extrato_p001_outubro_mostra_pagamento_de_setembro_recebido():
    resultado = extrato_produtor("P001", "2026-10", data_referencia=REFERENCIA)
    assert resultado["vendas_no_mes"] == []
    assert _ids_tx(resultado["recebidos_no_mes"]) == {"FIN-2026-001", "FIN-2026-002"}
    assert resultado["a_receber"] == [] and resultado["vencidas"] == []
    assert resultado["totais"]["recebido_no_mes"] == 940.0


def test_extrato_p001_setembro_separa_pago_de_pendente():
    resultado = extrato_produtor("P001", "2026-09", data_referencia=REFERENCIA)
    assert _ids_tx(resultado["vendas_no_mes"]) == {"FIN-2026-001", "FIN-2026-002", "FIN-2026-015"}
    assert {t["status_pagamento"] for t in resultado["vendas_no_mes"]} == {"pago"}
    assert resultado["totais"]["vendido_no_mes"] == 1090.0


def test_extrato_p003_tem_vencidas_com_atraso():
    resultado = extrato_produtor("P003", "2026-10", data_referencia=REFERENCIA)
    assert _ids_tx(resultado["vencidas"]) == {"FIN-2026-013", "FIN-2026-014"}
    assert all(t["dias_em_atraso"] == 12 for t in resultado["vencidas"])
    assert resultado["totais"]["vencido"] == 6020.0


def test_extrato_p010_separa_a_receber_de_vencido_pela_data():
    antes = extrato_produtor("P010", "2026-10", data_referencia="2026-10-30")
    depois = extrato_produtor("P010", "2026-10", data_referencia="2026-11-11")
    assert _ids_tx(antes["a_receber"]) == {"FIN-2026-024", "FIN-2026-025"}
    assert _ids_tx(depois["vencidas"]) == {"FIN-2026-024", "FIN-2026-025"}


def test_extrato_aceita_id_solto_e_rejeita_invalidos():
    assert extrato_produtor("p1", "2026-10", data_referencia=REFERENCIA)["produtor"]["produtor_id"] == "P001"
    assert not extrato_produtor("P999", "2026-10")["encontrado"]
    assert not extrato_produtor("P001 e P002", "2026-10")["encontrado"]
    assert "identificar_produtor" in extrato_produtor("Maria das Graças", "2026-10")["aviso"]
    assert not extrato_produtor("P001", "mês 13")["encontrado"]


@pytest.mark.parametrize(
    "mes, referencia, esperado",
    [("outubro", "2026-11-11", "2026-10"), ("10", "2026-10-30", "2026-10"), ("dezembro", "2026-11-11", "2025-12")],
)
def test_extrato_mes_sem_ano_e_o_mais_recente_ate_a_referencia(mes, referencia, esperado):
    resultado = extrato_produtor("P001", mes, data_referencia=referencia)
    assert resultado["mes"] == esperado
    assert esperado in resultado["aviso"]


# --------------------------------------------------------------------------- #
# identificar_produtor                                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "termo, esperado, por",
    [
        ("P008", "P008", "codigo"),
        ("p8", "P008", "codigo"),
        ("Josefa", "P008", "nome"),
        ("Dona Maria das Graças", "P001", "nome"),
        ("cicero romao", "P003", "nome"),
        ("(87) 99812-3456", "P001", "telefone"),  # remetente do PED-012
        ("+55 87 99745-1098", "P003", "telefone"),  # remetente do PED-015
    ],
)
def test_identificar_produtor(termo, esperado, por):
    resultado = identificar_produtor(termo, data_referencia=REFERENCIA)
    assert resultado["encontrado"]
    assert resultado["produtor"]["produtor_id"] == esperado
    assert resultado["por"] == por


def test_identificar_produtor_ambiguo_devolve_opcoes():
    resultado = identificar_produtor("Maria")
    assert not resultado["encontrado"]
    assert {o["produtor_id"] for o in resultado["opcoes"]} == {"P001", "P006"}


def test_identificar_produtor_inexistente_e_inativo():
    assert not identificar_produtor("Sebastião")["encontrado"]  # citado no PED-015, sem cadastro
    assert not identificar_produtor("P999")["encontrado"]
    assert not identificar_produtor("(81) 3333-4444")["encontrado"]
    inativo = identificar_produtor("Geraldo")
    assert inativo["encontrado"] and "inativo" in inativo["aviso"]


def test_identificar_produtor_mostra_vigencia_e_nao_devolve_telefone():
    resultado = identificar_produtor("Josefa", data_referencia="2026-11-05")
    assert resultado["produtor"]["certificacao_organica"]
    assert not resultado["produtor"]["certificacao_vigente"]
    assert "99845" not in json.dumps(resultado)


# --------------------------------------------------------------------------- #
# Dados sensíveis                                                             #
# --------------------------------------------------------------------------- #

SENSIVEIS = {
    "cpf", "chave_pix", "chave_pix_deposito", "banco", "agencia", "conta_corrente", "data_nascimento",
    "telefone", "email", "endereco",
}


def _saidas_das_ferramentas():
    return [
        buscar_produtores("queijo coalho"),
        buscar_produtores("mel silvestre", organico=True, data_referencia=REFERENCIA),
        buscar_produtores("mel silvestre", data_referencia="2026-11-05"),
        identificar_produtor("Josefa"),
        identificar_produtor("Maria"),
        identificar_produtor("(87) 99812-3456"),
        disponibilidade("goiaba", "10"),
        preco("queijo coalho", False, 150),
        rastrear_lote("LOT-2026-0089"),
        rastrear_lote("lote 093"),
        *(extrato_produtor(f"P{i:03d}", "2026-10", data_referencia=REFERENCIA) for i in range(1, 19)),
        *(extrato_produtor(f"P{i:03d}", "2026-09", data_referencia=REFERENCIA) for i in range(1, 19)),
    ]


def _chaves(objeto):
    if isinstance(objeto, dict):
        for k, v in objeto.items():
            yield k
            yield from _chaves(v)
    elif isinstance(objeto, list):
        for item in objeto:
            yield from _chaves(item)


def test_nenhuma_ferramenta_devolve_dado_pessoal_ou_bancario():
    produtores = obter_base().produtores
    proibidos = [
        *produtores["conta_corrente"], *produtores["telefone"], *produtores["email"], *produtores["endereco"],
    ]
    for saida in _saidas_das_ferramentas():
        texto = json.dumps(saida, ensure_ascii=False)
        assert not CPF.search(texto)
        assert not SENSIVEIS & set(_chaves(saida))
        assert not any(valor in texto for valor in proibidos if valor)


def test_esquema_marca_contato_como_sensivel():
    assert {"telefone", "email", "endereco"} <= {c.nome for c in TABELAS["produtores"] if c.sensivel}


# --------------------------------------------------------------------------- #
# Function calling                                                            #
# --------------------------------------------------------------------------- #


def test_valor_converte_decimal_do_bigquery():
    convertido = _valor(Decimal("32.50"))
    assert convertido == 32.5 and isinstance(convertido, float)
    json.dumps({"preco": convertido})


def test_repositorio_entrega_pedidos():
    repo = obter_repositorio()
    assert len(repo.pedidos()) == 15
    assert repo.pedido("PED-2026-012")["canal"]
    assert repo.pedido("PED-9999") is None


def test_pacote_nao_expoe_as_tabelas_direto():
    # Fora do pacote, os dados passam pelo repositório (ponto de troca para o BigQuery).
    for nome in ("obter_base", "carregar", "BaseDados"):
        assert nome not in pacote_dados.__all__
        assert not hasattr(pacote_dados, nome)


def test_consultas_leem_so_pelo_repositorio():
    # Padrão de troca do docs/04 §6: a versão BigQuery implementa o mesmo protocolo.
    assert isinstance(obter_repositorio(), DadosRepository)
    fonte = (Path(__file__).resolve().parents[1] / "sabor_da_terra" / "dados" / "consultas.py").read_text()
    assert "obter_base" not in fonte


@pytest.mark.parametrize("funcao", FERRAMENTAS, ids=lambda f: f.__name__)
def test_ferramentas_viram_declaracao_do_gemini(funcao):
    declaracao = types.FunctionDeclaration.from_callable_with_api_option(callable=funcao)
    assert declaracao.name == funcao.__name__
    assert declaracao.description


@pytest.mark.parametrize("saida", _saidas_das_ferramentas())
def test_saidas_sao_json(saida):
    json.dumps(saida)
