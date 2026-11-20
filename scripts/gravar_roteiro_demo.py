"""Roteiro da demo em modo fixture — o plano B sem internet (etapa #17).

Grava (ou reproduz, em fixture) as respostas reais do LLM para a sequência da
demonstração ao vivo. As frases seguem casos validados no gabarito da
avaliação (#14): mel silvestre orgânico (DOC-001), "e o da Josefa?" (CTX-001),
fila de triagem (Desafio A), resumo da P001 (PROD-001), notificações da fila,
relatório de pendências vencidas (PROD-003) e a recusa honesta (ANTI-001).

- Gravar (chave real no `.env`, custo de centavos):
    `LLM_MODO=gravar DATA_REFERENCIA=2026-10-30 python -m scripts.gravar_roteiro_demo`
- Replay sem API (é como a demo roda sem internet, no `app.py`):
    `LLM_MODO=fixture DATA_REFERENCIA=2026-10-30 python -m scripts.gravar_roteiro_demo`

A ORDEM importa: o histórico da sessão entra no prompt, então o replay exige a
mesma sequência de mensagens em uma sessão nova (botão "Nova sessão" na
interface). Os atalhos da barra lateral não usam o LLM e funcionam em qualquer
modo; este roteiro é para o chat.
"""

from dotenv import load_dotenv

from sabor_da_terra.assistente.estado import EstadoSessao, data_referencia_padrao
from sabor_da_terra.assistente.orquestrador import Assistente
from sabor_da_terra.llm.cliente import LLMClient

load_dotenv()  # GEMINI_API_KEY, LLM_MODO e DATA_REFERENCIA do .env — como no app.py

ROTEIRO = [
    "Quais produtores possuem certificação orgânica vigente para fornecer mel silvestre?",
    "E o da Josefa?",
    "Traga a fila de triagem de pedidos pendentes",
    "Resuma as vendas e pendências da produtora P001 (Maria das Graças Silva Ferreira)",
    "Redija as notificações de novos pedidos para os produtores da fila",
    "Gere um relatório autônomo com todos os pagamentos vencidos e pendentes até 30/10/2026",
    "A cooperativa possui certificação internacional para exportação?",
]


def main() -> None:
    assistente = Assistente(
        cliente_llm=LLMClient(),
        estado=EstadoSessao(data_referencia=data_referencia_padrao()),
    )
    print(
        f"Modo do LLM: {assistente.cliente.modo} · "
        f"Relógio da sessão: {assistente.estado.data_referencia}\n"
    )
    for numero, mensagem in enumerate(ROTEIRO, 1):
        print("=" * 70)
        print(f"Turno {numero}: {mensagem}")
        print("-" * 70)
        resposta = assistente.responder(mensagem)
        print(resposta)
        fontes = sorted(set(assistente.fontes_do_turno or []))
        if fontes:
            print(f"Fontes ({len(fontes)}): " + " · ".join(fontes))
    print("=" * 70)
    print(f"Roteiro concluído: {len(ROTEIRO)} turnos.")


if __name__ == "__main__":
    main()
