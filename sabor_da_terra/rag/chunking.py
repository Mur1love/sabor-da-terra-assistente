"""Divisão dos documentos em trechos com metadados enriquecidos."""

import re

from sabor_da_terra.dados.normalizacao import chave
from sabor_da_terra.rag.metadados import (
    extrair_metadados,
    enriquecer_metadados_trecho,
)


# Trechos menores que isso ("RESULTADO GERAL: APROVADO") não têm contexto
# sozinhos e são colados ao trecho seguinte.
TAMANHO_MINIMO = 120

PADRAO_PRODUTOR = re.compile(
    r"(?m)^\s*\d+\.\s+(P\d{3})\s+-\s+"
)



def identificar_secao(bloco: str) -> str | None:
    """Reconhece um título em maiúsculas na primeira linha do bloco.

    "NORMA APLICÁVEL:" → "norma_aplicavel"
    "RESULTADO DA AUDITORIA (18/03/2025):" → "resultado_da_auditoria"
    "VIGÊNCIA: 01/03/2026 a 28/02/2027" → "vigencia"
    """

    primeira_linha = bloco.splitlines()[0].strip()
    rotulo = primeira_linha.split(":", 1)[0]
    rotulo = re.sub(r"\([^)]*\)", "", rotulo).strip()

    if (
        len(rotulo) < 3
        or not any(letra.isalpha() for letra in rotulo)
        or rotulo != rotulo.upper()
        or any(letra.isdigit() for letra in rotulo)
        or rotulo.startswith("-")
    ):
        return None

    return re.sub(r"[^a-z0-9]+", "_", chave(rotulo)).strip("_")


def dividir_blocos(texto: str) -> list[str]:
    """Divide por linhas em branco, preservando blocos internos."""

    blocos = []

    for bloco in re.split(r"\n\s*\n", texto):
        # Remove as linhas de "=====" e "_____", que só enfeitam.
        bloco = re.sub(r"(?m)^[-=_\s]+$", "", bloco).strip()

        if bloco:
            blocos.append(bloco)

    return blocos


def dividir_produtores_vistoriados(bloco: str) -> list[str]:
    """Separa produtores numerados em trechos individuais."""

    correspondencias = list(PADRAO_PRODUTOR.finditer(bloco))

    if not correspondencias:
        return [bloco]

    partes = []

    cabecalho = bloco[:correspondencias[0].start()].strip()

    if cabecalho:
        partes.append(cabecalho)

    for indice, correspondencia in enumerate(correspondencias):
        inicio = correspondencia.start()

        if indice + 1 < len(correspondencias):
            fim = correspondencias[indice + 1].start()
        else:
            fim = len(bloco)

        parte = bloco[inicio:fim].strip()

        if parte:
            partes.append(parte)

    return partes


def juntar_trechos_curtos(
    partes: list[tuple[str, str]],
    minimo: int = TAMANHO_MINIMO,
) -> list[tuple[str, str]]:
    """Cola cada trecho curto no seguinte (ou no anterior, se for o último)."""

    resultado = []
    pendente = None

    for pedaco, secao in partes:
        if pendente:
            # O trecho juntado fica com a seção do primeiro pedaço: o
            # conteúdo dominante é o do meio, e rótulos curtos do fim
            # ("RESULTADO GERAL: APROVADO") não devem rotular trechos de
            # conformidade (ex.: NC-002). Em troca, alguns títulos deixam
            # de existir como metadado de seção — o texto do trecho e o
            # embedding continuam carregando o conteúdo inteiro.
            pedaco = f"{pendente[0]}\n\n{pedaco}"
            secao = pendente[1]
            pendente = None

        if len(pedaco) < minimo:
            pendente = (pedaco, secao)
            continue

        resultado.append((pedaco, secao))

    if pendente:
        if resultado:
            anterior, secao = resultado[-1]
            resultado[-1] = (f"{anterior}\n\n{pendente[0]}", secao)
        else:
            resultado.append(pendente)

    return resultado


def dividir_em_trechos(documento: dict) -> list[dict]:
    """Divide o documento preservando seções e contexto."""

    metadados_documento = extrair_metadados(documento)

    partes = []
    secao_atual = "introducao"

    for bloco in dividir_blocos(documento["texto"]):
        # O primeiro bloco é o título do documento: fica como "introducao".
        if partes:
            secao_atual = identificar_secao(bloco) or secao_atual

        if secao_atual == "produtores_vistoriados":
            pedacos = dividir_produtores_vistoriados(bloco)
        else:
            pedacos = [bloco]

        partes.extend(
            (pedaco, secao_atual)
            for pedaco in pedacos
            if pedaco.strip()
        )

    trechos = []

    for texto, secao in juntar_trechos_curtos(partes):
        metadados = enriquecer_metadados_trecho(
            texto,
            metadados_documento,
        )
        metadados["secao"] = secao

        trechos.append({"texto": texto, "metadados": metadados})

    return trechos
