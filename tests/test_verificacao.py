"""Etapa 14: trava de fatos — código, valor em R$ e data só chegam à tela se vieram dos dados."""

from sabor_da_terra.assistente.verificacao import (
    AVISO_FATOS_REMOVIDOS,
    Universo,
    fatos_sem_respaldo,
    so_fatos_com_respaldo,
)
from sabor_da_terra.produtores import resumo_produtor


def _universo_p003():
    return Universo.de(
        {"pergunta": "Quanto o Cícero (P003) tem em atraso do SuperBom?", "data_referencia": "2026-10-30"},
        resumo_produtor("P003", "2026-10", "2026-10-30"),
    )


def test_fatos_dos_dados_passam_intactos():
    texto = "FIN-2026-013 (R$ 4.500,00) e FIN-2026-014 (R$ 1.520,00), total R$ 6.020,00, vencidos em 18/10/2026."
    assert so_fatos_com_respaldo(texto, _universo_p003()) == texto


def test_valor_calculado_pelo_modelo_sai():
    """O LLM não faz contas (docs/04): soma que nenhuma função devolveu é removida."""
    texto = "Atrasado: R$ 6.020,00. Com juros, R$ 6.200,00."
    limpo = so_fatos_com_respaldo(texto, _universo_p003())
    assert "6.200,00" not in limpo and "R$ 6.020,00" in limpo
    assert limpo.endswith(AVISO_FATOS_REMOVIDOS)


def test_codigo_e_data_inventados_saem():
    universo = _universo_p003()
    assert fatos_sem_respaldo("O lote LOT-2026-0999 venceu em 05/01/2027.", universo) == ["LOT-2026-0999", "05/01/2027"]


def test_palavras_com_hifen_sem_digito_nao_sao_codigo():
    assert fatos_sem_respaldo("O pass-through e o e-mail seguem; BEM-VINDO.", Universo()) == []


def test_fatos_da_pergunta_valem():
    universo = Universo.de("Entrega na BR-423 km 12 para o PED-2026-006 em 29/10/2026")
    assert fatos_sem_respaldo("Entrega na BR-423 do PED-2026-006 em 29/10/2026.", universo) == []


def test_resposta_sem_nenhum_fato_verificavel_nao_muda():
    texto = "Não encontrei essa informação nos dados da cooperativa."
    assert so_fatos_com_respaldo(texto, Universo()) == texto


def test_formatacao_em_linhas_e_preservada():
    universo = Universo.de({"valor": 32.0, "id": "P003"})
    texto = "Itens:\n- Queijo do P003 a R$ 32,00.\n- Mel do P099 a R$ 50,00.\n\nFim."
    limpo = so_fatos_com_respaldo(texto, universo)
    assert "- Queijo do P003 a R$ 32,00." in limpo and "P099" not in limpo
    assert limpo.startswith("Itens:\n") and "Fim." in limpo
