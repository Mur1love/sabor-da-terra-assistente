"""Funções que o Gemini chama por function calling.

O SDK monta a declaração de cada ferramenta a partir dos tipos e da docstring,
por isso os parâmetros são simples e a docstring está em português. Cada função
devolve um dict pronto para JSON, com "encontrado" e, quando não acha com
certeza, um "aviso" para o assistente repassar. Contas e comparações de datas
ficam aqui, não no modelo, e os dados vêm de repositorio.py.

Nenhuma função daqui devolve CPF, PIX, telefone ou conta bancária.
"""

from __future__ import annotations

import math
import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

import pandas as pd

from sabor_da_terra.dados import normalizacao as n
from sabor_da_terra.dados.catalogo import Resolucao
from sabor_da_terra.dados.esquema import CAMPOS_SENSIVEIS
from sabor_da_terra.dados.repositorio import obter_repositorio

# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


# Converte um valor para JSON e mascara CPF que apareça em texto.
def _valor(v: Any) -> Any:
    if v is None or (isinstance(v, float) and v != v) or v is pd.NaT:
        return None
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):  
        v = float(v)
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, str):
        return n.mascarar_cpf_em_texto(v)
    if hasattr(v, "item"):  
        return _valor(v.item())
    return v


# Copia os campos pedidos de uma linha, sempre sem os sensíveis.
def _registro(linha: pd.Series, campos: list[str]) -> dict[str, Any]:

    return {c: _valor(linha[c]) for c in campos if c not in CAMPOS_SENSIVEIS}


# Arredonda para centavos (meio centavo arredonda para cima).
def _dinheiro(valor: Decimal) -> float:
    return float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# Resposta padrão quando o produto não foi encontrado.
def _nao_encontrado(resolucao: Resolucao) -> dict[str, Any]:
    return {
        "encontrado": False,
        "termo": resolucao.termo,
        "opcoes": resolucao.candidatos,
        "aviso": resolucao.aviso(),
    }


# Lê a data de referência ou usa a data de hoje.
def _referencia(data_referencia: Optional[str]) -> date:
    referencia = n.data(data_referencia) if data_referencia else date.today()
    if referencia is None:
        raise ValueError(data_referencia)
    return referencia


# Resposta padrão para data de referência inválida.
def _referencia_invalida(data_referencia: Optional[str]) -> dict[str, Any]:
    return {"encontrado": False, "aviso": f"Data de referência inválida: '{data_referencia}'. Use AAAA-MM-DD."}


_ID_PRODUTOR = re.compile(r"p?\s*-?\s*0*(\d{1,3})", re.IGNORECASE)


# Converte 'p1', 'P01' ou '1' em 'P001'.
def _normalizar_produtor_id(termo: str) -> str | None:
    m = _ID_PRODUTOR.fullmatch(str(termo).strip())
    return f"P{int(m.group(1)):03d}" if m else None


# Resposta padrão quando o código do produtor não existe.
def _produtor_nao_existe(termo: str) -> dict[str, Any]:
    return {
        "encontrado": False,
        "aviso": (
            f"Produtor '{termo}' não existe no cadastro. Para achar o código pelo nome ou "
            "telefone, use identificar_produtor."
        ),
    }


# Diz se a certificação orgânica vale na data informada.
def _certificacao_vigente(produtor: pd.Series, em: date | None) -> bool:
    validade = produtor["validade_certificacao"]
    return (
        bool(produtor["certificacao_organica"])
        and isinstance(em, date)
        and isinstance(validade, date)
        and validade >= em
    )


_CAMPOS_PRODUTOR = ["produtor_id", "nome", "municipio", "certificacao_organica", "validade_certificacao", "status"]
_CAMPOS_TRANSACAO = [
    "id_transacao", "data", "comprador", "produto", "quantidade", "unidade", "valor_unitario",
    "valor_total", "forma_pagamento", "status_pagamento", "data_vencimento", "data_pagamento",
    "observacao",
]


# Dados públicos do produtor, com a vigência da certificação calculada.
def _dados_produtor(produtor: pd.Series, referencia: date) -> dict[str, Any]:
    return {
        **_registro(produtor, _CAMPOS_PRODUTOR),
        "certificacao_vigente": _certificacao_vigente(produtor, referencia),
    }


