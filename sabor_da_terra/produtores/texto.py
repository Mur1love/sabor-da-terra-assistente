"""Formatação para o produtor rural e trava de dados sensíveis.

Valores em R$ com separador de milhar, datas em dd/mm/aaaa e quantidades
curtas ("150 kg"). Nenhum texto desta etapa pode levar CPF, conta bancária ou
chave PIX: dados_sensiveis_no_texto diz o que vazou, e os testes passam todo
texto gerado por ela.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

from sabor_da_terra.dados import obter_repositorio
from sabor_da_terra.dados.normalizacao import NOMES_MESES

_PLURAIS = {"unidade": "unidades", "maço": "maços", "dúzia": "dúzias", "litro": "litros"}

_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
# Conta corrente no formato do cadastro (28901-3, 0073921-7, 00134578-2).
_CONTA = re.compile(r"\b\d{5,8}-\d\b")
_AGENCIA = re.compile(r"ag[eê]ncia\s*\d{3,5}", re.IGNORECASE)


def reais(valor: float | Decimal) -> str:
    """R$ 1.440,00 (meio centavo arredonda para cima, como no extrato)."""
    centavos = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inteiro, fracao = f"{centavos:.2f}".split(".")
    sinal = "-" if inteiro.startswith("-") else ""
    inteiro = inteiro.lstrip("-")
    grupos = []
    while inteiro:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    return f"{sinal}R$ {'.'.join(grupos)},{fracao}"


def data_br(valor: date | str | None) -> str:
    """dd/mm/aaaa; texto que não é data ISO volta como veio ("jan/2027")."""
    if valor is None:
        return "sem data"
    if isinstance(valor, str):
        try:
            valor = date.fromisoformat(valor[:10])
        except ValueError:
            return valor
    return valor.strftime("%d/%m/%Y")


def numero(valor: float) -> str:
    """300, 46,7 — sem casas quando é inteiro."""
    valor = float(valor)
    return f"{valor:.0f}" if valor.is_integer() else f"{valor:.1f}".replace(".", ",")


def quantidade(valor: float, unidade: str | None) -> str:
    """150 kg, 1 dúzia, 120 dúzias."""
    unidade = unidade or ""
    texto_unidade = unidade if float(valor) == 1 else _PLURAIS.get(unidade, unidade)
    return f"{numero(valor)} {texto_unidade}".strip()


def dias(n: int) -> str:
    """1 dia, 12 dias."""
    return f"{n} {'dia' if n == 1 else 'dias'}"


def nome_do_mes(ano: int, mes: int) -> str:
    """outubro de 2026."""
    return f"{NOMES_MESES[mes - 1]} de {ano}"


@lru_cache(maxsize=1)
def _valores_sensiveis_do_cadastro() -> frozenset[str]:
    produtores = obter_repositorio().produtores()
    valores = set()
    for coluna in ("cpf", "chave_pix", "conta_corrente"):
        valores.update(str(v).strip() for v in produtores[coluna].dropna() if str(v).strip())
    return frozenset(valores)


def dados_sensiveis_no_texto(texto: str) -> list[str]:
    """Trechos do texto que parecem CPF, conta, agência ou chave PIX do cadastro. Vazio = texto limpo."""
    achados = [m.group(0) for padrao in (_CPF, _CONTA, _AGENCIA) for m in padrao.finditer(texto)]
    achados += [v for v in _valores_sensiveis_do_cadastro() if v in texto]
    return sorted(set(achados))
