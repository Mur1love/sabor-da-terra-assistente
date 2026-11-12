"""Acesso aos dados usado pelas consultas e ponto de troca para o BigQuery.

Hoje o RepositorioLocal responde com pandas sobre data/. Na etapa #15, uma
versão BigQuery implementa os mesmos métodos e devolve as mesmas colunas, sem
mexer nas consultas.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol, runtime_checkable

import pandas as pd

from sabor_da_terra.dados.carregamento import BaseDados, obter_base
from sabor_da_terra.dados.catalogo import Catalogo


@runtime_checkable
class DadosRepository(Protocol):
    """Consultas que toda fonte de dados precisa responder, com as colunas de esquema.py.

    Os valores seguem os tipos do Python, não os da fonte: DATE vira date,
    DATETIME vira datetime, NUMERIC vira float, INT64 vira int, BOOL vira bool
    e dado ausente vira None. O BigQuery devolve NUMERIC como Decimal e DATE às
    vezes como Timestamp; a implementação dele converte antes de devolver.
    """

    # Catálogo de produtos usado para resolver nomes.
    @property
    def catalogo(self) -> Catalogo: ...

    # Cadastro completo de produtores.
    def produtores(self) -> pd.DataFrame: ...

    # Um produtor pelo código, ou None se não existir.
    def produtor(self, produtor_id: str) -> pd.Series | None: ...

    # Produtores ligados a um produto base, ativos ou não.
    def produtores_do_produto(self, produto: str) -> pd.DataFrame: ...

    # Linha da sazonalidade de um produto num mês, ou None.
    def sazonalidade(self, produto: str, mes: int) -> pd.Series | None: ...

    # Linha da tabela de preços, ou None.
    def preco_da_variante(self, variante: str) -> pd.Series | None: ...

    # Todos os códigos de lote, em ordem.
    def ids_de_lote(self) -> list[str]: ...

    # Um lote pelo código, ou None.
    def lote(self, lote_id: str) -> pd.Series | None: ...

    # Uma venda pelo código, ou None.
    def transacao(self, id_transacao: str) -> pd.Series | None: ...

    # Todas as vendas de um produtor.
    def transacoes_do_produtor(self, produtor_id: str) -> pd.DataFrame: ...

    # Todos os pedidos recebidos.
    def pedidos(self) -> pd.DataFrame: ...

    # Um pedido pelo código, ou None.
    def pedido(self, pedido_id: str) -> pd.Series | None: ...


# Primeira linha do resultado, ou None se vier vazio.
def _uma(df: pd.DataFrame) -> pd.Series | None:
    return None if df.empty else df.iloc[0]


class RepositorioLocal:

    # Guarda as tabelas já carregadas.
    def __init__(self, base: BaseDados):
        self._base = base

    # Catálogo de produtos usado para resolver nomes.
    @property
    def catalogo(self) -> Catalogo:
        return self._base.catalogo

    # Cadastro completo de produtores.
    def produtores(self) -> pd.DataFrame:
        return self._base.produtores

    # Um produtor pelo código, ou None se não existir.
    def produtor(self, produtor_id: str) -> pd.Series | None:
        df = self._base.produtores
        return _uma(df[df["produtor_id"] == produtor_id])

    # Produtores ligados a um produto base, ativos ou não.
    def produtores_do_produto(self, produto: str) -> pd.DataFrame:
        ligacoes = self._base.produtor_produtos
        ids = ligacoes.loc[ligacoes["produto"] == produto, "produtor_id"]
        df = self._base.produtores
        return df[df["produtor_id"].isin(ids)]

    # Linha da sazonalidade de um produto num mês, ou None.
    def sazonalidade(self, produto: str, mes: int) -> pd.Series | None:
        df = self._base.sazonalidade
        return _uma(df[(df["produto"] == produto) & (df["mes"] == mes)])

    # Linha da tabela de preços, ou None.
    def preco_da_variante(self, variante: str) -> pd.Series | None:
        df = self._base.produtos
        return _uma(df[df["produto"] == variante])

    # Todos os códigos de lote, em ordem.
    def ids_de_lote(self) -> list[str]:
        return sorted(self._base.lotes["lote_id"])

    # Um lote pelo código, ou None.
    def lote(self, lote_id: str) -> pd.Series | None:
        df = self._base.lotes
        return _uma(df[df["lote_id"] == lote_id])

    # Uma venda pelo código, ou None.
    def transacao(self, id_transacao: str) -> pd.Series | None:
        df = self._base.transacoes
        return _uma(df[df["id_transacao"] == id_transacao])

    # Todas as vendas de um produtor.
    def transacoes_do_produtor(self, produtor_id: str) -> pd.DataFrame:
        df = self._base.transacoes
        return df[df["produtor_id"] == produtor_id]

    # Todos os pedidos recebidos.
    def pedidos(self) -> pd.DataFrame:
        return self._base.pedidos

    # Um pedido pelo código, ou None.
    def pedido(self, pedido_id: str) -> pd.Series | None:
        df = self._base.pedidos
        return _uma(df[df["pedido_id"] == pedido_id])


# Devolve o repositório em uso (hoje, o local).
@lru_cache(maxsize=1)
def obter_repositorio() -> DadosRepository:

    return RepositorioLocal(obter_base())
