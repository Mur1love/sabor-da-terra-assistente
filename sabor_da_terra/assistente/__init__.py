"""Orquestração do assistente com function calling (etapa 12).

Une as capacidades das etapas 4–11 num único assistente conversacional: o
Gemini recebe a mensagem da equipe, escolhe a função por function calling
nativo e mantém o contexto da sessão. A interface (#13) guarda o
`EstadoSessao` no `st.session_state` via `to_dict()/from_dict()`.
"""

from sabor_da_terra.assistente.estado import EstadoSessao, data_referencia_padrao
from sabor_da_terra.assistente.ferramentas import (
    FERRAMENTAS,
    NOME_PARA_FUNCAO,
    declarar_ferramentas,
)
from sabor_da_terra.assistente.mascaramento import mascarar_dados_sensiveis
from sabor_da_terra.assistente.orquestrador import (
    Assistente,
    MAX_CHAMADAS_POR_TURNO,
    MAX_ITERACOES_POR_TURNO,
)
from sabor_da_terra.assistente.prompt import PROMPT_RESPOSTA_FINAL, PROMPT_SISTEMA

__all__ = [
    "Assistente",
    "EstadoSessao",
    "FERRAMENTAS",
    "MAX_CHAMADAS_POR_TURNO",
    "MAX_ITERACOES_POR_TURNO",
    "NOME_PARA_FUNCAO",
    "PROMPT_RESPOSTA_FINAL",
    "PROMPT_SISTEMA",
    "declarar_ferramentas",
    "data_referencia_padrao",
    "mascarar_dados_sensiveis",
]
