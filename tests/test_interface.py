"""Etapa 13: interface Streamlit — fontes citadas, erros amigáveis e fila de triagem."""

import pytest

import pandas as pd

from sabor_da_terra.interface import (
    detalhes_da_fila,
    estilo_celula_prioridade,
    estilo_celula_problemas,
    extrair_fontes,
    formatar_fila,
    mensagem_de_erro,
)
from sabor_da_terra.llm.cliente import FixtureAusenteError
from sabor_da_terra.triagem.fila import triar_pendentes
from tests.dobles import Erro429


# ---------------------------------------------------------------------------
# Fontes da resposta documental
# ---------------------------------------------------------------------------


def test_extrair_fontes_um_marcador():
    assert extrair_fontes("certificado [fonte: data/certificacoes.txt] válido") == ["data/certificacoes.txt"]


def test_extrair_fontes_separa_ponto_e_virgula():
    texto = "por [fonte: data/financeiro.csv; data/lotes.csv] e [fonte: data/lotes.csv]"
    assert extrair_fontes(texto) == ["data/financeiro.csv", "data/lotes.csv"]


def test_extrair_fontes_sem_marcador():
    assert extrair_fontes("Não encontrei essa informação nos documentos.") == []


# ---------------------------------------------------------------------------
# Mensagens de erro amigáveis (nada de stack trace)
# ---------------------------------------------------------------------------


def test_mensagem_de_erro_429():
    msg = mensagem_de_erro(Erro429())
    assert "429" in msg and ("cota" in msg or "limite" in msg)


def test_mensagem_de_erro_fixture_ausente():
    assert "gravar" in mensagem_de_erro(FixtureAusenteError("x")).lower()


def test_mensagem_de_erro_generica():
    msg = mensagem_de_erro(RuntimeError("boom"))
    assert "Não consegui" in msg and "boom" not in msg


# ---------------------------------------------------------------------------
# Fila de triagem para o st.dataframe
# ---------------------------------------------------------------------------

COLUNAS_FILA = ["Ordem", "Pedido", "Comprador", "Prioridade", "Status", "Prazo", "Produtos", "Problemas"]


def test_formatar_fila_15_registros_ordem_canonica():
    df = formatar_fila(triar_pendentes("2026-10-30"))
    assert len(df) == 15
    assert list(df.columns) == COLUNAS_FILA
    # Urgentes no topo: alta primeiro, prazo vencido (PED-2026-006) na frente.
    assert df.iloc[0]["Pedido"] == "PED-2026-006"
    assert df.iloc[0]["Prioridade"] == "alta"
    assert df.iloc[0]["Problemas"] >= 1
    assert (df["Prioridade"].head(4) == "alta").all()
    assert df.iloc[-1]["Ordem"] == 15


def test_formatar_fila_produtos_e_prazo():
    df = formatar_fila(triar_pendentes("2026-10-30"))
    linha_com_produto = df[df["Produtos"] != ""].iloc[0]
    assert "kg" in linha_com_produto["Produtos"] or "un" in linha_com_produto["Produtos"]
    assert df["Prazo"].isna().sum() == 0  # "Não informado", nunca vazio


def test_formatar_fila_vazia():
    df = formatar_fila({"fila": [], "total_registros": 0})
    assert len(df) == 0
    assert list(df.columns) == COLUNAS_FILA


def test_detalhes_da_fila_traz_alertas():
    resultado = triar_pendentes("2026-10-30")
    detalhes = detalhes_da_fila(resultado)
    assert detalhes[0][0].startswith("PED-2026-006")
    assert any("PRAZO_VENCIDO" in markdown for _, markdown in detalhes)
    assert all(isinstance(titulo, str) and isinstance(markdown, str) for titulo, markdown in detalhes)


# ---------------------------------------------------------------------------
# Destaque visual das células da fila: legível no tema claro E no escuro
# ---------------------------------------------------------------------------


def test_estilo_celula_pinta_fundo_e_texto():
    """A regra carrega o texto junto: só o fundo fica ilegível no tema escuro."""
    for regra in (
        estilo_celula_prioridade("alta"),
        estilo_celula_prioridade("media"),
        estilo_celula_prioridade("baixa"),
        estilo_celula_problemas(3),
    ):
        assert "background-color:" in regra
        assert "color:" in regra


def test_estilo_celula_prioridade_valores():
    assert estilo_celula_prioridade("alta") == "background-color: #ffd9d9; color: #7f1d1d;"
    assert estilo_celula_prioridade("media") == "background-color: #fff3c4; color: #713f12;"
    assert estilo_celula_prioridade("baixa") == "background-color: #dcf5e3; color: #166534;"
    assert estilo_celula_prioridade("desconhecida") == ""


def test_estilo_celula_problemas_valores():
    assert estilo_celula_problemas(0) == ""
    assert estilo_celula_problemas(14) == "background-color: #ffd9d9; color: #7f1d1d;"
