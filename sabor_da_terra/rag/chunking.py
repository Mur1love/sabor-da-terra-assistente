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
}


def identificar_secao(bloco: str) -> str | None:
    """Identifica a seção a partir do início do bloco."""

    primeira_linha = bloco.splitlines()[0].strip().upper()

    for secao in sorted(SECOES_CONHECIDAS, key=len, reverse=True):
        if primeira_linha.startswith(secao):
            return secao.lower().replace(" ", "_")

    return None


def dividir_em_trechos(documento: dict) -> list[dict]:
    """Divide o documento em blocos, preservando origem e contexto."""

    texto = documento["texto"]
    blocos = re.split(r"\n\s*\n", texto)

    metadados_documento = extrair_metadados(documento)
    trechos = []
    secao_atual = "introducao"

    for bloco in blocos:
        bloco = bloco.strip()

        if not bloco:
            continue

        # Ignora blocos formados apenas por separadores.
        if re.fullmatch(r"[-=_\s]+", bloco):
            continue

        nova_secao = identificar_secao(bloco)

        if nova_secao:
            secao_atual = nova_secao

        # Identifica informações específicas deste trecho,
        # como produtor_id e produto.
        metadados_trecho = enriquecer_metadados_trecho(
            bloco,
            metadados_documento,
        )

        trecho = {
            "texto": bloco,
            "metadados": {
                **metadados_trecho,
                "secao": secao_atual,
            },
        }

        trechos.append(trecho)

    return trechos
