"""Mensagens da interface: fontes da resposta e erros em português amigável."""

from __future__ import annotations

import re

from sabor_da_terra.llm.cliente import FixtureAusenteError

# As citações viajam no texto como "[fonte: arquivo]" (regra 3 do prompt de
# sistema da #12); o motor de regras também junta arquivos com "; ".
FONTE_RE = re.compile(r"\[fonte:\s*([^\]]+)\]")
# Vários arquivos num marcador: "; " (regras de triagem) ou ", " (o modelo
# também escreve assim). Nome de arquivo do dataset não tem vírgula.
SEPARADOR_FONTES_RE = re.compile(r"\s*[;,]\s*")
# Textos prontos (resumo do produtor, relatórios) fecham com "Fontes: a; b."
LINHA_FONTES_RE = re.compile(r"^\s*Fontes:\s*(.+?)\.?\s*$", re.MULTILINE)

MENSAGEM_429 = (
    "Cota da API atingida (erro 429). O limite gratuito do Gemini é por minuto — "
    "aguarde um instante e envie a mensagem de novo."
)
MENSAGEM_FIXTURE = (
    "Modo fixture sem resposta gravada para esta mensagem. Rode uma vez com "
    "`LLM_MODO=gravar` para gravar a resposta (veja o README), ou troque para o modo real."
)
MENSAGEM_SEM_CHAVE = (
    "Chave da API não configurada. Preencha `GEMINI_API_KEY` no `.env` (veja o README) "
    "e reinicie a interface, ou use os atalhos da barra lateral, que funcionam sem a API."
)
MENSAGEM_GENERICA = (
    "Não consegui responder agora. Tente de novo em instantes; "
    "se persistir, verifique a conexão ou o modo do LLM na barra lateral."
)


def _nome_do_arquivo(fonte: str) -> str:
    """Forma canônica para comparar e exibir: sem o prefixo `data/`."""
    fonte = fonte.strip()
    return fonte[len("data/"):] if fonte.startswith("data/") else fonte


def _adicionar(fontes: list[str], candidatas: list[str]) -> None:
    for fonte in candidatas:
        nome = _nome_do_arquivo(fonte)
        if nome and nome not in fontes:
            fontes.append(nome)


def extrair_fontes(texto: str) -> list[str]:
    """Arquivos citados no texto da resposta, na ordem em que aparecem, sem repetição.

    Lê os marcadores `[fonte: ...]` e a linha `Fontes: a; b` dos textos prontos.
    Vários arquivos num mesmo marcador (separados por ";" ou ",") viram
    entradas individuais.
    """
    fontes: list[str] = []
    texto = str(texto or "")
    for grupo in FONTE_RE.findall(texto) + LINHA_FONTES_RE.findall(texto):
        for arquivo in SEPARADOR_FONTES_RE.split(grupo):
            arquivo = arquivo.strip()
            if arquivo and arquivo not in fontes:
                fontes.append(arquivo)
    return fontes


def fontes_da_resposta(texto: str, fontes_do_turno: list[str] | None = None) -> list[str]:
    """Rodapé de fontes: as saídas das funções (determinístico) e o que o texto citar.

    As fontes do turno vêm do orquestrador — não dependem de o modelo escrever
    o marcador. As citações do texto completam (ex.: trechos do RAG).
    """
    fontes: list[str] = []
    _adicionar(fontes, list(fontes_do_turno or []))
    _adicionar(fontes, extrair_fontes(texto))
    return fontes


def mensagem_de_erro(erro: BaseException) -> str:
    """Mensagem amigável para a tela — nunca stack trace."""
    if getattr(erro, "code", None) == 429:
        return MENSAGEM_429
    if isinstance(erro, FixtureAusenteError):
        return MENSAGEM_FIXTURE
    if isinstance(erro, RuntimeError) and "GEMINI_API_KEY" in str(erro):
        return MENSAGEM_SEM_CHAVE
    return MENSAGEM_GENERICA