# ---------------------------------------------------------------------------
# Ferramentas do assistente
# ---------------------------------------------------------------------------

_TRATAMENTOS = {"dona", "seu", "sr", "sra", "senhor", "senhora", "da", "das", "de", "do", "dos", "e"}


# Ferramenta: acha o produtor pelo código, nome ou telefone.
def identificar_produtor(termo: str, data_referencia: Optional[str] = None) -> dict:
    """Acha um produtor do cadastro pelo código, pelo nome ou pelo telefone.
    """
    repo = obter_repositorio()
    try:
        referencia = _referencia(data_referencia)
    except ValueError:
        return _referencia_invalida(data_referencia)

    texto = str(termo).strip()
    pid = _normalizar_produtor_id(texto)
    if pid:
        linha = repo.produtor(pid)
        if linha is None:
            return _produtor_nao_existe(texto)
        return _produtor_identificado(linha, "codigo", referencia)

    produtores = repo.produtores()
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) >= 8:
        telefones = produtores["telefone"].fillna("").map(lambda t: re.sub(r"\D", "", t))
        mesmos = produtores[telefones.map(lambda t: bool(t) and (t.endswith(digitos) or digitos.endswith(t)))]
        if len(mesmos) == 1:
            return _produtor_identificado(mesmos.iloc[0], "telefone", referencia)
        if len(mesmos) > 1:
            return _varios_produtores(mesmos, texto)
        return {"encontrado": False, "termo": texto, "aviso": "Nenhum produtor do cadastro tem esse telefone."}

    palavras = set(n.chave(texto).split()) - _TRATAMENTOS
    if not palavras:
        return {"encontrado": False, "termo": texto, "aviso": "Informe o código, o nome ou o telefone do produtor."}
    candidatos = produtores[produtores["nome"].map(lambda nome: palavras <= set(n.chave(nome).split()))]
    if len(candidatos) == 1:
        return _produtor_identificado(candidatos.iloc[0], "nome", referencia)
    if len(candidatos) > 1:
        return _varios_produtores(candidatos, texto)
    return {"encontrado": False, "termo": texto, "aviso": f"Nenhum produtor do cadastro tem '{texto}' no nome."}


# Resposta quando mais de um produtor corresponde ao termo.
def _varios_produtores(candidatos: pd.DataFrame, texto: str) -> dict[str, Any]:
    return {
        "encontrado": False,
        "termo": texto,
        "opcoes": [{"produtor_id": l["produtor_id"], "nome": l["nome"]} for _, l in candidatos.iterrows()],
        "aviso": f"Há {len(candidatos)} produtores que correspondem a '{texto}'. Pergunte qual.",
    }


# Resposta quando o produtor foi identificado.
def _produtor_identificado(linha: pd.Series, por: str, referencia: date) -> dict[str, Any]:
    return {
        "encontrado": True,
        "por": por,
        "data_referencia": referencia.isoformat(),
        "produtor": _dados_produtor(linha, referencia),
        "aviso": None if linha["ativo"] else "Produtor inativo: não recebe alocação de pedidos.",
    }


