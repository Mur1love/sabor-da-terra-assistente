"""Resposta às mensagens que os próprios produtores mandam (PED-2026-012, PED-2026-015).

A mensagem já vem triada (#9) como mensagem_produtor. O código reconhece o que
foi perguntado (vendas do mês, se um pagamento entrou, saldo, oferta de
produto, cadastro de produtor novo) e responde com os números do financeiro e a
demanda aberta. Nada é alocado. Dado bancário ou pessoal que o produtor
escreveu na mensagem não é repetido.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sabor_da_terra.dados import extrato_produtor, obter_repositorio
from sabor_da_terra.dados.normalizacao import NOMES_MESES, chave
from sabor_da_terra.produtores.demanda import FONTE_PEDIDOS, TIPOS_DEMANDA, demanda_aberta, fila_da_triagem
from sabor_da_terra.produtores.resumo import FONTE_FINANCEIRO
from sabor_da_terra.produtores.texto import data_br, nome_do_mes, quantidade, reais
from sabor_da_terra.triagem.fila import carregar_pedidos
from sabor_da_terra.triagem.schema import TipoMensagem

_PRODUTOR = re.compile(r"\bP\d{3}\b")
_MESES = {chave(nome): numero for numero, nome in enumerate(NOMES_MESES, start=1)}

FORA_DO_ESCOPO_CADASTRO = (
    "Cadastrar produtor novo não é algo que este assistente faz. Peça para a pessoa procurar a equipe "
    "da cooperativa. Os dados pessoais que você mandou não foram registrados nem repetidos aqui."
)


def _soma(valores) -> float:
    return float(sum((Decimal(str(v)) for v in valores), Decimal(0)))


# Meses citados, na ordem em que aparecem no texto.
def _meses_citados(texto: str) -> list[int]:
    achados = [(m.start(), numero) for nome, numero in _MESES.items() if (m := re.search(rf"\b{nome}\b", texto))]
    return [numero for _, numero in sorted(achados)]


# Ano do mês citado: o mais recente até a data de referência.
def _periodo(numero_mes: int, referencia: date) -> tuple[int, int]:
    return (referencia.year if numero_mes <= referencia.month else referencia.year - 1), numero_mes


def _intencoes(texto: str) -> dict[str, bool]:
    return {
        "vendas": bool(re.search(r"\bvend(i|eu|as|a)\b", texto)),
        "pagamento": bool(re.search(r"\b(pagamento|pagou|caiu)\b", texto)),
        "saldo": bool(re.search(r"\b(saldo|receber)\b", texto)),
        "cadastro_produtor": bool(re.search(r"\bcadastr", texto)),
        "dados_sensiveis": bool(re.search(r"\b(conta|agencia|cpf|pix)\b", texto)),
    }


def _secao_vendas(pid: str, ano: int, mes: int, referencia: date) -> list[str]:
    extrato = extrato_produtor(pid, f"{ano:04d}-{mes:02d}", referencia.isoformat())
    periodo = nome_do_mes(ano, mes)
    if not extrato["vendas_no_mes"]:
        return [f"Vendas de {periodo}: não há nenhuma venda registrada para você em {periodo} ({reais(0)})."]
    return [f"Vendas de {periodo}: {reais(extrato['totais']['vendido_no_mes'])} no total."] + [
        f"- {v['id_transacao']}: {quantidade(v['quantidade'], v['unidade'])} de {v['produto']} para "
        f"{v['comprador']}, {reais(v['valor_total'])}."
        for v in extrato["vendas_no_mes"]
    ]


def _secao_pagamento(pid: str, comprador: str, periodo: tuple[int, int] | None) -> tuple[list[str], dict]:
    tx = obter_repositorio().transacoes_do_produtor(pid)
    tx = tx[tx["comprador"] == comprador]
    if periodo is not None:
        tx = tx[tx["data"].map(lambda d: (d.year, d.month) == periodo).astype(bool)]
    quando = f" (vendas de {nome_do_mes(*periodo)})" if periodo else ""
    if tx.empty:
        return [f"Pagamento de {comprador}{quando}: não há venda sua para esse comprador nesse período."], {
            "comprador": comprador, "transacoes": [], "situacao": "sem_venda",
        }

    pagas, pendentes = tx[tx["status_pagamento"] == "pago"], tx[tx["status_pagamento"] != "pago"]
    if pendentes.empty:
        situacao = "pago"
        datas = sorted(set(pagas["data_pagamento"]))
        abertura = f"já entrou. Total de {reais(_soma(pagas['valor_total']))}"
        abertura += f", pago em {data_br(datas[0])}." if len(datas) == 1 else "."
    elif pagas.empty:
        situacao = "pendente"
        abertura = f"ainda não entrou. Total de {reais(_soma(pendentes['valor_total']))}."
    else:
        situacao = "parcial"
        abertura = f"entrou {reais(_soma(pagas['valor_total']))} e faltam {reais(_soma(pendentes['valor_total']))}."

    linhas = [f"Pagamento de {comprador}{quando}: {abertura}"]
    for _, v in tx.sort_values("id_transacao").iterrows():
        detalhe = (
            f"pago em {data_br(v['data_pagamento'])} (vencia em {data_br(v['data_vencimento'])})"
            if v["status_pagamento"] == "pago"
            else f"pendente, vence em {data_br(v['data_vencimento'])}"
        )
        linhas.append(
            f"- {v['id_transacao']}: {quantidade(float(v['quantidade']), v['unidade'])} de {v['produto']}, "
            f"{reais(v['valor_total'])}, {detalhe}."
        )
    return linhas, {"comprador": comprador, "transacoes": tx["id_transacao"].tolist(), "situacao": situacao}


def _secao_saldo(pid: str, referencia: date) -> tuple[list[str], float]:
    extrato = extrato_produtor(pid, f"{referencia.year:04d}-{referencia.month:02d}", referencia.isoformat())
    saldo = _soma([extrato["totais"]["a_receber"], extrato["totais"]["vencido"]])
    if not (extrato["vencidas"] or extrato["a_receber"]):
        return [f"Saldo a receber: {reais(saldo)}. Não há pagamento pendente em seu nome."], saldo
    linhas = [f"Saldo a receber: {reais(saldo)}."]
    for v in extrato["vencidas"]:
        nota = f" Anotação: \"{v['observacao']}\"." if v.get("observacao") else ""
        linhas.append(
            f"- {v['id_transacao']}: {reais(v['valor_total'])} de {v['comprador']}, venceu em "
            f"{data_br(v['data_vencimento'])} (atrasado).{nota}"
        )
    for v in extrato["a_receber"]:
        linhas.append(f"- {v['id_transacao']}: {reais(v['valor_total'])} de {v['comprador']}, vence em {data_br(v['data_vencimento'])}.")
    return linhas, saldo


def _secao_oferta(pid: str, itens: list, fila: dict) -> tuple[list[str], list[dict]]:
    repo = obter_repositorio()
    produtos_dele = set(repo.produtos_do_produtor(pid))
    ofertados = [f"{quantidade(i.quantidade, i.unidade)} de {i.produto}" if i.quantidade else i.produto for i in itens]
    linhas = [f"Sua oferta: {' e '.join(ofertados)}."]
    dados = []
    for item in itens:
        resolucao = repo.catalogo.resolver(item.produto)
        opcoes = [resolucao.base] if resolucao.encontrado else resolucao.candidatos
        candidatos = [c for c in opcoes if c in produtos_dele]
        linhas.append("")
        if not candidatos:
            linhas.append(f"{item.produto}: esse produto não está no seu cadastro. Fale com a equipe da cooperativa.")
            continue
        if not resolucao.encontrado:
            linhas.append(
                f"\"{item.produto}\": confirme qual é ({' ou '.join(resolucao.candidatos)}). "
                f"No seu cadastro consta {' e '.join(candidatos)}; os pedidos abaixo valem se for esse."
            )
        for produto in candidatos:
            demanda = demanda_aberta(pid, produto, fila)
            dados.append({"produto": produto, "demanda": demanda})
            if not demanda:
                linhas.append(f"{produto[:1].upper() + produto[1:]}: não há pedido em aberto agora.")
                continue
            linhas.append(f"{produto[:1].upper() + produto[1:]}: pedidos em aberto (nada está fechado):")
            for d in demanda:
                qtd = quantidade(d["quantidade"], d["unidade"]) if d["quantidade"] else "quantidade não informada"
                linha = f"- {d['pedido_id']}: {d['comprador']} pediu {qtd} ({TIPOS_DEMANDA[d['tipo']]})."
                if d["situacao_prazo"] == "vencido":
                    linha += f" O prazo era {data_br(d['prazo_entrega'])} e já passou: a cooperativa vai confirmar se o pedido ainda vale."
                elif d["prazo_entrega"]:
                    linha += f" Prazo: {data_br(d['prazo_entrega'])}."
                if not d["compra"]:
                    linha += " Cotação ainda não é compra."
                if d["alocado_para_voce"]:
                    linha += f" A triagem sugeriu {quantidade(d['alocado_para_voce'], d['unidade'])} seus, aguardando confirmação."
                linhas.append(linha)
    return linhas, dados


def responder_mensagem_produtor(pedido_id: str, data_referencia: Optional[str] = None) -> dict:
    """Responde uma mensagem enviada por um produtor (ex.: PED-2026-012, PED-2026-015) com os valores exatos
    do financeiro: vendas do mês, se um pagamento entrou (citando a transação), saldo a receber e, quando ele
    oferece produto, os pedidos em aberto daquele produto. Cadastro de produtor novo é recusado.
    data_referencia em AAAA-MM-DD; vazio = dia em que a mensagem chegou.
    """
    registro = next((r for r in carregar_pedidos() if r["id"] == pedido_id.strip().upper()), None)
    if registro is None:
        return {"encontrado": False, "aviso": f"Mensagem '{pedido_id}' não encontrada nos pedidos."}
    pedido = registro["pedido"]
    if pedido.tipo != TipoMensagem.MENSAGEM_PRODUTOR:
        return {"encontrado": False, "aviso": f"{registro['id']} não é mensagem de produtor ({pedido.tipo.value})."}
    achado = _PRODUTOR.search((pedido.comprador or "").upper())
    produtor = obter_repositorio().produtor(achado.group(0)) if achado else None
    if produtor is None:
        return {"encontrado": False, "aviso": "A mensagem não identifica um produtor do cadastro pelo código (Pxxx)."}
    pid = achado.group(0)

    recebida = datetime.fromisoformat(registro["data_recebimento"]).date() if registro.get("data_recebimento") else None
    try:
        referencia = date.fromisoformat(data_referencia) if data_referencia else (recebida or date.today())
    except ValueError:
        return {"encontrado": False, "aviso": f"Data de referência inválida: '{data_referencia}'. Use AAAA-MM-DD."}

    texto = chave(registro["mensagem_original"])
    intencoes = _intencoes(texto)
    intencoes["oferta"] = bool(pedido.itens)
    meses = _meses_citados(texto)

    linhas = [
        f"Olá, {produtor['nome']} ({pid})!",
        f"Resposta à sua mensagem de {data_br(recebida or referencia)} ({registro['id']}).",
    ]
    dados: dict[str, Any] = {}
    fontes = [FONTE_FINANCEIRO]

    if intencoes["vendas"]:
        # "esse mês" é o mês da mensagem; sem isso, vale o último mês citado.
        mes = (referencia.year, referencia.month)
        if not re.search(r"\b(esse|este) mes\b", texto) and meses:
            mes = _periodo(meses[-1], referencia)
        linhas += ["", *_secao_vendas(pid, *mes, referencia)]

    if intencoes["pagamento"]:
        compradores = obter_repositorio().transacoes_do_produtor(pid)["comprador"].unique()
        citados = sorted(c for c in compradores if re.search(rf"\b{re.escape(chave(c))}\b", texto))
        periodo = _periodo(meses[0], referencia) if meses else None
        dados["pagamentos"] = []
        for comprador in citados:
            secao, info = _secao_pagamento(pid, comprador, periodo)
            dados["pagamentos"].append(info)
            linhas += ["", *secao]
        if not citados:
            linhas += ["", "Não achei na mensagem de qual comprador é o pagamento. Diga o nome do comprador."]

    if intencoes["saldo"]:
        secao, dados["saldo"] = _secao_saldo(pid, referencia)
        linhas += ["", *secao]

    if intencoes["oferta"]:
        secao, dados["oferta"] = _secao_oferta(pid, pedido.itens, fila_da_triagem(referencia.isoformat()))
        linhas += ["", *secao]
        if pedido.prazo_entrega:
            linhas += ["", f"Você pediu resposta até {data_br(pedido.prazo_entrega)}."]
        linhas += ["Nada foi alocado nem confirmado. A equipe da cooperativa fala com você antes."]
        fontes.append(FONTE_PEDIDOS)

    fora = ["cadastro_produtor"] if intencoes["cadastro_produtor"] else []
    if fora:
        linhas += ["", FORA_DO_ESCOPO_CADASTRO]
    if not any(intencoes[k] for k in ("vendas", "pagamento", "saldo", "oferta")):
        linhas += ["", "Não entendi o pedido. A equipe da cooperativa vai responder você."]
    if intencoes["dados_sensiveis"]:
        linhas += ["", "Por segurança, não repetimos dados bancários nem documentos pessoais nesta mensagem."]
    linhas += ["", f"Fontes: {'; '.join(fontes)}."]

    return {
        "encontrado": True,
        "pedido_id": registro["id"],
        "produtor": {"produtor_id": pid, "nome": produtor["nome"]},
        "data_referencia": referencia.isoformat(),
        "intencoes": intencoes,
        "fora_do_escopo": fora,
        "dados": dados,
        "fontes": fontes,
        "texto": "\n".join(linhas),
        "confirmado": False,
    }
