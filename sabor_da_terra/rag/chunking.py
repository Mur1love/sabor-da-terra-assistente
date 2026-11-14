"""Divisão dos documentos em trechos com metadados enriquecidos."""

import re

from sabor_da_terra.rag.metadados import (
    extrair_metadados,
    enriquecer_metadados_trecho,
)


SECOES_CONHECIDAS = {
    "DADOS DO PRODUTOR",
    "PRODUTOS QUE ERAM CERTIFICADOS",
    "ESTABELECIMENTO INSPECIONADO",
    "PRODUTORES VISTORIADOS",
    "INSPEÇÃO DO DEPÓSITO CENTRAL",
    "NÃO CONFORMIDADES",
    "CONDIÇÕES OBRIGATÓRIAS",
    "ITENS CONTRATADOS",
    "FUNDAMENTAÇÃO LEGAL",
    "NUTRICIONISTA RESPONSÁVEL",
    "FISCAIS DO CONTRATO",
    "OBJETO",
    "VIGÊNCIA",
    "PAGAMENTO",
}

PADRAO_PRODUTOR = re.compile(
    r"(?m)^\s*\d+\.\s+(P\d{3})\s+-\s+"
)



def identificar_secao(bloco: str) -> str | None:
    """Identifica a seção a partir do início do bloco."""

    primeira_linha = bloco.splitlines()[0].strip().upper()

    for secao in sorted(SECOES_CONHECIDAS, key=len, reverse=True):
        if primeira_linha.startswith(secao):
            return secao.lower().replace(" ", "_")

    return None



def dividir_blocos(texto: str) -> list[str]:
    """Divide por linhas em branco, preservando blocos internos."""

    return [
        bloco.strip()
        for bloco in re.split(r"\n\s*\n", texto)
        if bloco.strip()
    ]


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


def dividir_em_trechos(documento: dict) -> list[dict]:
    """Divide o documento preservando seções e contexto."""

    blocos = dividir_blocos(documento["texto"])

    metadados_documento = extrair_metadados(documento)

    trechos = []
    secao_atual = "introducao"

    for bloco in blocos:
        if re.fullmatch(r"[-=_\s]+", bloco):
            continue

        nova_secao = identificar_secao(bloco)

        if nova_secao:
            secao_atual = nova_secao

        if secao_atual == "produtores_vistoriados":
            partes = dividir_produtores_vistoriados(bloco)
        else:
            partes = [bloco]

        for parte in partes:
            if not parte.strip():
                continue

            metadados_trecho = enriquecer_metadados_trecho(
                parte,
                metadados_documento,
            )

            trechos.append(
                {
                    "texto": parte,
                    "metadados": {
                        **metadados_trecho,
                        "secao": secao_atual,
                    },
                }
            )

    return trechos
