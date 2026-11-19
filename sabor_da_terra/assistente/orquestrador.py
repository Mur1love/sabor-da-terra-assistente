"""Orquestrador do assistente: o turno completo com function calling nativo.

Um turno (`responder`) roda assim:

1. A mensagem do usuário é mascarada (regra 2 do docs/03) e entra no histórico
   com o contexto da sessão (relógio + focos) — é assim que "ela" vira P008.
2. Laço de roteamento no Flash-Lite (`Papel.TRIAGEM`) com as ferramentas
   declaradas e o function calling automático desligado: o modelo propõe
   `function_call`s, o assistente executa as funções reais (relógio da sessão
   sobrepõe o argumento, saída mascarada, erro honesto, limite por turno) e
   devolve `function_response`s com `role="user"` — a API do Gemini só aceita
   user/model, e ecoa o content do modelo com a `thought_signature` preservada.
3. Resposta final do turno: se o único resultado traz texto pronto
   (`"resposta"` do RAG, `"texto"` do resumo), esse texto vai verbatim — sem
   segunda composição (regra 1 do docs/03); nos rascunhos de comunicação
   (resumo, notificação) o pass-through acrescenta que nada foi enviado. Se há
   síntese a fazer, o Flash
   (`Papel.RESPOSTA`) compõe a partir do payload com os resultados mascarados.
   Sem funções, o próprio texto do Flash-Lite fecha o turno.
4. Log por turno: modelos de cada papel (ou "pass-through"), funções chamadas
   (args mascarados), funções com LLM interno, erros e duração.
"""

from __future__ import annotations

import inspect
import json
import logging
import re
import time
from typing import Any

from google.genai import types

from sabor_da_terra.assistente.estado import EstadoSessao, data_referencia_padrao
from sabor_da_terra.assistente.ferramentas import FERRAMENTAS_COM_LLM, NOME_PARA_FUNCAO, declarar_ferramentas
from sabor_da_terra.assistente.mascaramento import mascarar_dados_sensiveis
from sabor_da_terra.assistente.prompt import (
    PROMPT_RESPOSTA_FINAL,
    PROMPT_RESPOSTA_TRIAGEM,
    PROMPT_SISTEMA,
    proximos_passos_da_triagem,
)
from sabor_da_terra.assistente.verificacao import Universo, so_fatos_com_respaldo
from sabor_da_terra.llm.cliente import FixtureAusenteError, LLMClient, Papel

logger = logging.getLogger("sabor_da_terra.assistente")

# Limites do turno: o laço nunca fica preso no function calling.
# Um pedido de 9 itens pede 9 verificações de conformidade, mais preço e
# disponibilidade; com 8, a triagem parava no meio (rodada 2 da #14). As funções
# depois da triagem são locais, sem LLM: o teto protege o turno, não a cota.
MAX_CHAMADAS_POR_TURNO = 24
MAX_ITERACOES_POR_TURNO = 4
JANELA_HISTORICO = 6  # turnos completos que ficam no histórico

# Saídas que já vêm com texto pronto para a equipe (RAG, resumo, notificação).
CHAVES_TEXTO_PRONTO = ("texto", "resposta")

# Papel das function responses no histórico. A API do Gemini aceita só
# "user"/"model" (400 com role="tool", visto ao vivo em 17/11/2026); a part
# `function_response` identifica a resposta, o papel é sempre "user".
ROLE_RESPOSTA_FUNCAO = "user"

# Saídas cujo texto é um rascunho endereçado a produtor/comprador: o pass-through
# precisa avisar a equipe que nada saiu da cooperativa (critério 3 da #12).
RASCUNHOS_SEM_ENVIO = ("resumo_produtor", "notificar_produtores")
AVISO_RASCUNHO = "Rascunho para revisão da equipe; nada foi enviado."

SEM_RESPOSTA = "Não consegui processar sua mensagem."
SEM_COMPOSICAO = "Não consegui compor a resposta agora; os dados das funções estão no log."


def _content_com_args_mascarados(content: types.Content) -> types.Content:
    """Cópia do content do modelo com os args das function_calls mascarados.

    O histórico volta ao modelo inteiro a cada iteração e turno — os args
    que o modelo escreveu (podendo conter dado de pessoa) não podem
    sobreviver nele sem máscara. A `thought_signature` de cada part é
    preservada: a API do Gemini exige a assinatura de volta no eco.
    """
    partes: list[types.Part] = []
    for parte in content.parts or []:
        chamada = parte.function_call
        if chamada is not None:
            mascarada = chamada.model_copy(deep=True)
            mascarada.args = mascarar_dados_sensiveis(dict(mascarada.args or {}))
            nova = types.Part(function_call=mascarada)
            if parte.thought_signature is not None:
                nova.thought_signature = parte.thought_signature
            partes.append(nova)
        elif parte.text is not None:
            # cópia inteira: texto, flag `thought` e `thought_signature` voltam como vieram
            partes.append(parte.model_copy(deep=True))
        else:
            partes.append(parte)
    return types.Content(role=content.role, parts=partes)