# Ferramenta: lista quem fornece um produto, separando certificação vencida.
def buscar_produtores(produto: str, organico: Optional[bool] = None, data_referencia: Optional[str] = None) -> dict:
    """Lista os produtores ativos que fornecem um produto.
    """
    repo = obter_repositorio()
    try:
        referencia = _referencia(data_referencia)
    except ValueError:
        return _referencia_invalida(data_referencia)

    resolucao = repo.catalogo.resolver(produto)
    if not resolucao.encontrado:
        return _nao_encontrado(resolucao)

    produtores = repo.produtores_do_produto(resolucao.base)
    inativos = produtores.loc[~produtores["ativo"], "produtor_id"].tolist()
    ativos = produtores[produtores["ativo"]]
    vigente = pd.Series(
        [_certificacao_vigente(linha, referencia) for _, linha in ativos.iterrows()], index=ativos.index, dtype=bool
    )
    vencidos = ativos[ativos["certificacao_organica"] & ~vigente]

    if organico is True:
        selecionados = ativos[vigente]
    elif organico is False:
        selecionados = ativos[~vigente]
    else:
        selecionados = ativos

    aviso = None
    if not vencidos.empty:
        lista = "; ".join(
            f"{l['produtor_id']} ({l['nome']}, venceu em {_valor(l['validade_certificacao'])})"
            for _, l in vencidos.iterrows()
        )
        aviso = (
            f"Em {referencia.isoformat()} a certificação orgânica está vencida para: {lista}. "
            "Esses produtores não podem vender como orgânico."
        )

    return {
        "encontrado": True,
        "produto": resolucao.base,
        "filtro_organico": organico,
        "data_referencia": referencia.isoformat(),
        "produtores": [_dados_produtor(linha, referencia) for _, linha in selecionados.iterrows()],
        "certificacao_vencida": [_registro(linha, ["produtor_id", "nome", "validade_certificacao"]) for _, linha in vencidos.iterrows()],
        "inativos_ignorados": inativos,
        "aviso": aviso,
    }


# Ferramenta: diz se o produto está na safra num mês.
def disponibilidade(produto: str, mes: str) -> dict:
    """Diz se um produto está em safra num mês, segundo o calendário de sazonalidade da cooperativa.
    """
    repo = obter_repositorio()
    numero_mes = n.mes(mes)
    if numero_mes is None:
        return {"encontrado": False, "aviso": f"Mês não reconhecido: '{mes}'. Use número, nome ou AAAA-MM."}

    resolucao = repo.catalogo.resolver(produto)
    if not resolucao.encontrado:
        return _nao_encontrado(resolucao)

    linha = repo.sazonalidade(resolucao.base, numero_mes)
    if linha is None:
        return {
            "encontrado": False,
            "produto": resolucao.base,
            "mes": n.NOMES_MESES[numero_mes - 1],
            "aviso": f"Não há dado de sazonalidade para '{resolucao.base}' no calendário da cooperativa.",
        }
    return {
        "encontrado": True,
        "produto": resolucao.base,
        "mes": n.NOMES_MESES[numero_mes - 1],
        "nivel": linha["nivel"],
        "disponivel": linha["nivel"] != "nenhuma",
        "observacao": _valor(linha["observacao"]),
        "fonte": "sazonalidade.csv",
        "aviso": None,
    }


# Ferramenta: calcula o orçamento pela tabela, com desconto de atacado.
def preco(produto: str, organico: bool, quantidade: float) -> dict:
    """Calcula o preço de uma quantidade de produto pela tabela de outubro/2026, com desconto de atacado.
    """
    repo = obter_repositorio()
    if quantidade is None or not math.isfinite(quantidade) or quantidade <= 0:
        return {"encontrado": False, "aviso": "Informe uma quantidade maior que zero."}

    resolucao = repo.catalogo.resolver(produto)
    if not resolucao.encontrado:
        return _nao_encontrado(resolucao)

    variantes = [resolucao.variante] if resolucao.variante else repo.catalogo.variantes(resolucao.base)
    if not variantes:
        return {
            "encontrado": False,
            "produto": resolucao.base,
            "aviso": f"'{resolucao.base}' não está na tabela de preços de outubro/2026.",
        }
    if len(variantes) > 1:
        return {
            "encontrado": False,
            "produto": resolucao.base,
            "opcoes": variantes,
            "aviso": f"'{resolucao.base}' tem mais de um preço na tabela: {', '.join(variantes)}. Pergunte qual.",
        }

    linha = repo.preco_da_variante(variantes[0])
    tipo = "orgânico" if organico else "convencional"
    unitario = linha["preco_organico"] if organico else linha["preco_convencional"]
    if pd.isna(unitario):
        return {
            "encontrado": True,
            "disponivel": False,
            "produto": linha["produto"],
            "tipo": tipo,
            "aviso": f"Não há oferta {'orgânica' if organico else 'convencional'} de '{linha['produto']}' na tabela (n/d).",
            "observacao": _valor(linha["observacao"]),
        }

    qtd = Decimal(str(quantidade))
    subtotal = Decimal(str(unitario)) * qtd
    pct = Decimal(str(linha["desconto_atacado_pct"]))
    minimo = Decimal(str(linha["volume_minimo_atacado"]))
    atacado = pct > 0 and qtd >= minimo
    desconto = subtotal * pct / 100 if atacado else Decimal(0)

    return {
        "encontrado": True,
        "disponivel": True,
        "produto": linha["produto"],
        "tipo": tipo,
        "unidade": linha["unidade"],
        "quantidade": float(qtd),
        "preco_unitario": _dinheiro(Decimal(str(unitario))),
        "subtotal": _dinheiro(subtotal),
        "desconto_atacado_aplicado": atacado,
        "desconto_atacado_pct": float(pct) if atacado else 0.0,
        "volume_minimo_atacado": float(minimo),
        "valor_desconto": _dinheiro(desconto),
        "total": _dinheiro(subtotal - desconto),
        "observacao": _valor(linha["observacao"]),
        "fonte": "tabela_precos_outubro_2026.csv",
        "aviso": None,
    }


