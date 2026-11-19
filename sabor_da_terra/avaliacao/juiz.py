"""Juiz LLM: decide critério a critério se a resposta atende o gabarito."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from sabor_da_terra.avaliacao.gabarito import Caso
from sabor_da_terra.llm.cliente import LLMClient, Papel
from sabor_da_terra.prompts.avaliacao import PROMPT_JUIZ, VERSAO_PROMPT_JUIZ


class ItemDeveConter(BaseModel):
    indice: int
    atendido: bool
    evidencia: str = Field(default="", max_length=400)


class ItemNaoDeveConter(BaseModel):
    indice: int
    ocorreu: bool
    evidencia: str = Field(default="", max_length=400)


class Julgamento(BaseModel):
    deve_conter: list[ItemDeveConter]
    nao_deve_conter: list[ItemNaoDeveConter]


class JulgamentoInvalido(RuntimeError):
    """O juiz respondeu fora do contrato (JSON inválido ou critério faltando)."""


def payload_do_juiz(caso: Caso, turnos: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "caso": caso.id,
        "versao_prompt": VERSAO_PROMPT_JUIZ,
        "conversa": [
            {
                "mensagem_da_equipe": t["mensagem"],
                "resposta_do_assistente": t["resposta"],
                "funcoes_chamadas": t["funcoes"],
                "fontes_exibidas": t["fontes"],
            }
            for t in turnos
        ],
        "esperado": caso.esperado,
        "deve_conter": [{"indice": i, "criterio": c} for i, c in enumerate(caso.deve_conter)],
        "nao_deve_conter": [{"indice": i, "criterio": c} for i, c in enumerate(caso.nao_deve_conter)],
    }


def julgar(caso: Caso, turnos: list[dict[str, Any]], cliente: LLMClient) -> dict[str, list[dict[str, Any]]]:
    """Critério a critério: `{"deve_conter": [...], "nao_deve_conter": [...]}`, na ordem do gabarito."""
    prompt = (
        f"{PROMPT_JUIZ}\n\nAVALIAÇÃO (JSON):\n"
        f"{json.dumps(payload_do_juiz(caso, turnos), ensure_ascii=False)}"
    )
    resposta = cliente.gerar(
        Papel.TRIAGEM,
        prompt,
        temperature=0,
        response_mime_type="application/json",
        response_schema=Julgamento.model_json_schema(),
    )
    try:
        julgamento = Julgamento.model_validate_json(resposta.text or "")
    except ValidationError as exc:
        raise JulgamentoInvalido(f"{caso.id}: resposta do juiz fora do schema: {exc}") from exc

    deve = {item.indice: item for item in julgamento.deve_conter}
    nao = {item.indice: item for item in julgamento.nao_deve_conter}
    faltando = [i for i in range(len(caso.deve_conter)) if i not in deve] + [
        i for i in range(len(caso.nao_deve_conter)) if i not in nao
    ]
    if faltando:
        raise JulgamentoInvalido(f"{caso.id}: o juiz pulou critérios (índices {faltando})")

    return {
        "deve_conter": [
            {"criterio": c, "atendido": deve[i].atendido, "evidencia": deve[i].evidencia}
            for i, c in enumerate(caso.deve_conter)
        ],
        "nao_deve_conter": [
            {"criterio": c, "ocorreu": nao[i].ocorreu, "evidencia": nao[i].evidencia}
            for i, c in enumerate(caso.nao_deve_conter)
        ],
    }
