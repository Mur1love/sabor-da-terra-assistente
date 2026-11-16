"""Etapa 12: orquestração do assistente — estado da sessão, mascaramento, ferramentas e turno."""

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from sabor_da_terra.assistente.estado import EstadoSessao, data_referencia_padrao
from sabor_da_terra.assistente.mascaramento import mascarar_dados_sensiveis
from sabor_da_terra.dados import obter_repositorio

RAIZ = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Estado da sessão
# ---------------------------------------------------------------------------


def test_estado_atualiza_produtor_em_foco_por_identificar():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("identificar_produtor", {}, {"encontrado": True, "produtor": {"produtor_id": "P008", "nome": "Josefa Alves de Souza"}})
    assert estado.produtor_em_foco == {"produtor_id": "P008", "nome": "Josefa Alves de Souza"}


def test_estado_atualiza_produto_por_buscar_e_por_conformidade_dict():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("buscar_produtores", {}, {"produto": "mel silvestre"})
    assert estado.produto_em_foco == "mel silvestre"
    estado.atualizar("verificar_conformidade", {}, {"produto": {"produto": "goiaba paluma", "quantidade": 300}})
    assert estado.produto_em_foco == "goiaba paluma"  # quirk: "produto" é dict na conformidade


def test_estado_atualiza_pedido_em_foco_pelo_id_na_mensagem():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("triar_pedido", {"mensagem": "300kg de goiaba para PED-2026-006, urgente"}, {"itens": [{"produto": "goiaba paluma"}]})
    assert estado.pedido_em_foco == "PED-2026-006"
    assert estado.produto_em_foco == "goiaba paluma"


def test_estado_rastrear_lote_atualiza_produto():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("rastrear_lote", {}, {"encontrado": True, "lote": {"lote_id": "LOT-2026-0089", "produto": "queijo coalho"}})
    assert estado.produto_em_foco == "queijo coalho"


def test_estado_ignora_resultados_sem_foco():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("triar_pendentes", {}, {"total_registros": 15})
    estado.atualizar("consultar_documentos", {}, {"resposta": "x"})
    estado.atualizar("notificar_produtores", {}, {"notificacoes": []})
    estado.atualizar("identificar_produtor", {}, {"encontrado": False, "aviso": "não existe"})
    assert (estado.produtor_em_foco, estado.pedido_em_foco, estado.produto_em_foco) == (None, None, None)


def test_data_referencia_padrao_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("DATA_REFERENCIA", "2026-10-30")
    assert data_referencia_padrao() == "2026-10-30"
    monkeypatch.delenv("DATA_REFERENCIA", raising=False)
    assert data_referencia_padrao() == date.today().isoformat()


def test_contexto_bloco_legivel_e_serializacao_idempotente():
    estado = EstadoSessao(data_referencia="2026-10-30", pedido_em_foco="PED-2026-006")
    estado.atualizar("identificar_produtor", {}, {"encontrado": True, "produtor": {"produtor_id": "P008", "nome": "Josefa Alves de Souza"}})
    bloco = estado.contexto()
    assert "2026-10-30" in bloco and "P008" in bloco and "PED-2026-006" in bloco
    assert EstadoSessao.from_dict(estado.to_dict()) == estado


# ---------------------------------------------------------------------------
# Mascaramento de dados sensíveis
# ---------------------------------------------------------------------------


def test_mascara_cpf_pix_conta_e_telefone_em_payload_aninhado():
    cadastro = obter_repositorio().produtores()
    cpf, pix = str(cadastro.iloc[0]["cpf"]), str(cadastro.iloc[0]["chave_pix"])
    conta, telefone = str(cadastro.iloc[0]["conta_corrente"]), str(cadastro.iloc[0]["telefone"])
    payload = {"a": [f"CPF {cpf} e PIX {pix}", {"conta": conta, "tel": telefone}]}
    texto = json.dumps(mascarar_dados_sensiveis(payload), ensure_ascii=False)
    assert cpf not in texto and pix not in texto and conta not in texto and telefone not in texto
    assert "***" in texto


def test_cpf_solto_em_texto_e_mascarado_e_texto_limpo_passa_igual():
    assert mascarar_dados_sensiveis("CPF 123.456.789-09 aqui") == "CPF ***.***.***-** aqui"
    assert mascarar_dados_sensiveis({"msg": "300kg de goiaba para PED-2026-006"}) == {"msg": "300kg de goiaba para PED-2026-006"}


def test_tipos_nao_string_ficam_intactos():
    assert mascarar_dados_sensiveis({"qtd": 300, "ok": True, "nada": None}) == {"qtd": 300, "ok": True, "nada": None}
