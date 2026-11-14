"""Busca lexical por identificadores documentais."""

import re


PADRAO_IDENTIFICADORES = re.compile(
    # (?<![\w.]) evita pegar "831/2003" de dentro de "Lei 10.831/2003".
    r"(?<![\w.])(?:"
    r"ORG-[A-Z]{2}-\d{4}-\d+"            # certificado IBD
    r"|ECO-BR-\d{4}-[A-Z]{2}-\d+"        # certificado Ecocert
    r"|ADAGRO-[A-Z]{2}-\d{4}-\d+"        # relatório ADAGRO
    r"|VS-[A-Z]{3}-\d{4}-\d+"            # laudo da vigilância sanitária
    r"|REN-\d{4}-\d+"                    # protocolo de renovação
    r"|BR-BIO-\d+"                       # registro Sisorg
    r"|[A-Z]{2}-SIE-\d+"                 # registro SIE: PE-SIE-0892
    r"|SIE[:\s]+[A-Z]{2}-\d+"            # registro SIE: SIE PE-0892
    r"|\d{3}/\d{4}(?:-[A-Z]+)?"          # contrato: 045/2026-PNAE
    r")",
    flags=re.IGNORECASE,
)


def normalizar_identificador(identificador: str) -> str:
    """Normaliza identificadores para comparação lexical."""

    identificador = identificador.upper()

    # Remove sufixos de contratos, como -PNAE.
    # Exemplo: 045/2026-PNAE -> 045/2026.
    if re.fullmatch(r"\d{3}/\d{4}-[A-Z]+", identificador):
        return identificador.split("-")[0]

    # "SIE PE-0892" e "PE-SIE-0892" são o mesmo registro.
    sie = re.fullmatch(r"SIE[:\s]+([A-Z]{2})-(\d+)", identificador)
    if sie:
        return f"{sie.group(1)}-SIE-{sie.group(2)}"

    return identificador


def extrair_identificadores(texto: str) -> list[str]:
    """Extrai e normaliza identificadores documentais."""

    encontrados = PADRAO_IDENTIFICADORES.findall(texto)

    return list(
        dict.fromkeys(
            normalizar_identificador(identificador)
            for identificador in encontrados
        )
    )


def calcular_score_lexical(
    pergunta: str,
    trecho: str,
) -> float:
    """Calcula a correspondência exata dos identificadores."""

    identificadores = extrair_identificadores(pergunta)

    if not identificadores:
        return 0.0

    encontrados = set(extrair_identificadores(trecho))

    correspondencias = sum(
        identificador in encontrados
        for identificador in identificadores
    )

    return correspondencias / len(identificadores)


def atende_filtros(metadados: dict, filtros: dict) -> bool:
    """Compara os filtros; campos em lista (ex.: produto) usam "contém"."""

    for chave, valor in filtros.items():
        atual = metadados.get(chave)

        if isinstance(atual, list):
            if valor not in atual:
                return False
        elif atual != valor:
            return False

    return True


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

        if not atende_filtros(metadados, filtros):
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
