"""Etapa 14: o gabarito inteiro (tests/gabarito/*.yaml) contra o assistente integrado.

Comando único: `pytest tests/test_gabarito.py`.

Cada caso roda no `Assistente` de verdade (roteamento, ferramentas, composição)
e é conferido em três frentes:
- funções esperadas (`funcoes_esperadas`) chamadas na conversa;
- citações válidas: arquivos de `data/` que saíram das funções do turno, e ao
  menos uma fonte por turno nos casos documentais;
- cada critério de `deve_conter` / `nao_deve_conter`, decidido pelo juiz
  (Flash-Lite com saída estruturada).

Roda 100% offline: repete as respostas gravadas na rodada real
(`python -m scripts.avaliar_gabarito`). Caso sem gravação é pulado com a
instrução — não finge passar. Os números por desafio e por requisito estão
no `docs/05-avaliacao.md`.
"""

import pytest

from sabor_da_terra.avaliacao.clientes import FALLBACK_DA_AVALIACAO
from sabor_da_terra.avaliacao.execucao import STATUS_OK, avaliar_caso
from sabor_da_terra.avaliacao.gabarito import carregar_casos
from sabor_da_terra.avaliacao.metricas import falhas
from sabor_da_terra.llm.cliente import VARIAVEL_FALLBACK, FixtureAusenteError, LLMClient

# Falhas conhecidas que ficaram como limitação registrada no docs/05 (id → causa).
# `strict=True`: se um caso desses passar a acertar, o teste avisa para tirar daqui.
# Rodada 3 (19/11/2026, prompt 1.5.0): 23 casos do gabarito e 2 de robustez.
# Nenhuma falha é de extração nem de regra (código determinístico).
LIMITACOES_CONHECIDAS: dict[str, str] = {
    # Orquestração: o modelo não chama (ou não encadeia) a função esperada.
    "CERT-002": "orquestração: não chama verificar_conformidade; faltam NC-001 e ausência de certificação",
    "CERT-003": "orquestração: resposta certa (11/11), mas sem verificar_conformidade",
    "CERT-004": "orquestração: sem verificar_conformidade, não cita o SIE pendente (premissa já não é aceita)",
    "DOC-001": "orquestração: resposta certa (8/8) por buscar_produtores, sem consultar_documentos",
    "DOC-003": "orquestração + recuperação: sem preco; contrato 045/2026-PNAE não recuperado",
    "PROD-002": "orquestração: sem triar_pendentes, não esclarece o tipo de manteiga",
    "PROD-004": "orquestração: notificar_produtores sem identificar_produtor; faltam certificação, SIE e exclusividade",
    "TRI-003": "orquestração: não chama verificar_conformidade; sem histórico do cliente e disponibilidade",
    "TRI-008": "orquestração: resposta certa (16/16), mas sem buscar_produtores e disponibilidade",
    "TRI-009": "orquestração: pedido de documentos sem consultar_documentos, verificar_conformidade e consultar_lotes",
    "TRI-010": "orquestração: resposta certa (20/20), mas sem preco e disponibilidade",
    "TRI-011": "orquestração: sem consultar_lotes; rastreabilidade, laudos fitossanitários e capacidade ficam de fora",
    "TRI-012": "orquestração: mensagem da produtora não passa por triar_pedido; P001 não identificada",
    "TRI-014": "orquestração: consulta documentos, mas sem buscar_produtores e consultar_lotes; o juiz conta nomes de produtores como dado pessoal",
    "TRI-015": "orquestração: oferta do produtor não passa por triar_pedido; P003 não identificado",
    "ROB-005": "orquestração: resposta certa, mas por verificar_conformidade em vez de identificar_produtor",
    # Composição: os dados estavam no turno e a resposta omite.
    "CERT-005": "composição: omite a capacidade estimada de 300 kg/mês",
    "CTX-003": "composição: não cita data/financeiro.csv e data/lotes.csv",
    "TRI-007": "composição: chama todas as funções, mas omite o cajá opcional, o mel orgânico e a restrição de P017",
    "TRI-013": "composição: chama as funções, mas omite o volume (200 crianças, 15 dias), preços de janeiro e capacidade",
    "ROB-003": "composição: diz destino e produtor, mas omite 45 kg e a entrega em 02/09/2026",
    # Recuperação: o trecho certo não chega ao modelo.
    "DOC-002": "recuperação: busca lexical não traz laudos e contratos institucionais",
    "DOC-006": "recuperação: cruzamento DAP/CAF entre cadastro e documentos fica incompleto",
    # Contexto (RF5): o segundo turno perde o que o primeiro estabeleceu.
    "CTX-001": "contexto: no turno 1 não identifica P002 e P018",
    "CTX-002": "contexto: no turno 2 perde o PED-2026-006 e indica P011 (sem SIE) para o atacado",
}


def _parametros(conjunto: str):
    for caso in carregar_casos(conjunto):
        marcas = []
        if caso.id in LIMITACOES_CONHECIDAS:
            marcas.append(pytest.mark.xfail(reason=LIMITACOES_CONHECIDAS[caso.id], strict=True))
        yield pytest.param(caso, id=caso.id, marks=marcas)


def _avaliar(caso, monkeypatch):
    monkeypatch.setenv(VARIAVEL_FALLBACK, FALLBACK_DA_AVALIACAO)
    try:
        resultado = avaliar_caso(caso, LLMClient(modo="fixture"))
    except FixtureAusenteError as erro:
        pytest.skip(f"{caso.id} sem gravação ({erro}) — rode python -m scripts.avaliar_gabarito")

    assert resultado["status"] == STATUS_OK, resultado.get("erro")
    detalhe = falhas([resultado])
    assert resultado["aprovado"], f"{caso.id} reprovado: {detalhe[0] if detalhe else resultado}"


@pytest.mark.parametrize("caso", list(_parametros("gabarito")))
def test_caso_do_gabarito(caso, monkeypatch):
    _avaliar(caso, monkeypatch)


@pytest.mark.parametrize("caso", list(_parametros("robustez")))
def test_variacao_coloquial_de_robustez(caso, monkeypatch):
    """5 variações coloquiais novas, fora do gabarito (tests/robustez/)."""
    _avaliar(caso, monkeypatch)
