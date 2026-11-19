"""Artefatos de implantação (etapa 15): o que dá para garantir lendo os arquivos.

Nada aqui fala com a nuvem. `terraform validate` e `docker build` rodam fora
da suíte (comandos no docs/04 §11).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.gerar_esquemas_bigquery import PASTA_BIGQUERY, esquema_json
from sabor_da_terra.dados.esquema import TABELAS

RAIZ = Path(__file__).resolve().parents[1]
INFRA = RAIZ / "infra"


@pytest.mark.parametrize("tabela", sorted(TABELAS))
def test_esquema_bigquery_igual_ao_da_camada_de_dados(tabela):
    arquivo = PASTA_BIGQUERY / f"{tabela}.json"
    assert arquivo.exists(), "rode: python -m scripts.gerar_esquemas_bigquery"
    assert arquivo.read_text(encoding="utf-8") == esquema_json(tabela), (
        f"{arquivo.name} saiu de sincronia com esquema.py: python -m scripts.gerar_esquemas_bigquery"
    )


def test_nenhum_segredo_ou_id_real_nos_artefatos():
    arquivos = [RAIZ / "Dockerfile", RAIZ / ".dockerignore"] + [
        arquivo for arquivo in INFRA.rglob("*") if arquivo.is_file() and ".terraform" not in arquivo.parts
    ]
    for arquivo in arquivos:
        texto = arquivo.read_text(encoding="utf-8")
        assert not re.search(r"AIza[0-9A-Za-z_\-]{35}", texto), f"chave de API em {arquivo.name}"
        assert "BEGIN PRIVATE KEY" not in texto, arquivo.name
        assert not re.search(r'project(_id)?\s*=\s*"(?!<)[a-z][a-z0-9-]{5,29}"', texto), (
            f"ID de projeto literal em {arquivo.name}"
        )