class Assistente:
    """A sessão de conversa: histórico em turnos, laço de funções e resposta final."""

    def __init__(
        self,
        cliente_llm: LLMClient | None = None,
        estado: EstadoSessao | None = None,
        max_chamadas: int = MAX_CHAMADAS_POR_TURNO,
        max_iteracoes: int = MAX_ITERACOES_POR_TURNO,
        janela: int = JANELA_HISTORICO,
    ) -> None:
        self._cliente = cliente_llm or LLMClient()
        self.estado = estado or EstadoSessao(data_referencia=data_referencia_padrao())
        self._max_chamadas = max_chamadas
        self._max_iteracoes = max_iteracoes
        self._janela = janela
        self._blocos: list[list[types.Content]] = []  # um bloco por turno, completo
        self._turno = 0
        # Arquivos de origem do último turno, tirados das SAÍDAS das funções
        # (determinístico): a interface monta o rodapé de fontes a partir daqui,
        # sem depender de o modelo escrever o marcador [fonte: ...].
        self.fontes_do_turno: list[str] = []
        # Funções executadas no último turno, na ordem (inclui as que voltaram
        # com erro): a avaliação confere `funcoes_esperadas` do gabarito aqui.
        self.funcoes_do_turno: list[str] = []

    @property
    def cliente(self) -> LLMClient:
        """O cliente LLM da sessão (modelos por papel, consumo e failover)."""
        return self._cliente

    # ------------------------------------------------------------------ #
    # Turno                                                              #
    # ------------------------------------------------------------------ #

    def responder(self, mensagem: str) -> str:
        """Um turno completo: roteamento, funções, resposta final e log."""
        inicio = time.perf_counter()
        self._turno += 1
        self.fontes_do_turno = []
        self.funcoes_do_turno = []
        mensagem = mascarar_dados_sensiveis(mensagem)
        self.estado.focar_pedido_do_texto(mensagem)  # "PED-2026-006" entra em foco venha ele de qual função vier
        self.estado.focar_comprador_do_texto(mensagem)  # "do SuperBom" entra em foco para o turno seguinte

        self._blocos.append(
            [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"{self.estado.contexto()}\n\n[MENSAGEM DO USUÁRIO]\n{mensagem}")],
                )
            ]
        )

        executadas: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        erros: list[str] = []
        rascunho: str | None = None

        for _ in range(self._max_iteracoes):
            resposta = self._cliente.gerar(Papel.TRIAGEM, self.historico, **self._config_roteamento())
            chamadas = resposta.function_calls or []
            if not chamadas:
                rascunho = resposta.text
                break
            self._blocos[-1].append(_content_com_args_mascarados(resposta.candidates[0].content))
            self._blocos[-1].append(self._executar_chamadas(chamadas, executadas, erros))

        final, fechamento = self._fechar_turno(mensagem, executadas, erros, rascunho)
        self._blocos[-1].append(types.Content(role="model", parts=[types.Part.from_text(text=final)]))
        if final != SEM_COMPOSICAO:  # sem resposta composta, não há o que atribuir a arquivo
            self.fontes_do_turno = _fontes_unicas(executadas)

        duracao = time.perf_counter() - inicio
        modelos = {
            "triagem": self._cliente.modelo(Papel.TRIAGEM),
            # sem composição o Flash não entra no turno: quem fechou foi o roteamento ou o texto pronto
            "resposta": self._cliente.modelo(Papel.RESPOSTA) if fechamento == "composto" else "pass-through",
        }
        logger.info(
            "turno=%d modelos=%s funcoes=%s com_llm_interno=%s erros=%s duracao=%.2fs",
            self._turno,
            modelos,
            [nome for nome, _, _ in executadas],
            [nome for nome, _, _ in executadas if nome in FERRAMENTAS_COM_LLM],
            erros,
            duracao,
        )
        return final

    # ------------------------------------------------------------------ #
    # Histórico (janela de turnos completos)                             #
    # ------------------------------------------------------------------ #

    @property
    def historico(self) -> list[types.Content]:
        """Os `janela` últimos turnos completos — nunca um turno pela metade.

        Lista, não tupla: é a forma de `contents` que o `google-genai` serializa.
        """
        return [conteudo for bloco in self._blocos[-self._janela :] for conteudo in bloco]

    # ------------------------------------------------------------------ #
    # Despacho e fechamento                                              #
    # ------------------------------------------------------------------ #

    def _config_roteamento(self) -> dict[str, Any]:
        """Config nativa do google-genai: declaração por callable, auto-chamada desligada."""
        return {
            "tools": [declarar_ferramentas()],
            "system_instruction": PROMPT_SISTEMA,
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
            "temperature": 0,
        }

    def _executar_chamadas(
        self,
        chamadas: list[types.FunctionCall],
        executadas: list[tuple[str, dict[str, Any], dict[str, Any]]],
        erros: list[str],
    ) -> types.Content:
        """Executa as chamadas na ordem; toda `function_call` recebe resposta."""
        partes: list[types.Part] = []
        for chamada in chamadas:
            nome = chamada.name or ""
            if len(executadas) >= self._max_chamadas:
                saida: dict[str, Any] = {"erro": f"Limite de {self._max_chamadas} chamadas de função por turno atingido."}
                erros.append(nome)
            else:
                saida = self._despachar(nome, dict(chamada.args or {}))
                self.funcoes_do_turno.append(nome)
                if saida.get("erro"):
                    erros.append(nome)
                else:
                    executadas.append((nome, dict(chamada.args or {}), saida))
            partes.append(types.Part.from_function_response(name=nome, response=saida))
        return types.Content(role=ROLE_RESPOSTA_FUNCAO, parts=partes)

    def _despachar(self, nome: str, args: dict[str, Any]) -> dict[str, Any]:
        """Chama a função real: relógio da sessão injetado, saída mascarada e logada."""
        funcao = NOME_PARA_FUNCAO.get(nome)
        if funcao is None:
            return {"erro": f"Função desconhecida: {nome}."}
        args = mascarar_dados_sensiveis(dict(args))
        if "data_referencia" in inspect.signature(funcao).parameters:
            args["data_referencia"] = self.estado.data_referencia
        if nome == "triar_pedido" and not args.get("data_recebimento"):
            args["data_recebimento"] = self.estado.data_referencia
        logger.info("funcao=%s args=%s", nome, args)
        try:
            saida = funcao(**args)
        except Exception as exc:  # noqa: BLE001 — o erro vai ao modelo com honestidade
            saida = {"erro": str(exc)}
        saida = mascarar_dados_sensiveis(saida)
        if nome == "triar_pedido" and isinstance(saida, dict) and not saida.get("erro"):
            passos = proximos_passos_da_triagem(saida)
            if passos:
                saida = {**saida, "proximos_passos": passos}
        self.estado.atualizar(nome, args, saida)
        return saida

    def _fechar_turno(
        self,
        mensagem: str,
        executadas: list[tuple[str, dict[str, Any], dict[str, Any]]],
        erros: list[str],
        rascunho: str | None,
    ) -> tuple[str, str]:
        """Fecha o turno e diz como fechou: `sem_funcao`, `pass_through` ou `composto`."""
        if not executadas:
            # Sem função, o texto é do roteamento: só pode afirmar o que a equipe
            # escreveu ou o que o estado da sessão já sabe (nada "de cabeça").
            universo = Universo.de(mensagem, self.estado.to_dict())
            return so_fatos_com_respaldo(rascunho or SEM_RESPOSTA, universo), "sem_funcao"
        if len(executadas) == 1 and not erros:
            nome, _, saida = executadas[0]
            pronta = next((saida[k] for k in CHAVES_TEXTO_PRONTO if isinstance(saida.get(k), str)), None)
            if pronta:
                if nome in RASCUNHOS_SEM_ENVIO:
                    pronta = f"{pronta}\n\n{AVISO_RASCUNHO}"
                if nome == "consultar_documentos":
                    pronta = _com_lacunas(pronta, saida)
                return pronta, "pass_through"  # texto validado na fonte, sem segunda composição
        return self._compor(mensagem, executadas, rascunho), "composto"

    def _compor(
        self,
        mensagem: str,
        executadas: list[tuple[str, dict[str, Any], dict[str, Any]]],
        rascunho: str | None,
    ) -> str:
        """Resposta final no Flash, a partir do payload com os resultados do turno."""
        payload = {
            "data_referencia": self.estado.data_referencia,
            "estado_da_sessao": self.estado.to_dict(),
            "pergunta": mensagem,
            # `proximos_passos` orienta o roteamento; não é dado para a resposta.
            "resultados_das_funcoes": [
                {"funcao": nome, "args": args, "saida": {k: v for k, v in saida.items() if k != "proximos_passos"}}
                for nome, args, saida in executadas
            ],
            "rascunho_do_roteamento": rascunho,
            "fontes_permitidas": sorted(_fontes_unicas(executadas)),
        }
        payload = mascarar_dados_sensiveis(payload)
        regras = PROMPT_RESPOSTA_FINAL
        if any(nome == "triar_pedido" for nome, _, _ in executadas):
            regras = f"{regras}\n{PROMPT_RESPOSTA_TRIAGEM}"
        prompt_final = (
            f"{regras}\n\n"
            f"CONTEXTO DO TURNO (JSON):\n{json.dumps(payload, ensure_ascii=False, default=str)}"
        )
        try:
            resposta = self._cliente.gerar(Papel.RESPOSTA, prompt_final, temperature=0)
        except FixtureAusenteError:
            # Fixture ausente é erro de infraestrutura do modo fixture, não falha
            # do modelo: sobe para quem puder completar a gravação.
            raise
        except Exception as exc:  # noqa: BLE001 — 504/503 do Flash não derrubam o turno
            logger.warning("composicao_final falhou (%s: %s); turno fecha com resposta honesta", type(exc).__name__, exc)
            return SEM_COMPOSICAO
        texto = resposta.text or SEM_COMPOSICAO
        texto = _so_citacoes_permitidas(texto, payload["fontes_permitidas"])
        # O rascunho do roteamento fica de fora do universo: é texto de LLM, não dado.
        universo = Universo.de(
            payload["resultados_das_funcoes"],
            payload["pergunta"],
            payload["estado_da_sessao"],
            payload["data_referencia"],
        )
        return so_fatos_com_respaldo(texto, universo)


