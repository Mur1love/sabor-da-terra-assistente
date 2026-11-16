"""O que a fila da triagem (#10) e os pedidos abertos dizem para um produtor.

Só leitura: nada aqui confirma pedido ou reserva.
- alocações: quantidades que a fila sugeriu para o produtor (base das notificações);
- demanda aberta: itens de compra e cotação de um produto que ele fornece
  (base da resposta a uma oferta, como a do PED-015).
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

from sabor_da_terra.dados import obter_repositorio
from sabor_da_terra.regras.fatos import obter_fatos
from sabor_da_terra.triagem.fila import carregar_pedidos, recebido_ate, triar_pendentes
from sabor_da_terra.triagem.schema import TipoMensagem

FONTE_PEDIDOS = "data/pedidos.json"

TIPOS_DEMANDA = {
    TipoMensagem.COMPRA.value: "compra",
    TipoMensagem.COMPRA_URGENTE.value: "compra urgente",
    TipoMensagem.COTACAO.value: "cotação",
}
TIPOS_COMPRA = {TipoMensagem.COMPRA.value, TipoMensagem.COMPRA_URGENTE.value}


@lru_cache(maxsize=4)
def fila_da_triagem(data_referencia: str) -> dict[str, Any]:
    """Fila consolidada da #10 na data (guardada em cache; tratar como só leitura)."""
    return triar_pendentes(data_referencia)


def situacao_do_prazo(prazo: str | None, referencia: date) -> str:
    """vencido, no_prazo, nao_informado ou nao_resolvido (prazo em texto, ex.: jan/2027)."""
    if not prazo:
        return "nao_informado"
    try:
        dia = date.fromisoformat(prazo)
    except ValueError:
        return "nao_resolvido"
    return "vencido" if dia < referencia else "no_prazo"


def _sugestoes(fila: dict[str, Any]):
    for registro in fila["fila"]:
        for resultado in registro.get("alocacoes", []):
            for sugestao in resultado.get("alocacoes", []):
                yield registro, resultado, sugestao


# Avaliação de conformidade do item na fila, ou {} se o item não foi avaliado (ex.: cotação).
def _avaliacao(fila: dict[str, Any], pedido_id: str, produto: str) -> dict[str, Any]:
    for registro in fila["fila"]:
        if registro["id"] == pedido_id:
            for avaliacao in registro.get("avaliacoes", []):
                if avaliacao.get("encontrado") and (avaliacao.get("item") or {}).get("produto") == produto:
                    return avaliacao
    return {}


def alocacoes_do_produtor(fila: dict[str, Any], produtor_id: str) -> list[dict[str, Any]]:
    """Sugestões de alocação da fila para o produtor, na ordem da fila."""
    referencia = date.fromisoformat(fila["data_referencia"])
    return [
        {
            "pedido_id": registro["id"],
            "tipo": registro["tipo"],
            "comprador": registro["comprador"],
            "prazo_entrega": registro["prazo_entrega"],
            "situacao_prazo": situacao_do_prazo(registro["prazo_entrega"], referencia),
            "produto": resultado["produto"],
            "quantidade": sugestao["quantidade"],
            "unidade": sugestao["unidade"],
            "organico": bool(_avaliacao(fila, registro["id"], resultado["produto"]).get("item", {}).get("organico")),
            "condicionada": bool(sugestao.get("condicionada")),
            "confirmar_producao": bool(sugestao.get("confirmar_producao")),
            "confirmado": False,
        }
        for registro, resultado, sugestao in _sugestoes(fila)
        if sugestao["produtor_id"] == produtor_id
    ]


def produtores_com_alocacao(fila: dict[str, Any]) -> list[str]:
    """Produtores que receberam alguma sugestão de alocação na fila, em ordem de código."""
    return sorted({sugestao["produtor_id"] for _, _, sugestao in _sugestoes(fila)})


# Diz se as regras tiraram o produtor do item na fila (ex.: orgânico com certificação vencida).
def _excluido_na_fila(fila: dict[str, Any], pedido_id: str, produto: str, produtor_id: str) -> bool:
    avaliacao = _avaliacao(fila, pedido_id, produto)
    return bool(avaliacao) and all(e["produtor_id"] != produtor_id for e in avaliacao.get("elegiveis", []))


def demanda_aberta(produtor_id: str, produto: str, fila: dict[str, Any]) -> list[dict[str, Any]]:
    """Itens de compra e cotação do produto recebidos até a data da fila que o produtor pode atender.

    Fica de fora o item de que as regras o excluíram e, nos itens que a fila
    não avaliou (cotações), o orgânico sem certificação vigente.
    """
    referencia = date.fromisoformat(fila["data_referencia"])
    repo = obter_repositorio()
    cadastro = repo.produtor(produtor_id)
    if cadastro is None or not cadastro["ativo"]:
        return []  # inativo não recebe alocação nem oportunidade
    certificado = any(c.vigente_em(referencia) for c in obter_fatos().certificacoes_de(produtor_id, produto))
    alocado = {a["pedido_id"]: a["quantidade"] for a in alocacoes_do_produtor(fila, produtor_id) if a["produto"] == produto}

    itens = []
    for registro in carregar_pedidos():
        pedido = registro["pedido"]
        if pedido.tipo.value not in TIPOS_DEMANDA or not recebido_ate(registro, referencia):
            continue
        for item in pedido.itens:
            if repo.catalogo.resolver(item.produto).base != produto:
                continue
            if _excluido_na_fila(fila, registro["id"], produto, produtor_id) or (item.exige_organico and not certificado):
                continue
            itens.append(
                {
                    "pedido_id": registro["id"],
                    "tipo": pedido.tipo.value,
                    "compra": pedido.tipo.value in TIPOS_COMPRA,
                    "comprador": pedido.comprador,
                    "prazo_entrega": pedido.prazo_entrega,
                    "situacao_prazo": situacao_do_prazo(pedido.prazo_entrega, referencia),
                    "produto": produto,
                    "quantidade": item.quantidade,
                    "unidade": item.unidade,
                    "alocado_para_voce": alocado.get(registro["id"]),
                    "fonte": f"{FONTE_PEDIDOS} ({registro['id']})",
                }
            )
    return itens
