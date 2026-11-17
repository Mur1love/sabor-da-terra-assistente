"""Lê e valida a base de fatos (fatos.yaml) usada pelas regras.

Cada fato traz a fonte, o arquivo de data/ de onde saiu. O YAML é a versão
local; em produção os mesmos fatos ficam numa tabela do BigQuery, e só
carregar_fatos muda. Um fato sem fonte ou com campo inválido impede a carga.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sabor_da_terra.dados.normalizacao import chave

ARQUIVO_FATOS = Path(__file__).with_name("fatos.yaml")

DIAS_DO_PERIODO = {"semana": 7, "mes": 30, "ano": 365}
DIAS_DA_SEMANA = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6}
SITUACOES_SIE = frozenset({"vigente", "pendente", "ausente"})
SITUACOES_DAP_CAF = frozenset({"vigente", "informada"})
TIPOS_DE_PRECO = frozenset({"contrato", "tabela"})


class FatosInvalidos(ValueError):
    pass


@dataclass(frozen=True)
class Renovacao:
    protocolo: str
    solicitada_em: dt.date
    auditoria_em: dt.date | None
    concluida_em: dt.date | None
    nova_validade: dt.date | None

    # Renovação só conta depois que o novo certificado sai.
    @property
    def concluida(self) -> bool:
        return self.concluida_em is not None and self.nova_validade is not None


@dataclass(frozen=True)
class Certificacao:
    produtor_id: str
    certificado: str
    certificadora: str
    emissao: dt.date
    validade: dt.date
    produtos: tuple[str, ...]
    fonte: str
    renovacao: Renovacao | None = None

    # Diz se a certificação vale no dia (o dia da validade ainda vale).
    def vigente_em(self, dia: dt.date) -> bool:
        if self.emissao <= dia <= self.validade:
            return True
        r = self.renovacao
        return bool(r and r.concluida and r.concluida_em <= dia <= r.nova_validade)

    # Último dia de validade, contando a renovação concluída.
    @property
    def validade_final(self) -> dt.date:
        r = self.renovacao
        return r.nova_validade if r and r.concluida else self.validade


@dataclass(frozen=True)
class RegistroSanitario:
    produtor_id: str
    situacao: str
    registro: str | None
    observacao: str | None
    fonte: str
    # Verdade quando o dataset documenta que o produto dispensa SIE na venda direta
    # (ex.: ovos do P017): a intermediação segue pedindo confirmação ao comprador.
    dispensa_venda_direta: bool = False


@dataclass(frozen=True)
class NaoConformidade:
    codigo: str
    relatorio: str
    produtor_id: str
    produtos: tuple[str, ...]
    descricao: str
    acao: str
    permitido: str
    fonte: str


@dataclass(frozen=True)
class DapCaf:
    produtor_id: str
    situacao: str
    numero: str | None
    fonte: str


@dataclass(frozen=True)
class Capacidade:
    produtor_id: str
    produtos: tuple[str, ...]
    minimo: float
    maximo: float
    unidade: str
    periodo: str
    meses: tuple[int, ...] | None
    fonte: str

    # Diz se a linha vale para o produto no mês.
    def vale_para(self, produto: str, mes: int) -> bool:
        return produto in self.produtos and (self.meses is None or mes in self.meses)

    # Capacidade (mínima, máxima) numa janela de dias.
    def na_janela(self, dias: int) -> tuple[float, float]:
        fator = dias / DIAS_DO_PERIODO[self.periodo]
        return self.minimo * fator, self.maximo * fator


@dataclass(frozen=True)
class ItemContrato:
    produto: str
    preco: float
    unidade: str
    exige_organico: bool
    observacao: str | None


@dataclass(frozen=True)
class Contrato:
    id: str
    numero: str
    comprador: str
    nomes: tuple[str, ...]
    apelidos: tuple[str, ...]
    inicio: dt.date
    fim: dt.date | None
    preco: str
    exige_sie_origem_animal: bool
    exige_dap_caf: bool
    dias_entrega: tuple[int, ...] | None
    condicoes: tuple[str, ...]
    itens: tuple[ItemContrato, ...]
    fonte: str

    # Diz se o contrato vale no dia (sem fim = prazo indeterminado).
    def vigente_em(self, dia: dt.date) -> bool:
        return self.inicio <= dia and (self.fim is None or dia <= self.fim)

    # Item do contrato para um produto, ou None.
    def item(self, produto: str) -> ItemContrato | None:
        return next((i for i in self.itens if i.produto == produto), None)


@dataclass(frozen=True)
class Fatos:
    certificacoes: tuple[Certificacao, ...]
    registros_sanitarios: tuple[RegistroSanitario, ...]
    nao_conformidades: tuple[NaoConformidade, ...]
    dap_caf: tuple[DapCaf, ...]
    capacidades: tuple[Capacidade, ...]
    origem_animal: frozenset[str]
    fonte_origem_animal: str
    contratos: tuple[Contrato, ...]

    # Certificações de um produtor que cobrem o produto.
    def certificacoes_de(self, produtor_id: str, produto: str) -> list[Certificacao]:
        return [c for c in self.certificacoes if c.produtor_id == produtor_id and produto in c.produtos]

    # Registro sanitário do produtor, ou None se nenhum documento fala dele.
    def registro_sanitario(self, produtor_id: str) -> RegistroSanitario | None:
        return next((r for r in self.registros_sanitarios if r.produtor_id == produtor_id), None)

    # Não conformidades que atingem o produto daquele produtor.
    def nao_conformidades_de(self, produtor_id: str, produto: str) -> list[NaoConformidade]:
        return [nc for nc in self.nao_conformidades if nc.produtor_id == produtor_id and produto in nc.produtos]

    # DAP/CAF do produtor, ou None se nenhum documento traz.
    def dap_caf_de(self, produtor_id: str) -> DapCaf | None:
        return next((d for d in self.dap_caf if d.produtor_id == produtor_id), None)

    # Capacidades do produtor para o produto no mês.
    def capacidades_de(self, produtor_id: str, produto: str, mes: int) -> list[Capacidade]:
        return [c for c in self.capacidades if c.produtor_id == produtor_id and c.vale_para(produto, mes)]

    # Diz se o produto é de origem animal.
    def eh_origem_animal(self, produto: str) -> bool:
        return produto in self.origem_animal

    # Contrato do comprador: o nome completo aparece no texto ou o texto é um apelido. None se não achar ou houver dúvida.
    def contrato_do_comprador(self, comprador: str | None) -> Contrato | None:
        texto = chave(comprador)
        if not texto:
            return None
        achados = [
            c
            for c in self.contratos
            if any(f" {chave(nome)} " in f" {texto} " for nome in c.nomes) or texto in {chave(a) for a in c.apelidos}
        ]
        return achados[0] if len(achados) == 1 else None


# ---------------------------------------------------------------------------
# Leitura e validação
# ---------------------------------------------------------------------------


# Pega um campo do registro e confere o tipo; falha com o caminho do campo.
def _campo(registro: dict, nome: str, tipo: type | tuple[type, ...], onde: str, opcional: bool = False) -> Any:
    valor = registro.get(nome)
    if valor is None:
        if opcional:
            return None
        raise FatosInvalidos(f"{onde}: falta '{nome}'.")
    if tipo is float and isinstance(valor, int) and not isinstance(valor, bool):
        valor = float(valor)
    if not isinstance(valor, tipo) or (tipo is dt.date and isinstance(valor, dt.datetime)):
        raise FatosInvalidos(f"{onde}: '{nome}' deveria ser {getattr(tipo, '__name__', tipo)}, veio {valor!r}.")
    if isinstance(valor, str) and not valor.strip():
        raise FatosInvalidos(f"{onde}: '{nome}' está vazio.")
    return valor


# Lista de textos não vazia (produtos, nomes, condições).
def _textos(registro: dict, nome: str, onde: str, opcional: bool = False) -> tuple[str, ...]:
    valores = _campo(registro, nome, list, onde, opcional)
    if valores is None:
        return ()
    if not valores or not all(isinstance(v, str) and v.strip() for v in valores):
        raise FatosInvalidos(f"{onde}: '{nome}' precisa ser uma lista de textos.")
    return tuple(valores)


# Lista de registros de uma seção do YAML.
def _secao(dados: dict, nome: str) -> list[dict]:
    secao = dados.get(nome)
    if not isinstance(secao, list) or not all(isinstance(r, dict) for r in secao):
        raise FatosInvalidos(f"Seção '{nome}' precisa ser uma lista de registros.")
    return secao


# Monta a certificação (e a renovação, se houver).
def _certificacao(r: dict, onde: str) -> Certificacao:
    renovacao = None
    if r.get("renovacao") is not None:
        bruto = _campo(r, "renovacao", dict, onde)
        sub = f"{onde}.renovacao"
        renovacao = Renovacao(
            protocolo=_campo(bruto, "protocolo", str, sub),
            solicitada_em=_campo(bruto, "solicitada_em", dt.date, sub),
            auditoria_em=_campo(bruto, "auditoria_em", dt.date, sub, opcional=True),
            concluida_em=_campo(bruto, "concluida_em", dt.date, sub, opcional=True),
            nova_validade=_campo(bruto, "nova_validade", dt.date, sub, opcional=True),
        )
        if (renovacao.concluida_em is None) != (renovacao.nova_validade is None):
            raise FatosInvalidos(f"{sub}: 'concluida_em' e 'nova_validade' vêm juntas.")
    cert = Certificacao(
        produtor_id=_campo(r, "produtor_id", str, onde),
        certificado=_campo(r, "certificado", str, onde),
        certificadora=_campo(r, "certificadora", str, onde),
        emissao=_campo(r, "emissao", dt.date, onde),
        validade=_campo(r, "validade", dt.date, onde),
        produtos=_textos(r, "produtos", onde),
        fonte=_campo(r, "fonte", str, onde),
        renovacao=renovacao,
    )
    if cert.validade < cert.emissao:
        raise FatosInvalidos(f"{onde}: validade antes da emissão.")
    return cert


# Monta uma linha de capacidade.
def _capacidade(r: dict, onde: str) -> Capacidade:
    maximo = _campo(r, "maximo", float, onde)
    minimo = _campo(r, "minimo", float, onde, opcional=True)
    minimo = maximo if minimo is None else minimo
    periodo = _campo(r, "periodo", str, onde)
    meses = _campo(r, "meses", list, onde, opcional=True)
    if periodo not in DIAS_DO_PERIODO:
        raise FatosInvalidos(f"{onde}: período '{periodo}' desconhecido.")
    if not 0 < minimo <= maximo:
        raise FatosInvalidos(f"{onde}: capacidade precisa de 0 < mínimo <= máximo.")
    if meses is not None and (
        not meses or not all(isinstance(m, int) and not isinstance(m, bool) and 1 <= m <= 12 for m in meses)
    ):
        raise FatosInvalidos(f"{onde}: 'meses' precisa ter números de 1 a 12.")
    return Capacidade(
        produtor_id=_campo(r, "produtor_id", str, onde),
        produtos=_textos(r, "produtos", onde),
        minimo=minimo,
        maximo=maximo,
        unidade=_campo(r, "unidade", str, onde),
        periodo=periodo,
        meses=tuple(meses) if meses else None,
        fonte=_campo(r, "fonte", str, onde),
    )


# Monta um contrato e seus itens.
def _contrato(r: dict, onde: str) -> Contrato:
    preco = _campo(r, "preco", str, onde)
    if preco not in TIPOS_DE_PRECO:
        raise FatosInvalidos(f"{onde}: 'preco' deve ser 'contrato' ou 'tabela'.")
    dias = _textos(r, "dias_entrega", onde, opcional=True)
    if any(d not in DIAS_DA_SEMANA for d in dias):
        raise FatosInvalidos(f"{onde}: dia de entrega desconhecido em {list(dias)}.")
    itens = []
    for i, bruto in enumerate(r.get("itens") or []):
        sub = f"{onde}.itens[{i}]"
        if not isinstance(bruto, dict):
            raise FatosInvalidos(f"{sub}: item precisa ser um registro.")
        itens.append(
            ItemContrato(
                produto=_campo(bruto, "produto", str, sub),
                preco=_campo(bruto, "preco", float, sub),
                unidade=_campo(bruto, "unidade", str, sub),
                exige_organico=bool(_campo(bruto, "exige_organico", bool, sub, opcional=True)),
                observacao=_campo(bruto, "observacao", str, sub, opcional=True),
            )
        )
    if preco == "contrato" and not itens:
        raise FatosInvalidos(f"{onde}: contrato com preço próprio precisa de itens.")
    _sem_repetidos([i.produto for i in itens], f"{onde}.itens", "produto")
    return Contrato(
        id=_campo(r, "id", str, onde),
        numero=_campo(r, "numero", str, onde),
        comprador=_campo(r, "comprador", str, onde),
        nomes=_textos(r, "nomes", onde),
        apelidos=_textos(r, "apelidos", onde, opcional=True),
        inicio=_campo(r, "inicio", dt.date, onde),
        fim=_campo(r, "fim", dt.date, onde, opcional=True),
        preco=preco,
        exige_sie_origem_animal=bool(_campo(r, "exige_sie_origem_animal", bool, onde, opcional=True)),
        exige_dap_caf=bool(_campo(r, "exige_dap_caf", bool, onde, opcional=True)),
        dias_entrega=tuple(DIAS_DA_SEMANA[d] for d in dias) or None,
        condicoes=_textos(r, "condicoes", onde, opcional=True),
        itens=tuple(itens),
        fonte=_campo(r, "fonte", str, onde),
    )


# Recusa situação fora da lista permitida.
def _situacao(r: dict, permitidas: frozenset[str], onde: str) -> str:
    situacao = _campo(r, "situacao", str, onde)
    if situacao not in permitidas:
        raise FatosInvalidos(f"{onde}: situação '{situacao}' fora de {sorted(permitidas)}.")
    return situacao


# Monta o registro sanitário (SIE) de um produtor.
def _registro_sanitario(r: dict, onde: str) -> RegistroSanitario:
    return RegistroSanitario(
        produtor_id=_campo(r, "produtor_id", str, onde),
        situacao=_situacao(r, SITUACOES_SIE, onde),
        registro=_campo(r, "registro", str, onde, opcional=True),
        observacao=_campo(r, "observacao", str, onde, opcional=True),
        fonte=_campo(r, "fonte", str, onde),
        dispensa_venda_direta=bool(_campo(r, "dispensa_venda_direta", bool, onde, opcional=True)),
    )


# Monta uma não conformidade da fiscalização.
def _nao_conformidade(r: dict, onde: str) -> NaoConformidade:
    return NaoConformidade(
        codigo=_campo(r, "codigo", str, onde),
        relatorio=_campo(r, "relatorio", str, onde),
        produtor_id=_campo(r, "produtor_id", str, onde),
        produtos=_textos(r, "produtos", onde),
        descricao=_campo(r, "descricao", str, onde),
        acao=_campo(r, "acao", str, onde),
        permitido=_campo(r, "permitido", str, onde),
        fonte=_campo(r, "fonte", str, onde),
    )


# Monta a DAP/CAF de um produtor.
def _dap_caf(r: dict, onde: str) -> DapCaf:
    return DapCaf(
        produtor_id=_campo(r, "produtor_id", str, onde),
        situacao=_situacao(r, SITUACOES_DAP_CAF, onde),
        numero=_campo(r, "numero", str, onde, opcional=True),
        fonte=_campo(r, "fonte", str, onde),
    )


# Recusa valores repetidos onde cada um precisa ser único.
def _sem_repetidos(valores: list, onde: str, campo: str) -> None:
    vistos = set()
    for valor in valores:
        if valor in vistos:
            raise FatosInvalidos(f"{onde}: '{campo}' repetido ({valor!r}); cada fato deve aparecer uma vez.")
        vistos.add(valor)


# Recusa duas linhas de capacidade para o mesmo produtor, produto e mês.
def _capacidades_sem_sobreposicao(capacidades: tuple[Capacidade, ...]) -> None:
    vistos = set()
    for c in capacidades:
        for produto in c.produtos:
            for mes in c.meses or range(1, 13):
                chave_linha = (c.produtor_id, produto, mes)
                if chave_linha in vistos:
                    raise FatosInvalidos(f"capacidades: duas linhas para {c.produtor_id}, {produto}, mês {mes}.")
                vistos.add(chave_linha)


# Confere o que precisa ser único entre os registros.
def _validar_unicidade(fatos: Fatos) -> None:
    _sem_repetidos([c.certificado for c in fatos.certificacoes], "certificacoes_organicas", "certificado")
    _sem_repetidos([r.produtor_id for r in fatos.registros_sanitarios], "registros_sanitarios", "produtor_id")
    _sem_repetidos([(nc.relatorio, nc.codigo) for nc in fatos.nao_conformidades], "nao_conformidades", "codigo")
    _sem_repetidos([d.produtor_id for d in fatos.dap_caf], "dap_caf", "produtor_id")
    _sem_repetidos([c.id for c in fatos.contratos], "contratos", "id")
    _sem_repetidos(
        [chave(nome) for c in fatos.contratos for nome in (*c.nomes, *c.apelidos)], "contratos", "nome ou apelido"
    )
    _capacidades_sem_sobreposicao(fatos.capacidades)


# Aplica a função de montagem a cada registro da seção.
def _montar(dados: dict, nome: str, montar) -> tuple:
    return tuple(montar(r, f"{nome}[{i}]") for i, r in enumerate(_secao(dados, nome)))


# Lê o YAML e devolve os fatos validados.
def carregar_fatos(caminho: Path | str = ARQUIVO_FATOS) -> Fatos:
    with open(caminho, encoding="utf-8") as arquivo:
        dados = yaml.safe_load(arquivo)
    if not isinstance(dados, dict):
        raise FatosInvalidos("O arquivo de fatos precisa ser um mapa de seções.")

    origem = dados.get("origem_animal")
    if not isinstance(origem, dict):
        raise FatosInvalidos("Seção 'origem_animal' precisa ter 'produtos' e 'fonte'.")

    fatos = Fatos(
        certificacoes=_montar(dados, "certificacoes_organicas", _certificacao),
        registros_sanitarios=_montar(dados, "registros_sanitarios", _registro_sanitario),
        nao_conformidades=_montar(dados, "nao_conformidades", _nao_conformidade),
        dap_caf=_montar(dados, "dap_caf", _dap_caf),
        capacidades=_montar(dados, "capacidades", _capacidade),
        origem_animal=frozenset(_textos(origem, "produtos", "origem_animal")),
        fonte_origem_animal=_campo(origem, "fonte", str, "origem_animal"),
        contratos=_montar(dados, "contratos", _contrato),
    )
    _validar_unicidade(fatos)
    return fatos


# Carrega os fatos uma vez e reaproveita nas chamadas seguintes.
@lru_cache(maxsize=1)
def obter_fatos() -> Fatos:
    return carregar_fatos()
