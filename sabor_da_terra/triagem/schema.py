"""Schema Pydantic da saída estruturada da triagem de pedidos (Etapa 9)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TipoMensagem(str, Enum):
    """Classificação da intenção principal da mensagem recebida."""

    COMPRA = "compra"
    COMPRA_URGENTE = "compra_urgente"
    COTACAO = "cotacao"
    CONSULTA = "consulta"
    MENSAGEM_PRODUTOR = "mensagem_produtor"
    NOTIFICACAO_OFICIAL = "notificacao_oficial"


class ItemPedidoExtraido(BaseModel):
    """Item individual extraído da mensagem em linguagem natural."""

    produto: str = Field(
        ...,
        min_length=1,
        description="Nome do produto mapeado para o catálogo da cooperativa quando identificável.",
    )
    produto_original: str | None = Field(
        default=None,
        description="Expressão original usada na mensagem antes da normalização.",
    )
    quantidade: float | None = Field(
        default=None,
        gt=0,
        description="Quantidade solicitada ou ofertada; nulo se não especificada.",
    )
    unidade: str | None = Field(
        default=None,
        description="Unidade de medida normalizada (ex.: kg, maço, unidade, dúzia, litro).",
    )
    exige_organico: bool = Field(
        default=False,
        description="Verdadeiro se a mensagem exige ou solicita certificação orgânica para o item.",
    )
    opcional: bool = Field(
        default=False,
        description="Verdadeiro se o item é condicional (ex.: 'se tiver ricota', 'cajá se tiver').",
    )


class PedidoTriado(BaseModel):
    """Registro estruturado resultante da triagem de uma mensagem."""

    tipo: TipoMensagem = Field(
        ...,
        description="Classificação principal da mensagem recebida.",
    )
    idioma: str = Field(
        default="pt",
        description="Código ISO-639-1 do idioma da mensagem (ex.: 'pt', 'en').",
    )
    comprador: str | None = Field(
        default=None,
        description="Nome do comprador, instituição, produtor ou órgão remetente.",
    )
    canal: str | None = Field(
        default=None,
        description="Canal de entrada da mensagem (ex.: email, whatsapp, formulario_web).",
    )
    itens: list[ItemPedidoExtraido] = Field(
        default_factory=list,
        description="Lista de produtos mencionados na mensagem.",
    )
    prazo_entrega: str | None = Field(
        default=None,
        description="Data ou prazo de entrega resolvido (YYYY-MM-DD ou texto quando aberto).",
    )
    prazo_original: str | None = Field(
        default=None,
        description="Trecho original da mensagem que indica data ou prazo.",
    )
    observacoes: list[str] = Field(
        default_factory=list,
        description="Detalhes relevantes: pagamento, local de entrega, NF, exigências documentais.",
    )
    campos_faltantes: list[str] = Field(
        default_factory=list,
        description="Campos essenciais ausentes na mensagem (ex.: prazo_entrega, quantidade).",
    )
    ambiguidades: list[str] = Field(
        default_factory=list,
        description="Referências implícitas ('o de sempre'), termos genéricos ou conflitos de data.",
    )


def validar_pedido_triado(bruto: str | dict[str, Any] | PedidoTriado) -> PedidoTriado:
    """Valida e converte uma resposta JSON (str ou dict) para PedidoTriado."""
    if isinstance(bruto, PedidoTriado):
        return bruto
    if isinstance(bruto, str):
        return PedidoTriado.model_validate_json(bruto)
    return PedidoTriado.model_validate(bruto)


def esquema_resposta_triagem() -> dict[str, Any]:
    """JSON Schema do `PedidoTriado` para o parâmetro `response_schema` do Gemini.

    O SDK/aceite do Gemini não aceita todas as construções do JSON Schema do
    Pydantic: `$ref`/`$defs` são inlinados e `exclusiveMinimum` (gerado por
    `gt=`) vira `minimum` — a exclusividade de 0 continua garantida pela
    validação do `PedidoTriado` sobre a resposta do modelo.
    """
    return _esquema_compativel_gemini(PedidoTriado.model_json_schema())


def _esquema_compativel_gemini(esquema: dict[str, Any]) -> dict[str, Any]:
    """Cópia do esquema com `$defs` inlinados e campos não suportados ajustados."""
    definicoes: dict[str, Any] = esquema.pop("$defs", {})

    def resolver(nodo: Any) -> Any:
        if isinstance(nodo, list):
            return [resolver(item) for item in nodo]
        if not isinstance(nodo, dict):
            return nodo
        if "$ref" in nodo:
            nome = str(nodo["$ref"]).split("/")[-1]
            return resolver(definicoes.get(nome, {}))
        saida: dict[str, Any] = {}
        for chave, valor in nodo.items():
            if chave == "exclusiveMinimum":
                saida["minimum"] = valor
            else:
                saida[chave] = resolver(valor)
        return saida

    return {chave: resolver(valor) for chave, valor in esquema.items()}
