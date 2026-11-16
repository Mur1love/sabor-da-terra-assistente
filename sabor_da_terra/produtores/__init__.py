"""Comunicação com produtores (etapa 11, Desafio C): resumos personalizados e notificações.

Os números vêm das funções de dados (#4) e das regras (#5); a fila de pedidos
vem da triagem (#10). O texto sai de um modelo fixo e pode passar pelo Gemini
(redacao.py), que só reescreve. Nenhum texto leva CPF ou dado bancário.
"""

from sabor_da_terra.produtores.mensagens import responder_mensagem_produtor
from sabor_da_terra.produtores.notificar import notificacao_produtor, notificacoes_da_fila, notificar_produtores
from sabor_da_terra.produtores.redacao import redigir
from sabor_da_terra.produtores.resumo import montar_resumo, relatorio_pendencias_vencidas, resumo_produtor

# Funções que o assistente (#12) expõe ao Gemini por function calling (as duas da issue #11).
# responder_mensagem_produtor e relatorio_pendencias_vencidas ficam de fora até a #12 decidir se precisa delas.
FERRAMENTAS = [resumo_produtor, notificar_produtores]

__all__ = [
    "FERRAMENTAS",
    "montar_resumo",
    "notificacao_produtor",
    "notificacoes_da_fila",
    "notificar_produtores",
    "redigir",
    "relatorio_pendencias_vencidas",
    "responder_mensagem_produtor",
    "resumo_produtor",
]
