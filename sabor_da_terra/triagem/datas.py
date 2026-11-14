"""Resolução determinística de datas relativas e detecção de conflitos de dia da semana."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re
import unicodedata


_DIAS_SEMANA: dict[str, int] = {
    "segunda": 0,
    "segunda-feira": 0,
    "terca": 1,
    "terca-feira": 1,
    "quarta": 2,
    "quarta-feira": 2,
    "quinta": 3,
    "quinta-feira": 3,
    "sexta": 4,
    "sexta-feira": 4,
    "sabado": 5,
    "domingo": 6,
}

_NOMES_DIAS_PT: dict[int, str] = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

_MESES: dict[str, int] = {
    "jan": 1,
    "janeiro": 1,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "abr": 4,
    "abril": 4,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "ago": 8,
    "agosto": 8,
    "set": 9,
    "setembro": 9,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dez": 12,
    "dezembro": 12,
}

_REGEX_DIA_SEMANA = (
    r"(?P<dia_semana>segunda(?:-feira)?|ter[cç]a(?:-feira)?|quarta(?:-feira)?|"
    r"quinta(?:-feira)?|sexta(?:-feira)?|s[aá]bado|domingo)"
)
_REGEX_MES_TEXTO = (
    r"(?P<mes_txt>janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|"
    r"setembro|outubro|novembro|dezembro|jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)"
)


@dataclass(frozen=True)
class ResultadoData:
    """Resultado determinístico da interpretação de data/prazo de uma mensagem."""

    data_iso: str | None
    trecho_original: str | None
    conflito: str | None = None


def _sem_acento_lower(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto.lower())
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def converter_data_referencia(valor: str | date | datetime) -> date:
    """Converte string ISO/BR, date ou datetime em datetime.date."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = valor.strip()
    if "T" in texto:
        texto = texto.split("T", 1)[0]
    elif " " in texto:
        texto = texto.split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data de referência inválida: {valor!r}")


def _inferir_ano(dia: int, mes: int, ref: date, ano_explicito: int | None) -> date:
    if ano_explicito is not None:
        return date(ano_explicito, mes, dia)
    candidato = date(ref.year, mes, dia)
    if (ref - candidato).days > 180:
        return date(ref.year + 1, mes, dia)
    return candidato


def _proximo_dia_semana(ref: date, dia_alvo: int, forcar_proxima_semana: bool = False) -> date:
    delta = (dia_alvo - ref.weekday()) % 7
    if delta == 0 and forcar_proxima_semana:
        delta = 7
    return ref + timedelta(days=delta)


def _extrair_data_explicita(texto: str, ref: date) -> tuple[date, str] | None:
    # 1. Intervalo do tipo "04 a 08 de novembro de 2026" -> usa data inicial
    m_intervalo = re.search(
        rf"\b(?P<dia>\d{{1,2}})\s*(?:a|ate|até|-)\s*\d{{1,2}}\s+de\s+{_REGEX_MES_TEXTO}"
        r"(?:\s+de\s+(?P<ano>\d{4}))?\b",
        texto,
        flags=re.IGNORECASE,
    )
    if m_intervalo:
        dia = int(m_intervalo.group("dia"))
        mes = _MESES[_sem_acento_lower(m_intervalo.group("mes_txt"))]
        ano = int(m_intervalo.group("ano")) if m_intervalo.group("ano") else None
        try:
            return _inferir_ano(dia, mes, ref, ano), m_intervalo.group(0)
        except ValueError:
            pass

    # 2. Data por extenso: "04 de novembro de 2026" ou "8 de novembro"
    m_extenso = re.search(
        rf"\b(?P<dia>\d{{1,2}})\s+de\s+{_REGEX_MES_TEXTO}(?:\s+de\s+(?P<ano>\d{{4}}))?\b",
        texto,
        flags=re.IGNORECASE,
    )
    if m_extenso:
        dia = int(m_extenso.group("dia"))
        mes = _MESES[_sem_acento_lower(m_extenso.group("mes_txt"))]
        ano = int(m_extenso.group("ano")) if m_extenso.group("ano") else None
        try:
            return _inferir_ano(dia, mes, ref, ano), m_extenso.group(0)
        except ValueError:
            pass

    # 3. Data abreviada com mês textual: "01/nov", "04/nov/2026", "08-nov"
    m_mes_abrev = re.search(
        rf"\b(?P<dia>\d{{1,2}})[/-]{_REGEX_MES_TEXTO}(?:[/-](?P<ano>\d{{4}}))?\b",
        texto,
        flags=re.IGNORECASE,
    )
    if m_mes_abrev:
        dia = int(m_mes_abrev.group("dia"))
        mes = _MESES[_sem_acento_lower(m_mes_abrev.group("mes_txt"))]
        ano = int(m_mes_abrev.group("ano")) if m_mes_abrev.group("ano") else None
        try:
            return _inferir_ano(dia, mes, ref, ano), m_mes_abrev.group(0)
        except ValueError:
            pass

    # 4. Data numérica: "29/10" ou "29/10/2026"
    m_num = re.search(
        r"\b(?P<dia>\d{1,2})/(?P<mes>\d{1,2})(?:/(?P<ano>\d{4}))?\b",
        texto,
    )
    if m_num:
        dia = int(m_num.group("dia"))
        mes = int(m_num.group("mes"))
        ano = int(m_num.group("ano")) if m_num.group("ano") else None
        if 1 <= mes <= 12:
            try:
                return _inferir_ano(dia, mes, ref, ano), m_num.group(0)
            except ValueError:
                pass

    return None


