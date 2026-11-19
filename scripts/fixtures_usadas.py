"""Quais fixtures de `tests/fixtures/llm` a suíte realmente lê — e quais ficaram órfãs.

Uso:
    python -m scripts.fixtures_usadas                  # resumo: usadas, órfãs, novas
    python -m scripts.fixtures_usadas --listar-usadas  # um caminho por linha (para o git add)
    python -m scripts.fixtures_usadas --listar-orfas

O nome de cada fixture é o hash do pedido (papel, modelo, prompt, config):
mudar um prompt muda o hash, e a gravação antiga vira órfã — nenhum teste a
lê mais. Este script roda a suíte inteira em modo fixture registrando cada
arquivo lido; o que não foi lido é órfão. Não apaga nada: a decisão é de quem
for commitar.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import subprocess
from pathlib import Path

import pytest

from sabor_da_terra.llm.cliente import LLMClient

RAIZ = Path(__file__).resolve().parents[1]
PASTA_FIXTURES = RAIZ / "tests" / "fixtures" / "llm"


class _RegistroDeLeitura:
    """Plugin do pytest: anota cada fixture que o `LLMClient` lê durante a suíte."""

    def __init__(self) -> None:
        self.lidas: set[Path] = set()

    def pytest_sessionstart(self, session) -> None:  # noqa: ARG002 — assinatura do hook
        original = LLMClient._ler_fixture
        lidas = self.lidas

        def ler_e_anotar(cliente, caminho):
            caminho = Path(caminho)
            if caminho.exists():
                lidas.add(caminho.resolve())
            return original(cliente, caminho)

        LLMClient._ler_fixture = ler_e_anotar


def fixtures_lidas_pela_suite() -> set[Path]:
    registro = _RegistroDeLeitura()
    with contextlib.redirect_stdout(io.StringIO()):
        pytest.main(["-q", "-p", "no:cacheprovider", str(RAIZ / "tests")], plugins=[registro])
    return registro.lidas


def nao_versionadas() -> set[Path]:
    saida = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", str(PASTA_FIXTURES)],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    return {(RAIZ / linha).resolve() for linha in saida.splitlines() if linha.endswith(".json")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--listar-usadas", action="store_true", help="fixtures NOVAS que a suíte lê")
    grupo.add_argument("--listar-orfas", action="store_true", help="fixtures que nenhum teste lê")
    args = parser.parse_args(argv)

    todas = {p.resolve() for p in PASTA_FIXTURES.rglob("*.json")}
    lidas = fixtures_lidas_pela_suite() & todas  # fora disso: gravações em tmp_path dos testes unitários
    novas = nao_versionadas()
    orfas = todas - lidas
    rel = lambda caminhos: sorted(str(p.relative_to(RAIZ)) for p in caminhos)  # noqa: E731

    if args.listar_usadas:
        print("\n".join(rel(novas & lidas)))
    elif args.listar_orfas:
        print("\n".join(rel(orfas)))
    else:
        print(f"Fixtures: {len(todas)} no total, {len(lidas)} lidas pela suíte, {len(orfas)} órfãs.")
        print(f"Não versionadas: {len(novas)} — {len(novas & lidas)} usadas, {len(novas & orfas)} órfãs.")
        print(f"Versionadas que viraram órfãs: {len(orfas - novas)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
