"""Camada de dados (etapa 4). O assistente consulta os dados por funções, sem colar tabelas no prompt.

Quem está fora deste pacote lê os dados pelo repositório (obter_repositorio) ou
pelas ferramentas. Ler as tabelas direto do carregamento pularia o ponto de
troca para o BigQuery.
"""

from sabor_da_terra.dados.consultas import (
    FERRAMENTAS,
    buscar_produtores,
    disponibilidade,
    extrato_produtor,
    identificar_produtor,
    preco,
    rastrear_lote,
)
from sabor_da_terra.dados.repositorio import DadosRepository, RepositorioLocal, obter_repositorio

__all__ = [
    "FERRAMENTAS",
    "DadosRepository",
    "RepositorioLocal",
    "buscar_produtores",
    "disponibilidade",
    "extrato_produtor",
    "identificar_produtor",
    "obter_repositorio",
    "preco",
    "rastrear_lote",
]
