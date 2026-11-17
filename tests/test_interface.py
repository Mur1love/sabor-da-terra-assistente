"""Etapa 13: interface Streamlit — fontes citadas, erros amigáveis e fila de triagem."""

import pytest

from sabor_da_terra.interface import extrair_fontes, mensagem_de_erro
from sabor_da_terra.llm.cliente import FixtureAusenteError
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
