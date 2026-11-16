"""Redação final pelo Gemini Flash, presa aos números do rascunho.

O rascunho (modelo fixo de resumo.py, notificar.py ou mensagens.py) já tem
todos os valores. O Gemini só reescreve em linguagem mais natural; a resposta
volta conferida: todo valor em R$, data e código (FIN-, PED-) do texto novo tem
de existir no rascunho, nenhum código do rascunho pode sumir e não pode haver
dado sensível. Se algo falhar, ou se a API não estiver disponível, fica o
rascunho, que já é um texto válido para o produtor.
"""

from __future__ import annotations

import re
from typing import Any

from sabor_da_terra.llm.cliente import LLMClient, Papel
from sabor_da_terra.prompts.produtores import PROMPT_REDACAO_PRODUTOR, VERSAO_PROMPT_PRODUTORES
from sabor_da_terra.produtores.texto import dados_sensiveis_no_texto

_VALOR = re.compile(r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}(?!\d)")
# Qualquer coisa escrita como dinheiro, mesmo fora do formato (R$ 4.600, R$4500).
_QUALQUER_VALOR = re.compile(r"R\$\s?\d[\d.,]*")
_DATA = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
_CODIGO = re.compile(r"\b(?:FIN|PED)-\d{4}-\d{3}\b")


def _valores(texto: str) -> set[str]:
    return {re.sub(r"R\$\s?", "R$ ", v) for v in _VALOR.findall(texto)}


def problemas_da_redacao(rascunho: str, texto: str) -> list[str]:
    """O que o texto reescrito mudou de proibido em relação ao rascunho. Vazio = pode usar."""
    problemas = []
    for bruto in _QUALQUER_VALOR.findall(texto):
        if not _VALOR.fullmatch(bruto.rstrip(".,")):
            problemas.append(f"valor fora do formato R$ 0,00: {bruto.rstrip('.,')}")
    valores_rascunho, valores_texto = _valores(rascunho), _valores(texto)
    for valor in sorted(valores_texto - valores_rascunho):
        problemas.append(f"valor que não está no rascunho: {valor}")
    for valor in sorted(valores_rascunho - valores_texto):
        problemas.append(f"valor do rascunho que sumiu: {valor}")
    for data in sorted(set(_DATA.findall(texto)) - set(_DATA.findall(rascunho))):
        problemas.append(f"data que não está no rascunho: {data}")
    codigos_rascunho, codigos_texto = set(_CODIGO.findall(rascunho)), set(_CODIGO.findall(texto))
    for codigo in sorted(codigos_texto - codigos_rascunho):
        problemas.append(f"código que não está no rascunho: {codigo}")
    for codigo in sorted(codigos_rascunho - codigos_texto):
        problemas.append(f"código do rascunho que sumiu: {codigo}")
    for trecho in dados_sensiveis_no_texto(texto):
        problemas.append(f"dado sensível no texto: {trecho}")
    return problemas


def redigir(rascunho: str, cliente_llm: LLMClient | None = None) -> dict[str, Any]:
    """Reescreve o rascunho com o Gemini Flash; devolve o texto usado e de onde ele veio."""
    cliente = cliente_llm or LLMClient()
    prompt = f"{PROMPT_REDACAO_PRODUTOR}\nRASCUNHO:\n{rascunho}"
    try:
        resposta = cliente.gerar(Papel.RESPOSTA, prompt, temperature=0.2)
        texto = (resposta.text or "").strip()
    except Exception as exc:  # sem chave, sem fixture ou API fora: o rascunho já serve
        return {"texto": rascunho, "origem": "modelo_fixo", "problemas": [f"Gemini indisponível: {exc}"],
                "versao_prompt": VERSAO_PROMPT_PRODUTORES}

    problemas = ["resposta vazia"] if not texto else problemas_da_redacao(rascunho, texto)
    return {
        "texto": rascunho if problemas else texto,
        "origem": "modelo_fixo" if problemas else "gemini",
        "problemas": problemas,
        "versao_prompt": VERSAO_PROMPT_PRODUTORES,
    }
