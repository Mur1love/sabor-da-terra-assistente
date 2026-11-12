import re

from sabor_da_terra.rag.metadados import extrair_metadados


def dividir_em_trechos(documento: dict) -> list[dict]:
    """Divide o documento em blocos, preservando sua origem."""

    texto = documento["texto"]

    blocos = re.split(r"\n\s*\n", texto)

    metadados = extrair_metadados(documento)
    trechos = []

    for indice, bloco in enumerate(blocos):
        bloco = bloco.strip()

        if not bloco:
            continue

        # Ignora blocos compostos apenas por separadores.
        if re.fullmatch(r"[-=_\s]+", bloco):
            continue

        trecho = {
            "texto": bloco,
            "metadados": {
                **metadados,
                "secao": f"bloco_{indice + 1}",
            },
        }

        trechos.append(trecho)

    return trechos
