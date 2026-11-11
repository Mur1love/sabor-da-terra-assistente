"""Teste de fumaça real: Flash-Lite (triagem), Flash (resposta) e embedding.

Uso (requer GEMINI_API_KEY no .env):
    python -m scripts.smoke_llm

Cada chamada grava uma fixture em tests/fixtures/llm/ para os testes offline.
"""

import os

from dotenv import load_dotenv

from sabor_da_terra.llm.cliente import LLMClient, Papel


def main() -> int:
    load_dotenv()
    os.environ["LLM_MODO"] = "real"
    cliente = LLMClient()
    try:
        triagem = cliente.gerar(Papel.TRIAGEM, "Responda apenas: ok")
        resposta = cliente.gerar(Papel.RESPOSTA, "Responda apenas: ok")
        vetor = cliente.embedar("teste de embedding")
    except RuntimeError as exc:
        print(f"FALHOU: {exc}")
        return 1
    print(f"Flash-Lite: {triagem!r}")
    print(f"Flash: {resposta!r}")
    print(f"Embedding: {len(vetor)} dimensões")
    print(f"Chamadas por modelo: {cliente.chamadas_por_modelo()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
