"""Roda um caso do gabarito no assistente integrado e avalia o resultado.

Duas partes:
- determinística: as funções esperadas foram chamadas? As fontes exibidas
  existem em `data/` e saíram das funções do turno (citação válida)?
- juiz LLM: cada critério de `deve_conter` / `nao_deve_conter`.

Um turno que fecha sem composição (`SEM_COMPOSICAO`: cota/API fora) não é
falha do assistente — o caso sai como `erro_infra` e não é julgado.
"""

from __future__ import annotations

import time
from typing import Any

from sabor_da_terra.assistente.estado import EstadoSessao
from sabor_da_terra.assistente.orquestrador import SEM_COMPOSICAO, Assistente
from sabor_da_terra.avaliacao.gabarito import Caso, arquivos_de_fonte, data_referencia, requisitos_funcionais
from sabor_da_terra.avaliacao.juiz import JulgamentoInvalido, julgar
from sabor_da_terra.interface.mensagens import extrair_fontes, fontes_da_resposta
from sabor_da_terra.llm.cliente import FixtureAusenteError, LLMClient
from sabor_da_terra.rag.responder import listar_arquivos_data

STATUS_OK = "ok"
STATUS_ERRO_INFRA = "erro_infra"
STATUS_ERRO_JUIZ = "erro_juiz"


def executar_turnos(caso: Caso, cliente: LLMClient) -> list[dict[str, Any]]:
    """Uma sessão nova por caso; um registro por turno (resposta, funções, fontes, duração)."""
    assistente = Assistente(cliente_llm=cliente, estado=EstadoSessao(data_referencia=data_referencia(caso)))
    turnos: list[dict[str, Any]] = []
    for mensagem in caso.turnos:
        inicio = time.perf_counter()
        resposta = assistente.responder(mensagem)
        turnos.append(
            {
                "mensagem": mensagem,
                "resposta": resposta,
                "funcoes": list(assistente.funcoes_do_turno),
                "fontes_do_turno": list(assistente.fontes_do_turno),
                "fontes": fontes_da_resposta(resposta, assistente.fontes_do_turno),
                "duracao_s": round(time.perf_counter() - inicio, 1),
            }
        )
        if resposta == SEM_COMPOSICAO:
            break  # turnos seguintes rodariam sobre um histórico que a replay não reproduz
    return turnos


def _normalizar(fonte: str) -> str:
    return fonte[len("data/"):] if fonte.startswith("data/") else fonte


def checar_citacoes(caso: Caso, turnos: list[dict[str, Any]]) -> dict[str, Any]:
    """Citação válida: arquivo existe em `data/` e saiu das funções do turno.

    Para casos documentais (RF3, exceto recusas), cada turno precisa exibir ao
    menos uma fonte. Citar o arquivo que o gabarito dá como fonte é medido à
    parte (`fonte_esperada_citada`), sem reprovar o caso.
    """
    existentes = listar_arquivos_data()
    invalidas: list[str] = []
    turnos_sem_fonte: list[int] = []
    exibidas: list[str] = []
    for i, turno in enumerate(turnos, start=1):
        do_turno = {_normalizar(f) for f in turno["fontes_do_turno"]}
        for fonte in turno["fontes"]:
            if fonte not in exibidas:
                exibidas.append(fonte)
            if fonte not in existentes:
                invalidas.append(fonte)
        for marcada in extrair_fontes(turno["resposta"]):
            if _normalizar(marcada) not in do_turno and _normalizar(marcada) not in invalidas:
                invalidas.append(_normalizar(marcada))  # o modelo citou o que as funções não devolveram
        if not turno["fontes"]:
            turnos_sem_fonte.append(i)

    esperadas = arquivos_de_fonte(caso)
    esperada_citada = any(
        fonte == esperada or (esperada.endswith("/") and fonte.startswith(esperada))
        for fonte in exibidas
        for esperada in esperadas
    )
    aplicavel = caso.documental
    return {
        "aplicavel": aplicavel,
        "ok": (not invalidas and not turnos_sem_fonte) if aplicavel else not invalidas,
        "exibidas": exibidas,
        "invalidas": invalidas,
        "turnos_sem_fonte": turnos_sem_fonte if aplicavel else [],
        "fonte_esperada_citada": esperada_citada if esperadas else None,
    }


def checar_funcoes(caso: Caso, turnos: list[dict[str, Any]]) -> dict[str, Any]:
    chamadas = sorted({f for t in turnos for f in t["funcoes"]})
    faltando = [f for f in caso.funcoes_esperadas if f not in chamadas]
    return {"esperadas": list(caso.funcoes_esperadas), "chamadas": chamadas, "faltando": faltando, "ok": not faltando}


def avaliar_caso(caso: Caso, cliente: LLMClient, cliente_juiz: LLMClient | None = None) -> dict[str, Any]:
    """Executa, checa e julga um caso. `FixtureAusenteError` sobe (replay incompleta)."""
    resultado: dict[str, Any] = {
        "id": caso.id,
        "desafio": caso.desafio,
        "requisito": caso.requisito,
        "requisitos_funcionais": list(requisitos_funcionais(caso)),
        "anti_alucinacao": caso.anti_alucinacao,
        "documental": caso.documental,
        "data_referencia": data_referencia(caso),
    }
    try:
        turnos = executar_turnos(caso, cliente)
    except FixtureAusenteError:
        raise
    except Exception as exc:  # noqa: BLE001 — falha de API registrada, a rodada segue
        resultado.update(status=STATUS_ERRO_INFRA, erro=f"{type(exc).__name__}: {exc}"[:500], aprovado=False)
        return resultado

    resultado["turnos"] = turnos
    if any(t["resposta"] == SEM_COMPOSICAO for t in turnos) or len(turnos) < len(caso.turnos):
        resultado.update(status=STATUS_ERRO_INFRA, erro="turno fechou sem composição (cota ou API fora)", aprovado=False)
        return resultado

    resultado["funcoes"] = checar_funcoes(caso, turnos)
    resultado["citacoes"] = checar_citacoes(caso, turnos)
    try:
        resultado["criterios"] = julgar(caso, turnos, cliente_juiz or cliente)
    except FixtureAusenteError:
        raise
    except JulgamentoInvalido as exc:
        resultado.update(status=STATUS_ERRO_JUIZ, erro=str(exc)[:500], aprovado=False)
        return resultado
    except Exception as exc:  # noqa: BLE001
        resultado.update(status=STATUS_ERRO_INFRA, erro=f"juiz: {type(exc).__name__}: {exc}"[:500], aprovado=False)
        return resultado

    criterios = resultado["criterios"]
    resultado["status"] = STATUS_OK
    resultado["criterios_ok"] = sum(c["atendido"] for c in criterios["deve_conter"]) + sum(
        not c["ocorreu"] for c in criterios["nao_deve_conter"]
    )
    resultado["criterios_total"] = caso.total_criterios
    resultado["aprovado"] = (
        resultado["criterios_ok"] == caso.total_criterios
        and resultado["funcoes"]["ok"]
        and resultado["citacoes"]["ok"]
    )
    return resultado