_MARCADOR_FONTE_RE = re.compile(r"\s*\[fonte:\s*([^\]]+)\]")
_SEPARADOR_FONTES_RE = re.compile(r"\s*[;,]\s*")


def _com_lacunas(texto: str, saida: dict[str, Any]) -> str:
    """Resposta documental + o que os documentos não cobrem (campo `lacunas` do RAG).

    Quando o RAG achou resposta mas só parcial ("o documento não traz isso para
    todos os produtores"), a lacuna vira um aviso explícito para a equipe
    conferir caso a caso. Lacuna sozinha (nada encontrado) já é a resposta.
    """
    lacunas = [str(item).strip().rstrip(".") for item in saida.get("lacunas") or [] if str(item).strip()]
    if not saida.get("encontrado") or not lacunas:
        return texto
    return (
        f"{texto}\n\n**O que os documentos não cobrem:** {'; '.join(lacunas)}. "
        "Antes de usar essa informação, confirme caso a caso, com o produtor ou com o documento original."
    )


def _sem_prefixo_data(fonte: str) -> str:
    fonte = fonte.strip()
    return fonte[len("data/"):] if fonte.startswith("data/") else fonte


def _so_citacoes_permitidas(texto: str, permitidas: list[str]) -> str:
    """Guarda determinística de citação: só fica `[fonte: …]` que as funções devolveram.

    O prompt já manda citar só `fontes_permitidas`, mas o modelo erra o nome
    (visto na rodada 1 da #14: `tabelas_precos_...`, arquivo que não existe).
    Arquivo fora da lista sai do marcador; marcador vazio sai do texto. O
    rodapé de fontes da interface continua vindo das saídas das funções.
    """
    validas = {_sem_prefixo_data(f) for f in permitidas}

    def filtrar(achado: re.Match) -> str:
        arquivos = [a for a in _SEPARADOR_FONTES_RE.split(achado.group(1)) if a.strip()]
        mantidos = [a.strip() for a in arquivos if _sem_prefixo_data(a) in validas]
        if len(mantidos) < len(arquivos):
            logger.info("citacao_removida=%s", [a for a in arquivos if a.strip() not in mantidos])
        return f" [fonte: {'; '.join(mantidos)}]" if mantidos else ""

    return _MARCADOR_FONTE_RE.sub(filtrar, texto)


def _fontes_unicas(executadas: list[tuple[str, dict[str, Any], dict[str, Any]]]) -> list[str]:
    """Arquivos citados pelas funções do turno, na ordem de chamada, sem repetição."""
    fontes: list[str] = []
    for _, _, saida in executadas:
        for fonte in _fontes_da_saida(saida):
            if fonte not in fontes:
                fontes.append(fonte)
    return fontes


def _fontes_da_saida(saida: dict[str, Any]) -> list[str]:
    """Arquivos citados numa saída: `fontes`, `fonte` e citações do RAG.

    Pasta ("fichas_tecnicas/", fonte de alerta de AUSÊNCIA de dado) não é
    documento citável: fica de fora — o alerta já diz onde se procurou.
    """
    fontes: list[str] = []
    fontes.extend(str(f) for f in saida.get("fontes") or [])
    if saida.get("fonte"):
        fontes.append(str(saida["fonte"]))
    fontes.extend(
        str(citacao.get("arquivo")) for citacao in saida.get("citacoes") or [] if citacao.get("arquivo")
    )
    return [fonte for fonte in fontes if not fonte.rstrip().endswith("/")]
