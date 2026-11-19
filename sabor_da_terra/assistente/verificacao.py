"""Trava de fatos: nada que as funções não devolveram chega à tela.

O texto final do turno é escrito por um LLM — e LLM erra: troca um código,
soma valores por conta própria, "lembra" uma data. O dado certo existe (veio
das funções); o risco está na escrita. Esta trava confere, de forma
determinística e sem nova chamada à API, os fatos verificáveis da resposta
contra o universo do turno (saídas das funções + pergunta + estado):

- códigos do dataset: P003, PED-2026-006, LOT-2026-0089, FIN-2026-013,
  REN-2026-0456, PE-SIE-0892, NC-001…;
- valores em R$ (o LLM não faz contas — docs/04: total que não veio de uma
  função é calculado pelo modelo e sai);
- datas completas (dd/mm/aaaa).

A frase que traz um fato sem respaldo sai inteira; se algo saiu, a resposta
avisa. Não é um juiz de sentido — é a garantia mínima de que código, valor e
data na tela existem nos dados.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

logger = logging.getLogger("sabor_da_terra.assistente")

AVISO_FATOS_REMOVIDOS = (
    "_Parte da resposta foi omitida por não estar nos dados consultados neste turno._"
)

# Códigos: P003 e identificadores com hífen e ao menos um dígito (PED-2026-006,
# LOT-2026-0089, FIN-2026-013, REN-2026-0456, PE-SIE-0892, ORG-PE-2024-003876).
_CODIGO_RE = re.compile(r"\b(?:P\d{3}|(?=[A-Z0-9-]*\d)[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\b")
_VALOR_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)")
_DATA_BR_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
_DATA_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})")
_NUMERO_RE = re.compile(r"\d+(?:[.,]\d+)*")
# Fim de frase seguido de espaço: a unidade que sai quando traz fato sem respaldo.
_FIM_DE_FRASE_RE = re.compile(r"(?<=[.!?])\s+")


def _valor_brl(texto: str) -> float | None:
    """'4.500,00' → 4500.0; '32' → 32.0."""
    try:
        return round(float(texto.replace(".", "").replace(",", ".")), 2)
    except ValueError:
        return None


def _numeros_de_texto(texto: str) -> set[float]:
    """Números de um texto livre, lidos nos formatos BR e EN (4.500,00 / 4500.0)."""
    numeros: set[float] = set()
    for bruto in _NUMERO_RE.findall(texto):
        for candidato in (bruto.replace(".", "").replace(",", "."), bruto.replace(",", "")):
            try:
                numeros.add(round(float(candidato), 2))
            except ValueError:
                pass
    return numeros


def _data_iso(dia: str, mes: str, ano: str) -> str | None:
    try:
        return date(int(ano), int(mes), int(dia)).isoformat()
    except ValueError:
        return None


@dataclass
class Universo:
    """Fatos que o turno pode afirmar: tudo que veio das funções, da pergunta e do estado."""

    codigos: set[str] = field(default_factory=set)
    valores: set[float] = field(default_factory=set)
    datas: set[str] = field(default_factory=set)

    @classmethod
    def de(cls, *fontes: Any) -> "Universo":
        universo = cls()
        for fonte in fontes:
            universo._absorver(fonte)
        return universo

    def _absorver(self, valor: Any) -> None:
        if isinstance(valor, bool) or valor is None:
            return
        if isinstance(valor, (int, float)):
            self.valores.add(round(float(valor), 2))
            return
        if isinstance(valor, dict):
            for chave, item in valor.items():
                self._absorver(str(chave))
                self._absorver(item)
            return
        if isinstance(valor, (list, tuple, set)):
            for item in valor:
                self._absorver(item)
            return
        texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False, default=str)
        self.codigos.update(c.upper() for c in _CODIGO_RE.findall(texto.upper()))
        self.valores.update(_numeros_de_texto(texto))
        self.datas.update(f"{a}-{m}-{d}" for a, m, d in _DATA_ISO_RE.findall(texto))
        self.datas.update(filter(None, (_data_iso(d, m, a) for d, m, a in _DATA_BR_RE.findall(texto))))


def fatos_sem_respaldo(trecho: str, universo: Universo) -> list[str]:
    """Códigos, valores e datas do trecho que não estão no universo do turno."""
    faltando: list[str] = []
    for codigo in _CODIGO_RE.findall(trecho):
        if codigo.upper() not in universo.codigos:
            faltando.append(codigo)
    for bruto in _VALOR_RE.findall(trecho):
        valor = _valor_brl(bruto)
        if valor is not None and valor not in universo.valores:
            faltando.append(f"R$ {bruto}")
    for dia, mes, ano in _DATA_BR_RE.findall(trecho):
        iso = _data_iso(dia, mes, ano)
        if iso and iso not in universo.datas:
            faltando.append(f"{dia}/{mes}/{ano}")
    return faltando


def so_fatos_com_respaldo(texto: str, universo: Universo) -> str:
    """Tira as frases com fato sem respaldo; avisa no fim se alguma saiu."""
    removidos: list[str] = []
    linhas_mantidas: list[str] = []
    for linha in texto.split("\n"):
        frases = _FIM_DE_FRASE_RE.split(linha)
        mantidas = []
        for frase in frases:
            faltando = fatos_sem_respaldo(frase, universo)
            if faltando:
                removidos.extend(faltando)
            else:
                mantidas.append(frase)
        if mantidas or not linha.strip():
            linhas_mantidas.append(" ".join(mantidas))
    if not removidos:
        return texto
    logger.info("fatos_removidos=%s", sorted(set(removidos)))
    limpo = re.sub(r"\n{3,}", "\n\n", "\n".join(linhas_mantidas)).strip()
    return f"{limpo}\n\n{AVISO_FATOS_REMOVIDOS}" if limpo else AVISO_FATOS_REMOVIDOS
