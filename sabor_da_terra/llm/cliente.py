"""Cliente único do Gemini: modelo por papel, troca AI Studio/Vertex AI por ambiente.

Segundo o docs/03: Flash-Lite para triagem e extração, Flash para a resposta
final e Gemini Embedding para o RAG. O retry de 429 é nosso (o do SDK fica
desligado) e o modo fixture grava/reproduz respostas para os testes.
"""

import os
import time
from enum import Enum
from pathlib import Path
from typing import Callable

from google import genai
from google.genai import types

MODO_PADRAO = "real"
MODOS_VALIDOS = ("real", "fixture")


class Papel(str, Enum):
    TRIAGEM = "triagem"
    RESPOSTA = "resposta"
    EMBEDDING = "embedding"


MODELOS_PADRAO: dict[Papel, str] = {
    Papel.TRIAGEM: "gemini-3.5-flash-lite",
    Papel.RESPOSTA: "gemini-3.8-flash",
    Papel.EMBEDDING: "gemini-embedding-001",
}

VARIAVEIS_MODELO: dict[Papel, str] = {
    Papel.TRIAGEM: "MODELO_TRIAGEM",
    Papel.RESPOSTA: "MODELO_RESPOSTA",
    Papel.EMBEDDING: "MODELO_EMBEDDING",
}


class FixtureAusenteError(RuntimeError):
    """Resposta não gravada para o par (papel, prompt, config) em modo fixture."""


class LLMClient:
    """Escolhe o modelo pelo papel e chama a Gemini API (ou Vertex AI)."""

    def __init__(
        self,
        modo: str | None = None,
        pasta_fixtures: Path | None = None,
        cliente: genai.Client | None = None,
        dormir: Callable[[float], None] = time.sleep,
        max_tentativas: int = 4,
    ) -> None:
        bruto = modo if modo is not None else os.getenv("LLM_MODO", MODO_PADRAO)
        self._modo = str(bruto).strip().lower()
        if self._modo not in MODOS_VALIDOS:
            raise ValueError(f"LLM_MODO inválido: {self._modo!r} (use 'real' ou 'fixture').")
        self._pasta_fixtures = pasta_fixtures or (
            Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "llm"
        )
        self._cliente = cliente
        self._dormir = dormir
        self._max_tentativas = max_tentativas

    @property
    def modo(self) -> str:
        return self._modo

    def modelo(self, papel: Papel) -> str:
        """Nome do modelo do papel; variável de ambiente vence o padrão."""
        return os.getenv(VARIAVEIS_MODELO[papel]) or MODELOS_PADRAO[papel]

    # ------------------------------------------------------------------ #
    # Configuração do backend (Gemini API ou Vertex AI)                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _usar_vertexai() -> bool:
        return os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().upper() in {"TRUE", "1", "YES"}

    @classmethod
    def _validar_configuracao(cls) -> None:
        if cls._usar_vertexai():
            projeto = os.getenv("GOOGLE_CLOUD_PROJECT")
            local = os.getenv("GOOGLE_CLOUD_LOCATION")
            if not projeto or not local:
                raise RuntimeError(
                    "GOOGLE_GENAI_USE_VERTEXAI=TRUE exige GOOGLE_CLOUD_PROJECT e "
                    "GOOGLE_CLOUD_LOCATION no .env, além de 'gcloud auth "
                    "application-default login'."
                )
        elif not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            raise RuntimeError(
                "GEMINI_API_KEY não definida. Copie .env.example para .env e preencha "
                "a chave restrita do AI Studio (ou rode com LLM_MODO=fixture para "
                "usar respostas gravadas)."
            )

    def _cliente_google(self) -> genai.Client:
        """Cria o cliente sob demanda; em modo fixture nunca é chamado."""
        if self._cliente is None:
            self._validar_configuracao()
            # Retry interno do SDK desligado: o retry 429 é implementado aqui.
            self._cliente = genai.Client(
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(attempts=1)
                )
            )
        return self._cliente

    # ------------------------------------------------------------------ #
    # Chamadas                                                           #
    # ------------------------------------------------------------------ #

    def gerar(self, papel: Papel, prompt: str, **config_geracao) -> str:
        """Gera texto com o modelo do papel e devolve o texto da resposta."""
        if self.modo == "fixture":
            raise FixtureAusenteError(
                "Modo fixture ainda não implementado nesta task (chega na próxima)."
            )
        resposta = self._cliente_google().models.generate_content(
            model=self.modelo(papel),
            contents=prompt,
            config=types.GenerateContentConfig(**config_geracao) if config_geracao else None,
        )
        return resposta.text
