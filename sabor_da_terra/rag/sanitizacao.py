"""Sanitização de dados sensíveis para indexação RAG."""

import re


PADROES_SENSIVEIS = [
    (
        re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
        "[CPF REMOVIDO]",
    ),
    (
        re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
        "[CNPJ REMOVIDO]",
    ),
    (
        re.compile(
            r"(?im)^\s*Banco do Brasil\s*-\s*Ag\.[^\n]*$"
        ),
        "[DADOS BANCÁRIOS REMOVIDOS]",
    ),
]


def sanitizar_texto(texto: str) -> str:
    """Mascara informações sensíveis antes dos embeddings."""

    resultado = texto

    for padrao, substituicao in PADROES_SENSIVEIS:
        resultado = padrao.sub(substituicao, resultado)

    return resultado


def sanitizar_trechos(trechos: list[dict]) -> list[dict]:
    """Retorna cópias dos trechos com texto sanitizado."""

    resultado = []

    for trecho in trechos:
        resultado.append({
            **trecho,
            "texto": sanitizar_texto(trecho["texto"]),
            "metadados": {
                **trecho["metadados"],
            },
        })

    return resultado
