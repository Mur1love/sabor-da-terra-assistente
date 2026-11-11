"""Lê os 6 arquivos de data/ e monta as tabelas no formato de esquema.py.

A pasta data/ não é alterada: a limpeza acontece em memória. Os CSVs são lidos
como texto para não perder o zero da agência "0437" nem o "n/d" dos preços.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from sabor_da_terra.dados import normalizacao as n
from sabor_da_terra.dados.catalogo import Catalogo
from sabor_da_terra.dados.esquema import colunas

PASTA_DADOS = Path(__file__).resolve().parents[2] / "data"

_MESES_CSV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@dataclass(frozen=True)
class BaseDados:
    produtores: pd.DataFrame
    produtor_produtos: pd.DataFrame
    produtos: pd.DataFrame
    sazonalidade: pd.DataFrame
    pedidos: pd.DataFrame
    transacoes: pd.DataFrame
    lotes: pd.DataFrame
    catalogo: Catalogo


# Lê um CSV de data/ com tudo como texto, sem o pandas converter nada.
def _ler_csv(pasta: Path, nome: str) -> pd.DataFrame:
    return pd.read_csv(pasta / nome, dtype=str, keep_default_na=False, encoding="utf-8")


# Deixa só as colunas do esquema, na ordem dele, com todo dado ausente como None.
def _ordenar(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    df = df[colunas(tabela)].reset_index(drop=True)
    for coluna in df.columns:
        if df[coluna].isna().any():
            df[coluna] = df[coluna].astype(object).where(df[coluna].notna(), None)
    return df


# Monta a tabela de preços: números limpos, unidade padronizada e flags de oferta.
def _carregar_produtos(pasta: Path) -> pd.DataFrame:
    cru = _ler_csv(pasta, "tabela_precos_outubro_2026.csv")
    df = pd.DataFrame(
        {
            "produto": cru["produto"].map(n.texto),
            "unidade": cru["unidade"].map(n.chave),
            "preco_convencional": cru["preco_convencional"].map(n.numero),
            "preco_organico": cru["preco_organico"].map(n.numero),
            "desconto_atacado_pct": cru["desconto_atacado_pct"].map(n.numero).fillna(0.0),
            "volume_minimo_atacado": cru["volume_minimo_atacado_kg"].map(n.numero).fillna(0.0),
            "observacao": cru["observacao"].map(n.texto),
        }
    )
    df["unidade"] = df["unidade"].replace({"duzia": "dúzia", "maco": "maço"})
    df["tem_oferta_convencional"] = df["preco_convencional"].notna()
    df["tem_oferta_organica"] = df["preco_organico"].notna()
    return df


# Passa a sazonalidade de uma coluna por mês para uma linha por produto e mês.
def _carregar_sazonalidade(pasta: Path) -> pd.DataFrame:
    cru = _ler_csv(pasta, "sazonalidade.csv")
    linhas = [
        {
            "produto": n.texto(linha["produto"]),
            "mes": numero_mes,
            "nivel": n.status(linha[sigla]),
            "observacao": n.texto(linha["observacao"]),
        }
        for _, linha in cru.iterrows()
        for numero_mes, sigla in enumerate(_MESES_CSV, start=1)
    ]
    return pd.DataFrame(linhas)


# Monta o cadastro de produtores e liga cada um aos produtos do catálogo.
def _carregar_produtores(pasta: Path, catalogo: Catalogo) -> tuple[pd.DataFrame, pd.DataFrame]:
    cru = _ler_csv(pasta, "produtores.csv")
    df = pd.DataFrame(
        {
            "produtor_id": cru["id"].str.strip().str.upper(),
            "nome": cru["nome_completo"].map(n.texto),
            "cpf": cru["cpf"].map(n.texto),
            "data_nascimento": cru["data_nascimento"].map(n.data),
            "telefone": cru["telefone"].map(n.texto),
            "email": cru["email"].map(n.texto),
            "endereco": cru["endereco"].map(n.texto),
            "municipio": cru["municipio"].map(n.texto),
            "certificacao_organica": cru["certificacao_organica"].map(n.booleano),
            "validade_certificacao": cru["validade_certificacao"].map(n.data),
            "chave_pix": cru["chave_pix"].map(n.texto),
            "banco": cru["banco"].map(n.texto),
            "agencia": cru["agencia"].map(n.texto),
            "conta_corrente": cru["conta_corrente"].map(n.texto),
            "status": cru["status"].map(n.status),
        }
    )
    # P015 está "inativo": continua no cadastro, mas não recebe alocação.
    df["ativo"] = df["status"].eq("ativo")

    ligacoes = []
    for produtor_id, lista in zip(df["produtor_id"], cru["produtos"]):
        for produto_cadastrado in filter(None, (n.texto(p) for p in lista.split(","))):
            resolucao = catalogo.resolver(produto_cadastrado)
            ligacoes.append(
                {
                    "produtor_id": produtor_id,
                    "produto_cadastrado": produto_cadastrado,
                    "produto": resolucao.base,
                }
            )
    return _ordenar(df, "produtores"), _ordenar(pd.DataFrame(ligacoes), "produtor_produtos")


# Lê os pedidos do JSON e padroniza canal, status e datas.
def _carregar_pedidos(pasta: Path) -> pd.DataFrame:
    registros = json.loads((pasta / "pedidos.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(
        {
            "pedido_id": [r["id"] for r in registros],
            "data_recebimento": [n.data_hora(r["data_recebimento"]) for r in registros],
            "canal": [n.status(r["canal"]) for r in registros],
            "remetente": [n.texto(r.get("remetente")) for r in registros],
            "comprador": [n.texto(r.get("comprador")) for r in registros],
            "mensagem_original": [r["mensagem_original"] for r in registros],
            "status": [n.status(r["status"]) for r in registros],
        }
    )
    return _ordenar(df, "pedidos")


# Acha o nome do produto no catálogo e a unidade em que ele é vendido.
def _produto_e_unidade(nome: str, catalogo: Catalogo, unidades: dict[str, str]) -> tuple[str, str | None]:
    resolucao = catalogo.resolver(nome)
    base = resolucao.base or n.texto(nome)
    variantes = catalogo.variantes(base) if base else []
    return base, unidades.get(variantes[0]) if variantes else None


# Monta a tabela de vendas do financeiro, sem nome e CPF do produtor.
def _carregar_transacoes(pasta: Path, catalogo: Catalogo, unidades: dict[str, str]) -> pd.DataFrame:
    cru = _ler_csv(pasta, "financeiro.csv")
    produto_unidade = [_produto_e_unidade(p, catalogo, unidades) for p in cru["produto"]]
    df = pd.DataFrame(
        {
            "id_transacao": cru["id_transacao"].str.strip().str.upper(),
            "data": cru["data"].map(n.data),
            "produtor_id": cru["produtor_id"].str.strip().str.upper(),
            "comprador": cru["comprador"].map(n.texto),
            "tipo": cru["tipo"].map(n.status),
            "produto": [p for p, _ in produto_unidade],
            "quantidade": cru["quantidade_kg"].map(n.numero),
            "unidade": [u for _, u in produto_unidade],
            "valor_unitario": cru["valor_unitario"].map(n.numero),
            "valor_total": cru["valor_total"].map(n.numero),
            "forma_pagamento": cru["forma_pagamento"].map(n.texto),
            "status_pagamento": cru["status_pagamento"].map(n.status),
            "data_vencimento": cru["data_vencimento"].map(n.data),
            "data_pagamento": cru["data_pagamento"].map(n.data),
            "chave_pix_deposito": cru["chave_pix_deposito"].map(n.texto),
            "observacao": cru["observacao"].map(n.texto),
        }
    )
    return _ordenar(df, "transacoes")


# Monta a tabela de lotes e liga cada lote à sua venda.
def _carregar_lotes(
    pasta: Path, catalogo: Catalogo, unidades: dict[str, str], transacoes: pd.DataFrame
) -> pd.DataFrame:
    cru = _ler_csv(pasta, "lotes.csv")
    produto_unidade = [_produto_e_unidade(p, catalogo, unidades) for p in cru["produto"]]
    temperatura = cru["temperatura_transporte_c"].map(n.chave)
    df = pd.DataFrame(
        {
            "lote_id": cru["lote_id"].str.strip().str.upper(),
            "data_colheita": cru["data_colheita"].map(n.data),
            "data_entrega": cru["data_entrega"].map(n.data),
            "produtor_id": cru["produtor_id"].str.strip().str.upper(),
            "produto": [p for p, _ in produto_unidade],
            "quantidade": cru["quantidade_kg"].map(n.numero),
            "unidade": [u for _, u in produto_unidade],
            "comprador": cru["comprador"].map(n.texto),
            "pedido_id": cru["pedido_id"].map(n.texto),
            "temperatura_transporte_c": temperatura.map(n.numero),
            "transporte_ambiente": temperatura.eq("ambiente"),
            "validade": cru["validade"].map(n.data),
            "inspecao_visual": cru["inspecao_visual"].map(n.status),
            "observacao": cru["observacao"].map(n.texto),
        }
    )
    df["id_transacao"] = [_transacao_do_lote(lote, transacoes) for _, lote in df.iterrows()]
    return _ordenar(df, "lotes")


# Procura a venda de um lote pelo produtor, produto, comprador e quantidade.
def _transacao_do_lote(lote: pd.Series, transacoes: pd.DataFrame) -> str | None:
    candidatas = transacoes[
        (transacoes["produtor_id"] == lote["produtor_id"])
        & (transacoes["produto"] == lote["produto"])
        & (transacoes["comprador"] == lote["comprador"])
        & (transacoes["quantidade"] == lote["quantidade"])
    ]
    return candidatas["id_transacao"].iloc[0] if len(candidatas) == 1 else None


# Lê todos os arquivos e devolve as tabelas prontas.
def carregar(pasta: Path | str = PASTA_DADOS) -> BaseDados:

    pasta = Path(pasta)
    produtos = _carregar_produtos(pasta)
    sazonalidade = _carregar_sazonalidade(pasta)
    catalogo = Catalogo(list(produtos["produto"]), list(sazonalidade["produto"].unique()))
    produtos["produto_base"] = produtos["produto"].map(catalogo.base_da_variante)
    unidades = dict(zip(produtos["produto"], produtos["unidade"]))

    produtores, produtor_produtos = _carregar_produtores(pasta, catalogo)
    transacoes = _carregar_transacoes(pasta, catalogo, unidades)
    return BaseDados(
        produtores=produtores,
        produtor_produtos=produtor_produtos,
        produtos=_ordenar(produtos, "produtos"),
        sazonalidade=_ordenar(sazonalidade, "sazonalidade"),
        pedidos=_carregar_pedidos(pasta),
        transacoes=transacoes,
        lotes=_carregar_lotes(pasta, catalogo, unidades, transacoes),
        catalogo=catalogo,
    )


# Carrega os dados uma vez e reaproveita nas chamadas seguintes.
@lru_cache(maxsize=1)
def obter_base() -> BaseDados:

    return carregar()
