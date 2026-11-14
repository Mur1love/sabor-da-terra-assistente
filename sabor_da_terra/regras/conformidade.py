"""Ferramenta verificar_conformidade: diz se um item de pedido pode ser atendido, por quem e a que preço.

A decisão é toda em código (docs/04 §5, princípio 3): o Gemini só chama a
função e narra o resultado. A função avaliar recebe fatos e repositório como
parâmetros, para os testes trocarem um fato (por exemplo, registrar a
renovação da P008) sem mexer no YAML.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError

from sabor_da_terra.dados import DadosRepository, obter_repositorio, preco
from sabor_da_terra.dados import normalizacao as n
from sabor_da_terra.regras.alertas import BLOQUEANTES, Alerta, GRAVE, ordenar
from sabor_da_terra.regras.fatos import Fatos, obter_fatos
from sabor_da_terra.regras.validadores import (
    CADASTRO,
    Avaliacao,
    Contexto,
    regra_capacidade,
    regra_certificacao_organica,
    regra_contrato,
    regra_exclusividade,
    regra_nao_conformidade,
    regra_produtor_inativo,
    regra_registro_sanitario,
    regra_safra,
    regra_unidade,
)

# Jeitos de escrever as unidades da tabela (chave sem acento → unidade da tabela).
_UNIDADES = {
    "kg": "kg", "quilo": "kg", "quilos": "kg", "kilo": "kg", "kilos": "kg", "quilograma": "kg", "quilogramas": "kg",
    "un": "unidade", "und": "unidade", "unid": "unidade", "unidade": "unidade", "unidades": "unidade",
    "maco": "maço", "macos": "maço",
    "dz": "dúzia", "duzia": "dúzia", "duzias": "dúzia",
    "l": "litro", "litro": "litro", "litros": "litro",
}


class ItemPedido(BaseModel):
    """Um item de pedido."""

    produto: str = Field(description="Nome do produto como veio no pedido (ex.: 'mel silvestre', 'queijo coalho').")
    quantidade: float = Field(description="Quantidade na unidade de venda do produto (kg, unidade, maço, dúzia ou litro).")
    unidade: Optional[str] = Field(default=None, description="Unidade em que a quantidade veio no pedido, se informada.")
    organico: bool = Field(default=False, description="True quando o comprador pede produto orgânico.")


# Ferramenta: diz se o item pode ser vendido, por quais produtores e a que preço, com alertas e fontes.
def verificar_conformidade(
    item: ItemPedido, data_entrega: str, comprador: str, data_referencia: Optional[str] = None
) -> dict:
    """Verifica um item de pedido contra as regras da cooperativa: certificação orgânica na data, SIE e fiscalização,
    safra, capacidade, produtor inativo ou exclusivo e o contrato do comprador (preço, dia de entrega, exigências).
    data_entrega e data_referencia em AAAA-MM-DD; data_referencia é o dia do pedido (vazio = hoje).
    Devolve os produtores elegíveis e os excluídos com o motivo, o preço e alertas com a fonte de cada um.
    """
    try:
        item = item if isinstance(item, ItemPedido) else ItemPedido.model_validate(item)
    except ValidationError:
        return {"encontrado": False, "aviso": "Item inválido: informe pelo menos o produto e a quantidade."}
    if not math.isfinite(item.quantidade) or item.quantidade <= 0:
        return {"encontrado": False, "aviso": "Informe uma quantidade maior que zero."}

    entrega = _data(data_entrega)
    if entrega is None:
        return {"encontrado": False, "aviso": f"Data de entrega inválida: '{data_entrega}'. Use AAAA-MM-DD."}
    referencia = _data(data_referencia) if data_referencia else dt.date.today()
    if referencia is None:
        return {"encontrado": False, "aviso": f"Data de referência inválida: '{data_referencia}'. Use AAAA-MM-DD."}
    if entrega < referencia:
        return {
            "encontrado": False,
            "aviso": f"A data de entrega ({entrega.isoformat()}) é anterior à data de referência ({referencia.isoformat()}).",
        }

    return avaliar(item, entrega, comprador, referencia, fatos=obter_fatos(), repo=obter_repositorio())


# Lê uma data ISO ou brasileira; None se vier vazia ou inválida.
def _data(texto: Optional[str]) -> dt.date | None:
    try:
        return n.data(texto)
    except ValueError:
        return None


# Unidade da tabela para o que veio no pedido; o texto original se não reconhecer.
def _normalizar_unidade(unidade: Optional[str]) -> str | None:
    if not unidade or not unidade.strip():
        return None
    return _UNIDADES.get(n.chave(unidade), unidade.strip())


# Avalia o item com fatos e repositório dados (o núcleo da ferramenta).
def avaliar(
    item: ItemPedido,
    data_entrega: dt.date,
    comprador: str,
    data_referencia: dt.date,
    fatos: Fatos,
    repo: DadosRepository,
) -> dict:
    resolucao = repo.catalogo.resolver(item.produto)
    if not resolucao.encontrado:
        return {
            "encontrado": False,
            "termo": resolucao.termo,
            "opcoes": resolucao.candidatos,
            "aviso": resolucao.aviso(),
        }

    produto = resolucao.base
    variantes = [resolucao.variante] if resolucao.variante else repo.catalogo.variantes(produto)
    linha_preco = repo.preco_da_variante(variantes[0]) if variantes else None
    contrato = fatos.contrato_do_comprador(comprador)
    item_contrato = contrato.item(produto) if contrato else None

    ctx = Contexto(
        produto=produto,
        variante=resolucao.variante,
        unidade_venda=linha_preco["unidade"] if linha_preco is not None else None,
        unidade_item=_normalizar_unidade(item.unidade),
        quantidade=item.quantidade,
        organico=item.organico or bool(item_contrato and item_contrato.exige_organico),
        data_entrega=data_entrega,
        data_referencia=data_referencia,
        comprador=(comprador or "").strip(),
        contrato=contrato,
        item_contrato=item_contrato,
        produtores=repo.produtores_do_produto(produto),
        fatos=fatos,
        repo=repo,
    )

    # Primeira fase: cada regra só olha quem as anteriores não tiraram, para o
    # produtor excluído não acumular alertas que já não mudam a decisão.
    avaliacao = Avaliacao()
    for regra in (regra_produtor_inativo, regra_certificacao_organica, regra_nao_conformidade, regra_registro_sanitario):
        restantes = ctx.produtores[~ctx.produtores["produtor_id"].isin(list(avaliacao.excluidos))]
        avaliacao.juntar(regra(replace(ctx, produtores=restantes)))

    elegiveis = ctx.ativos[~ctx.ativos["produtor_id"].isin(list(avaliacao.excluidos))]
    if elegiveis.empty:
        avaliacao.alertas.append(_sem_produtor_elegivel(ctx, avaliacao))

    capacidade_avaliacao, capacidade = regra_capacidade(ctx, elegiveis)
    for parcial in (
        regra_unidade(ctx),
        regra_safra(ctx),
        capacidade_avaliacao,
        regra_exclusividade(ctx),
        regra_contrato(ctx, elegiveis),
    ):
        avaliacao.juntar(parcial)

    alertas = ordenar(avaliacao.alertas)
    preco_item = _preco(ctx) if not elegiveis.empty else None  # sem quem venda, não há o que orçar
    fontes = {arquivo for alerta in alertas for arquivo in alerta.arquivos()}
    if preco_item and preco_item.get("fonte"):
        fontes.add(preco_item["fonte"])

    return {
        "encontrado": True,
        "item": {
            "produto": produto,
            "variante": resolucao.variante,
            "quantidade": item.quantidade,
            "unidade": ctx.unidade_venda,
            "organico": ctx.organico,
        },
        "comprador": ctx.comprador or None,
        "contrato": contrato.numero if contrato else None,
        "data_entrega": data_entrega.isoformat(),
        "data_referencia": data_referencia.isoformat(),
        "pode_atender": not elegiveis.empty and not any(a.codigo in BLOQUEANTES for a in alertas),
        "elegiveis": [
            {
                "produtor_id": linha["produtor_id"],
                "nome": linha["nome"],
                "municipio": linha["municipio"],
                "pendencias": sorted(set(avaliacao.pendencias.get(linha["produtor_id"], []))),
            }
            for _, linha in elegiveis.sort_values("produtor_id").iterrows()
        ],
        "excluidos": [
            {
                "produtor_id": linha["produtor_id"],
                "nome": linha["nome"],
                "motivos": list(dict.fromkeys(avaliacao.excluidos[linha["produtor_id"]])),
            }
            for _, linha in ctx.produtores.sort_values("produtor_id").iterrows()
            if linha["produtor_id"] in avaliacao.excluidos
        ],
        "capacidade": capacidade,
        "preco": preco_item,
        "alertas": [a.como_dict() for a in alertas],
        "fontes": sorted(fontes),
        "aviso": None,
    }


# Alerta para quando nenhum produtor pode atender o item.
def _sem_produtor_elegivel(ctx: Contexto, avaliacao: Avaliacao) -> Alerta:
    tipo = f"{ctx.produto} como orgânico" if ctx.organico else ctx.produto
    if ctx.produtores.empty:
        motivo = "nenhum produtor do cadastro fornece o produto"
    else:
        motivo = "os motivos de cada produtor estão nos outros alertas (" + ", ".join(sorted(avaliacao.excluidos)) + ")"
    return Alerta("SEM_PRODUTOR_ELEGIVEL", GRAVE, f"Nenhum produtor pode atender {tipo}: {motivo}.", CADASTRO)


# Preço do item: contrato do comprador quando houver, senão a tabela geral.
def _preco(ctx: Contexto) -> dict[str, Any] | None:
    if ctx.unidade_divergente:
        return None
    tabela = preco(ctx.variante or ctx.produto, ctx.organico, ctx.quantidade)
    contrato = ctx.contrato
    if contrato is None or contrato.preco == "tabela":
        return {"origem": "tabela", **tabela}
    if ctx.item_contrato is None or not contrato.vigente_em(ctx.data_entrega):
        return None  # sem item no contrato ou contrato vencido: não há preço contratado

    unitario = Decimal(str(ctx.item_contrato.preco))
    total = (unitario * Decimal(str(ctx.quantidade))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "origem": "contrato",
        "contrato": contrato.numero,
        "produto": ctx.produto,
        "unidade": ctx.item_contrato.unidade,
        "quantidade": ctx.quantidade,
        "preco_unitario": float(unitario),
        "total": float(total),
        "preco_tabela_geral": tabela.get("preco_unitario") if tabela.get("disponivel") else None,
        "observacao": ctx.item_contrato.observacao,
        "fonte": contrato.fonte,
    }


# Lista de ferramentas que as regras expõem ao Gemini por function calling.
FERRAMENTAS = [verificar_conformidade]
