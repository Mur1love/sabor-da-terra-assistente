"""Resumo personalizado do produtor: vendas do mês, pagamentos, pedidos e documentos.

Os números vêm do extrato_produtor da etapa 4 (pandas sobre financeiro.csv);
nada é calculado pelo modelo. O texto sai de um modelo fixo, em frases curtas
e valores em R$, e pode depois passar pelo Gemini (redacao.py), que só reescreve.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sabor_da_terra.dados import extrato_produtor, obter_repositorio
from sabor_da_terra.produtores.demanda import alocacoes_do_produtor, fila_da_triagem
from sabor_da_terra.produtores.texto import data_br, dias, nome_do_mes, quantidade, reais
from sabor_da_terra.regras.produtor import alertas_do_produtor

FONTE_FINANCEIRO = "data/financeiro.csv"


def _soma(valores) -> float:
    return float(sum((Decimal(str(v)) for v in valores), Decimal(0)))


# Vendas agrupadas por produto e comprador, com as transações de cada grupo.
def _vendas_agrupadas(vendas: list[dict]) -> list[dict[str, Any]]:
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for venda in vendas:
        grupos[(venda["produto"], venda["comprador"], venda["unidade"])].append(venda)
    return [
        {
            "produto": produto,
            "comprador": comprador,
            "unidade": unidade,
            "quantidade": _soma(v["quantidade"] for v in itens),
            "valor": _soma(v["valor_total"] for v in itens),
            "transacoes": [v["id_transacao"] for v in itens],
        }
        for (produto, comprador, unidade), itens in grupos.items()
    ]


def _transacao(item: dict) -> dict[str, Any]:
    campos = [
        "id_transacao", "data", "comprador", "produto", "quantidade", "unidade", "valor_total",
        "forma_pagamento", "status_pagamento", "data_vencimento", "data_pagamento", "observacao",
    ]
    saida = {c: item.get(c) for c in campos}
    if "dias_em_atraso" in item:
        saida["dias_em_atraso"] = item["dias_em_atraso"]
    return saida


def montar_resumo(
    produtor_id: str,
    mes: str,
    data_referencia: Optional[str] = None,
    fila: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dados e texto do resumo. Com `fila` (saída de triar_pendentes), inclui os pedidos alocados."""
    extrato = extrato_produtor(produtor_id, mes, data_referencia)
    if not extrato.get("encontrado"):
        return extrato

    referencia = date.fromisoformat(extrato["data_referencia"])
    pid = extrato["produtor"]["produtor_id"]
    ano, numero_mes = (int(p) for p in extrato["mes"].split("-"))
    totais = dict(extrato["totais"])
    totais["saldo_a_receber"] = _soma([totais["a_receber"], totais["vencido"]])

    alertas = alertas_do_produtor(pid, referencia)
    dados = {
        "encontrado": True,
        "produtor": {k: extrato["produtor"][k] for k in ("produtor_id", "nome", "municipio")},
        "mes": extrato["mes"],
        "periodo": nome_do_mes(ano, numero_mes),
        "data_referencia": extrato["data_referencia"],
        "vendas": _vendas_agrupadas(extrato["vendas_no_mes"]),
        "vendas_no_mes": [_transacao(v) for v in extrato["vendas_no_mes"]],
        "recebidos_no_mes": [_transacao(v) for v in extrato["recebidos_no_mes"]],
        "vencidas": [_transacao(v) for v in extrato["vencidas"]],
        "a_receber": sorted((_transacao(v) for v in extrato["a_receber"]), key=lambda v: v["data_vencimento"]),
        "totais": totais,
        "pedidos_alocados": alocacoes_do_produtor(fila, pid) if fila is not None else None,
        "alertas": alertas,
        "aviso": extrato.get("aviso"),
    }
    fontes = [FONTE_FINANCEIRO, "data/produtores.csv"]
    if fila is not None:
        fontes.append("data/pedidos.json")
    fontes += sorted({f"data/{arquivo.strip()}" for a in alertas for arquivo in a["fonte"].split(";")})
    dados["fontes"] = list(dict.fromkeys(fontes))
    dados["texto"] = texto_do_resumo(dados)
    return dados


