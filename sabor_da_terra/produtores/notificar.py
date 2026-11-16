"""Notificação de novos pedidos para o produtor, individual ou em lote a partir da fila (#10).

Cada pedido sugerido vem com comprador, produto, quantidade, prazo, local e
horário de entrega e as exigências do contrato. Nada é dado como fechado: a
fila só sugere, e o texto pede que o produtor confirme quanto pode entregar.
O envio (WhatsApp, SMS, e-mail) fica fora do protótipo; no desenho, Pub/Sub e
Cloud Scheduler disparam esta função.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sabor_da_terra.dados import obter_repositorio
from sabor_da_terra.produtores.demanda import (
    TIPOS_DEMANDA,
    alocacoes_do_produtor,
    fila_da_triagem,
    produtores_com_alocacao,
)
from sabor_da_terra.produtores.texto import data_br, quantidade, reais
from sabor_da_terra.regras.fatos import Fatos, obter_fatos

_DIAS_NO_PLURAL = ["segundas", "terças", "quartas", "quintas", "sextas", "sábados", "domingos"]


def condicoes_de_entrega(comprador: str | None, produto: str, fatos: Fatos) -> dict[str, Any]:
    """Local/horário, pagamento e exigências do contrato do comprador.

    "exigencias" vale para o pedido todo; "exigencias_item" (preço do contrato,
    orgânico, SIE) é só do produto.
    """
    contrato = fatos.contrato_do_comprador(comprador)
    if contrato is None:
        return {
            "contrato": None,
            "entrega": ["sem contrato registrado com o comprador; local e horário a combinar com a cooperativa"],
            "pagamento": [],
            "exigencias": [],
            "exigencias_item": [],
            "fonte": None,
        }

    entrega = [c for c in contrato.condicoes if "entrega" in c and "pagamento" not in c and "multa" not in c]
    if contrato.dias_entrega:
        entrega.append("entregas só às " + " e ".join(_DIAS_NO_PLURAL[d] for d in contrato.dias_entrega))
    pagamento = [c for c in contrato.condicoes if "pagamento" in c]
    exigencias = [c for c in contrato.condicoes if c not in entrega and c not in pagamento]
    if contrato.exige_dap_caf:
        exigencias.append("DAP ou CAF vigente")
    exigencias_item = []
    item = contrato.item(produto)
    if item is not None:
        exigencias_item.append(f"preço do contrato {reais(item.preco)} por {item.unidade}")
        if item.exige_organico:
            exigencias_item.append("só orgânico, com certificação válida")
    if contrato.exige_sie_origem_animal and fatos.eh_origem_animal(produto):
        exigencias_item.append("só com SIE, SIM ou SISBI (origem animal)")
    return {
        "contrato": contrato.numero,
        "entrega": entrega or ["local e horário a combinar com a cooperativa"],
        "pagamento": [c.removeprefix("pagamento ") for c in pagamento],
        "exigencias": exigencias,
        "exigencias_item": exigencias_item,
        "fonte": contrato.fonte,
    }


def notificacao_produtor(produtor_id: str, fila: dict[str, Any], fatos: Fatos | None = None) -> dict[str, Any]:
    """Notificação de um produtor com os pedidos que a fila sugeriu para ele."""
    fatos = fatos if fatos is not None else obter_fatos()
    produtor = obter_repositorio().produtor(produtor_id)
    if produtor is None:
        return {"encontrado": False, "aviso": f"Produtor '{produtor_id}' não existe no cadastro."}

    alocacoes = alocacoes_do_produtor(fila, produtor_id)
    for alocacao in alocacoes:
        alocacao["condicoes"] = condicoes_de_entrega(alocacao["comprador"], alocacao["produto"], fatos)
    fontes = ["data/pedidos.json"] + [f"data/{a['condicoes']['fonte']}" for a in alocacoes if a["condicoes"]["fonte"]]

    dados = {
        "encontrado": True,
        "produtor": {"produtor_id": produtor_id, "nome": produtor["nome"]},
        "data_referencia": fila["data_referencia"],
        "pedidos_sugeridos": alocacoes,
        "fontes": list(dict.fromkeys(fontes)),
        "confirmado": False,
        "enviada": False,
    }
    dados["texto"] = texto_da_notificacao(dados)
    return dados


def _linha_prazo(prazo: str | None, situacao: str) -> str:
    if situacao == "vencido":
        return f"Prazo: {data_br(prazo)}. Esse prazo já passou: a cooperativa vai confirmar com o comprador se o pedido ainda vale."
    if situacao == "nao_informado":
        return "Prazo: não informado pelo comprador."
    return f"Prazo: {data_br(prazo)}."


def texto_da_notificacao(dados: dict[str, Any]) -> str:
    """Texto da notificação em frases curtas, um bloco por pedido, sem dado bancário."""
    p = dados["produtor"]
    linhas = [f"Olá, {p['nome']} ({p['produtor_id']})!"]
    if not dados["pedidos_sugeridos"]:
        linhas.append(f"Não há pedido novo para você até {data_br(dados['data_referencia'])}.")
        return "\n".join(linhas)

    linhas += [
        f"Chegaram pedidos com seus produtos (até {data_br(dados['data_referencia'])}).",
        "Nada está fechado ainda. Responda dizendo quanto você consegue entregar.",
    ]
    por_pedido: dict[str, list[dict]] = {}
    for a in dados["pedidos_sugeridos"]:
        por_pedido.setdefault(a["pedido_id"], []).append(a)
    for n, (pedido_id, itens) in enumerate(por_pedido.items(), start=1):
        primeiro = itens[0]
        c = primeiro["condicoes"]
        linhas += ["", f"{n}) {pedido_id} - {primeiro['comprador']} ({TIPOS_DEMANDA.get(primeiro['tipo'], primeiro['tipo'])})"]
        for a in itens:
            organico = " orgânico" if a["organico"] else ""
            extras = a["condicoes"]["exigencias_item"]
            linha = f"   - {quantidade(a['quantidade'], a['unidade'])} de {a['produto']}{organico} para você"
            linha += f" ({'; '.join(extras)})." if extras else "."
            if a["confirmar_producao"]:
                linha += " Passa do mínimo da sua produção da semana: confirme se consegue."
            linhas.append(linha)
        linhas.append(f"   {_linha_prazo(primeiro['prazo_entrega'], primeiro['situacao_prazo'])}")
        linhas.append(f"   Entrega: {'; '.join(c['entrega'])}.")
        if c["pagamento"]:
            linhas.append(f"   Pagamento: {'; '.join(c['pagamento'])}.")
        if c["exigencias"]:
            linhas.append(f"   Exigências do contrato {c['contrato']}: {'; '.join(c['exigencias'])}.")
        situacao = "reserva aguardando confirmação do pedido" if any(a["condicionada"] for a in itens) else "sugestão da cooperativa"
        linhas.append(f"   Situação: {situacao}. Não é venda fechada.")

    linhas += ["", f"Fontes: {'; '.join(dados['fontes'])}."]
    return "\n".join(linhas)


def notificacoes_da_fila(fila: dict[str, Any], produtor_id: str | None = None) -> dict[str, Any]:
    """Modo lote: uma notificação por produtor com alocação na fila (ou só a do produtor pedido)."""
    fatos = obter_fatos()
    produtores = [produtor_id] if produtor_id is not None else produtores_com_alocacao(fila)
    notificacoes = [notificacao_produtor(pid, fila, fatos=fatos) for pid in produtores]
    return {
        "encontrado": True,
        "data_referencia": fila["data_referencia"],
        "total": len(notificacoes),
        "produtores": produtores,
        "notificacoes": notificacoes,
        "enviadas": False,
        "aviso": "Textos gerados para revisão da equipe; nada foi enviado nem confirmado.",
    }


def notificar_produtores(data_referencia: Optional[str] = None, produtor_id: Optional[str] = None) -> dict:
    """Gera as notificações de novos pedidos para os produtores a partir da fila de triagem do dia
    (data_referencia em AAAA-MM-DD; vazio = hoje). Sem produtor_id, sai uma notificação por produtor com pedido
    sugerido na fila; com produtor_id (ex.: P002), só a dele. Cada notificação traz comprador, produto,
    quantidade, prazo, local e horário de entrega e exigências do contrato. Nada é enviado.
    """
    try:
        referencia = date.fromisoformat(data_referencia) if data_referencia else date.today()
    except ValueError:
        return {"encontrado": False, "aviso": f"Data de referência inválida: '{data_referencia}'. Use AAAA-MM-DD."}
    pid = None
    if produtor_id:
        pid = str(produtor_id).strip().upper()
        if obter_repositorio().produtor(pid) is None:
            return {"encontrado": False, "aviso": f"Produtor '{produtor_id}' não existe no cadastro."}
    return notificacoes_da_fila(fila_da_triagem(referencia.isoformat()), produtor_id=pid)
