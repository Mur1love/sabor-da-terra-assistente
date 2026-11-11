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
        print(f"[1/3] triagem   → {cliente.modelo(Papel.TRIAGEM)}", flush=True)
        triagem = cliente.gerar(Papel.TRIAGEM, "Responda apenas: ok")

        print(f"[2/3] resposta  → {cliente.modelo(Papel.RESPOSTA)}", flush=True)
        resposta = cliente.gerar(Papel.RESPOSTA, "Responda apenas: ok")

        print(f"[3/3] embedding → {cliente.modelo(Papel.EMBEDDING)}", flush=True)
        vetor = cliente.embedar("teste de embedding")
    except Exception as exc:
        # 429 esgotado, 503 de alta demanda, falha de rede: mensagem curta em vez de traceback.
        print(f"FALHOU em {type(exc).__name__}: {exc}")
        print("Dica: rode de novo em ~1 min (503/429 são transientes e não consomem cota).")
        return 1
    print(f"Flash-Lite: {triagem!r}")
    print(f"Flash: {resposta!r}")
    print(f"Embedding: {len(vetor)} dimensões")
    print(f"Chamadas por modelo: {cliente.chamadas_por_modelo()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
