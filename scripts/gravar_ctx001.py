"""Grava (uma vez) o diálogo real do gabarito CTX-001 com o Gemini e o deixa pronto
para o replay do teste `test_ctx001_dialogo_gravado_repete_a_gravacao_real`.

Uso:
    python -m scripts.gravar_ctx001                 # grava o que faltar, repete o resto

O modo é híbrido: cada chamada procura a fixture; se ela existe, é repetida
sem gastar cota; se falta, é gravada com `LLM_MODO=gravar`. Rodar de novo
depois de completar a gravação não gasta nada. Os clientes que as ferramentas
criam por dentro (planner e busca do RAG, extração da triagem) também passam
pelo modo híbrido — sem isso a replay do teste não acharia as chamadas deles.

Turno que fecha sem composição real (429/503/504 do Flash viram a resposta
honesta `SEM_COMPOSICAO`) interrompe a gravação: seguir adiante gravaria os
turnos seguintes sobre um histórico que a replay nunca reproduz.

Requer GEMINI_API_KEY no .env (a cota do Flash no free tier é de 20
solicitações/dia — se estourar, o script fecha com honestidade e pede para
rodar de novo depois da janela de cota).
"""

import os
import time

from dotenv import load_dotenv

from sabor_da_terra.assistente.estado import EstadoSessao
from sabor_da_terra.assistente.orquestrador import SEM_COMPOSICAO, SEM_RESPOSTA, Assistente
from sabor_da_terra.avaliacao.clientes import ClienteHibrido, ligar_clientes_internos

DATA_REFERENCIA_DEMO = "2026-10-30"
# Turnos 1 e 2 com as palavras do gabarito (tests/gabarito/casos-contexto.yaml, CTX-001);
# turno 3 do critério de aceite da issue #12. "mel silvestre" explícito evita a pergunta
# de esclarecimento entre mel silvestre e mel de jandaíra vista na gravação de 17/11.
DIALOGO = (
    "Quais produtores têm certificação orgânica vigente para mel silvestre?",
    "E o da Josefa?",
    "Manda um resumo pra ela",
)


def main() -> int:
    load_dotenv()
    os.environ["DATA_REFERENCIA"] = DATA_REFERENCIA_DEMO
    try:
        cliente = ClienteHibrido()
    except RuntimeError as exc:  # chave ausente — a fumaça não roda
        print(f"FALHOU: {exc}")
        return 1
    ligar_clientes_internos()
    sessao = Assistente(cliente_llm=cliente, estado=EstadoSessao(data_referencia=DATA_REFERENCIA_DEMO))
    for i, mensagem in enumerate(DIALOGO, 1):
        print(f"== TURNO {i} ==", flush=True)
        inicio = time.perf_counter()
        try:
            resposta = sessao.responder(mensagem)
        except Exception as exc:  # 429/503 do free tier são transientes
            print(f"FALHOU no turno {i}: {type(exc).__name__}: {exc}", flush=True)
            print("Dica: rode de novo depois da janela de cota (o que já foi gravado é repetido).")
            return 1
        print(resposta, flush=True)
        if resposta in (SEM_COMPOSICAO, SEM_RESPOSTA):
            print(f"FALHOU no turno {i}: o turno fechou sem resposta do modelo (cota ou API fora).", flush=True)
            print("Dica: rode de novo depois da janela de cota (o que já foi gravado é repetido).")
            return 1
        print(f"(duracao {time.perf_counter() - inicio:.0f}s)", flush=True)
    print(f"== ESTADO == {sessao.estado.to_dict()}")
    print("Gravação completa: o teste test_ctx001_dialogo_gravado_repete_a_gravacao_real já roda em fixture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
