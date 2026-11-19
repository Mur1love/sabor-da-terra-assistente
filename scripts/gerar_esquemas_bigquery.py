"""Gera infra/bigquery/<tabela>.json a partir de sabor_da_terra/dados/esquema.py.

O esquema da camada de dados (etapa 4) é a fonte única: o Terraform lê estes
JSON para criar as tabelas do BigQuery, e o teste test_infra.py falha se os
arquivos saírem de sincronia com o esquema.py.

Rodar: python -m scripts.gerar_esquemas_bigquery
"""

from __future__ import annotations

import json
from pathlib import Path

from sabor_da_terra.dados.esquema import TABELAS, Coluna

PASTA_BIGQUERY = Path(__file__).resolve().parents[1] / "infra" / "bigquery"

DESCRICAO_SENSIVEL = "Dado pessoal ou bancário: as ferramentas do assistente nunca devolvem este campo."


# Uma coluna no formato de esquema do BigQuery (o mesmo do `bq mk --schema`).
def campo_bigquery(coluna: Coluna) -> dict:
    campo = {
        "name": coluna.nome,
        "type": coluna.tipo,
        "mode": "REQUIRED" if coluna.obrigatoria else "NULLABLE",
    }
    if coluna.sensivel:
        campo["description"] = DESCRICAO_SENSIVEL
    return campo


# Texto do arquivo de uma tabela, com quebra de linha no fim.
def esquema_json(tabela: str) -> str:
    campos = [campo_bigquery(coluna) for coluna in TABELAS[tabela]]
    return json.dumps(campos, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    PASTA_BIGQUERY.mkdir(parents=True, exist_ok=True)
    for tabela in TABELAS:
        destino = PASTA_BIGQUERY / f"{tabela}.json"
        destino.write_text(esquema_json(tabela), encoding="utf-8")
        print(f"gravado {destino.relative_to(PASTA_BIGQUERY.parents[1])}")


if __name__ == "__main__":
    main()
