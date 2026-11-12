"""Cliente único do Gemini: modelo por papel, troca AI Studio/Vertex AI por ambiente.

Segundo o docs/03: Flash-Lite para triagem e extração, Flash para a resposta
final e Gemini Embedding para o RAG. O retry de 429/503 é nosso (o do SDK fica
desligado). Há três modos: `real` só chama a API (nada é gravado — a demo e a
triagem não poluem o repositório), `gravar` chama e grava a resposta completa
no fixture, e `fixture` reproduz o gravado sem nenhuma chamada.
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
MODOS_VALIDOS = ("real", "fixture", "gravar")


def _serializar_para_hash(obj: Any) -> Any:
    """Converte prompt/config para forma estável e JSON-serializável.

    Aceita os tipos do SDK (pydantic — ex.: `types.Schema` no `response_schema`)
    e o histórico em lista (etapa 12); tudo vira texto determinístico.
    """
    if obj is None or isinstance(obj, (str, bool, int, float)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _serializar_para_hash(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serializar_para_hash(v) for v in obj]
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        return _serializar_para_hash(dump(mode="json", exclude_none=True))
    return str(obj)


class Papel(str, Enum):
    TRIAGEM = "triagem"
    RESPOSTA = "resposta"
    EMBEDDING = "embedding"


MODELOS_PADRAO: dict[Papel, str] = {
    Papel.TRIAGEM: "gemini-3.5-flash-lite",
    Papel.RESPOSTA: "gemini-3.8-flash",
    Papel.EMBEDDING: "gemini-embedding-001",
}

# Nome da variável fala do PAPEL, não do modelo: trocar o modelo da triagem
# não pode deixar o nome da variável mentindo.
VARIAVEIS_MODELO: dict[Papel, str] = {
    Papel.TRIAGEM: "GEMINI_MODELO_TRIAGEM",
    Papel.RESPOSTA: "GEMINI_MODELO_RESPOSTA",
    # EMBEDDING já fala do papel (não de modelo) — decisão do mantenedor.
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
            raise ValueError(
                f"LLM_MODO inválido: {self._modo!r} (use 'real', 'gravar' ou 'fixture')."
            )
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
            # Retry interno do SDK desligado: o retry 429/503 é implementado aqui.
            # Timeout de 60s: o padrão do SDK é None (sem prazo) e um stall do
            # servidor deixaria a chamada bloqueada para sempre (vi no smoke).
            self._cliente = genai.Client(
                http_options=types.HttpOptions(
                    timeout=60_000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                )
            )
        return self._cliente

    # ------------------------------------------------------------------ #
    # Fixture (gravação e replay de respostas reais)                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hash_fixture(papel: Papel, modelo: str, prompt: Any, config: dict | None) -> str:
        """Chave estável do par (papel, modelo, prompt, config) — 16 hex."""
        conteudo = json.dumps(
            {
                "papel": papel.value,
                "modelo": modelo,
                "prompt": _serializar_para_hash(prompt),
                "config": _serializar_para_hash(config or {}),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:16]

    def _ler_fixture(self, caminho: Path) -> dict[str, Any]:
        if not caminho.exists():
            raise FixtureAusenteError(
                f"Nenhuma fixture para este papel/prompt em {caminho}. "
                "Rode uma vez com LLM_MODO=gravar para gravar a resposta."
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
        """Executa a chamada HTTP repetindo apenas erros transitórios com backoff.

        429 (cota) e 503 (modelo sobrecarregado) são transitórios; o limite do
        Flash é por minuto, então as esperas (10s, 20s, 40s) somam mais de um
        minuto até a última tentativa, cobrindo a janela de cota.
        """
        erros_transitorios = (429, 503)
        tentativa = 1
        while True:
            try:
                return acao()
            except Exception as exc:
                if getattr(exc, "code", None) not in erros_transitorios or tentativa >= self._max_tentativas:
                    raise
                self._dormir(min(60.0, 10.0 * (2 ** (tentativa - 1))))
                tentativa += 1

    def gerar(
        self, papel: Papel, prompt: str | list, **config_geracao
    ) -> types.GenerateContentResponse:
        """Gera com o modelo do papel e devolve a resposta completa do SDK.

        `prompt` pode ser uma string ou o histórico da conversa em lista
        (etapa 12). `config_geracao` aceita o que o SDK aceita, inclusive
        `response_schema` para resposta em JSON (etapa 9). O texto e os
        function calls são lidos pelo chamador (`resposta.text`,
        `resposta.function_calls`) — resposta sem texto é válida (etapa 12).
        """
        modelo = self.modelo(papel)
        chave = self._hash_fixture(papel, modelo, prompt, config_geracao or None)
        caminho = self._pasta_fixtures / papel.value / f"{chave}.json"

        if self.modo == "fixture":
            return types.GenerateContentResponse.model_validate(
                self._ler_fixture(caminho)["resposta"]
            )

        resposta = self._executar_com_retry(
            lambda: self._cliente_google().models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(**config_geracao) if config_geracao else None,
            )
        )
        self._contar_chamada(modelo)
        if self.modo == "gravar":
            self._gravar_fixture(
                caminho,
                {
                    "papel": papel.value,
                    "modelo": modelo,
                    "prompt_sha256": chave,
                    "resposta": resposta.to_json_dict(),
                },
            )
        return resposta

    def embedar(self, texto: str) -> list[float]:
        """Gera o embedding do texto com o modelo de embeddings do docs/03."""
        modelo = self.modelo(Papel.EMBEDDING)
        chave = self._hash_fixture(Papel.EMBEDDING, modelo, texto, None)
        caminho = self._pasta_fixtures / Papel.EMBEDDING.value / f"{chave}.json"

        if self.modo == "fixture":
            return [float(v) for v in self._ler_fixture(caminho)["valores"]]

        resposta = self._executar_com_retry(
            lambda: self._cliente_google().models.embed_content(model=modelo, contents=texto)
        )
        valores = [float(v) for v in resposta.embeddings[0].values]
        self._contar_chamada(modelo)
        if self.modo == "gravar":
            self._gravar_fixture(
                caminho,
                {
                    "papel": Papel.EMBEDDING.value,
                    "modelo": modelo,
                    "prompt_sha256": chave,
                    "valores": valores,
                },
            )
        return valores
