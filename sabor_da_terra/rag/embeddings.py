"""Integração dos embeddings documentais com cache persistente."""

from pathlib import Path

from sabor_da_terra.llm.cliente import Papel
from sabor_da_terra.rag.cache import CacheEmbeddings


MODELO_EMBEDDING = "gemini-embedding-001"


class GeradorEmbeddings:
    """Gera embeddings, reutilizando os vetores armazenados."""

    def __init__(
        self,
        cliente,
        caminho_cache: Path,
        modelo: str | None = None,
    ):
        self.cliente = cliente
        self.cache = CacheEmbeddings(caminho_cache)

        # Identifica automaticamente o modelo configurado no LLMClient.
        if modelo is not None:
            self.modelo = modelo

        elif callable(getattr(cliente, "modelo", None)):
            self.modelo = cliente.modelo(Papel.EMBEDDING)

        else:
            # Compatibilidade com clientes simulados dos testes.
            self.modelo = MODELO_EMBEDDING

    def gerar(self, texto_seguro: str) -> list[float]:
        """Consulta o cache antes de gerar o vetor.

        O texto já chega sanitizado (ver preparar_nos).
        """

        if not texto_seguro.strip():
            raise ValueError(
                "Não é possível gerar embedding de texto vazio."
            )

        # 1. Verifica se o embedding já está armazenado.
        embedding = self.cache.obter(
            texto_seguro,
            self.modelo,
        )

        if embedding is not None:
            return embedding

        # 2. Gera um novo embedding utilizando o cliente existente.
        embedding = self.cliente.embedar(texto_seguro)

        # 3. Salva o vetor para reutilização nas próximas execuções.
        self.cache.salvar(
            texto_seguro,
            self.modelo,
            embedding,
        )

        return embedding