_LOTE_COMPLETO = re.compile(r"LOT\D*(\d{4})\D*(\d{1,4})$")


# Ferramenta: mostra a origem de um lote, aceitando o código escrito de outro jeito.
def rastrear_lote(lote_id: str) -> dict:
    """Mostra a rastreabilidade de um lote: produtor, produto, datas, transporte, comprador e venda ligada.
    """
    repo = obter_repositorio()
    ids = repo.ids_de_lote()
    termo = str(lote_id).strip().strip(".,;:!?()[]{}\"'")
    texto_maiusculo = termo.upper()

    completo = _LOTE_COMPLETO.search(texto_maiusculo)
    if completo:
        candidato = f"LOT-{completo.group(1)}-{int(completo.group(2)):04d}"
        if candidato in ids:
            return _lote_encontrado(candidato, exato=True, termo=termo)

    grupos = re.findall(r"\d+", texto_maiusculo)
    if not grupos:
        return {"encontrado": False, "termo": termo, "aviso": f"'{termo}' não parece um código de lote."}

    numero = int(grupos[-1])
    ano_informado = next((int(g) for g in grupos[:-1] if len(g) == 4), None)
    mesmo_numero = [i for i in ids if i.endswith(f"-{numero:04d}")]

    if not mesmo_numero:
        return {
            "encontrado": False,
            "termo": termo,
            "aviso": f"Não existe lote correspondente a '{termo}'. Lotes registrados: {ids[0]} a {ids[-1]}.",
        }
    if ano_informado is not None and all(not l.startswith(f"LOT-{ano_informado}-") for l in mesmo_numero):
        return {
            "encontrado": False,
            "termo": termo,
            "sugestoes": mesmo_numero,
            "aviso": (
                f"O lote '{termo}' não existe (não há lote de {ano_informado} com esse número). "
                f"O mais próximo é {', '.join(mesmo_numero)}. Confirme antes de usar."
            ),
        }
    if len(mesmo_numero) > 1:
        return {
            "encontrado": False,
            "termo": termo,
            "sugestoes": mesmo_numero,
            "aviso": f"Há mais de um lote com o número {numero}: {', '.join(mesmo_numero)}. Pergunte qual.",
        }
    return _lote_encontrado(mesmo_numero[0], exato=False, termo=termo)


# Monta a resposta completa de um lote que existe.
def _lote_encontrado(lote_id: str, exato: bool, termo: str) -> dict:
    repo = obter_repositorio()
    lote = repo.lote(lote_id)
    produtor = repo.produtor(lote["produtor_id"])
    id_transacao = lote["id_transacao"]
    transacao = repo.transacao(id_transacao) if isinstance(id_transacao, str) else None

    return {
        "encontrado": True,
        "exato": exato,
        "lote": _registro(
            lote,
            [
                "lote_id", "produto", "quantidade", "unidade", "data_colheita", "data_entrega", "validade",
                "comprador", "pedido_id", "temperatura_transporte_c", "transporte_ambiente",
                "inspecao_visual", "observacao",
            ],
        ),
        "produtor": (
            {
                **_registro(produtor, _CAMPOS_PRODUTOR),
                "certificacao_vigente_na_entrega": _certificacao_vigente(produtor, lote["data_entrega"]),
            }
            if produtor is not None
            else None
        ),
        "transacao": (
            _registro(transacao, ["id_transacao", "data", "valor_total", "status_pagamento", "data_pagamento"])
            if transacao is not None
            else None
        ),
        "fonte": "lotes.csv",
        "aviso": None if exato else f"Não há lote escrito exatamente '{termo}'; interpretado como {lote_id}.",
    }


