"""Estado da sessão do assistente: relógio da sessão e entidades em foco.

O `produtor_em_foco`, `pedido_em_foco` e `produto_em_foco` são o que resolve
"e o dela?", "esse lote" e "manda pra ele" (requisito 5 de docs/01 §6): o
contexto da sessão entra no turno e o foco é atualizado pelo resultado de
cada função executada. A interface da #13 lê e devolve este estado pelo
`st.session_state` via `to_dict()/from_dict()`.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

# A demo pode simular um dia (ex.: DATA_REFERENCIA=2026-10-30) ou usar a data real.
DATA_REFERENCIA_ENV = "DATA_REFERENCIA"

# Pedidos do dataset (PED-2026-006, PED-2026-SEP-018), citados na mensagem.
ID_PEDIDO_RE = re.compile(r"\bPED-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")


def data_referencia_padrao() -> str:
    """Relógio da sessão: `DATA_REFERENCIA` do ambiente, senão hoje (AAAA-MM-DD)."""
    valor = (os.getenv(DATA_REFERENCIA_ENV) or "").strip()
    if valor:
        return valor
    return date.today().isoformat()


@dataclass
class EstadoSessao:
    """Entidades em foco durante a sessão (a data é fixada no início da sessão)."""

    data_referencia: str
    produtor_em_foco: dict[str, str] | None = None  # {"produtor_id", "nome"}
    pedido_em_foco: str | None = None
    produto_em_foco: str | None = None

    # ------------------------------------------------------------------ #
    # Atualização pelo resultado das funções                             #
    # ------------------------------------------------------------------ #

    def atualizar(self, nome_funcao: str, args: dict[str, Any], resultado: dict[str, Any]) -> None:
        """Atualiza os focos a partir da função executada e da saída dela."""
        if not isinstance(resultado, dict):
            return
        produtor = _produtor_do_resultado(resultado)
        if produtor:
            self.produtor_em_foco = produtor
        produto = _produto_do_resultado(nome_funcao, args, resultado)
        if produto:
            self.produto_em_foco = produto
        if nome_funcao == "triar_pedido":
            self._focar_pedido_de(args, resultado)

    def focar_pedido_do_texto(self, texto: str) -> bool:
        """Foca o pedido citado no texto da equipe (ex.: "PED-2026-006"), se houver.

        O pedido entra em foco pelo que a equipe escreveu, venha ele de `triar_pedido`
        ou de qualquer outra função — "e o queijo desse pedido?" depende disso.
        """
        achado = ID_PEDIDO_RE.search(str(texto).upper())
        if achado:
            self.pedido_em_foco = achado.group(0)
            return True
        return False

    def _focar_pedido_de(self, args: dict[str, Any], resultado: dict[str, Any]) -> None:
        self.focar_pedido_do_texto(str(args.get("mensagem", "")))
        itens = resultado.get("itens") or []
        if itens and isinstance(itens, list):
            produto = (itens[0] or {}).get("produto")
            if produto:
                self.produto_em_foco = str(produto)

    # ------------------------------------------------------------------ #
    # Contexto do turno e serialização                                   #
    # ------------------------------------------------------------------ #

    def contexto(self) -> str:
        """Bloco de texto do estado, injetado no conteúdo de cada turno."""
        produtor = "—"
        if self.produtor_em_foco:
            produtor = f"{self.produtor_em_foco.get('produtor_id', '—')} ({self.produtor_em_foco.get('nome', '')})"
        return "\n".join(
            (
                "[CONTEXTO DA SESSÃO]",
                f"data_referencia: {self.data_referencia}",
                f"produtor_em_foco: {produtor}",
                f"pedido_em_foco: {self.pedido_em_foco or '—'}",
                f"produto_em_foco: {self.produto_em_foco or '—'}",
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "EstadoSessao":
        return cls(
            data_referencia=str(dados["data_referencia"]),
            produtor_em_foco=dados.get("produtor_em_foco"),
            pedido_em_foco=dados.get("pedido_em_foco"),
            produto_em_foco=dados.get("produto_em_foco"),
        )


def _produtor_do_resultado(resultado: dict[str, Any]) -> dict[str, str] | None:
    produtor = resultado.get("produtor")
    if not (resultado.get("encontrado") and isinstance(produtor, dict)):
        return None
    identificador, nome = produtor.get("produtor_id"), produtor.get("nome")
    if not (identificador and nome):
        return None
    return {"produtor_id": str(identificador), "nome": str(nome)}


def _produto_do_resultado(nome_funcao: str, args: dict[str, Any], resultado: dict[str, Any]) -> str | None:
    """Nome do produto em foco, na forma que cada ferramenta devolve."""
    item = resultado.get("item")  # verificar_conformidade traz o item avaliado
    if isinstance(item, dict) and item.get("produto"):
        return str(item["produto"])
    produto = resultado.get("produto")
    if not produto and nome_funcao == "rastrear_lote":
        produto = (resultado.get("lote") or {}).get("produto")
    return str(produto) if produto else None
