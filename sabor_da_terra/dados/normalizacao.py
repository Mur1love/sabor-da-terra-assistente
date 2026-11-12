"""Converte o texto cru dos arquivos em valor tipado, ou None quando o dado falta."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

VALORES_AUSENTES = {"", "n/d", "nd", "-", "null", "none", "nan"}

MESES = {
    "jan": 1, "janeiro": 1,
    "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3,
    "abr": 4, "abril": 4,
    "mai": 5, "maio": 5,
    "jun": 6, "junho": 6,
    "jul": 7, "julho": 7,
    "ago": 8, "agosto": 8,
    "set": 9, "setembro": 9,
    "out": 10, "outubro": 10,
    "nov": 11, "novembro": 11,
    "dez": 12, "dezembro": 12,
}
NOMES_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")


# Diz se o valor está vazio ou é um marcador como 'n/d'.
def ausente(valor: object) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and valor != valor:  # NaN
        return True
    return str(valor).strip().lower() in VALORES_AUSENTES


# Versão do texto para comparar: minúsculas, sem acento e sem hífen.
def chave(texto: object) -> str:
    if ausente(texto):
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().replace("-", " ").split())


# Limpa os espaços do texto e mantém os acentos.
def texto(valor: object) -> str | None:
    if ausente(valor):
        return None
    return " ".join(str(valor).split())


# Converte texto em número, com vírgula ou ponto decimal.
def numero(valor: object) -> float | None:

    if ausente(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    bruto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    try:
        return float(bruto)
    except ValueError:
        return None


# Converte data ISO ou no formato brasileiro.
def data(valor: object) -> date | None:
    if ausente(valor):
        return None
    bruto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(bruto, formato).date()
        except ValueError:
            continue
    raise ValueError(f"Data em formato desconhecido: {valor!r}")


# Converte data e hora no formato ISO.
def data_hora(valor: object) -> datetime | None:
    if ausente(valor):
        return None
    return datetime.fromisoformat(str(valor).strip())


# Converte 'sim'/'nao' em verdadeiro ou falso.
def booleano(valor: object) -> bool:
    return chave(valor) in {"sim", "s", "true", "1", "yes"}


# Padroniza um status: minúsculas e sem acento.
def status(valor: object) -> str | None:
    return chave(valor) or None


# Descobre o mês a partir de número, nome ou ano-mês.
def mes(valor: object) -> int | None:
    if isinstance(valor, int):
        return valor if 1 <= valor <= 12 else None
    k = chave(valor)
    if k in MESES:
        return MESES[k]
    m = re.fullmatch(r"(\d{4})[-/ ](\d{1,2})|(\d{1,2})[-/ ](\d{4})|(\d{1,2})", k)
    if not m:
        return None
    numero_mes = int(m.group(2) or m.group(3) or m.group(5))
    return numero_mes if 1 <= numero_mes <= 12 else None


# Descobre ano e mês a partir de '2026-10' ou '10/2026'.
def ano_mes(valor: object) -> tuple[int, int] | None:
    k = chave(valor)
    m = re.fullmatch(r"(\d{4})[-/ ](\d{1,2})", k) or re.fullmatch(r"(\d{1,2})[-/ ](\d{4})", k)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    ano, numero_mes = (a, b) if a > 12 else (b, a)
    return (ano, numero_mes) if 1 <= numero_mes <= 12 else None


# Esconde qualquer CPF que apareça num texto.
def mascarar_cpf_em_texto(valor: str) -> str:
    return _CPF.sub("***.***.***-**", valor)
