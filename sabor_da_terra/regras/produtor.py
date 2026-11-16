"""Alertas de um produtor: certificação orgânica, SIE, fiscalização e cadastro.

As regras de conformidade.py olham um item de pedido; aqui o recorte é o
produtor inteiro, para o resumo da etapa 11 avisar o que
limita as vendas dele. Os fatos são os mesmos de fatos.yaml, e cada alerta cita
a fonte. As mensagens não começam pelo nome do produtor: servem tanto para a
equipe quanto para o texto enviado ao próprio produtor.
"""

from __future__ import annotations

import datetime as dt

from sabor_da_terra.dados import DadosRepository, obter_repositorio
from sabor_da_terra.regras.alertas import ATENCAO, GRAVE, INFO, Alerta, ordenar
from sabor_da_terra.regras.fatos import Fatos, obter_fatos
from sabor_da_terra.regras.validadores import CADASTRO, DIAS_AVISO_VENCIMENTO, _br, _por_que_nao_vale


# Junta nomes de produto numa frase: "mel silvestre, geleia de frutas e doce de goiaba".
def _lista(nomes: list[str]) -> str:
    return nomes[0] if len(nomes) == 1 else f"{', '.join(nomes[:-1])} e {nomes[-1]}"


def alertas_do_produtor(
    produtor_id: str,
    data_referencia: dt.date,
    fatos: Fatos | None = None,
    repo: DadosRepository | None = None,
) -> list[dict[str, str]]:
    """Alertas do produtor na data de referência, do mais grave para o menos grave."""
    fatos = fatos if fatos is not None else obter_fatos()
    repo = repo if repo is not None else obter_repositorio()
    produtor = repo.produtor(produtor_id)
    if produtor is None:
        raise ValueError(f"Produtor inexistente: {produtor_id}")

    alertas: list[Alerta] = []
    for cert in (c for c in fatos.certificacoes if c.produtor_id == produtor_id):
        if not cert.vigente_em(data_referencia):
            if len(cert.produtos) == 1:
                limite = f"{cert.produtos[0]} não pode ser vendido como orgânico"
            else:
                limite = f"estes produtos não podem ser vendidos como orgânicos: {_lista(list(cert.produtos))}"
            alertas.append(
                Alerta(
                    "CERTIFICACAO_VENCIDA",
                    GRAVE,
                    f"Certificação orgânica {cert.certificado}: {_por_que_nao_vale(cert, data_referencia, data_referencia)}. "
                    f"Até sair o novo certificado, {limite}.",
                    cert.fonte,
                )
            )
            continue
        restam = (cert.validade_final - data_referencia).days
        if restam <= DIAS_AVISO_VENCIMENTO:
            alertas.append(
                Alerta(
                    "CERTIFICACAO_A_VENCER",
                    ATENCAO,
                    f"Certificação orgânica {cert.certificado} vence em {_br(cert.validade_final)} "
                    f"(faltam {restam} {'dia' if restam == 1 else 'dias'}). "
                    "Comece a renovação para não parar de vender como orgânico.",
                    cert.fonte,
                )
            )

    produtos = repo.produtos_do_produtor(produtor_id)
    animais = [p for p in produtos if fatos.eh_origem_animal(p)]

    com_nc = set()
    for nc in (nc for nc in fatos.nao_conformidades if nc.produtor_id == produtor_id):
        com_nc.update(nc.produtos)
        alertas.append(
            Alerta(
                "NAO_CONFORMIDADE_SANITARIA",
                GRAVE,
                f"{nc.codigo} ({nc.relatorio}): {nc.descricao}. Por isso {nc.acao}; até lá, só é permitida a "
                f"{nc.permitido}.",
                nc.fonte,
            )
        )

    registro = fatos.registro_sanitario(produtor_id)
    sem_registro = [p for p in animais if p not in com_nc]
    if sem_registro and not (registro and registro.situacao == "vigente"):
        estado = "Registro no SIE pendente" if registro and registro.situacao == "pendente" else "Sem registro no SIE"
        observacao = f" {registro.observacao}" if registro and registro.observacao else ""
        alertas.append(
            Alerta(
                "REGISTRO_SANITARIO",
                ATENCAO,
                f"{estado}: compradores que exigem registro sanitário, como o PNAE, não aceitam "
                f"{_lista(sem_registro)}.{observacao}",
                registro.fonte if registro else fatos.fonte_origem_animal,
            )
        )

    if not produtor["ativo"]:
        alertas.append(Alerta("PRODUTOR_INATIVO", INFO, "Cadastro inativo: não recebe alocação de pedidos.", CADASTRO))

    return [a.como_dict() for a in ordenar(alertas)]
