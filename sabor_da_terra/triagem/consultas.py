"""Análise informativa de cotações e consultas da cooperativa."""

from __future__ import annotations

from datetime import date
from typing import Any

from sabor_da_terra.dados.consultas import buscar_produtores, preco
from sabor_da_terra.dados.repositorio import obter_repositorio
from sabor_da_terra.triagem.orcamento import consolidar_orcamento
from sabor_da_terra.triagem.schema import PedidoTriado, TipoMensagem
from sabor_da_terra.triagem.validar import validar_item


TIPOS_COMERCIAIS = {
    TipoMensagem.COTACAO,
    TipoMensagem.CONSULTA,
}

TERMOS_DOCUMENTAIS = {
    "dap_caf": ("dap/caf", "dap", "caf"),
    "certificacao_organica": (
        "certificação orgânica",
        "certificacao organica",
    ),
    "certificacao_internacional": (
        "certificação internacional",
        "certificacao internacional",
        "equivalente internacional",
    ),
    "rastreabilidade": ("rastreabilidade",),
    "laudo_sanitario": (
        "laudo sanitário",
        "laudo sanitario",
    ),
    "certificado_fitossanitario": (
        "certificados fitossanitários",
        "certificados fitossanitarios",
        "certificado fitossanitário",
        "certificado fitossanitario",
    ),
    "nota_fiscal": ("nota fiscal", "dados de nf"),
}


def criar_pendencia(
    codigo: str,
    mensagem: str,
    fonte: str,
) -> dict[str, str]:
    """Cria uma pendência com origem identificada."""
    return {
        "codigo": codigo,
        "mensagem": mensagem,
        "fonte": fonte,
    }


def data_valida(valor: str | None) -> bool:
    """Verifica se o prazo é uma data ISO válida."""
    if not valor:
        return False

    try:
        date.fromisoformat(valor)
    except ValueError:
        return False

    return True


def identificar_documentos_solicitados(
    pedido: PedidoTriado,
) -> list[dict[str, Any]]:
    """Identifica exigências, sem presumir documentos existentes."""
    texto = " ".join(pedido.observacoes).casefold()
    documentos = []

    for codigo, termos in TERMOS_DOCUMENTAIS.items():
        if any(termo in texto for termo in termos):
            documentos.append({
                "tipo": codigo,
                "situacao": "comprovacao_pendente",
                "fonte": "pedido_estruturado.observacoes",
            })

    return documentos



def listar_catalogo_organico(
    data_referencia: str,
) -> dict[str, Any]:
    """Lista produtos com fornecedores orgânicos certificados.

    Não verifica estoque ou capacidade para uma entrega futura.
    Os preços são referências da tabela de outubro/2026.
    """
    date.fromisoformat(data_referencia)

    repo = obter_repositorio()
    produtos = []

    # bases é uma lista de produtos, não um método.
    for produto in sorted(repo.catalogo.bases):
        consulta = buscar_produtores(
            produto=produto,
            organico=True,
            data_referencia=data_referencia,
        )

        if not consulta.get("encontrado"):
            continue

        produtores = consulta.get("produtores", [])

        if not produtores:
            continue

        variantes = repo.catalogo.variantes(produto)
        precos = []

        for variante in variantes:
            resultado_preco = preco(
                produto=variante,
                organico=True,
                quantidade=1,
            )

            precos.append({
                "variante": variante,
                "preco_disponivel": bool(
                    resultado_preco.get("disponivel", False)
                ),
                "unidade": resultado_preco.get("unidade"),
                "preco_unitario": resultado_preco.get(
                    "preco_unitario"
                ),
                "fonte": resultado_preco.get(
                    "fonte",
                    "tabela_precos_outubro_2026.csv",
                ),
                "aviso": resultado_preco.get("aviso"),
            })

        produtos.append({
            "produto": produto,
            "produtores": [
                {
                    "produtor_id": produtor["produtor_id"],
                    "nome": produtor["nome"],
                    "municipio": produtor.get("municipio"),
                    "certificacao_vigente": produtor[
                        "certificacao_vigente"
                    ],
                    "validade_certificacao": produtor.get(
                        "validade_certificacao"
                    ),
                }
                for produtor in produtores
            ],
            "precos": precos,
            "fonte_produtores": "cadastro de produtores",
            "fonte_precos": "tabela_precos_outubro_2026.csv",
            "disponibilidade_confirmada": False,
        })

    return {
        "data_referencia": data_referencia,
        "total_produtos": len(produtos),
        "produtos": produtos,
        "certificacoes_verificadas_na_referencia": True,
        "disponibilidade_futura_confirmada": False,
        "capacidade_reservada": False,
        "fonte": (
            "catálogo da cooperativa; cadastro de produtores; "
            "tabela_precos_outubro_2026.csv"
        ),
        "aviso": (
            "Certificações verificadas na data de referência. "
            "Preços informativos da tabela de outubro/2026. "
            "Confirmar estoque, safra, preços atualizados e "
            "vigência documental para a data de retirada."
        ),
    }



