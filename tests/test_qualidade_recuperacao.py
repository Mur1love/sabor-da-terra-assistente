"""Avaliação da qualidade da recuperação documental do RAG.

Critério de aceite da Issue 7:
Pelo menos 9 de 10 perguntas devem recuperar o documento
esperado entre os três primeiros resultados.

Este teste só realiza chamadas reais à API quando
EXECUTAR_TESTES_RAG_REAL=1.
"""

import os
from pathlib import Path

import pytest

from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.rag.recuperacao import buscar_documentos


RAIZ = Path(__file__).resolve().parents[1]

PASTA_INDICE = RAIZ / ".cache" / "rag" / "indice"
ARQUIVO_CACHE = RAIZ / ".cache" / "rag" / "embeddings.json"


GABARITO = [
    (
        "certificação da Josefa",
        "cert_organica_josefa_souza_P008.txt",
    ),
    (
        "frango caipira SIE",
        "inspecao_adagro_2026.txt",
    ),
    (
        "certificação orgânica da Ana Bezerra",
        "cert_organica_ana_bezerra_P004.txt",
    ),
    (
        "laudo sanitário do apiário de José",
        "laudo_sanitario_apiario_jose_P002.txt",
    ),
    (
        "laudo sanitário da queijaria de Cícero",
        "laudo_sanitario_queijaria_cicero_P003.txt",
    ),
    (
        "contrato do PNAE de Garanhuns",
        "contrato_pnae_garanhuns.txt",
    ),
    (
        "contrato do Mercado Bom Preço",
        "contrato_mercado_bom_preco.txt",
    ),
    (
        "características técnicas da goiaba Paluma",
        "goiaba_paluma.txt",
    ),
    (
        "ficha técnica do queijo coalho",
        "queijo_coalho.txt",
    ),
    (
        "informações técnicas sobre hortaliças",
        "hortalicas.txt",
    ),
]


@pytest.mark.skipif(
    os.getenv("EXECUTAR_TESTES_RAG_REAL") != "1",
    reason=(
        "Teste de recuperação real desativado. "
        "Defina EXECUTAR_TESTES_RAG_REAL=1 para executar."
    ),
)
def test_recuperacao_top3():
    """Verifica se pelo menos 9/10 documentos aparecem no top-3."""

    assert PASTA_INDICE.is_dir(), (
        "Índice vetorial não encontrado. "
        "Execute 'python -m sabor_da_terra.rag.indexar'."
    )

    assert len(GABARITO) == 10, (
        "O gabarito deve conter exatamente 10 perguntas."
    )

    # O conftest.py força LLM_MODO=fixture.
    # Aqui criamos explicitamente um cliente real,
    # somente quando este teste é habilitado.
    cliente = LLMClient(modo="real")

    acertos = 0
    erros = []

    for numero, (pergunta, arquivo_esperado) in enumerate(
        GABARITO,
        start=1,
    ):
        resultados = buscar_documentos(
            pergunta=pergunta,
            filtros=None,
            k=3,
            cliente=cliente,
            pasta_indice=PASTA_INDICE,
            arquivo_cache=ARQUIVO_CACHE,
        )

        assert resultados, (
            f"A pergunta {numero} não retornou resultados."
        )

        assert all(
            resultado.get("arquivo")
            for resultado in resultados
        ), (
            f"A pergunta {numero} retornou "
            "um resultado sem arquivo."
        )

        arquivos_encontrados = [
            resultado["arquivo"]
            for resultado in resultados
        ]

        acertou = arquivo_esperado in arquivos_encontrados

        if acertou:
            acertos += 1
        else:
            erros.append(
                {
                    "pergunta": pergunta,
                    "esperado": arquivo_esperado,
                    "encontrados": arquivos_encontrados,
                }
            )

        print(f"\n[{numero}/10] {pergunta}")
        print(f"Esperado: {arquivo_esperado}")

        for posicao, resultado in enumerate(
            resultados,
            start=1,
        ):
            print(
                f"  {posicao}º - {resultado['arquivo']} "
                f"(score: {resultado['score']:.4f})"
            )

        print(
            "Resultado: "
            + ("ACERTOU" if acertou else "ERROU")
        )

    total = len(GABARITO)
    taxa_acerto = acertos / total

    print("\n" + "=" * 60)
    print("RELATÓRIO FINAL DA RECUPERAÇÃO DOCUMENTAL")
    print("=" * 60)
    print(f"Total de perguntas: {total}")
    print(f"Acertos: {acertos}")
    print(f"Erros: {len(erros)}")
    print(f"Taxa de acerto: {taxa_acerto:.1%}")

    if erros:
        print("\nPERGUNTAS QUE FALHARAM:")

        for erro in erros:
            print(f"\nPergunta: {erro['pergunta']}")
            print(f"Esperado: {erro['esperado']}")
            print(f"Encontrados: {erro['encontrados']}")

    print("=" * 60)

    assert acertos >= 9, (
        f"Critério de aceite não atingido: "
        f"{acertos}/{total} acertos "
        f"({taxa_acerto:.1%}). "
        "São necessários pelo menos 9 acertos."
    )
