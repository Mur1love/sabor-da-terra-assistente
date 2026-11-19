"""Cliente híbrido: repete o que já foi gravado e grava só o que falta.

Usado nas rodadas reais da avaliação (#14) e na gravação do CTX-001 (#12).
Cada chamada procura a fixture; se ela existe, é repetida sem gastar cota;
se falta, é gravada com `LLM_MODO=gravar`. Rodar de novo depois de completar
a gravação não gasta nada. Os clientes que as ferramentas criam por dentro
(planner e busca do RAG, extração da triagem) também passam pelo modo
híbrido — sem isso a replay não acharia as chamadas deles.

O `RegistroDeConsumo` soma o que TODAS as instâncias fizeram (o cliente do
assistente e os internos das ferramentas): é a medida de cota da rodada.
"""

from __future__ import annotations

import importlib
from collections import Counter
from dataclasses import dataclass, field

from sabor_da_terra.llm.cliente import FixtureAusenteError, LLMClient

# Fallback da composição nas rodadas da avaliação: a gravação e a replay
# (tests/test_gabarito.py) precisam usar o mesmo para as chaves baterem.
FALLBACK_DA_AVALIACAO = "gemini-3.5-flash-lite"

# Módulos que criam o próprio LLMClient por dentro das ferramentas.
MODULOS_COM_CLIENTE_INTERNO = (
    "sabor_da_terra.rag.responder",
    "sabor_da_terra.rag.recuperacao",
    "sabor_da_terra.triagem.extrair",
)


@dataclass
class RegistroDeConsumo:
    """Consumo somado de todas as instâncias do cliente híbrido."""

    chamadas_reais: Counter = field(default_factory=Counter)  # por modelo
    replays: int = 0
    failovers: int = 0
    # Toda chamada por papel (gravada OU repetida): o que a conversa gastaria ao vivo.
    demanda_por_papel: Counter = field(default_factory=Counter)

    def zerar(self) -> None:
        self.chamadas_reais.clear()
        self.replays = 0
        self.failovers = 0
        self.demanda_por_papel.clear()

    def instantaneo(self) -> dict:
        return {
            "chamadas_reais": dict(sorted(self.chamadas_reais.items())),
            "replays": self.replays,
            "failovers": self.failovers,
            "demanda_por_papel": dict(sorted(self.demanda_por_papel.items())),
        }


REGISTRO = RegistroDeConsumo()


class ClienteHibrido(LLMClient):
    """Replay em fixture; quando a fixture falta, grava aquela chamada única."""

    def __init__(self, *_args, **_kwargs) -> None:
        super().__init__(modo="fixture")
        self._gravador = LLMClient(modo="gravar", pasta_fixtures=self._pasta_fixtures, dormir=self._dormir)

    def _gravar(self, acao):
        antes = Counter(self._gravador.chamadas_por_modelo())
        failovers_antes = self._gravador.failovers()
        try:
            return acao()
        finally:
            REGISTRO.chamadas_reais.update(Counter(self._gravador.chamadas_por_modelo()) - antes)
            REGISTRO.failovers += self._gravador.failovers() - failovers_antes

    def gerar(self, papel, prompt, **config_geracao):
        REGISTRO.demanda_por_papel[papel.value] += 1
        try:
            resposta = super().gerar(papel, prompt, **config_geracao)
        except FixtureAusenteError:
            return self._gravar(lambda: self._gravador.gerar(papel, prompt, **config_geracao))
        REGISTRO.replays += 1
        return resposta

    def embedar(self, texto: str) -> list[float]:
        REGISTRO.demanda_por_papel["embedding"] += 1
        try:
            vetor = super().embedar(texto)
        except FixtureAusenteError:
            return self._gravar(lambda: self._gravador.embedar(texto))
        REGISTRO.replays += 1
        return vetor


def ligar_clientes_internos(classe: type[LLMClient] = ClienteHibrido) -> None:
    """Faz as ferramentas criarem `classe` no lugar do `LLMClient`."""
    for nome in MODULOS_COM_CLIENTE_INTERNO:
        setattr(importlib.import_module(nome), "LLMClient", classe)
