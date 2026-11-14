"""Normalização de produtos e unidades contra o catálogo da cooperativa (Etapa 4)."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
import re

from sabor_da_terra.dados.catalogo import Catalogo, Resolucao
from sabor_da_terra.dados.normalizacao import chave
from sabor_da_terra.triagem.schema import ItemPedidoExtraido

_RAIZ = Path(__file__).resolve().parents[2]
_ARQ_PRECOS = _RAIZ / "data" / "tabela_precos_outubro_2026.csv"
_ARQ_SAZONALIDADE = _RAIZ / "data" / "sazonalidade.csv"

_UNIDADES_MAP: dict[str, str] = {
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "quilo": "kg",
    "quilos": "kg",
    "kilograma": "kg",
    "kilogramas": "kg",
    "quilograma": "kg",
    "quilogramas": "kg",
    "g": "g",
    "gr": "g",
    "grama": "g",
    "gramas": "g",
    "maco": "maço",
    "macos": "maço",
    "un": "unidade",
    "und": "unidade",
    "unid": "unidade",
    "unidade": "unidade",
    "unidades": "unidade",
    "pe": "unidade",
    "pes": "unidade",
    "cabeca": "unidade",
    "cabecas": "unidade",
    "dz": "dúzia",
    "duzia": "dúzia",
    "duzias": "dúzia",
    "l": "litro",
    "lt": "litro",
    "litro": "litro",
    "litros": "litro",
    "pote": "pote",
    "potes": "pote",
    "frasco": "frasco",
    "frascos": "frasco",
    "garrafa": "garrafa",
    "garrafas": "garrafa",
    "bandeja": "bandeja",
    "bandejas": "bandeja",
    "caixa": "caixa",
    "caixas": "caixa",
    "saco": "saco",
    "sacos": "saco",
}

_TRADUCOES_EN: dict[str, str] = {
    "mango": "manga",
    "mangoes": "manga",
    "guava": "goiaba",
    "guavas": "goiaba",
    "passion fruit": "maracujá",
    "honey": "mel",
    "wild honey": "mel silvestre",
    "cheese": "queijo",
    "cassava": "macaxeira",
    "yam": "inhame",
    "tomato": "tomate",
    "tomatoes": "tomate",
    "lettuce": "alface",
    "eggs": "ovos caipira",
    "chicken": "frango caipira",
}

_PALAVRAS_RUIDO: set[str] = {
    "aquele",
    "aquela",
    "aqueles",
    "aquelas",
    "mesmo",
    "mesma",
    "fresco",
    "fresca",
    "frescos",
    "frescas",
    "variado",
    "variada",
    "variados",
    "variadas",
    "puro",
    "pura",
    "organico",
    "organica",
    "organicos",
    "organicas",
    "certificacao",
    "com",
    "sabe",
    "tipo",
}


@lru_cache(maxsize=1)
def carregar_catalogo_padrao() -> tuple[Catalogo, dict[str, str]]:
    """Carrega o catálogo oficial da cooperativa e a unidade padrão de cada produto."""
    nomes_preco: list[str] = []
    unidades: dict[str, str] = {}

    if _ARQ_PRECOS.exists():
        with _ARQ_PRECOS.open(encoding="utf-8-sig", newline="") as f:
            for linha in csv.DictReader(f):
                prod = (linha.get("produto") or "").strip()
                unid = normalizar_unidade(linha.get("unidade"))
                if prod:
                    nomes_preco.append(prod)
                    if unid and prod not in unidades:
                        unidades[prod] = unid

    nomes_sazonalidade: list[str] = []
    if _ARQ_SAZONALIDADE.exists():
        with _ARQ_SAZONALIDADE.open(encoding="utf-8-sig", newline="") as f:
            for linha in csv.DictReader(f):
                prod = (linha.get("produto") or "").strip()
                if prod:
                    nomes_sazonalidade.append(prod)

    catalogo = Catalogo(nomes_preco=nomes_preco, nomes_sazonalidade=nomes_sazonalidade)
    for prod, unid in list(unidades.items()):
        base = catalogo.base_da_variante(prod)
        unidades.setdefault(base, unid)

    return catalogo, unidades


def normalizar_unidade(unidade: str | None) -> str | None:
    """Converte abreviações e plurais de unidade para o padrão do catálogo."""
    if not unidade or not unidade.strip():
        return None
    limpo = re.sub(r"[.\s]+$", "", unidade.strip())
    k = chave(limpo)
    if not k:
        return None
    return _UNIDADES_MAP.get(k, limpo.lower())


def _limpar_expressao_produto(termo: str) -> str:
    """Remove parênteses mantendo qualificadores úteis e descarta palavras de preenchimento."""
    sem_parenteses = re.sub(r"[()\[\],;:!?]+", " ", termo)
    tokens = [t for t in sem_parenteses.split() if chave(t) not in _PALAVRAS_RUIDO]
    candidato = " ".join(tokens).strip()
    if not candidato:
        return termo.strip()
    k = chave(candidato)
    if k in _TRADUCOES_EN:
        return _TRADUCOES_EN[k]
    return candidato


def normalizar_produto(termo: str, catalogo: Catalogo | None = None) -> Resolucao:
    """Mapeia o nome extraído (coloquial, abreviado ou em inglês) para o catálogo."""
    if catalogo is None:
        catalogo, _ = carregar_catalogo_padrao()

    bruto = termo.strip()
    if not bruto:
        return Resolucao(termo=termo)

    # 1. Tentativa direta no catálogo (preserva 'queijo manteiga' vs 'manteiga de garrafa')
    res_direta = catalogo.resolver(bruto)
    if res_direta.encontrado:
        return res_direta

    # 2. Limpeza de expressões coloquiais/parênteses/inglês (ex.: 'mel (aquele silvestre mesmo)')
    limpo = _limpar_expressao_produto(bruto)
    if chave(limpo) != chave(bruto):
        res_limpa = catalogo.resolver(limpo)
        if res_limpa.encontrado or res_limpa.ambiguo or res_limpa.candidatos:
            return Resolucao(
                termo=termo,
                base=res_limpa.base,
                variante=res_limpa.variante,
                candidatos=res_limpa.candidatos,
                ambiguo=res_limpa.ambiguo,
            )

    return res_direta


def normalizar_itens_pedido(
    itens: list[ItemPedidoExtraido],
    catalogo: Catalogo | None = None,
) -> tuple[list[ItemPedidoExtraido], list[str]]:
    """Normaliza produtos e unidades de uma lista de itens, retornando avisos de ambiguidade."""
    cat_padrao, unidades_padrao = carregar_catalogo_padrao()
    cat = catalogo or cat_padrao

    itens_normalizados: list[ItemPedidoExtraido] = []
    avisos: list[str] = []

    for item in itens:
        resolucao = normalizar_produto(item.produto, catalogo=cat)
        nome_final = resolucao.base or _limpar_expressao_produto(item.produto)
        origem = item.produto_original or (
            item.produto if chave(nome_final) != chave(item.produto) else None
        )

        unidade_final = normalizar_unidade(item.unidade)
        if unidade_final is None and item.quantidade is not None and resolucao.base:
            unidade_final = unidades_padrao.get(resolucao.base)

        itens_normalizados.append(
            item.model_copy(
                update={
                    "produto": nome_final,
                    "produto_original": origem,
                    "unidade": unidade_final,
                }
            )
        )

        aviso = resolucao.aviso()
        if aviso and aviso not in avisos:
            avisos.append(aviso)

    return itens_normalizados, avisos
