from types import SimpleNamespace


class Erro429(Exception):
    code = 429


class ModeloFake:
    def __init__(
        self,
        texto: str = "resposta fake",
        embedding: list[float] | None = None,
        falhas_429: int = 0,
    ):
        self.texto = texto
        self.embedding = embedding or [0.1, 0.2]
        self.falhas_429 = falhas_429
        self.chamadas: list[tuple[str, str, str]] = []

    def generate_content(self, *, model: str, contents: str, config=None):
        self.chamadas.append(("gerar", model, contents))
        if self.falhas_429:
            self.falhas_429 -= 1
            raise Erro429()
        return SimpleNamespace(text=self.texto)

    def embed_content(self, *, model: str, contents: str, config=None):
        self.chamadas.append(("embedar", model, contents))
        if self.falhas_429:
            self.falhas_429 -= 1
            raise Erro429()
        return SimpleNamespace(embeddings=[SimpleNamespace(values=self.embedding)])


class ClienteFake:
    def __init__(self, modelo: ModeloFake):
        self.models = modelo
