"""Extração de metadados dos documentos da cooperativa."""

import re
from datetime import datetime
from functools import lru_cache

from sabor_da_terra.dados.carregamento import obter_base
from sabor_da_terra.dados.catalogo import APELIDOS
from sabor_da_terra.dados.normalizacao import chave


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


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acento e só letras/números separados por espaço."""

    return " ".join(re.sub(r"[^a-z0-9]+", " ", chave(texto)).split())


@lru_cache(maxsize=1)
def _nomes_produtos() -> list[tuple[str, str]]:
    """Nomes do catálogo (e apelidos) → produto base, do mais longo ao mais curto."""

    catalogo = obter_base().catalogo
    nomes = {_normalizar(base): base for base in catalogo.bases}
    nomes.update(
        {
            _normalizar(apelido): base
            for apelido, base in APELIDOS.items()
            if base in catalogo.bases
        }
    )

    return sorted(nomes.items(), key=lambda item: len(item[0]), reverse=True)


def identificar_produtos(texto: str) -> list[str]:
    """Produtos do catálogo citados no texto, pelo nome base."""

    restante = f" {_normalizar(texto)} "
    produtos = []

    for nome, base in _nomes_produtos():
        alvo = f" {nome} "

        if alvo in restante:
            if base not in produtos:
                produtos.append(base)

            # Tira o nome achado para "tomate cereja" não contar também "tomate".
            restante = restante.replace(alvo, " | ")

    return produtos


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
        "produto": identificar_produtos(documento["texto"]),
        "secao": "documento_completo",
    }

    return metadados


def enriquecer_metadados_trecho(
    texto: str,
    metadados_documento: dict,
) -> dict:
    """Enriquece metadados com informações específicas do trecho."""

    metadados = metadados_documento.copy()

    # Identifica os produtores mencionados no trecho.
    produtores = set(
        re.findall(
            r"\bP\d{3}\b",
            texto,
            flags=re.IGNORECASE,
        )
    )

    if len(produtores) == 1:
        metadados["produtor_id"] = next(iter(produtores)).upper()

    elif len(produtores) > 1:
        # Evita associar vários produtores a um único ID.
        metadados["produtor_id"] = None

    # Produtos citados no trecho; sem citação, herda os do documento.
    metadados["produto"] = (
        identificar_produtos(texto)
        or list(metadados_documento.get("produto", []))
    )

    return metadados