# Ferramenta: resumo financeiro do produtor no mês.
def extrato_produtor(produtor_id: str, mes: str, data_referencia: Optional[str] = None) -> dict:
    """Extrato financeiro de um produtor: vendas do mês, recebimentos do mês, valores a receber e vencidos.
    """
    repo = obter_repositorio()
    pid = _normalizar_produtor_id(produtor_id)
    produtor = repo.produtor(pid) if pid else None
    if produtor is None:
        return _produtor_nao_existe(produtor_id)

    try:
        referencia = _referencia(data_referencia)
    except ValueError:
        return _referencia_invalida(data_referencia)

    aviso = None
    periodo = n.ano_mes(mes)
    if periodo is None:
        numero_mes = n.mes(mes)
        if numero_mes is None:
            return {"encontrado": False, "aviso": f"Mês inválido: '{mes}'. Use AAAA-MM, ex.: 2026-10."}
        ano = referencia.year if numero_mes <= referencia.month else referencia.year - 1
        periodo = (ano, numero_mes)
        aviso = f"Mês '{mes}' interpretado como {ano:04d}-{numero_mes:02d} (o mais recente até {referencia.isoformat()})."
    ano, numero_mes = periodo

    # Diz se a data cai no mês do extrato.
    def no_mes(d: date | None) -> bool:
        return isinstance(d, date) and d.year == ano and d.month == numero_mes

    tx = repo.transacoes_do_produtor(pid)
    vendas = tx[tx["data"].map(no_mes).astype(bool)]
    recebidos = tx[(tx["status_pagamento"] == "pago") & tx["data_pagamento"].map(no_mes).astype(bool)]
    pendentes = tx[tx["status_pagamento"] == "pendente"]
    venceu = pendentes["data_vencimento"].map(lambda d: isinstance(d, date) and d < referencia).astype(bool)
    a_receber, vencidas = pendentes[~venceu], pendentes[venceu]

    # Transforma as transações em lista, com dias de atraso quando pedido.
    def lista(df: pd.DataFrame, com_atraso: bool = False) -> list[dict]:
        itens = []
        for _, linha in df.sort_values("data").iterrows():
            item = _registro(linha, _CAMPOS_TRANSACAO)
            if com_atraso:
                item["dias_em_atraso"] = (referencia - linha["data_vencimento"]).days
            itens.append(item)
        return itens

    # Soma os valores em Decimal para não perder centavos.
    def total(df: pd.DataFrame) -> float:
        return _dinheiro(sum((Decimal(str(v)) for v in df["valor_total"]), Decimal(0)))

    return {
        "encontrado": True,
        "produtor": _dados_produtor(produtor, referencia),
        "mes": f"{ano:04d}-{numero_mes:02d}",
        "data_referencia": referencia.isoformat(),
        "vendas_no_mes": lista(vendas),
        "recebidos_no_mes": lista(recebidos),
        "a_receber": lista(a_receber),
        "vencidas": lista(vencidas, com_atraso=True),
        "totais": {
            "vendido_no_mes": total(vendas),
            "recebido_no_mes": total(recebidos),
            "a_receber": total(a_receber),
            "vencido": total(vencidas),
        },
        "fonte": "financeiro.csv",
        "aviso": aviso,
    }


# Lista de ferramentas que o assistente expõe ao Gemini por function calling.
FERRAMENTAS = [identificar_produtor, buscar_produtores, disponibilidade, preco, rastrear_lote, extrato_produtor]
