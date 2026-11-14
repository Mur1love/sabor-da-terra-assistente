"""Cache persistente de embeddings documentais."""

import hashlib
import json
from pathlib import Path


class CacheEmbeddings:
    """Armazena embeddings usando hash do conteúdo."""

    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self.dados = self._carregar()
        self._alterado = False

    def _carregar(self) -> dict:
        if not self.caminho.exists():
            return {}

        with self.caminho.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    @staticmethod
    def gerar_chave(texto: str, modelo: str) -> str:
        conteudo = f"{modelo}\0{texto}"

        return hashlib.sha256(
            conteudo.encode("utf-8")
        ).hexdigest()

    def obter(self, texto: str, modelo: str) -> list[float] | None:
        chave = self.gerar_chave(texto, modelo)
        return self.dados.get(chave)

    def salvar(
        self,
        texto: str,
        modelo: str,
        embedding: list[float],
    ) -> None:
        """Guarda em memória; o arquivo só é escrito em gravar()."""

        chave = self.gerar_chave(texto, modelo)
        self.dados[chave] = embedding
        self._alterado = True

    def gravar(self) -> None:
        """Escreve o cache no disco uma vez, se algo mudou."""

        if not self._alterado:
            return

        self.caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporario = self.caminho.with_suffix(".tmp")

        with temporario.open("w", encoding="utf-8") as arquivo:
            json.dump(self.dados, arquivo)

        temporario.replace(self.caminho)
        self._alterado = False
