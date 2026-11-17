"""Grava (uma vez) o diálogo real do gabarito CTX-001 com o Gemini e o deixa pronto
para o replay do teste `test_ctx001_dialogo_gravado_repete_a_gravacao_real`.

Uso:
    python -m scripts.gravar_ctx001                 # grava o que faltar, repete o resto

O modo é híbrido: cada chamada procura a fixture; se ela existe, é repetida
sem gastar cota; se falta, é gravada com `LLM_MODO=gravar`. Rodar de novo
depois de completar a gravação não gasta nada.

Requer GEMINI_API_KEY no .env (a cota do Flash no free tier é de 20
solicitações/dia — se estourar, o script fecha com honestidade e pede para
rodar de novo depois da janela de cota).
"""

import os
import time

from dotenv import load_dotenv

from sabor_da_terra.llm.cliente import FixtureAusenteError, LLMClient
from sabor_da_terra.assistente.orquestrador import Assistente
from sabor_da_terra.assistente.estado import EstadoSessao

DATA_REFERENCIA_DEMO = "2026-10-30"
DILOGO = (
    "Quem tem mel orgânico vigente?",
    "E a Josefa?",
    "Manda um resumo pra ela",
)


class ClienteHibrido(LLMClient):
    """Replay em fixture; quando a fixture falta, grava aquela chamada única."""

    def __init__(self) -> None:
        super().__init__(modo="fixture")
        self._gravador = LLMClient(
            modo="gravar", pasta_fixtures=self._pasta_fixtures, dormir=self._dormir
        )

    def gerar(self, papel, prompt, **config_geracao):
        try:
            return super().gerar(papel, prompt, **config_geracao)
        except FixtureAusenteError:
            print(f"  → gravando fixture faltante ({papel.value})...", flush=True)
            return self._gravador.gerar(papel, prompt, **config_geracao)


def main() -> int:
    load_dotenv()
    os.environ["DATA_REFERENCIA"] = DATA_REFERENCIA_DEMO
    try:
        cliente = ClienteHibrido()
    except RuntimeError as exc:  # chave ausente — a fumaça não roda
        print(f"FALHOU: {exc}")
        return 1
    sessao = Assistente(cliente_llm=cliente, estado=EstadoSessao(data_referencia=DATA_REFERENCIA_DEMO))
    for i, mensagem in enumerate(DILOGO, 1):
        print(f"== TURNO {i} ==", flush=True)
        inicio = time.perf_counter()
        try:
            print(sessao.responder(mensagem), flush=True)
        except Exception as exc:  # 429/503 do free tier são transientes
            print(f"FALHOU no turno {i}: {type(exc).__name__}: {exc}", flush=True)
            print("Dica: rode de novo depois da janela de cota (o que já foi gravado é repetido).")
            return 1
        print(f"(duracao {time.perf_counter() - inicio:.0f}s)", flush=True)
    print(f"== ESTADO == {sessao.estado.to_dict()}")
    print("Gravação completa: o teste test_ctx001_dialogo_gravado_repete_a_gravacao_real já roda em fixture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