def texto_do_resumo(dados: dict[str, Any]) -> str:
    """Texto do resumo em linguagem simples: frases curtas, valores em R$, sem dado bancário."""
    p = dados["produtor"]
    periodo = dados["periodo"]
    t = dados["totais"]
    linhas = [
        f"Olá, {p['nome']} ({p['produtor_id']})!",
        f"Este é o seu resumo de {periodo}, com dados até {data_br(dados['data_referencia'])}.",
        "",
        f"VENDAS DE {periodo.upper()}",
    ]
    if dados["vendas"]:
        for grupo in dados["vendas"]:
            linhas.append(
                f"- {quantidade(grupo['quantidade'], grupo['unidade'])} de {grupo['produto']} para "
                f"{grupo['comprador']}: {reais(grupo['valor'])} ({', '.join(grupo['transacoes'])})."
            )
        linhas.append(f"Total vendido no mês: {reais(t['vendido_no_mes'])}.")
    else:
        linhas.append(f"- Nenhuma venda registrada em {periodo} ({reais(0)}).")

    linhas += ["", "PAGAMENTOS QUE VOCÊ RECEBEU NO MÊS"]
    if dados["recebidos_no_mes"]:
        for v in dados["recebidos_no_mes"]:
            linhas.append(
                f"- {v['id_transacao']}: {reais(v['valor_total'])} de {v['comprador']} "
                f"({v['produto']}), pago em {data_br(v['data_pagamento'])}."
            )
        linhas.append(f"Total recebido no mês: {reais(t['recebido_no_mes'])}.")
    else:
        linhas.append("- Nenhum pagamento recebido no mês.")

    linhas += ["", "PAGAMENTOS ATRASADOS"]
    if dados["vencidas"]:
        for v in dados["vencidas"]:
            nota = f" Anotação: \"{v['observacao']}\"." if v.get("observacao") else ""
            linhas.append(
                f"- {v['id_transacao']}: {reais(v['valor_total'])} de {v['comprador']} "
                f"({quantidade(v['quantidade'], v['unidade'])} de {v['produto']}). "
                f"Venceu em {data_br(v['data_vencimento'])}, com {dias(v['dias_em_atraso'])} de atraso.{nota}"
            )
        linhas.append(f"Total atrasado: {reais(t['vencido'])}. Dúvidas sobre esses valores: fale com a equipe da cooperativa.")
    else:
        linhas.append("- Nenhum pagamento atrasado.")

    linhas += ["", "A RECEBER (PRÓXIMOS VENCIMENTOS)"]
    if dados["a_receber"]:
        for v in dados["a_receber"]:
            linhas.append(
                f"- {v['id_transacao']}: {reais(v['valor_total'])} de {v['comprador']} "
                f"({v['produto']}), vence em {data_br(v['data_vencimento'])}."
            )
    else:
        linhas.append("- Nada a receber no prazo.")
    linhas.append(f"Saldo total a receber: {reais(t['saldo_a_receber'])}.")

    if dados["pedidos_alocados"] is not None:
        linhas += ["", "PEDIDOS SUGERIDOS PARA VOCÊ"]
        if dados["pedidos_alocados"]:
            for a in dados["pedidos_alocados"]:
                linhas.append(
                    f"- {a['pedido_id']}: {quantidade(a['quantidade'], a['unidade'])} de {a['produto']} para "
                    f"{a['comprador']}, entrega até {data_br(a['prazo_entrega'])}."
                )
            linhas.append("Nenhum desses pedidos está fechado. A cooperativa vai confirmar com você antes.")
        else:
            linhas.append("- Nenhum pedido sugerido para você agora.")

    alertas = dados["alertas"]
    if alertas:
        linhas += ["", "AVISOS SOBRE SEUS DOCUMENTOS"]
        linhas += [f"- {a['mensagem']}" for a in alertas]

    linhas += ["", f"Fontes: {'; '.join(dados['fontes'])}."]
    return "\n".join(linhas)


