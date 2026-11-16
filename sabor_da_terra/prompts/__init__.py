"""Prompts versionados do assistente Sabor da Terra."""

from sabor_da_terra.prompts.consulta_documental import (
    PROMPT_PLANEJAMENTO_CONSULTA,
    PROMPT_RESPOSTA_DOCUMENTAL,
    VERSAO_PROMPT_DOCUMENTAL,
)
from sabor_da_terra.prompts.produtores import PROMPT_REDACAO_PRODUTOR, VERSAO_PROMPT_PRODUTORES
from sabor_da_terra.prompts.triagem import (
    INSTRUCOES_SISTEMA_TRIAGEM,
    VERSAO_PROMPT_TRIAGEM,
    montar_prompt_triagem,
)

__all__ = [
    "VERSAO_PROMPT_DOCUMENTAL",
    "PROMPT_PLANEJAMENTO_CONSULTA",
    "PROMPT_RESPOSTA_DOCUMENTAL",
    "VERSAO_PROMPT_PRODUTORES",
    "PROMPT_REDACAO_PRODUTOR",
    "VERSAO_PROMPT_TRIAGEM",
    "INSTRUCOES_SISTEMA_TRIAGEM",
    "montar_prompt_triagem",
]
