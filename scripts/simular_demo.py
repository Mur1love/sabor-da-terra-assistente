"""Teste de cota (#14): simula a demo completa da #18 e mede as chamadas por papel.

Uso:
    python -m scripts.simular_demo

Roda o roteiro da demonstração (issue #18) numa sessão só, com o cliente
híbrido: o que já foi gravado é repetido, o que falta é gravado. A medida é a
DEMANDA da conversa — toda chamada por papel, gravada ou repetida —, que é o
que a demo gastaria ao vivo. O resultado vai para `docs/avaliacao/cota-demo.json`
e entra no docs/05 (cabe na cota do docs/03 ou não, e o plano B).
"""

from __future__ import annotations

import json
import time
from datetime import date

from sabor_da_terra.assistente.estado import EstadoSessao
from sabor_da_terra.assistente.orquestrador import Assistente
from sabor_da_terra.avaliacao.clientes import REGISTRO, ClienteHibrido, ligar_clientes_internos
from sabor_da_terra.avaliacao.gabarito import DATA_REFERENCIA_PADRAO, RAIZ
from scripts.avaliar_gabarito import PASTA_RESULTADOS, preparar_ambiente

# Free tier confirmado no docs/03 (por projeto, reinicia à meia-noite do Pacífico).
LIMITES_DOCS03 = {
    "triagem": {"modelo": "Flash-Lite", "rpm": 15, "rpd": 500},
    "resposta": {"modelo": "Flash", "rpm": 5, "rpd": 20},
}

_PED_006 = """PEDIDO URGENTE

Necessitamos com máxima urgência para HOJE (29/10):
- Queijo coalho: 200kg
- Queijo manteiga: 50kg
- Mel silvestre orgânico: 40kg
- Goiaba: 300kg

Pagamento: boleto 30 dias conforme contrato.
Entrega: CD SuperBom, BR-423 km 12, Garanhuns.

Se não atenderem hoje perdemos a promoção de fim de semana.

Roberto Cavalcanti
Gerente de Compras"""

# Roteiro da #18: triagem com problemas, documental com citação, continuidade
# de contexto, um "não sei" e um resumo de produtor (PED-012).
ROTEIRO = (
    ("triagem com problemas (PED-006)", f"Chegou este pedido do SuperBom, faz a triagem:\n\n{_PED_006}"),
    ("consulta documental com citação", "Quais produtores têm certificação orgânica vigente para mel silvestre?"),
    ("continuidade de contexto", "E o da Josefa?"),
    ("caso 'não sei' (lote inexistente)", "Onde está o lote LOT-2024-089?"),
    (
        "resumo de produtor (PED-012)",
        "A produtora do telefone (87) 99812-3456 quer saber quanto vendeu esse mês e se o pagamento "
        "do Mercado Bom Preço de setembro já caiu. Monta o resumo dela.",
    ),
)


def main() -> int:
    preparar_ambiente()
    ligar_clientes_internos()
    REGISTRO.zerar()
    assistente = Assistente(cliente_llm=ClienteHibrido(), estado=EstadoSessao(data_referencia=DATA_REFERENCIA_PADRAO))

    turnos = []
    for etapa, mensagem in ROTEIRO:
        antes = dict(REGISTRO.demanda_por_papel)
        inicio = time.perf_counter()
        resposta = assistente.responder(mensagem)
        demanda = {p: n - antes.get(p, 0) for p, n in REGISTRO.demanda_por_papel.items() if n - antes.get(p, 0)}
        turnos.append(
            {
                "etapa": etapa,
                "mensagem": mensagem,
                "resposta": resposta,
                "funcoes": list(assistente.funcoes_do_turno),
                "fontes": list(assistente.fontes_do_turno),
                "demanda_por_papel": demanda,
                "duracao_s": round(time.perf_counter() - inicio, 1),
            }
        )
        print(f"== {etapa}: {demanda} em {turnos[-1]['duracao_s']}s", flush=True)
        print(resposta[:400], flush=True)

    total = dict(REGISTRO.demanda_por_papel)
    cabe = {
        papel: {
            **limite,
            "demanda_da_demo": total.get(papel, 0),
            "pico_por_turno": max((t["demanda_por_papel"].get(papel, 0) for t in turnos), default=0),
            "cabe_no_rpd": total.get(papel, 0) <= limite["rpd"],
            "demos_por_dia": limite["rpd"] // total[papel] if total.get(papel) else None,
        }
        for papel, limite in LIMITES_DOCS03.items()
    }
    resultado = {
        "data": date.today().isoformat(),
        "data_referencia": DATA_REFERENCIA_PADRAO,
        "turnos": turnos,
        "demanda_por_papel": total,
        "consumo_real_da_simulacao": REGISTRO.instantaneo(),
        "cota_docs03": cabe,
    }
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_RESULTADOS / "cota-demo.json"
    caminho.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nDemanda da demo por papel: {total}")
    for papel, c in cabe.items():
        print(f"- {papel} ({c['modelo']}): {c['demanda_da_demo']} de {c['rpd']}/dia -> "
              f"{'cabe' if c['cabe_no_rpd'] else 'NÃO cabe'}; {c['demos_por_dia']} demos/dia; pico {c['pico_por_turno']}/turno (RPM {c['rpm']})")
    print(f"Resultado em {caminho.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
