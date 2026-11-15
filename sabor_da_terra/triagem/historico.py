"""Consulta ao histórico para gerar hipóteses de pedidos ambíguos."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import unicodedata

import pandas as pd


CAMINHO_FINANCEIRO = Path("data/financeiro.csv")
CAMINHO_LOTES = Path("data/lotes.csv")


def normalizar_texto(texto: str) -> str:
    """Remove acentos e normaliza espaços e letras."""

    texto = unicodedata.normalize("NFKD", texto.casefold())

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return " ".join(texto.split())


def identificar_historico(
    comprador: str,
    data_referencia: str,
    expressao: str = "ultima_vez",
    caminho_financeiro: Path = CAMINHO_FINANCEIRO,
    caminho_lotes: Path = CAMINHO_LOTES,
) -> dict:
    """Gera hipóteses a confirmar com base em registros anteriores."""

    referencia = date.fromisoformat(data_referencia)

    if expressao not in {"ultima_vez", "de_sempre"}:
        raise ValueError("Expressão histórica não reconhecida.")

    registros = []

    fontes = [
        (
            caminho_financeiro,
            "data",
            "id_transacao",
        ),
        (
            caminho_lotes,
            "data_entrega",
            "lote_id",
        ),
    ]

    comprador_normalizado = normalizar_texto(comprador)

    for caminho, coluna_data, coluna_id in fontes:
        if not caminho.exists():
            continue

        tabela = pd.read_csv(caminho)

        for _, linha in tabela.iterrows():
            nome_historico = normalizar_texto(
                str(linha.get("comprador", ""))
            )

            if not nome_historico:
                continue

            if (
                nome_historico not in comprador_normalizado
                and comprador_normalizado not in nome_historico
            ):
                continue

            data_registro = pd.to_datetime(
                linha.get(coluna_data),
                errors="coerce",
            )

            if pd.isna(data_registro):
                continue

            data_registro = data_registro.date()

            if data_registro >= referencia:
                continue

            registros.append({
                "produto": linha["produto"],
                "quantidade_kg": float(linha["quantidade_kg"]),
                "data": data_registro.isoformat(),
                "fonte": str(caminho),
                "registro_id": str(linha[coluna_id]),
                "confirmado": False,
            })

    registros.sort(
        key=lambda registro: registro["data"],
        reverse=True,
    )

    if not registros:
        return {
            "comprador": comprador,
            "expressao": expressao,
            "hipoteses": [],
            "requer_confirmacao": True,
            "aviso": (
                "Nenhum histórico correspondente foi encontrado. "
                "Solicitar esclarecimento ao comprador."
            ),
        }

    if expressao == "ultima_vez":
        data_mais_recente = registros[0]["data"]

        hipoteses = [
            registro
            for registro in registros
            if registro["data"] == data_mais_recente
        ]
    else:
        # Mantém os registros encontrados como evidências,
        # sem assumir que o mais frequente foi solicitado.
        hipoteses = registros

    return {
        "comprador": comprador,
        "expressao": expressao,
        "hipoteses": hipoteses,
        "requer_confirmacao": True,
        "aviso": (
            "Hipótese baseada no histórico. "
            "Confirmar produto e quantidade com o comprador."
        ),
    }
