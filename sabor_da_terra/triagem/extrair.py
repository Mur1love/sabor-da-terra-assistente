"""Extração estruturada e triagem inicial de mensagens/pedidos (Etapa 9)."""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

from pydantic import ValidationError

from sabor_da_terra.dados.catalogo import Catalogo
from sabor_da_terra.dados.normalizacao import mascarar_cpf_em_texto
from sabor_da_terra.llm.cliente import LLMClient, Papel
from sabor_da_terra.prompts.triagem import (
    INSTRUCOES_SISTEMA_TRIAGEM,
    montar_prompt_triagem,
)
from sabor_da_terra.triagem.datas import analisar_prazo_mensagem
from sabor_da_terra.triagem.normalizar import normalizar_itens_pedido
from sabor_da_terra.triagem.schema import (
    PedidoTriado,
    TipoMensagem,
    esquema_resposta_triagem,
    validar_pedido_triado,
)


class ErroExtracaoTriagem(RuntimeError):
    """Falha explícita quando a saída do modelo não valida contra PedidoTriado."""


_PADROES_REFERENCIA_IMPLICITA: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bo\s+de\s+sempre\b", re.IGNORECASE),
        "Referência implícita detectada ('o de sempre'): necessário consultar histórico do comprador.",
    ),
    (
        re.compile(r"\b(?:da|na|a)\s+[uú]ltima\s+vez\b", re.IGNORECASE),
        "Referência implícita detectada ('da última vez'): necessário consultar pedidos/lotes anteriores do comprador.",
    ),
    (
        re.compile(r"\b(?:aquele|aquela)\s+queijo\b", re.IGNORECASE),
        "Especificação vaga de produto ('aquele queijo'): confirmar variedade exata no histórico.",
    ),
]


def _detectar_referencias_implicitas(mensagem: str) -> list[str]:
    achados: list[str] = []
    for padrao, descricao in _PADROES_REFERENCIA_IMPLICITA:
        if padrao.search(mensagem) and descricao not in achados:
            achados.append(descricao)
    return achados


def _enriquecer_pos_extracao(
    pedido: PedidoTriado,
    *,
    mensagem: str,
    data_recebimento: str | date | datetime | None,
    canal: str | None,
    comprador: str | None,
    catalogo: Catalogo | None,
) -> PedidoTriado:
    """Aplica regras determinísticas sobre o JSON extraído pelo Flash-Lite."""
    itens_norm, avisos_catalogo = normalizar_itens_pedido(pedido.itens, catalogo=catalogo)

    prazo_entrega = pedido.prazo_entrega
    prazo_original = pedido.prazo_original
    conflito_data: str | None = None

    if data_recebimento is not None:
        res_data = analisar_prazo_mensagem(
            mensagem=mensagem,
            data_recebimento=data_recebimento,
            prazo_extraido=pedido.prazo_original or pedido.prazo_entrega,
        )
        if res_data.data_iso:
            prazo_entrega = res_data.data_iso
        if res_data.trecho_original:
            prazo_original = res_data.trecho_original
        conflito_data = res_data.conflito

    ambiguidades = list(pedido.ambiguidades)
    extras_ambiguidade: list[str] = []
    if conflito_data:
        extras_ambiguidade.append(conflito_data)
    extras_ambiguidade.extend(_detectar_referencias_implicitas(mensagem))
    extras_ambiguidade.extend(avisos_catalogo)

    for texto_amb in extras_ambiguidade:
        if texto_amb and not any(texto_amb.lower() == a.lower() for a in ambiguidades):
            ambiguidades.append(texto_amb)

    campos_faltantes = list(pedido.campos_faltantes)
    if (
        pedido.tipo in {TipoMensagem.COMPRA, TipoMensagem.COMPRA_URGENTE}
        and not prazo_entrega
        and "prazo_entrega" not in campos_faltantes
    ):
        campos_faltantes.append("prazo_entrega")

    if any(item.quantidade is None for item in itens_norm) and "quantidade" not in campos_faltantes:
        campos_faltantes.append("quantidade")

    observacoes = [mascarar_cpf_em_texto(obs) for obs in pedido.observacoes if obs.strip()]
    ambiguidades = [mascarar_cpf_em_texto(amb) for amb in ambiguidades if amb.strip()]

    return pedido.model_copy(
        update={
            "comprador": pedido.comprador or comprador,
            "canal": pedido.canal or canal,
            "itens": itens_norm,
            "prazo_entrega": prazo_entrega,
            "prazo_original": prazo_original,
            "observacoes": observacoes,
            "campos_faltantes": campos_faltantes,
            "ambiguidades": ambiguidades,
        }
    )


def extrair_pedido(
    mensagem: str,
    *,
    data_recebimento: str | date | datetime | None = None,
    canal: str | None = None,
    comprador: str | None = None,
    remetente: str | None = None,
    llm: LLMClient | None = None,
    catalogo: Catalogo | None = None,
) -> PedidoTriado:
    """Classifica e extrai uma mensagem usando Gemini Flash-Lite com response_schema.

    Valida o retorno contra `PedidoTriado`; se inválido, realiza exatamente
    uma nova tentativa informando o erro de validação antes de falhar.
    """
    if not mensagem or not mensagem.strip():
        raise ValueError("A mensagem para triagem não pode ser vazia.")

    cliente = llm or LLMClient()
    data_str = (
        data_recebimento.isoformat()
        if isinstance(data_recebimento, (date, datetime))
        else data_recebimento
    )

    erro_anterior: str | None = None
    ultimo_erro: Exception | None = None

    for tentativa in range(2):
        prompt = montar_prompt_triagem(
            mensagem,
            data_recebimento=data_str,
            canal=canal,
            comprador=comprador,
            remetente=remetente,
            erro_validacao_anterior=erro_anterior,
        )
        resposta = cliente.gerar(
            Papel.TRIAGEM,
            prompt,
            system_instruction=INSTRUCOES_SISTEMA_TRIAGEM,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=esquema_resposta_triagem(),
        )
        bruto = getattr(resposta, "text", None) or ""
        try:
            extraido = validar_pedido_triado(bruto)
            return _enriquecer_pos_extracao(
                extraido,
                mensagem=mensagem,
                data_recebimento=data_recebimento,
                canal=canal,
                comprador=comprador,
                catalogo=catalogo,
            )
        except (ValidationError, ValueError) as exc:
            ultimo_erro = exc
            erro_anterior = str(exc)

    raise ErroExtracaoTriagem(
        f"Falha ao validar saída estruturada da triagem após 2 tentativas: {ultimo_erro}"
    ) from ultimo_erro


def triar_pedido(
    mensagem: str,
    data_recebimento: str | None = None,
    canal: str | None = None,
    comprador: str | None = None,
    remetente: str | None = None,
) -> dict[str, Any]:
    """Ferramenta exposta para function calling (Etapa 12): classifica e extrai um pedido."""
    resultado = extrair_pedido(
        mensagem,
        data_recebimento=data_recebimento,
        canal=canal,
        comprador=comprador,
        remetente=remetente,
    )
    return resultado.model_dump(mode="json")
