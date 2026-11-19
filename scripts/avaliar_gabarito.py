"""Rodada da avaliação ponta a ponta (#14): o gabarito inteiro contra o assistente.

Uso:
    python -m scripts.avaliar_gabarito                    # rodada 1, todos os casos
    python -m scripts.avaliar_gabarito --rodada 2         # rodada 2 (depois das correções)
    python -m scripts.avaliar_gabarito --casos ANTI-001 DOC-005
    python -m scripts.avaliar_gabarito --relatorio        # só imprime o relatório da rodada
    python -m scripts.avaliar_gabarito --conjunto robustez  # as 5 variações coloquiais (fora do gabarito)

O cliente é híbrido: o que já está gravado em `tests/fixtures/llm` é repetido
sem gastar cota; o que falta é gravado com a API real. Rodar de novo completa
só o que ficou para trás (casos com `erro_infra` por cota são refeitos). O
resultado de cada caso vai para `docs/avaliacao/rodada-N.json` assim que sai.

Para a replay do `pytest tests/test_gabarito.py` bater com a gravação, a
rodada usa os modelos padrão do projeto (ignora os do `.env`) e o fallback
fixo da avaliação. Requer `GEMINI_API_KEY` no `.env`.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from sabor_da_terra.assistente.prompt import VERSAO_PROMPT_ASSISTENTE
from sabor_da_terra.avaliacao.clientes import (
    FALLBACK_DA_AVALIACAO,
    REGISTRO,
    ClienteHibrido,
    ligar_clientes_internos,
)
from sabor_da_terra.avaliacao.execucao import STATUS_OK, avaliar_caso
from sabor_da_terra.avaliacao.gabarito import RAIZ, carregar_casos
from sabor_da_terra.avaliacao.metricas import falhas, metricas, relatorio_markdown
from sabor_da_terra.llm.cliente import VARIAVEL_FALLBACK, LLMClient, Papel
from sabor_da_terra.prompts.avaliacao import VERSAO_PROMPT_JUIZ

PASTA_RESULTADOS = RAIZ / "docs" / "avaliacao"
VARIAVEIS_DE_MODELO = ("GEMINI_MODELO_TRIAGEM", "GEMINI_MODELO_RESPOSTA", "GEMINI_MODEL_EMBEDDING")


def arquivo_da_rodada(rodada: int, conjunto: str = "gabarito") -> Path:
    prefixo = "" if conjunto == "gabarito" else f"{conjunto}-"
    return PASTA_RESULTADOS / f"{prefixo}rodada-{rodada}.json"


def carregar_rodada(rodada: int, conjunto: str = "gabarito") -> dict:
    caminho = arquivo_da_rodada(rodada, conjunto)
    if caminho.exists():
        return json.loads(caminho.read_text(encoding="utf-8"))
    return {
        "rodada": rodada,
        "conjunto": conjunto,
        "data": date.today().isoformat(),
        "resultados": [],
        "execucoes": [],
    }


def salvar_rodada(dados: dict) -> None:
    conjunto = dados.get("conjunto", "gabarito")
    ordem = {caso.id: i for i, caso in enumerate(carregar_casos(conjunto))}
    dados["resultados"].sort(key=lambda r: ordem.get(r["id"], len(ordem)))
    dados["metricas"] = metricas(dados["resultados"])
    dados["falhas"] = falhas(dados["resultados"])
    consumo = {"chamadas_reais": {}, "replays": 0, "failovers": 0}
    for execucao in dados["execucoes"]:
        for modelo, n in execucao["consumo"]["chamadas_reais"].items():
            consumo["chamadas_reais"][modelo] = consumo["chamadas_reais"].get(modelo, 0) + n
        consumo["replays"] += execucao["consumo"]["replays"]
        consumo["failovers"] += execucao["consumo"]["failovers"]
    dados["consumo"] = consumo
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    arquivo_da_rodada(dados["rodada"], conjunto).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preparar_ambiente() -> None:
    """A avaliação roda SÓ no Flash-Lite: roteamento, composição e juiz.

    Decisão da equipe (18/11/2026): o Flash não entra nas rodadas. A cota dele
    no free tier (20/dia, por projeto) não comporta uma rodada (37 casos, 40+
    composições) e fica reservada; com o Flash em 503, cada composição ainda
    perderia 70s de retry antes do failover. A gravação fica sob a chave do
    Flash-Lite — exatamente onde a replay (fallback da composição) a procura.
    """
    load_dotenv()
    for variavel in VARIAVEIS_DE_MODELO:
        os.environ.pop(variavel, None)
    os.environ[VARIAVEL_FALLBACK] = FALLBACK_DA_AVALIACAO
    os.environ["GEMINI_MODELO_RESPOSTA"] = FALLBACK_DA_AVALIACAO


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rodada", type=int, default=1)
    parser.add_argument("--conjunto", choices=("gabarito", "robustez"), default="gabarito")
    parser.add_argument("--casos", nargs="*", help="IDs dos casos (padrão: todos os que faltam ou falharam por infra)")
    parser.add_argument("--refazer", action="store_true", help="reavalia também os casos já avaliados (replay não gasta cota)")
    parser.add_argument("--relatorio", action="store_true", help="só imprime o relatório da rodada salva")
    args = parser.parse_args(argv)

    dados = carregar_rodada(args.rodada, args.conjunto)
    if args.relatorio:
        print(relatorio_markdown(dados))
        return 0

    preparar_ambiente()
    ligar_clientes_internos()
    REGISTRO.zerar()
    feitos = {r["id"]: r for r in dados["resultados"]}
    casos = [c for c in carregar_casos(args.conjunto) if not args.casos or c.id in args.casos]
    if not args.refazer and not args.casos:
        casos = [c for c in casos if feitos.get(c.id, {}).get("status") != STATUS_OK]

    print(f"Rodada {args.rodada}: {len(casos)} caso(s) a avaliar.", flush=True)
    sonda = LLMClient(modo="fixture")
    dados["modelos"] = {
        "roteamento_e_juiz": sonda.modelo(Papel.TRIAGEM),
        "composicao": sonda.modelo(Papel.RESPOSTA),
        "fallback_composicao": FALLBACK_DA_AVALIACAO,
    }
    dados["versoes_prompt"] = {"assistente": VERSAO_PROMPT_ASSISTENTE, "juiz": VERSAO_PROMPT_JUIZ}
    execucao = {"data": date.today().isoformat(), "casos": [], "consumo": REGISTRO.instantaneo()}
    dados["execucoes"].append(execucao)

    for i, caso in enumerate(casos, 1):
        print(f"[{i}/{len(casos)}] {caso.id} ({len(caso.turnos)} turno(s))...", flush=True)
        resultado = avaliar_caso(caso, ClienteHibrido())
        feitos[caso.id] = resultado
        dados["resultados"] = list(feitos.values())
        execucao["casos"].append(caso.id)
        execucao["consumo"] = REGISTRO.instantaneo()
        salvar_rodada(dados)
        if resultado["status"] == STATUS_OK:
            marca = "APROVADO" if resultado["aprovado"] else "reprovado"
            print(f"    {marca}: {resultado['criterios_ok']}/{resultado['criterios_total']} critérios; "
                  f"funções ok={resultado['funcoes']['ok']}; citações ok={resultado['citacoes']['ok']}", flush=True)
        else:
            print(f"    {resultado['status']}: {resultado.get('erro', '')[:160]}", flush=True)

    print("\n" + relatorio_markdown(dados))
    print(f"\nResultados em {arquivo_da_rodada(args.rodada, args.conjunto).relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
