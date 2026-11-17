"""Uma função por regra de negócio. Cada uma devolve alertas com fonte.

As regras da primeira fase tiram produtores do item (inativo, certificação,
fiscalização, SIE). As da segunda olham o item com quem sobrou (safra,
capacidade, exclusividade, contrato). Nenhuma regra lê arquivo: os dados vêm
do repositório da etapa 4 e os fatos de fatos.yaml.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from sabor_da_terra.dados import DadosRepository
from sabor_da_terra.dados.normalizacao import NOMES_MESES
from sabor_da_terra.regras.alertas import ATENCAO, GRAVE, INFO, Alerta
from sabor_da_terra.regras.fatos import Certificacao, Contrato, Fatos, ItemContrato

CADASTRO = "produtores.csv"
SAZONALIDADE = "sazonalidade.csv"
TABELA_DE_PRECOS = "tabela_precos_outubro_2026.csv"
FICHAS_TECNICAS = "fichas_tecnicas/"

# Prazo mínimo usado na capacidade: as fichas dão produção por semana, então
# um pedido para amanhã é comparado com uma semana de produção.
JANELA_MINIMA_DIAS = 7

# Certificação que vence até esta quantidade de dias depois da entrega ganha aviso.
DIAS_AVISO_VENCIMENTO = 30

_DIAS_DA_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
_DIAS_NO_PLURAL = ["segundas", "terças", "quartas", "quintas", "sextas", "sábados", "domingos"]


@dataclass(frozen=True)
class Contexto:
    produto: str
    variante: str | None
    unidade_venda: str | None
    unidade_item: str | None
    quantidade: float
    organico: bool
    data_entrega: dt.date
    data_referencia: dt.date
    comprador: str
    contrato: Contrato | None
    item_contrato: ItemContrato | None
    produtores: pd.DataFrame
    fatos: Fatos
    repo: DadosRepository

    # Produtores ativos ligados ao produto.
    @property
    def ativos(self) -> pd.DataFrame:
        return self.produtores[self.produtores["ativo"]]

    # Diz se a quantidade está numa unidade diferente da tabela.
    @property
    def unidade_divergente(self) -> bool:
        return bool(self.unidade_item and self.unidade_venda and self.unidade_item != self.unidade_venda)


@dataclass
class Avaliacao:
    alertas: list[Alerta] = field(default_factory=list)
    excluidos: dict[str, list[str]] = field(default_factory=dict)
    pendencias: dict[str, list[str]] = field(default_factory=dict)

    # Tira o produtor do item pelo motivo dado.
    def excluir(self, produtor_id: str, codigo: str) -> None:
        self.excluidos.setdefault(produtor_id, []).append(codigo)

    # Mantém o produtor, mas com algo a confirmar.
    def pendente(self, produtor_id: str, codigo: str) -> None:
        self.pendencias.setdefault(produtor_id, []).append(codigo)

    # Soma a avaliação de outra regra a esta.
    def juntar(self, outra: Avaliacao) -> Avaliacao:
        self.alertas.extend(outra.alertas)
        for pid, codigos in outra.excluidos.items():
            self.excluidos.setdefault(pid, []).extend(codigos)
        for pid, codigos in outra.pendencias.items():
            self.pendencias.setdefault(pid, []).extend(codigos)
        return self


# Data no formato usado nas mensagens (dd/mm/aaaa).
def _br(dia: dt.date) -> str:
    return dia.strftime("%d/%m/%Y")


# Número curto para mensagem: 300, 46,7.
def _num(valor: float) -> str:
    return f"{valor:.0f}" if float(valor).is_integer() else f"{valor:.1f}".replace(".", ",")


# Real com duas casas: R$ 3,80.
def _reais(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


# Primeira letra maiúscula, para frase que começa com o nome do produto.
def _frase(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


# "P008 (Josefa Alves de Souza)".
def _rotulo(linha: pd.Series) -> str:
    return f"{linha['produtor_id']} ({linha['nome']})"


_PLURAIS = {"unidade": "unidades", "maço": "maços", "dúzia": "dúzias", "litro": "litros"}


# Quantidade com a unidade concordando: 1 dúzia, 120 dúzias, 40 kg.
def _qtd(valor: float, unidade: str) -> str:
    return f"{_num(valor)} {unidade if valor == 1 else _PLURAIS.get(unidade, unidade)}"


# Explica por que a certificação não vale no dia, sem dar a entender que já vale.
# "hoje" é a data de referência: decide se a auditoria ainda vai acontecer ou já passou.
def _por_que_nao_vale(cert: Certificacao, dia: dt.date, hoje: dt.date) -> str:
    r = cert.renovacao
    if dia < cert.emissao:
        return f"ela só começa a valer em {_br(cert.emissao)}"
    if r and r.concluida and dia < r.concluida_em:
        return f"venceu em {_br(cert.validade)} e o certificado renovado só vale a partir de {_br(r.concluida_em)}"
    if r and r.concluida:
        return f"o certificado renovado valeu até {_br(r.nova_validade)}"
    texto = f"venceu em {_br(cert.validade)}"
    if r:
        texto += f". A renovação foi pedida em {_br(r.solicitada_em)} (protocolo {r.protocolo})"
        if r.auditoria_em and hoje <= r.auditoria_em:
            texto += f" e a auditoria está marcada para {_br(r.auditoria_em)}"
        elif r.auditoria_em:
            texto += (
                f"; a auditoria estava marcada para {_br(r.auditoria_em)}, "
                "e não há certificado renovado registrado"
            )
        texto += ". O pedido de renovação não libera a venda como orgânico"
    return texto


# ---------------------------------------------------------------------------
# Primeira fase: quem não pode atender
# ---------------------------------------------------------------------------


# Produtor inativo nunca recebe alocação.
def regra_produtor_inativo(ctx: Contexto) -> Avaliacao:
    av = Avaliacao()
    for _, linha in ctx.produtores[~ctx.produtores["ativo"]].iterrows():
        av.excluir(linha["produtor_id"], "PRODUTOR_INATIVO")
        av.alertas.append(
            Alerta("PRODUTOR_INATIVO", INFO, f"{_rotulo(linha)} está inativo no cadastro e não recebe alocação.", CADASTRO)
        )
    return av


# Item orgânico só sai de quem tem certificação vigente na data da entrega.
def regra_certificacao_organica(ctx: Contexto) -> Avaliacao:
    av = Avaliacao()
    if not ctx.organico:
        return av

    sem_certificacao = []
    for _, linha in ctx.ativos.iterrows():
        pid = linha["produtor_id"]
        certificacoes = ctx.fatos.certificacoes_de(pid, ctx.produto)
        if not certificacoes:
            sem_certificacao.append(_rotulo(linha))
            av.excluir(pid, "SEM_CERTIFICACAO_ORGANICA")
            continue

        vigentes = [c for c in certificacoes if c.vigente_em(ctx.data_entrega)]
        if not vigentes:
            cert = max(certificacoes, key=lambda c: c.validade_final)
            av.excluir(pid, "CERTIFICACAO_VENCIDA")
            mensagem = (
                f"{_rotulo(linha)}: a certificação orgânica {cert.certificado} não vale em {_br(ctx.data_entrega)}; "
                f"{_por_que_nao_vale(cert, ctx.data_entrega, ctx.data_referencia)}. Não pode vender {ctx.produto} como orgânico."
            )
            av.alertas.append(Alerta("CERTIFICACAO_VENCIDA", GRAVE, mensagem, cert.fonte))
            continue

        cert = max(vigentes, key=lambda c: c.validade_final)
        restam = (cert.validade_final - ctx.data_entrega).days
        if restam <= DIAS_AVISO_VENCIMENTO:
            av.alertas.append(
                Alerta(
                    "CERTIFICACAO_A_VENCER",
                    INFO,
                    f"{_rotulo(linha)}: a certificação orgânica vale até {_br(cert.validade_final)}, "
                    f"{restam} dia(s) depois da entrega. Para entregas depois disso, é preciso comprovar a renovação.",
                    cert.fonte,
                )
            )

    if sem_certificacao:
        av.alertas.append(
            Alerta(
                "SEM_CERTIFICACAO_ORGANICA",
                INFO,
                f"Sem certificação orgânica para {ctx.produto}: {', '.join(sem_certificacao)}.",
                CADASTRO,
            )
        )
    return av


# Não conformidade da fiscalização suspende a intermediação do produto.
def regra_nao_conformidade(ctx: Contexto) -> Avaliacao:
    av = Avaliacao()
    for _, linha in ctx.ativos.iterrows():
        for nc in ctx.fatos.nao_conformidades_de(linha["produtor_id"], ctx.produto):
            av.excluir(linha["produtor_id"], "NAO_CONFORMIDADE_SANITARIA")
            av.alertas.append(
                Alerta(
                    "NAO_CONFORMIDADE_SANITARIA",
                    GRAVE,
                    f"{nc.codigo} ({nc.relatorio}): {_rotulo(linha)}, {nc.descricao}. "
                    f"Por isso {nc.acao}; até lá, só é permitida a {nc.permitido}.",
                    nc.fonte,
                )
            )
    return av


# Produto de origem animal precisa de SIE vigente; o PNAE não aceita sem.
def regra_registro_sanitario(ctx: Contexto) -> Avaliacao:
    av = Avaliacao()
    if not ctx.fatos.eh_origem_animal(ctx.produto):
        return av

    exige = bool(ctx.contrato and ctx.contrato.exige_sie_origem_animal)
    for _, linha in ctx.ativos.iterrows():
        pid = linha["produtor_id"]
        if ctx.fatos.nao_conformidades_de(pid, ctx.produto):
            continue  # a não conformidade já trata do registro
        registro = ctx.fatos.registro_sanitario(pid)
        if registro and registro.situacao == "vigente":
            continue

        # Decisão da #12 (gabarito CTX-002): produtor de origem animal SEM registro SIE
        # nenhum sai da intermediação — só a venda direta fica. Quando o dataset documenta
        # dispensa para venda direta (ovos do P017), fica a pendência de confirmar com o
        # comprador. SIE em processo (pendente) segue como pendência.
        dispensa_venda_direta = bool(registro and registro.dispensa_venda_direta)
        sem_registro = registro is None or (registro.situacao == "ausente" and not dispensa_venda_direta)
        estado = "tem o SIE pendente" if registro and registro.situacao == "pendente" else "não tem registro SIE"
        fonte = registro.fonte if registro else ctx.fatos.fonte_origem_animal
        observacao = f" {registro.observacao}" if registro and registro.observacao else ""
        if exige or sem_registro:
            if exige:
                motivo = (
                    f"{_rotulo(linha)} {estado}, e o contrato {ctx.contrato.numero} exige SIE, SIM ou SISBI "
                    f"para produto de origem animal.{observacao}"
                )
            else:
                motivo = (
                    f"{_rotulo(linha)} {estado} para {ctx.produto}, e a venda por meio da cooperativa "
                    f"(revenda) exige SIE, SIM ou SISBI; para ele só fica a venda direta ao consumidor.{observacao}"
                )
            av.excluir(pid, "SIE_EXIGIDO")
            av.alertas.append(Alerta("SIE_EXIGIDO", GRAVE, motivo, fonte))
        else:
            av.pendente(pid, "REGISTRO_SANITARIO")
            comprador = ctx.comprador or "o comprador"
            av.alertas.append(
                Alerta(
                    "REGISTRO_SANITARIO",
                    ATENCAO,
                    f"{_rotulo(linha)} {estado} para {ctx.produto}.{observacao} Compradores que exigem registro "
                    f"sanitário, como o PNAE, não aceitam; confirme se {comprador} aceita.",
                    fonte,
                )
            )
    return av


# ---------------------------------------------------------------------------
# Segunda fase: o item com quem sobrou
# ---------------------------------------------------------------------------


# Quantidade numa unidade diferente da tabela não dá para precificar nem comparar.
def regra_unidade(ctx: Contexto) -> Avaliacao:
    av = Avaliacao()
    if ctx.unidade_divergente:
        av.alertas.append(
            Alerta(
                "UNIDADE_DIFERENTE",
                ATENCAO,
                f"A tabela vende {ctx.produto} por {ctx.unidade_venda}, e o item veio em {ctx.unidade_item}. "
                "Converta a quantidade antes de calcular preço e capacidade.",
                TABELA_DE_PRECOS,
            )
        )
    return av


# Disponibilidade do calendário no mês da entrega.
def regra_safra(ctx: Contexto) -> Avaliacao:
    av = Avaliacao()
    mes = ctx.data_entrega.month
    nome_mes = NOMES_MESES[mes - 1]
    linha = ctx.repo.sazonalidade(ctx.produto, mes)
    if linha is None:
        av.alertas.append(
            Alerta("SAFRA_SEM_DADO", INFO, f"Não há dado de sazonalidade para {ctx.produto} no calendário.", SAZONALIDADE)
        )
        return av

    observacao = f" {linha['observacao']}" if linha["observacao"] else ""
    if linha["nivel"] == "nenhuma":
        av.alertas.append(
            Alerta(
                "FORA_DE_SAFRA",
                GRAVE,
                f"{_frase(ctx.produto)} está fora de safra em {nome_mes}: disponibilidade 'nenhuma' no calendário.{observacao}",
                SAZONALIDADE,
            )
        )
    elif linha["nivel"] == "baixa":
        av.alertas.append(
            Alerta(
                "SAFRA_BAIXA",
                ATENCAO,
                f"{_frase(ctx.produto)} tem disponibilidade baixa em {nome_mes}; confirme a quantidade com os produtores.{observacao}",
                SAZONALIDADE,
            )
        )
    return av


# Quantidade pedida contra a capacidade documentada dos elegíveis no prazo.
def regra_capacidade(ctx: Contexto, elegiveis: pd.DataFrame) -> tuple[Avaliacao, dict | None]:
    av = Avaliacao()
    if elegiveis.empty or ctx.unidade_divergente or not ctx.unidade_venda:
        return av, None

    janela = max((ctx.data_entrega - ctx.data_referencia).days, JANELA_MINIMA_DIAS)
    mes = ctx.data_entrega.month
    por_produtor, sem_dado, fontes = [], [], []
    for _, linha in elegiveis.iterrows():
        pid = linha["produtor_id"]
        linhas = [c for c in ctx.fatos.capacidades_de(pid, ctx.produto, mes) if c.unidade == ctx.unidade_venda]
        if not linhas:
            sem_dado.append(pid)
            continue
        minimo, maximo = linhas[0].na_janela(janela)
        por_produtor.append({"produtor_id": pid, "minimo": round(minimo, 1), "maximo": round(maximo, 1)})
        fontes.append(linhas[0].fonte)

    if not por_produtor:
        av.alertas.append(
            Alerta(
                "CAPACIDADE_SEM_DADO",
                INFO,
                f"Não há capacidade documentada em {ctx.unidade_venda} para {ctx.produto} nos produtores elegíveis; "
                "confirme a quantidade com eles.",
                FICHAS_TECNICAS,
            )
        )
        return av, None

    soma_min = sum(p["minimo"] for p in por_produtor)
    soma_max = sum(p["maximo"] for p in por_produtor)
    faixa = _qtd(soma_min, ctx.unidade_venda) if soma_min == soma_max else (
        f"de {_num(soma_min)} a {_qtd(soma_max, ctx.unidade_venda)}"
    )
    pedido = _qtd(ctx.quantidade, ctx.unidade_venda)
    base = f"Capacidade documentada dos elegíveis em {janela} dias: {faixa}."
    if sem_dado:
        base += f" Sem capacidade documentada: {', '.join(sem_dado)}."
    fonte = "; ".join(dict.fromkeys(fontes))

    if ctx.quantidade > soma_max:
        av.alertas.append(Alerta("CAPACIDADE_EXCEDIDA", GRAVE, f"O pedido de {pedido} passa da capacidade. {base}", fonte))
    elif ctx.quantidade > soma_min:
        av.alertas.append(
            Alerta("CAPACIDADE_NO_LIMITE", ATENCAO, f"O pedido de {pedido} está no limite. {base} Confirme com os produtores.", fonte)
        )
    else:
        av.alertas.append(
            Alerta(
                "CAPACIDADE",
                INFO,
                f"O pedido de {pedido} cabe na capacidade. {base} Capacidade de produção não é estoque: "
                "confirme a disponibilidade com os produtores.",
                fonte,
            )
        )

    bloco = {
        "janela_dias": janela,
        "unidade": ctx.unidade_venda,
        "minimo": round(soma_min, 1),
        "maximo": round(soma_max, 1),
        "por_produtor": por_produtor,
        "sem_dado": sem_dado,
    }
    return av, bloco


# Produto de um só produtor ativo: sem alternativa se ele falhar.
def regra_exclusividade(ctx: Contexto) -> Avaliacao:
    av = Avaliacao()
    if len(ctx.ativos) == 1:
        linha = ctx.ativos.iloc[0]
        av.alertas.append(
            Alerta(
                "PRODUTOR_EXCLUSIVO",
                INFO,
                f"Só {_rotulo(linha)} fornece {ctx.produto}: não há outro produtor se ele não puder atender.",
                CADASTRO,
            )
        )
    return av


# Preço, prazo de vigência, dia de entrega e exigências do contrato do comprador.
def regra_contrato(ctx: Contexto, elegiveis: pd.DataFrame) -> Avaliacao:
    av = Avaliacao()
    contrato = ctx.contrato
    if contrato is None:
        quem = f"'{ctx.comprador}'" if ctx.comprador else "este comprador"
        av.alertas.append(
            Alerta("SEM_CONTRATO", INFO, f"Não há contrato registrado com {quem}: vale a tabela geral de preços.", TABELA_DE_PRECOS)
        )
        return av

    vigente = contrato.vigente_em(ctx.data_entrega)
    if not vigente:
        fim = _br(contrato.fim) if contrato.fim else "prazo indeterminado"
        mensagem = (
            f"O contrato {contrato.numero} vale de {_br(contrato.inicio)} até {fim}; a entrega em "
            f"{_br(ctx.data_entrega)} fica fora desse período."
        )
        if contrato.preco == "contrato":
            mensagem += " Não há preço contratado válido para essa data."
        av.alertas.append(Alerta("CONTRATO_FORA_DA_VIGENCIA", ATENCAO, mensagem, contrato.fonte))

    if contrato.preco == "contrato" and vigente:
        item = ctx.item_contrato
        if item is None:
            av.alertas.append(
                Alerta(
                    "ITEM_FORA_DO_CONTRATO",
                    ATENCAO,
                    f"{_frase(ctx.produto)} não está no contrato {contrato.numero}: não há preço contratado para ele.",
                    contrato.fonte,
                )
            )
        else:
            mensagem = f"{contrato.comprador} paga {_reais(item.preco)}/{item.unidade} por {ctx.produto} pelo contrato {contrato.numero}, não pela tabela geral."
            if item.observacao:
                mensagem += f" Observação do contrato: {item.observacao}."
            av.alertas.append(Alerta("PRECO_CONTRATO", INFO, mensagem, contrato.fonte))
            if item.exige_organico:
                av.alertas.append(
                    Alerta(
                        "CONTRATO_EXIGE_ORGANICO",
                        INFO,
                        f"O contrato {contrato.numero} compra {ctx.produto} orgânico; o item foi avaliado como orgânico.",
                        contrato.fonte,
                    )
                )

    if contrato.dias_entrega and ctx.data_entrega.weekday() not in contrato.dias_entrega:
        dias = " e ".join(_DIAS_NO_PLURAL[d] for d in contrato.dias_entrega)
        av.alertas.append(
            Alerta(
                "ENTREGA_FORA_DO_DIA",
                ATENCAO,
                f"O contrato {contrato.numero} prevê entrega só às {dias}; {_br(ctx.data_entrega)} é "
                f"{_DIAS_DA_SEMANA[ctx.data_entrega.weekday()]}.",
                contrato.fonte,
            )
        )

    if contrato.exige_dap_caf:
        for _, linha in elegiveis.iterrows():
            pid = linha["produtor_id"]
            dap = ctx.fatos.dap_caf_de(pid)
            if dap and dap.situacao == "vigente":
                continue
            av.pendente(pid, "DAP_CAF_NAO_COMPROVADA")
            if dap:
                mensagem = (
                    f"{_rotulo(linha)}: a DAP/CAF ({dap.numero}) aparece no documento sem validade, e o contrato "
                    f"{contrato.numero} exige DAP ou CAF vigente. Comprove antes de faturar."
                )
                fonte = dap.fonte
            else:
                mensagem = (
                    f"{_rotulo(linha)}: nenhum documento comprova DAP ou CAF vigente, e o contrato {contrato.numero} "
                    "exige. Comprove antes de faturar."
                )
                fonte = contrato.fonte
            av.alertas.append(Alerta("DAP_CAF_NAO_COMPROVADA", ATENCAO, mensagem, fonte))

    if contrato.condicoes:
        av.alertas.append(
            Alerta(
                "EXIGENCIAS_CONTRATO",
                INFO,
                f"Contrato {contrato.numero} com {contrato.comprador}: {'; '.join(contrato.condicoes)}.",
                contrato.fonte,
            )
        )
    return av
