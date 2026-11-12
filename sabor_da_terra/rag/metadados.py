"""Extração de metadados dos documentos da cooperativa."""

import re
from datetime import datetime


def extrair_produtor_id(nome_arquivo: str) -> str | None:
    """Identifica o código do produtor no nome do arquivo."""

    resultado = re.search(
        r"(?:^|_)P(\d{3})(?:_|\.|$)",
        nome_arquivo,
        flags=re.IGNORECASE,
    )

    if resultado:
        return f"P{resultado.group(1)}"

    return None


def extrair_data_validade(texto: str) -> str | None:
    """Extrai a data de validade explícita do documento."""

    resultado = re.search(
        r"Data de Validade:\s*(\d{2}/\d{2}/\d{4})",
        texto,
        flags=re.IGNORECASE,
    )

    if not resultado:
        return None

    data = datetime.strptime(
        resultado.group(1), "%d/%m/%Y"
    )

    return data.date().isoformat()


def extrair_metadados(documento: dict) -> dict:
    """Enriquece o documento com metadados identificáveis."""

    metadados = {
        "arquivo": documento["arquivo"],
        "tipo_documento": documento["tipo_documento"],
        "caminho": documento["caminho"],
        "produtor_id": extrair_produtor_id(
            documento["arquivo"]
        ),
        "data_validade": extrair_data_validade(
            documento["texto"]
        ),
        "secao": "documento_completo",
    }

    return metadados