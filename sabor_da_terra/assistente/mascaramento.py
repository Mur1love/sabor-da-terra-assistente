"""Máscara de dados sensíveis antes de qualquer envio ao modelo.

Regra 2 do docs/03: nunca enviar dado real de pessoa. Tudo que sai do
assistente ao modelo (mensagem do usuário, saída de função, payload de
composição) e tudo que vai ao log passa por `mascarar_dados_sensiveis`:
CPF por regex (mesmo padrão da camada de dados), conta por regex (mesmo
padrão de `produtores/texto.py`) e os valores exatos do cadastro (cpf,
telefone, e-mail, chave PIX e conta) substituídos por "***".
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from sabor_da_terra.dados import obter_repositorio
from sabor_da_terra.dados.normalizacao import mascarar_cpf_em_texto

# Conta corrente no formato do cadastro (28901-3, 0073921-7, 00134578-2).
_CONTA = re.compile(r"\b\d{5,8}-\d\b")

MASCARA = "***"

# Colunas do cadastro que não podem chegar ao modelo em hipótese alguma.
COLUNAS_SENSIVEIS = ("cpf", "telefone", "email", "chave_pix", "chave_pix_deposito", "conta_corrente")


@lru_cache(maxsize=1)
def valores_sensiveis_do_cadastro() -> frozenset[str]:
    """Valores exatos de pessoa no cadastro dos produtores (vazio = nada a mascarar)."""
    produtores = obter_repositorio().produtores()
    valores: set[str] = set()
    for coluna in COLUNAS_SENSIVEIS:
        if coluna in produtores.columns:
            valores.update(
                str(valor).strip() for valor in produtores[coluna].dropna() if str(valor).strip()
            )
    return frozenset(valores)


def _mascarar_texto(texto: str) -> str:
    texto = mascarar_cpf_em_texto(texto)
    for valor in valores_sensiveis_do_cadastro():
        if valor in texto:
            texto = texto.replace(valor, MASCARA)
    return _CONTA.sub(MASCARA, texto)


def mascarar_dados_sensiveis(obj: Any) -> Any:
    """Percorre dict/list/tuple/str e mascara CPF, PIX, conta, telefone e e-mail."""
    if isinstance(obj, str):
        return _mascarar_texto(obj)
    if isinstance(obj, dict):
        return {chave: mascarar_dados_sensiveis(valor) for chave, valor in obj.items()}
    if isinstance(obj, list):
        return [mascarar_dados_sensiveis(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(mascarar_dados_sensiveis(item) for item in obj)
    return obj
