"""Integração dos embeddings documentais com cache persistente."""

from pathlib import Path

from sabor_da_terra.rag.cache import CacheEmbeddings
from sabor_da_terra.rag.sanitizacao import sanitizar_texto


MODELO_EMBEDDING = "gemini-embedding-001"


class GeradorEmbeddings:
    """Gera embeddings, reutilizando os vetores armazenados."""

    def __init__(
        self,
        cliente,
        caminho_cache: Path,
        modelo: str = MODELO_EMBEDDING,
    ):
        self.cliente = cliente
        self.cache = CacheEmbeddings(caminho_cache)
        self.modelo = modelo

    def gerar(self, texto: str) -> list[float]:
        """Sanitiza o texto e consulta o cache antes de gerar o vetor."""

        texto_seguro = sanitizar_texto(texto)

        if not texto_seguro.strip():
            raise ValueError(
                "Não é possível gerar embedding de texto vazio."
            )

        embedding = self.cache.obter(
            texto_seguro,
            self.modelo,
        )

        if embedding is not None:
            return embedding

        embedding = self.cliente.embedar(texto_seguro)

        self.cache.salvar(
            texto_seguro,
            self.modelo,
            embedding,
        )

        return embedding
