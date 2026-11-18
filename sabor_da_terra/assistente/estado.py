"""Estado da sessão do assistente: relógio da sessão e entidades em foco.

O `produtor_em_foco`, `pedido_em_foco`, `produto_em_foco` e `comprador_em_foco`
são o que resolve "e o dela?", "esse lote", "manda pra ele" e "as entregas dele
pra esse cliente" (requisito 5 de docs/01 §6): o
contexto da sessão entra no turno e o foco é atualizado pelo resultado de
cada função executada. A interface da #13 lê e devolve este estado pelo
`st.session_state` via `to_dict()/from_dict()`.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from sabor_da_terra.dados import normalizacao as n

# A demo pode simular um dia (ex.: DATA_REFERENCIA=2026-10-30) ou usar a data real.
DATA_REFERENCIA_ENV = "DATA_REFERENCIA"

# Pedidos do dataset (PED-2026-006, PED-2026-SEP-018), citados na mensagem.
ID_PEDIDO_RE = re.compile(r"\bPED-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")

ARQUIVO_FINANCEIRO = Path(__file__).resolve().parents[2] / "data" / "financeiro.csv"

# Palavras que não identificam um comprador ("Rede SuperBom Atacado" é "superbom").
_PALAVRAS_GENERICAS_COMPRADOR = {
    "rede", "atacado", "restaurante", "mercado", "hotel", "fazenda", "unidade", "prefeitura",
    "feira", "de", "da", "do", "das", "dos", "e",
}


@lru_cache(maxsize=1)
def _compradores() -> dict[str, frozenset[str]]:
    """Compradores do dataset (lotes e financeiro) → palavras que os identificam no texto."""
    import pandas as pd

    from sabor_da_terra.dados import obter_repositorio  # import tardio: o estado não carrega dados à toa

    nomes = set(obter_repositorio().lotes()["comprador"].dropna())
    if ARQUIVO_FINANCEIRO.exists():
        nomes |= set(pd.read_csv(ARQUIVO_FINANCEIRO)["comprador"].dropna())
    compradores: dict[str, frozenset[str]] = {}
    for nome in sorted(nomes):
        palavras = {p.strip(".,;:-()") for p in n.chave(nome).split()} - {""}
        distintivas = palavras - _PALAVRAS_GENERICAS_COMPRADOR
        compradores[str(nome)] = frozenset(distintivas or palavras)
    return compradores


def comprador_citado(texto: str) -> str | None:
    """Comprador do dataset citado no texto — todas as palavras distintivas presentes.

    "do SuperBom" → "Rede SuperBom Atacado"; "Mercado Bom Preço" exige "bom" E
    "preco" (um "bom dia" ou "qual o preço" sozinho não casa). Com dois
    candidatos, fica o mais específico (mais palavras casadas).
    """
    palavras = {p.strip(".,;:!?-()\"'") for p in n.chave(texto).split()}
    candidatos = [(len(chave), nome) for nome, chave in _compradores().items() if chave and chave <= palavras]
    return max(candidatos)[1] if candidatos else None


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
    comprador_em_foco: str | None = None

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
        comprador = _comprador_do_resultado(args, resultado)
        if comprador:
            self.comprador_em_foco = comprador

    def focar_comprador_do_texto(self, texto: str) -> bool:
        """Foca o comprador citado pela equipe ("do SuperBom"), se for um do dataset."""
        comprador = comprador_citado(texto)
        if comprador:
            self.comprador_em_foco = comprador
            return True
        return False

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
                f"comprador_em_foco: {self.comprador_em_foco or '—'}",
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
            comprador_em_foco=dados.get("comprador_em_foco"),
        )


def _produtor_do_resultado(resultado: dict[str, Any]) -> dict[str, str] | None:
    produtor = resultado.get("produtor")
    if not (resultado.get("encontrado") and isinstance(produtor, dict)):
        return None
    identificador, nome = produtor.get("produtor_id"), produtor.get("nome")
    if not (identificador and nome):
        return None
    return {"produtor_id": str(identificador), "nome": str(nome)}


def _comprador_do_resultado(args: dict[str, Any], resultado: dict[str, Any]) -> str | None:
    """Comprador que a função usou ou devolveu (argumento, pedido consultado ou lote rastreado)."""
    candidatos = [
        args.get("comprador"),
        (resultado.get("pedido") or {}).get("comprador") if isinstance(resultado.get("pedido"), dict) else None,
        (resultado.get("lote") or {}).get("comprador") if isinstance(resultado.get("lote"), dict) else None,
    ]
    for valor in candidatos:
        if valor:
            return comprador_citado(str(valor)) or str(valor)
    return None


def _produto_do_resultado(nome_funcao: str, args: dict[str, Any], resultado: dict[str, Any]) -> str | None:
    """Nome do produto em foco, na forma que cada ferramenta devolve."""
    item = resultado.get("item")  # verificar_conformidade traz o item avaliado
    if isinstance(item, dict) and item.get("produto"):
        return str(item["produto"])
    produto = resultado.get("produto")
    if not produto and nome_funcao == "rastrear_lote":
        produto = (resultado.get("lote") or {}).get("produto")
    return str(produto) if produto else None
