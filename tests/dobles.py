from typing import Any

from google.genai import types


class Erro429(Exception):
    code = 429


class Erro503(Exception):
    code = 503


class Erro504(Exception):
    code = 504


class ModeloFake:
    """Doble do `models` do SDK que devolve respostas REAIS do SDK.

    Resposta de texto e/ou function_call — assim `to_json_dict()` (gravar) e
    `model_validate` (replay) exercitam o mesmo caminho da API verdadeira.
    """

    def __init__(
        self,
        texto: str | None = "resposta fake",
        function_call: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        falhas_429: int = 0,
    ):
        self.texto = texto
        self.function_call = function_call
        self.embedding = embedding or [0.1, 0.2]
        self.falhas_429 = falhas_429
        self.chamadas: list[tuple[str, str, Any]] = []

    def _resposta(self) -> types.GenerateContentResponse:
        partes = []
        if self.texto is not None:
            partes.append({"text": self.texto})
        if self.function_call is not None:
            partes.append({"functionCall": self.function_call})
        return types.GenerateContentResponse.model_validate(
            {"candidates": [{"content": {"role": "model", "parts": partes}}]}
        )

    def generate_content(self, *, model: str, contents: Any, config: Any = None):
        self.chamadas.append(("gerar", model, contents))
        if self.falhas_429:
            self.falhas_429 -= 1
            raise Erro429()
        return self._resposta()

    def embed_content(self, *, model: str, contents: Any, config: Any = None):
        self.chamadas.append(("embedar", model, contents))
        if self.falhas_429:
            self.falhas_429 -= 1
            raise Erro429()
        return types.EmbedContentResponse.model_validate(
            {"embeddings": [{"values": self.embedding}]}
        )


class ClienteFake:
    def __init__(self, modelo: ModeloFake):
        self.models = modelo