def analisar_consulta(
    pedido: PedidoTriado,
    data_referencia: str,
) -> dict[str, Any]:
    """Analisa cotações e consultas sem reservar capacidade."""
    if pedido.tipo not in TIPOS_COMERCIAIS:
        raise ValueError(
            "A análise comercial aceita apenas cotação ou consulta."
        )

    referencia = date.fromisoformat(data_referencia)
    prazo_valido = data_valida(pedido.prazo_entrega)

    data_entrega = (
        date.fromisoformat(pedido.prazo_entrega)
        if prazo_valido
        else None
    )

    prazo_utilizavel = (
        data_entrega is not None
        and data_entrega >= referencia
    )

    informacoes_disponiveis = []
    pendencias = []
    avaliacoes = []

    documentos = identificar_documentos_solicitados(pedido)
    catalogo_organico = None

    if not pedido.prazo_entrega:
        pendencias.append(criar_pendencia(
            "PRAZO_ENTREGA_AUSENTE",
            "Informar a data de entrega para avaliar "
            "safra, capacidade e certificações na data.",
            "pedido_estruturado.prazo_entrega",
        ))
    elif not prazo_valido:
        pendencias.append(criar_pendencia(
            "PRAZO_ENTREGA_NAO_RESOLVIDO",
            f"O prazo '{pedido.prazo_entrega}' precisa "
            "ser convertido em uma data exata.",
            "pedido_estruturado.prazo_entrega",
        ))
    elif not prazo_utilizavel:
        pendencias.append(criar_pendencia(
            "PRAZO_ENTREGA_VENCIDO",
            "A data de entrega é anterior à referência.",
            "pedido_estruturado.prazo_entrega",
        ))

    for campo in pedido.campos_faltantes:
        pendencias.append(criar_pendencia(
            "CAMPO_FALTANTE",
            f"Confirmar campo: {campo}.",
            "pedido_estruturado.campos_faltantes",
        ))

    for ambiguidade in pedido.ambiguidades:
        pendencias.append(criar_pendencia(
            "AMBIGUIDADE",
            ambiguidade,
            "pedido_estruturado.ambiguidades",
        ))

    if not pedido.itens:
        pendencias.append(criar_pendencia(
            "ITENS_NAO_ESPECIFICADOS",
            "É necessário definir quais produtos "
            "serão consultados ou cotados.",
            "pedido_estruturado.itens",
        ))

        # Consulta aberta de catálogo orgânico:
        # não exige que o comprador escolha itens antes
        # de receber uma lista informativa.
        texto = " ".join([
            *pedido.observacoes,
            *pedido.ambiguidades,
        ]).casefold()

        if pedido.tipo == TipoMensagem.CONSULTA and (
            "orgânic" in texto or "organic" in texto
        ):
            catalogo_organico = listar_catalogo_organico(
                data_referencia
            )

            informacoes_disponiveis.append({
                "tipo": "catalogo_organico",
                "total_produtos": catalogo_organico[
                    "total_produtos"
                ],
                "fonte": catalogo_organico["fonte"],
            })

            pendencias.append(criar_pendencia(
                "DISPONIBILIDADE_FUTURA_A_CONFIRMAR",
                "Confirmar datas de retirada, disponibilidade "
                "e certificações vigentes nessas datas.",
                "pedido_estruturado.observacoes; cadastro de produtores",
            ))

    for documento in documentos:
        pendencias.append(criar_pendencia(
            "DOCUMENTO_A_COMPROVAR",
            "Verificar a documentação exigida: "
            f"{documento['tipo']}.",
            documento["fonte"],
        ))

    for item in pedido.itens:
        informacoes_disponiveis.append({
            "produto": item.produto,
            "quantidade": item.quantidade,
            "unidade": item.unidade,
            "exige_organico": item.exige_organico,
            "opcional": item.opcional,
            "fonte": "pedido_estruturado.itens",
        })

        if item.quantidade is None:
            pendencias.append(criar_pendencia(
                "QUANTIDADE_A_CONFIRMAR",
                f"Informar quantidade de {item.produto}.",
                "pedido_estruturado.itens",
            ))
            continue

        if not prazo_utilizavel:
            pendencias.append(criar_pendencia(
                "AVALIACAO_DEPENDE_DO_PRAZO",
                f"A disponibilidade de {item.produto} "
                "depende da data de entrega.",
                "pedido_estruturado.prazo_entrega",
            ))
            continue

        avaliacao = validar_item(
            item=item,
            comprador=pedido.comprador,
            data_entrega=data_entrega.isoformat(),
            data_referencia=data_referencia,
        )

        avaliacoes.append(avaliacao)

        for alerta in avaliacao.get("alertas", []):
            fontes = alerta.get("fontes", [])
            fonte = alerta.get("fonte")

            if not fonte and fontes:
                fonte = "; ".join(str(f) for f in fontes)

            pendencias.append({
                "codigo": alerta.get(
                    "codigo", "CONFORMIDADE"
                ),
                "mensagem": alerta.get("mensagem", ""),
                "fonte": fonte or "regras.conformidade",
            })

        if not avaliacao.get("encontrado"):
            pendencias.append(criar_pendencia(
                "ITEM_NAO_AVALIADO",
                avaliacao.get("aviso")
                or f"Não foi possível avaliar {item.produto}.",
                "catalogo; pedido_estruturado.itens",
            ))

    orcamento = (
        consolidar_orcamento(avaliacoes)
        if avaliacoes
        else None
    )

    if orcamento is not None:
        orcamento["orcamento_completo"] = (
            bool(orcamento.get("orcamento_completo", False))
            and len(avaliacoes) == len(pedido.itens)
            and all(
                avaliacao.get("encontrado", False)
                and avaliacao.get("pode_atender", False)
                for avaliacao in avaliacoes
            )
            and not pedido.ambiguidades
        )

    return {
        "tipo": pedido.tipo.value,
        "comprador": pedido.comprador,
        "prazo_entrega": pedido.prazo_entrega,
        "data_referencia": data_referencia,
        "informacoes_disponiveis": informacoes_disponiveis,
        "documentos_solicitados": documentos,
        "catalogo_organico": catalogo_organico,
        "avaliacoes": avaliacoes,
        "orcamento": orcamento,
        "pendencias": pendencias,
        "quantidade_itens": len(pedido.itens),
        "quantidade_itens_avaliados": len(avaliacoes),
        "pode_responder_parcialmente": bool(
            informacoes_disponiveis or documentos
        ),
        "requer_confirmacao": bool(
            pendencias or not prazo_utilizavel
        ),
        "capacidade_reservada": False,
        "pedido_confirmado": False,
        "aviso": (
            "Análise informativa. Não representa reserva "
            "de capacidade, disponibilidade garantida "
            "ou confirmação de venda."
        ),
    }
