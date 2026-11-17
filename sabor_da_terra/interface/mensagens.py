"""Mensagens da interface: fontes citadas no texto e erros em português amigável."""

from __future__ import annotations

import re

from sabor_da_terra.llm.cliente import FixtureAusenteError

# As citações viajam no texto como "[fonte: arquivo]" (regra 3 do prompt de
# sistema da #12); o motor de regras também junta arquivos com "; ".
FONTE_RE = re.compile(r"\[fonte:\s*([^\]]+)\]")

MENSAGEM_429 = (
    "⚠️ Cota da API atingida (erro 429). O limite gratuito do Gemini é por minuto — "
    "aguarde um instante e envie a mensagem de novo."
)
MENSAGEM_FIXTURE = (
    "⚠️ Modo fixture sem resposta gravada para esta mensagem. Rode uma vez com "
    "`LLM_MODO=gravar` para gravar a resposta (veja o README), ou troque para o modo real."
)
MENSAGEM_GENERICA = (
    "⚠️ Não consegui responder agora. Tente de novo em instantes; "
    "se persistir, verifique a conexão ou o modo do LLM na barra lateral."
)


def extrair_fontes(texto: str) -> list[str]:
    """Arquivos citados no texto da resposta, na ordem em que aparecem, sem repetição.

    Vários arquivos num mesmo marcador (separados por ";") viram entradas
    individuais — é assim que as fontes chegam das regras de triagem.
    """
    fontes: list[str] = []
    for grupo in FONTE_RE.findall(str(texto or "")):
        for arquivo in grupo.split(";"):
            arquivo = arquivo.strip()
            if arquivo and arquivo not in fontes:
                fontes.append(arquivo)
    return fontes


def mensagem_de_erro(erro: BaseException) -> str:
    """Mensagem amigável para a tela — nunca stack trace."""
    if getattr(erro, "code", None) == 429:
        return MENSAGEM_429
    if isinstance(erro, FixtureAusenteError):
        return MENSAGEM_FIXTURE
    return MENSAGEM_GENERICA
