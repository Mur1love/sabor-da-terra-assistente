"""Busca lexical por identificadores documentais."""

import re


PADRAO_IDENTIFICADORES = re.compile(
    r"\b(?:"
    r"ORG-PE-\d{4}-\d+"
    r"|ADAGRO-[A-Z]{2}-\d{4}-\d+"
    r"|\d{3}/\d{4}(?:-[A-Z]+)?"
    r")\b",
    flags=re.IGNORECASE,
)


def extrair_identificadores(texto: str) -> list[str]:
    """Extrai identificadores documentais de um texto."""

    encontrados = PADRAO_IDENTIFICADORES.findall(texto)

    return list(dict.fromkeys(
        identificador.upper()
        for identificador in encontrados
    ))


def calcular_score_lexical(
    pergunta: str,
    trecho: str,
) -> float:
    """Calcula a correspondência exata dos identificadores."""

    identificadores = extrair_identificadores(pergunta)

    if not identificadores:
        return 0.0

    encontrados = set(
        extrair_identificadores(trecho)
    )

    correspondencias = sum(
        identificador in encontrados
        for identificador in identificadores
    )

    return correspondencias / len(identificadores)


def buscar_por_identificadores(
    pergunta: str,
    nos: list,
    filtros: dict | None = None,
) -> list[dict]:
    """Busca nós com identificadores exatos, respeitando filtros."""

    filtros = filtros or {}
    resultados = []

    for no in nos:
        metadados = no.metadata

        if any(
            metadados.get(chave) != valor
            for chave, valor in filtros.items()
        ):
            continue

        score = calcular_score_lexical(
            pergunta,
            no.text,
        )

        if score <= 0:
            continue

        resultados.append(
            {
                "id": no.node_id,
                "arquivo": metadados.get("arquivo"),
                "trecho": no.text,
                "metadados": metadados,
                "score_lexical": score,
            }
        )

    return sorted(
        resultados,
        key=lambda item: item["score_lexical"],
        reverse=True,
    )
