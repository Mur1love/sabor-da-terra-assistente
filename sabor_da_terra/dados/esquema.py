"""Colunas e tipos das tabelas, iguais aos que vão para o BigQuery.

Em relação aos arquivos de data/: nome e CPF do produtor ficam só no cadastro,
quantidade_kg virou quantidade + unidade, a sazonalidade tem uma linha por
produto e mês, e produtor_produtos liga cada produtor aos produtos do catálogo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Coluna:
    nome: str
    tipo: str  # tipo do BigQuery: STRING, DATE, DATETIME, NUMERIC, INT64, BOOL
    obrigatoria: bool = False
    sensivel: bool = False  # dado pessoal ou bancário: as ferramentas nunca devolvem


TABELAS: dict[str, list[Coluna]] = {
    "produtores": [
        Coluna("produtor_id", "STRING", obrigatoria=True),
        Coluna("nome", "STRING", obrigatoria=True),
        Coluna("cpf", "STRING", sensivel=True),
        Coluna("data_nascimento", "DATE", sensivel=True),
        Coluna("telefone", "STRING", sensivel=True),
        Coluna("email", "STRING", sensivel=True),
        Coluna("endereco", "STRING", sensivel=True),
        Coluna("municipio", "STRING"),
        Coluna("certificacao_organica", "BOOL", obrigatoria=True),
        Coluna("validade_certificacao", "DATE"),
        Coluna("chave_pix", "STRING", sensivel=True),
        Coluna("banco", "STRING", sensivel=True),
        Coluna("agencia", "STRING", sensivel=True),
        Coluna("conta_corrente", "STRING", sensivel=True),
        Coluna("status", "STRING", obrigatoria=True),
        Coluna("ativo", "BOOL", obrigatoria=True),
    ],
    "produtor_produtos": [
        Coluna("produtor_id", "STRING", obrigatoria=True),
        Coluna("produto_cadastrado", "STRING", obrigatoria=True),
        Coluna("produto", "STRING"),  # nome no catálogo; nulo se não há preço/sazonalidade
    ],
    "produtos": [
        Coluna("produto", "STRING", obrigatoria=True),
        Coluna("produto_base", "STRING", obrigatoria=True),
        Coluna("unidade", "STRING", obrigatoria=True),
        Coluna("preco_convencional", "NUMERIC"),
        Coluna("preco_organico", "NUMERIC"),
        Coluna("tem_oferta_convencional", "BOOL", obrigatoria=True),
        Coluna("tem_oferta_organica", "BOOL", obrigatoria=True),
        Coluna("desconto_atacado_pct", "NUMERIC", obrigatoria=True),
        Coluna("volume_minimo_atacado", "NUMERIC", obrigatoria=True),
        Coluna("observacao", "STRING"),
    ],
    "sazonalidade": [
        Coluna("produto", "STRING", obrigatoria=True),
        Coluna("mes", "INT64", obrigatoria=True),
        Coluna("nivel", "STRING", obrigatoria=True),
        Coluna("observacao", "STRING"),
    ],
    "pedidos": [
        Coluna("pedido_id", "STRING", obrigatoria=True),
        Coluna("data_recebimento", "DATETIME", obrigatoria=True),
        Coluna("canal", "STRING", obrigatoria=True),
        Coluna("remetente", "STRING"),
        Coluna("comprador", "STRING"),
        Coluna("mensagem_original", "STRING", obrigatoria=True),
        Coluna("status", "STRING", obrigatoria=True),
    ],
    "transacoes": [
        Coluna("id_transacao", "STRING", obrigatoria=True),
        Coluna("data", "DATE", obrigatoria=True),
        Coluna("produtor_id", "STRING", obrigatoria=True),
        Coluna("comprador", "STRING", obrigatoria=True),
        Coluna("tipo", "STRING", obrigatoria=True),
        Coluna("produto", "STRING", obrigatoria=True),
        Coluna("quantidade", "NUMERIC", obrigatoria=True),
        Coluna("unidade", "STRING", obrigatoria=True),
        Coluna("valor_unitario", "NUMERIC", obrigatoria=True),
        Coluna("valor_total", "NUMERIC", obrigatoria=True),
        Coluna("forma_pagamento", "STRING", obrigatoria=True),
        Coluna("status_pagamento", "STRING", obrigatoria=True),
        Coluna("data_vencimento", "DATE"),
        Coluna("data_pagamento", "DATE"),
        Coluna("chave_pix_deposito", "STRING", sensivel=True),
        Coluna("observacao", "STRING"),
    ],
    "lotes": [
        Coluna("lote_id", "STRING", obrigatoria=True),
        Coluna("data_colheita", "DATE"),
        Coluna("data_entrega", "DATE"),
        Coluna("produtor_id", "STRING", obrigatoria=True),
        Coluna("produto", "STRING", obrigatoria=True),
        Coluna("quantidade", "NUMERIC", obrigatoria=True),
        Coluna("unidade", "STRING", obrigatoria=True),
        Coluna("comprador", "STRING"),
        Coluna("pedido_id", "STRING"),
        Coluna("temperatura_transporte_c", "NUMERIC"),
        Coluna("transporte_ambiente", "BOOL", obrigatoria=True),
        Coluna("validade", "DATE"),
        Coluna("inspecao_visual", "STRING"),
        Coluna("observacao", "STRING"),
        Coluna("id_transacao", "STRING"),  # ligação lote ↔ transação
    ],
}

CAMPOS_SENSIVEIS: frozenset[str] = frozenset(
    coluna.nome for colunas in TABELAS.values() for coluna in colunas if coluna.sensivel
)


# Lista as colunas de uma tabela, na ordem do esquema.
def colunas(tabela: str) -> list[str]:
    return [coluna.nome for coluna in TABELAS[tabela]]
