"""Interface conversacional (etapa 13): lógica pura por trás do `app.py` Streamlit.

Aqui mora o que dá para testar sem rodar o Streamlit: extração das fontes
citadas no texto da resposta, mensagens de erro amigáveis e a formatação da
fila de triagem para o `st.dataframe`. As chamadas `st.*` ficam no `app.py`.
"""

from sabor_da_terra.interface.fila import (
    detalhes_da_fila,
    estilo_celula_prioridade,
    estilo_celula_problemas,
    formatar_fila,
)
from sabor_da_terra.interface.mensagens import extrair_fontes, mensagem_de_erro

__all__ = [
    "detalhes_da_fila",
    "estilo_celula_prioridade",
    "estilo_celula_problemas",
    "extrair_fontes",
    "formatar_fila",
    "mensagem_de_erro",
]