def _detectar_conflito_dia_semana(texto: str, data_alvo: date) -> str | None:
    m_dia = re.search(rf"\b{_REGEX_DIA_SEMANA}\b", texto, flags=re.IGNORECASE)
    if not m_dia:
        return None
    bruto = m_dia.group("dia_semana")
    chave = _sem_acento_lower(bruto)
    esperado = _DIAS_SEMANA.get(chave)
    if esperado is None:
        return None

    real = data_alvo.weekday()
    if real == esperado:
        return None

    nome_real = _NOMES_DIAS_PT[real]
    # Calcula a data correspondente ao dia da semana citado na mesma semana
    diferenca = esperado - real
    if diferenca > 3:
        diferenca -= 7
    elif diferenca < -3:
        diferenca += 7
    data_sugerida = data_alvo + timedelta(days=diferenca)

    return (
        f"Conflito de data: mensagem informa '{bruto}' junto com "
        f"{data_alvo.strftime('%d/%m/%Y')}, mas {data_alvo.strftime('%d/%m/%Y')} "
        f"cai em {nome_real} (a {_NOMES_DIAS_PT[esperado]} correspondente seria "
        f"{data_sugerida.strftime('%d/%m/%Y')})."
    )


def analisar_prazo_mensagem(
    mensagem: str,
    data_recebimento: str | date | datetime,
    prazo_extraido: str | None = None,
) -> ResultadoData:
    """Resolve datas relativas/explícitas e verifica conflito com o dia da semana.

    Quando ``prazo_extraido`` é fornecido pelo LLM, analisa tanto esse trecho
    quanto o texto completo da ``mensagem`` para garantir detecção determinística
    de conflitos (ex.: 'sexta (01/nov)' ou 'terça 04/nov').
    """
    ref = converter_data_referencia(data_recebimento)
    fontes = [t.strip() for t in (prazo_extraido, mensagem) if t and t.strip()]

    # 1. Prioriza datas explícitas (com ou sem dia da semana associado)
    for fonte in fontes:
        achado = _extrair_data_explicita(fonte, ref)
        if achado is not None:
            data_alvo, trecho = achado
            conflito = _detectar_conflito_dia_semana(fonte, data_alvo)
            if conflito is None and fonte != mensagem:
                conflito = _detectar_conflito_dia_semana(mensagem, data_alvo)
            return ResultadoData(
                data_iso=data_alvo.isoformat(),
                trecho_original=prazo_extraido or trecho,
                conflito=conflito,
            )

    # 2. Expressões relativas: "depois de amanhã", "amanhã", "hoje"
    for fonte in fontes:
        if re.search(r"\bdepois\s+de\s+amanh[aã]\b", fonte, flags=re.IGNORECASE):
            return ResultadoData(
                data_iso=(ref + timedelta(days=2)).isoformat(),
                trecho_original=prazo_extraido or "depois de amanhã",
            )
        if re.search(r"\bamanh[aã]\b|\btomorrow\b", fonte, flags=re.IGNORECASE):
            return ResultadoData(
                data_iso=(ref + timedelta(days=1)).isoformat(),
                trecho_original=prazo_extraido or "amanhã",
            )
        if re.search(r"\bhoje\b|\btoday\b", fonte, flags=re.IGNORECASE):
            return ResultadoData(
                data_iso=ref.isoformat(),
                trecho_original=prazo_extraido or "hoje",
            )

    # 3. Dia da semana relativo isolado (ex.: "pra sabado", "na próxima sexta")
    for fonte in fontes:
        m_sem = re.search(
            rf"\b(?:(?P<qual>pr[oó]xim[ao]|essa|esta|nesta)\s+)?{_REGEX_DIA_SEMANA}\b",
            fonte,
            flags=re.IGNORECASE,
        )
        if m_sem:
            chave = _sem_acento_lower(m_sem.group("dia_semana"))
            dia_alvo = _DIAS_SEMANA[chave]
            qual = _sem_acento_lower(m_sem.group("qual") or "")
            data_alvo = _proximo_dia_semana(
                ref, dia_alvo, forcar_proxima_semana=qual.startswith("proxim")
            )
            return ResultadoData(
                data_iso=data_alvo.isoformat(),
                trecho_original=prazo_extraido or m_sem.group(0),
            )

    # 4. Data ISO já normalizada vinda do LLM (YYYY-MM-DD)
    if prazo_extraido and re.fullmatch(r"\d{4}-\d{2}-\d{2}", prazo_extraido.strip()):
        data_alvo = converter_data_referencia(prazo_extraido)
        conflito = _detectar_conflito_dia_semana(mensagem, data_alvo)
        return ResultadoData(
            data_iso=data_alvo.isoformat(),
            trecho_original=prazo_extraido,
            conflito=conflito,
        )

    return ResultadoData(
        data_iso=prazo_extraido,
        trecho_original=prazo_extraido,
    )
