"""Carregamento dos documentos da cooperativa Sabor da Terra."""

from pathlib import Path

PASTAS_DOCUMENTAIS = {
    "certificacoes": "certificacao",
    "contratos": "contrato",
    "fichas_tecnicas": "ficha_tecnica",
}


def carregar_documentos(diretorio_base: Path) -> list[dict]:
    """Carrega os documentos TXT e identifica sua origem."""

    documentos = []

    for pasta, tipo_documento in PASTAS_DOCUMENTAIS.items():
        caminho_pasta = diretorio_base / pasta

        if not caminho_pasta.is_dir():
            raise FileNotFoundError(
                f"Pasta documental não encontrada: {caminho_pasta}"
            )

        for arquivo in sorted(caminho_pasta.glob("*.txt")):
            texto = arquivo.read_text(encoding="utf-8")

            if not texto.strip():
                raise ValueError(
                    f"Documento vazio: {arquivo.name}"
                )

            documentos.append({
                "arquivo": arquivo.name,
                "tipo_documento": tipo_documento,
                "caminho": str(
                    arquivo.relative_to(diretorio_base)
                ),
                "texto": texto,
            })

    return documentos
