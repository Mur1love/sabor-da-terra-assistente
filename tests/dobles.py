from types import SimpleNamespace


class ModeloFake:
    def __init__(self, texto: str = "resposta fake", embedding: list[float] | None = None):
        self.texto = texto
        self.embedding = embedding or [0.1, 0.2]
        self.chamadas: list[tuple[str, str, str]] = []

    def generate_content(self, *, model: str, contents: str, config=None):
        self.chamadas.append(("gerar", model, contents))
        return SimpleNamespace(text=self.texto)

    def embed_content(self, *, model: str, contents: str, config=None):
        self.chamadas.append(("embedar", model, contents))
        return SimpleNamespace(embeddings=[SimpleNamespace(values=self.embedding)])


class ClienteFake:
    def __init__(self, modelo: ModeloFake):
        self.models = modelo