def resumo_produtor(produtor_id: str, mes: str, data_referencia: Optional[str] = None) -> dict:
    """Resumo personalizado de um produtor no mês: vendas por produto e comprador (kg e R$), pagamentos
    recebidos, atrasados e a receber, pedidos sugeridos para ele na fila de triagem e avisos dos documentos
    (certificação orgânica, SIE, fiscalização). mes em AAAA-MM (ou nome do mês); data_referencia em
    AAAA-MM-DD (vazio = hoje). Os valores vêm de financeiro.csv; o texto já vem pronto, sem CPF nem conta.
    """
    referencia = data_referencia or date.today().isoformat()
    try:
        fila = fila_da_triagem(date.fromisoformat(referencia).isoformat())
    except ValueError:
        return {"encontrado": False, "aviso": f"Data de referência inválida: '{data_referencia}'. Use AAAA-MM-DD."}
    return montar_resumo(produtor_id, mes, referencia, fila=fila)


def relatorio_pendencias_vencidas(data_referencia: Optional[str] = None) -> dict:
    """Relatório da cooperativa com todos os pagamentos pendentes já vencidos na data (AAAA-MM-DD, vazio = hoje):
    produtor, comprador, valor, vencimento e dias de atraso. Os títulos ainda no prazo vêm separados em a_vencer.
    """
    try:
        referencia = date.fromisoformat(data_referencia) if data_referencia else date.today()
    except ValueError:
        return {"encontrado": False, "aviso": f"Data de referência inválida: '{data_referencia}'. Use AAAA-MM-DD."}
    repo = obter_repositorio()
    vencidas, a_vencer = [], []
    for _, produtor in repo.produtores().iterrows():
        tx = repo.transacoes_do_produtor(produtor["produtor_id"])
        for _, linha in tx[tx["status_pagamento"] == "pendente"].iterrows():
            item = {
                "id_transacao": linha["id_transacao"],
                "produtor_id": produtor["produtor_id"],
                "produtor": produtor["nome"],
                "comprador": linha["comprador"],
                "produto": linha["produto"],
                "valor_total": float(linha["valor_total"]),
                "data_vencimento": linha["data_vencimento"].isoformat(),
                "observacao": linha["observacao"] or None,
            }
            if linha["data_vencimento"] < referencia:
                item["dias_em_atraso"] = (referencia - linha["data_vencimento"]).days
                vencidas.append(item)
            else:
                a_vencer.append(item)
    vencidas.sort(key=lambda v: (v["data_vencimento"], v["id_transacao"]))
    a_vencer.sort(key=lambda v: (v["data_vencimento"], v["id_transacao"]))
    total = _soma(v["valor_total"] for v in vencidas)

    linhas = [f"Pagamentos vencidos e não recebidos até {data_br(referencia)}:"]
    linhas += [
        f"- {v['id_transacao']}: {v['produtor_id']} ({v['produtor']}), {v['comprador']}, {reais(v['valor_total'])}, "
        f"venceu em {data_br(v['data_vencimento'])} ({dias(v['dias_em_atraso'])} de atraso)."
        + (f" Anotação: \"{v['observacao']}\"." if v["observacao"] else "")
        for v in vencidas
    ] or ["- Nenhum."]
    linhas.append(f"Total vencido: {reais(total)}.")
    if a_vencer:
        linhas.append("Ainda no prazo (não estão atrasados): " + ", ".join(
            f"{v['id_transacao']} (vence {data_br(v['data_vencimento'])})" for v in a_vencer
        ) + ".")
    linhas.append(f"Fonte: {FONTE_FINANCEIRO}.")

    return {
        "encontrado": True,
        "data_referencia": referencia.isoformat(),
        "vencidas": vencidas,
        "total_vencido": total,
        "a_vencer": a_vencer,
        "texto": "\n".join(linhas),
        "fonte": FONTE_FINANCEIRO,
    }
