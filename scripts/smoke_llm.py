"""Teste de fumaça real: Flash-Lite (triagem), Flash (resposta) e embedding.

Uso (requer GEMINI_API_KEY no .env):
    python -m scripts.smoke_llm                  # só valida (não grava nada)
    LLM_MODO=gravar python -m scripts.smoke_llm  # valida e grava/regrava fixtures

Qualquer erro da API (chave inválida, cota, modelo sobrecarregado) sai como
"FALHOU" sem traceback — a saída é feita para ser colada na issue.
"""

import os

from dotenv import load_dotenv

from sabor_da_terra.llm.cliente import LLMClient, Papel


def rodar(cliente: LLMClient) -> int:
    """Faz as 3 chamadas (Flash-Lite, Flash, embedding) com progresso por chamada."""
    print(f"[1/3] triagem   → {cliente.modelo(Papel.TRIAGEM)}", flush=True)
    triagem = cliente.gerar(Papel.TRIAGEM, "Responda apenas: ok")
    print(f"Flash-Lite: {triagem.text!r}")

    print(f"[2/3] resposta  → {cliente.modelo(Papel.RESPOSTA)}", flush=True)
    resposta = cliente.gerar(Papel.RESPOSTA, "Responda apenas: ok")
    print(f"Flash: {resposta.text!r}")

    print(f"[3/3] embedding → {cliente.modelo(Papel.EMBEDDING)}", flush=True)
    vetor = cliente.embedar("teste de embedding")
    print(f"Embedding: {len(vetor)} dimensões")
    print(f"Chamadas por modelo: {cliente.chamadas_por_modelo()}")
    return 0


def main() -> int:
    load_dotenv()
    # Padronizado 'real' (só valida); LLM_MODO=gravar no ambiente grava fixtures.
    os.environ.setdefault("LLM_MODO", "real")
    try:
        return rodar(LLMClient())
    except Exception as exc:  # erros da API do Google não são RuntimeError
        print(f"FALHOU: {type(exc).__name__}: {exc}")
        print("Dica: rode de novo em ~1 min (503/429 são transientes e não consomem cota).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
