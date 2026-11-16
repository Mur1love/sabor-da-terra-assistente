"""Ferramentas do assistente: as funções das etapas 4–11 declaradas ao Gemini.

Fonte única: nada é reimplementado aqui. Cada callable é convertido em
`FunctionDeclaration` pela assinatura + docstring (`from_callable_with_api_option`
— padrão das etapas 8–11), e a declaração é cacheada: o hash de fixture do
cliente exige que a config do `gerar` seja determinística.

Único adaptador: `triar_pendentes` é declarada sem `caminho_pedidos` (o
default aponta para tests/fixtures/; o modelo não pode redirecionar caminho
de arquivo).
"""

from functools import lru_cache
from typing import Any, Callable

from google.genai import types

from sabor_da_terra.dados.consultas import (
    buscar_produtores,
    disponibilidade,
    identificar_produtor,
    preco,
    rastrear_lote,
)
from sabor_da_terra.produtores import notificar_produtores, resumo_produtor
from sabor_da_terra.rag.responder import consultar_documentos
from sabor_da_terra.regras.conformidade import verificar_conformidade
from sabor_da_terra.triagem.extrair import triar_pedido
from sabor_da_terra.triagem.fila import triar_pendentes as _triar_pendentes_real


def triar_pendentes(data_referencia: str) -> dict[str, Any]:
    """Gera a fila consolidada dos pedidos pendentes na data da triagem (AAAA-MM-DD),
    com prioridade, urgência, alocação e correspondências de ofertas."""
    return _triar_pendentes_real(data_referencia)


FERRAMENTAS: list[Callable] = [
    identificar_produtor,
    buscar_produtores,
    disponibilidade,
    preco,
    rastrear_lote,
    verificar_conformidade,
    consultar_documentos,
    triar_pedido,
    triar_pendentes,
    resumo_produtor,
    notificar_produtores,
]

NOME_PARA_FUNCAO: dict[str, Callable] = {f.__name__: f for f in FERRAMENTAS}

# Ferramentas que criam o próprio LLMClient por dentro (roteamento/extração aninhados).
FERRAMENTAS_COM_LLM: tuple[str, ...] = ("triar_pedido", "consultar_documentos")


@lru_cache(maxsize=1)
def declarar_ferramentas() -> types.Tool:
    """Declaração única das ferramentas para o `tools` do `GenerateContentConfig`."""
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration.from_callable_with_api_option(callable=f) for f in FERRAMENTAS
        ]
    )
