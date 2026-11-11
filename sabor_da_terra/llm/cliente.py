"""Cliente único do Gemini: modelo por papel, troca AI Studio/Vertex AI por ambiente.

Segundo o docs/03: Flash-Lite para triagem e extração, Flash para a resposta
final e Gemini Embedding para o RAG. O retry de 429 é nosso (o do SDK fica
desligado) e o modo fixture grava/reproduz respostas para os testes.
"""

import hashlib
import json
import os
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable

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
    Papel.TRIAGEM: "GEMINI_MODEL_FLASH_LITE",
    Papel.RESPOSTA: "GEMINI_MODEL_FLASH",
    Papel.EMBEDDING: "GEMINI_MODEL_EMBEDDING",
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
        self._chamadas: dict[str, int] = {}

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
    # Fixture (gravação e replay de respostas reais)                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hash_fixture(papel: Papel, modelo: str, prompt: str, config: dict | None) -> str:
        """Chave estável do par (papel, modelo, prompt, config) — 16 hex."""
        conteudo = json.dumps(
            {"papel": papel.value, "modelo": modelo, "prompt": prompt, "config": config or {}},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:16]

    def _caminho_fixture(self, papel: Papel, modelo: str, prompt: str, config: dict | None) -> Path:
        return self._pasta_fixtures / papel.value / f"{self._hash_fixture(papel, modelo, prompt, config)}.json"

    def _ler_fixture(self, caminho: Path) -> dict[str, Any]:
        if not caminho.exists():
            raise FixtureAusenteError(
                f"Nenhuma fixture para este papel/prompt em {caminho}. "
                "Rode uma vez com LLM_MODO=real para gravar a resposta."
            )
        return json.loads(caminho.read_text(encoding="utf-8"))

    def _gravar_fixture(self, caminho: Path, dados: dict[str, Any]) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _contar_chamada(self, modelo: str) -> None:
        self._chamadas[modelo] = self._chamadas.get(modelo, 0) + 1

    def chamadas_por_modelo(self) -> dict[str, int]:
        """Chamadas bem-sucedidas à API por modelo (replay de fixture não conta)."""
        return dict(self._chamadas)

    # ------------------------------------------------------------------ #
    # Chamadas                                                           #
    # ------------------------------------------------------------------ #

    def _executar_com_retry(self, acao: Callable[[], Any]) -> Any:
        """Executa a chamada HTTP repetindo apenas erro 429 com backoff."""
        tentativa = 1
        while True:
            try:
                return acao()
            except Exception as exc:
                if getattr(exc, "code", None) != 429 or tentativa >= self._max_tentativas:
                    raise
                self._dormir(min(30.0, 1.0 * (2 ** (tentativa - 1))))
                tentativa += 1

    def gerar(self, papel: Papel, prompt: str, **config_geracao) -> str:
        """Gera texto com o modelo do papel e devolve o texto da resposta."""
        modelo = self.modelo(papel)
        caminho = self._caminho_fixture(papel, modelo, prompt, config_geracao or None)

        if self.modo == "fixture":
            return str(self._ler_fixture(caminho)["resposta"])

        resposta = self._executar_com_retry(
            lambda: self._cliente_google().models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(**config_geracao) if config_geracao else None,
            )
        )
        texto = resposta.text
        if not texto:
            raise RuntimeError(
                "Resposta sem texto do modelo (possível bloqueio de segurança ou "
                "falha silenciosa). Revise o prompt/configuração antes de repetir "
                "a chamada — nada foi gravado em fixture nem contado."
            )
        self._gravar_fixture(
            caminho,
            {
                "papel": papel.value,
                "modelo": modelo,
                "prompt_sha256": self._hash_fixture(papel, modelo, prompt, config_geracao or None),
                "resposta": texto,
            },
        )
        self._contar_chamada(modelo)
        return texto

    def embedar(self, texto: str) -> list[float]:
        """Gera o embedding do texto com o modelo de embeddings do docs/03."""
        modelo = self.modelo(Papel.EMBEDDING)
        caminho = self._caminho_fixture(Papel.EMBEDDING, modelo, texto, None)

        if self.modo == "fixture":
            return [float(v) for v in self._ler_fixture(caminho)["valores"]]

        resposta = self._executar_com_retry(
            lambda: self._cliente_google().models.embed_content(model=modelo, contents=texto)
        )
        valores = [float(v) for v in resposta.embeddings[0].values]
        self._gravar_fixture(
            caminho,
            {
                "papel": Papel.EMBEDDING.value,
                "modelo": modelo,
                "prompt_sha256": self._hash_fixture(Papel.EMBEDDING, modelo, texto, None),
                "valores": valores,
            },
        )
        self._contar_chamada(modelo)
        return valores
