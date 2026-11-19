"""O gabarito da #6 como dado: casos, turnos, relógio da sessão e requisitos funcionais.

Os YAML de `tests/gabarito/` são a fonte; aqui eles viram `Caso` com o que a
avaliação ponta a ponta (#14) precisa saber de cada um — sem alterar o
gabarito. O mapeamento caso → requisito funcional (docs/01 §6) é explícito e
revisável: as regras ficam em `requisitos_funcionais`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
PASTA_GABARITO = RAIZ / "tests" / "gabarito"
ARQUIVO_PEDIDOS = RAIZ / "data" / "pedidos.json"

# Dia do dataset (os 15 pedidos chegam entre 28 e 30/10/2026): relógio padrão
# dos casos que não trazem data própria — o mesmo da demo.
DATA_REFERENCIA_PADRAO = "2026-10-30"

ARQUIVOS_GABARITO = (
    "anti-alucinacao.yaml",
    "casos-certificacoes.yaml",
    "casos-consulta-documental.yaml",
    "casos-contexto.yaml",
    "casos-produtores.yaml",
    "casos-triagem.yaml",
)

# Conjuntos avaliados: o gabarito da #6 (a nota do critério de aceite) e as
# variações coloquiais de robustez, fora do gabarito (tarefa da #14).
CONJUNTOS = {
    "gabarito": (PASTA_GABARITO, ARQUIVOS_GABARITO),
    "robustez": (RAIZ / "tests" / "robustez", ("variacoes-coloquiais.yaml",)),
}

# Os três gargalos do docs/01 (o gabarito escreve o documental de dois jeitos).
DESAFIOS = {
    "Triagem de pedidos": "Triagem de pedidos",
    "Consulta documental": "Consulta documental",
    "Consulta inteligente à base documental": "Consulta documental",
    "Comunicação com produtores": "Comunicação com produtores",
}

# Requisitos funcionais do docs/01 §6 (transcrição resumida).
REQUISITOS_FUNCIONAIS = {
    "RF1": "Interface conversacional por texto",
    "RF2": "Português coloquial, abreviações e informação implícita",
    "RF3": "Resposta documental precisa, indicando o documento de origem",
    "RF4": "Relatórios e notificações autônomos",
    "RF5": "Contexto mantido ao longo da sessão",
    "RF6": "Dizer que não sabe, sem inventar (anti-alucinação)",
}

_TURNO_RE = re.compile(r"^\s*Turno\s+\d+\s*:\s*(.+?)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Caso:
    """Um caso do gabarito, com os campos do YAML e o que deriva deles."""

    id: str
    arquivo: str
    desafio: str
    requisito: str
    entrada: str
    esperado: str
    funcoes_esperadas: tuple[str, ...]
    deve_conter: tuple[str, ...]
    nao_deve_conter: tuple[str, ...]
    fonte: tuple[str, ...]
    pedido_id: str | None = None
    data_recebimento: str | None = None
    turnos: tuple[str, ...] = field(default=())

    @property
    def anti_alucinacao(self) -> bool:
        return "RF6" in requisitos_funcionais(self)

    @property
    def documental(self) -> bool:
        """Resposta que precisa citar documento (RF3) — recusas (RF6) ficam de fora."""
        return "RF3" in requisitos_funcionais(self) and not self.anti_alucinacao

    @property
    def total_criterios(self) -> int:
        return len(self.deve_conter) + len(self.nao_deve_conter)


def _turnos(entrada: str) -> tuple[str, ...]:
    """'Turno 1: ...\\nTurno 2: ...' vira um turno por linha; o resto é um turno só."""
    linhas = [linha for linha in str(entrada).splitlines() if linha.strip()]
    turnos = [m.group(1) for linha in linhas if (m := _TURNO_RE.match(linha))]
    if turnos and len(turnos) == len(linhas):
        return tuple(turnos)
    return (str(entrada).strip(),)


def _caso(dados: dict[str, Any], arquivo: str) -> Caso:
    entrada = str(dados["entrada"])
    return Caso(
        id=str(dados["id"]),
        arquivo=arquivo,
        desafio=DESAFIOS.get(str(dados["desafio"]).strip(), str(dados["desafio"]).strip()),
        requisito=str(dados["requisito"]).strip(),
        entrada=entrada.strip(),
        esperado=str(dados["esperado"]).strip(),
        funcoes_esperadas=tuple(dados.get("funcoes_esperadas") or ()),
        deve_conter=tuple(str(c) for c in dados.get("deve_conter") or ()),
        nao_deve_conter=tuple(str(c) for c in dados.get("nao_deve_conter") or ()),
        fonte=tuple(str(f) for f in dados.get("fonte") or ()),
        pedido_id=dados.get("pedido_id"),
        data_recebimento=dados.get("data_recebimento"),
        turnos=_turnos(entrada),
    )


@lru_cache(maxsize=None)
def carregar_casos(conjunto: str = "gabarito") -> tuple[Caso, ...]:
    """Os casos do conjunto (`gabarito` ou `robustez`), na ordem dos arquivos."""
    pasta, arquivos = CONJUNTOS[conjunto]
    casos: list[Caso] = []
    for nome in arquivos:
        for dados in yaml.safe_load((pasta / nome).read_text(encoding="utf-8")):
            casos.append(_caso(dados, nome))
    return tuple(casos)


def caso_por_id(caso_id: str) -> Caso:
    for conjunto in CONJUNTOS:
        for caso in carregar_casos(conjunto):
            if caso.id == caso_id:
                return caso
    raise KeyError(caso_id)


@lru_cache(maxsize=1)
def _datas_dos_pedidos() -> dict[str, str]:
    registros = json.loads(ARQUIVO_PEDIDOS.read_text(encoding="utf-8"))
    return {r["id"]: str(r["data_recebimento"])[:10] for r in registros}


def data_referencia(caso: Caso) -> str:
    """Relógio da sessão do caso: a data do caso, senão a do pedido, senão a da demo."""
    if caso.data_recebimento:
        return datetime.strptime(str(caso.data_recebimento).strip(), "%d/%m/%Y %H:%M:%S").date().isoformat()
    if caso.pedido_id and caso.pedido_id in _datas_dos_pedidos():
        return _datas_dos_pedidos()[caso.pedido_id]
    return DATA_REFERENCIA_PADRAO


def requisitos_funcionais(caso: Caso) -> tuple[str, ...]:
    """RFs do docs/01 §6 que o caso exercita.

    - RF1: todo caso (a interação é sempre por texto).
    - RF2: casos TRI-* (as 15 mensagens como o cliente escreveu) e ROB-* (robustez).
    - RF3: desafio "Consulta documental".
    - RF4: casos de comunicação com produtores (relatórios e notificações).
    - RF5: casos multi-turno.
    - RF6: casos ANTI-* e os que o gabarito escreve como "sem inventar"/"lacunas".
    """
    rfs = ["RF1"]
    if caso.id.startswith(("TRI-", "ROB-")):
        rfs.append("RF2")
    if caso.desafio == "Consulta documental":
        rfs.append("RF3")
    if caso.id.startswith("PROD-"):
        rfs.append("RF4")
    if len(caso.turnos) > 1:
        rfs.append("RF5")
    requisito = caso.requisito.lower()
    if caso.id.startswith("ANTI-") or "inventar" in requisito or "lacuna" in requisito:
        rfs.append("RF6")
    return tuple(rfs)


def arquivos_de_fonte(caso: Caso) -> tuple[str, ...]:
    """Arquivos de `data/` que o gabarito dá como fonte (sem o prefixo, sem anotação)."""
    arquivos: list[str] = []
    for item in caso.fonte:
        base = item.split(" (")[0].strip()
        if base.startswith("data/"):
            base = base[len("data/"):]
            if base and base not in arquivos:
                arquivos.append(base)
    return tuple(arquivos)
