"""Fila consolidada de triagem de pedidos da cooperativa."""

from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from typing import Any

from sabor_da_terra.regras.fatos import obter_fatos
from sabor_da_terra.triagem.alocar import AlocadorSemanal
from sabor_da_terra.triagem.consultas import analisar_consulta
from sabor_da_terra.triagem.historico import identificar_historico
from sabor_da_terra.triagem.notificacoes import analisar_notificacao

from sabor_da_terra.triagem.orcamento import consolidar_orcamento
from sabor_da_terra.triagem.priorizar import classificar_prioridade, classificar_urgencia
from sabor_da_terra.triagem.schema import PedidoTriado, TipoMensagem
from sabor_da_terra.triagem.validar import validar_item
from sabor_da_terra.triagem.ofertas import identificar_ofertas, cruzar_ofertas

CAMINHO_PEDIDOS = Path("tests/fixtures/triagem_15_pedidos.json")

TIPOS_COMPRA = {TipoMensagem.COMPRA, TipoMensagem.COMPRA_URGENTE}

TIPOS_COMERCIAIS = {TipoMensagem.COTACAO, TipoMensagem.CONSULTA}

ORDEM_PRIORIDADE = {"alta": 0, "media": 1, "analise": 2, "baixa": 3}


def carregar_pedidos(
    caminho: Path = CAMINHO_PEDIDOS,
) -> list[dict[str, Any]]:
    """Carrega pedidos estruturados e recupera metadados originais."""

    with caminho.open(encoding="utf-8") as arquivo:
        registros = json.load(arquivo)

    if not isinstance(registros, list):
        raise ValueError("O arquivo de pedidos deve conter uma lista.")

    caminho_originais = Path("data/pedidos.json")
    originais_por_id = {}

    if caminho_originais.is_file():
        with caminho_originais.open(encoding="utf-8") as arquivo:
            originais = json.load(arquivo)

        if not isinstance(originais, list):
            raise ValueError(
                "O arquivo original de pedidos deve conter uma lista."
            )

        originais_por_id = {
            registro["id"]: registro
            for registro in originais
        }

    pedidos = []

    for registro in registros:
        if "id" not in registro or "resultado" not in registro:
            raise ValueError("Registro sem id ou resultado.")

        pedido = PedidoTriado.model_validate(registro["resultado"])
        original = originais_por_id.get(registro["id"], {})

        pedidos.append({
            "id": registro["id"],
            "pedido": pedido,
            "data_recebimento": (
                registro.get("data_recebimento")
                or original.get("data_recebimento")
            ),
            "mensagem_original": (
                registro.get("mensagem_original")
                or original.get("mensagem_original", "")
            ),
        })

    return pedidos


def identificar_referencia_historica(pedido: PedidoTriado) -> str | None:
    """Identifica referências implícitas ao histórico."""
    texto = " ".join([*pedido.ambiguidades, *pedido.observacoes]).casefold()
    if "de sempre" in texto:
        return "de_sempre"
    if "última vez" in texto or "ultima vez" in texto:
        return "ultima_vez"
    return None

def criar_alerta(codigo: str, mensagem: str, fonte: str) -> dict[str, str]:
    """Cria um alerta com fonte identificável."""
    return {"codigo": codigo, "mensagem": mensagem, "fonte": fonte}

def sugerir_hipotese_documental(
        pedido: PedidoTriado,
        historico: dict[str, Any] | None,
        ) -> dict[str, Any] | None:
    """Sugere um produto com evidência documental, sem confirmar a compra."""
    if historico is None or historico.get("hipoteses"):
        return None
    termos = " ".join(
        [
            *(item.produto for item in pedido.itens),
            *pedido.ambiguidades,
            *pedido.observacoes,
        ]
    ).casefold()
    if "queijo" not in termos or "artesanal" not in termos:
        return None
    fonte = Path("data/fichas_tecnicas/queijo_coalho.txt")
    if not fonte.is_file():
        return None
    conteudo = fonte.read_text(encoding="utf-8").casefold()
    if "queijo de coalho artesanal" not in conteudo:
        return None
    return {
        "produto": "queijo coalho",
        "descricao": "Queijo de Coalho Artesanal do Agreste",
        "tipo_evidencia": "ficha_tecnica",
        "fonte": str(fonte),
        "historico_comprovado": False,
        "confirmado": False,
        "requer_confirmacao": True,
        "aviso": (
            "Possível queijo coalho artesanal, conforme ficha técnica. "
            "Não foi encontrado histórico anterior deste comprador. "
            "Confirmar o produto solicitado antes de qualquer alocação."
        ),
    }

def identificar_contrato(comprador: str | None) -> dict[str, Any] | None:
    """Identifica contratos usando os fatos da Issue #5."""
    contrato = obter_fatos().contrato_do_comprador(comprador)
    if contrato is None:
        return None
    return {
        "numero": contrato.numero,
        "comprador": contrato.comprador,
        "inicio": contrato.inicio.isoformat(),
        "fim": contrato.fim.isoformat() if contrato.fim else None,
        "exige_dap_caf": contrato.exige_dap_caf,
        "exige_sie_origem_animal": contrato.exige_sie_origem_animal,
        "condicoes": list(contrato.condicoes),
        "fonte": contrato.fonte,
    }

def prioridade_do_registro(registro: dict[str, Any], data_referencia: date) -> dict[str, Any]:
    """Classifica prioridade considerando o contrato."""
    pedido: PedidoTriado = registro["pedido"]
    contrato = identificar_contrato(pedido.comprador)
    return classificar_prioridade(
        pedido, data_referencia=data_referencia, possui_contrato=contrato is not None
    )

def calcular_urgencia(
        registro: dict[str, Any], pedido: PedidoTriado, possui_contrato: bool
        ) -> dict[str, Any]:
    """Calcula urgência sem inventar data de recebimento."""
    data_recebimento = registro.get("data_recebimento")
    if not data_recebimento:
        return {
            "horas_restantes": None,
            "data_recebimento": None,
            "prazo_entrega": pedido.prazo_entrega,
            "urgencia_nao_calculada": True,
            "requer_confirmacao": True,
            "aviso": (
                "Data de recebimento não informada. "
                "Não é possível calcular a urgência em horas."
            ),
            "fonte": "registro.data_recebimento",
        }
    resultado = classificar_urgencia(
        pedido,
        data_recebimento=data_recebimento,
        mensagem_original=registro.get("mensagem_original", ""),
        possui_contrato=possui_contrato,
    )
    return {
        **resultado,
        "urgencia_nao_calculada": resultado.get("horas_restantes") is None,
    }

def processar_pedido(
        registro: dict[str, Any], data_referencia: date, alocador: AlocadorSemanal
        ) -> dict[str, Any]:
    """Processa um registro sem confirmar pedidos ou produção."""
    pedido: PedidoTriado = registro["pedido"]
    identificador = registro["id"]
    contrato = identificar_contrato(pedido.comprador)
    prioridade = classificar_prioridade(
        pedido,
        data_referencia=data_referencia,
        possui_contrato=contrato is not None,
    )
    urgencia = calcular_urgencia(
        registro=registro, pedido=pedido, possui_contrato=contrato is not None
    )
    alertas: list[dict[str, Any]] = []
    avaliacoes: list[dict[str, Any]] = []
    alocacoes: list[dict[str, Any]] = []
    historico = None
    analise_comercial = None
    # 1. Dados ausentes para cálculo de urgência.
    if not registro.get("data_recebimento"):
        alertas.append(criar_alerta(
            "DATA_RECEBIMENTO_AUSENTE",
            "Não foi possível calcular a urgência em horas porque a data de recebimento não foi informada.",
            "registro.data_recebimento",
        ))
    # 2. Ambiguidades e campos faltantes.
    for ambiguidade in pedido.ambiguidades:
        alertas.append(criar_alerta(
            "AMBIGUIDADE", ambiguidade, "pedido_estruturado.ambiguidades"
        ))
    for campo in pedido.campos_faltantes:
        alertas.append(criar_alerta(
            "CAMPO_FALTANTE", f"Campo pendente: {campo}",
            "pedido_estruturado.campos_faltantes",
        ))
    # 3. Prazo.
    if prioridade["situacao_prazo"] == "vencido":
        alertas.append(criar_alerta(
            "PRAZO_VENCIDO", "Prazo vencido. Confirmar validade da solicitação.",
            "pedido_estruturado.prazo_entrega",
        ))
    if prioridade["situacao_prazo"] == "nao_resolvido":
        alertas.append(criar_alerta(
            "PRAZO_NAO_RESOLVIDO", "Prazo textual exige esclarecimento.",
            "pedido_estruturado.prazo_entrega",
        ))
    # 4. Histórico e hipótese documental.
    expressao = identificar_referencia_historica(pedido)
    if expressao and pedido.comprador:
        historico = identificar_historico(
        comprador=pedido.comprador,
        data_referencia=data_referencia.isoformat(),
        expressao=expressao,
        )
        alertas.append(criar_alerta(
            "CONFIRMAR_HISTORICO",
            historico["aviso"],
            "data/financeiro.csv; data/lotes.csv",
        ))
        hipotese_documental = sugerir_hipotese_documental(
        pedido=pedido,
        historico=historico,
        )
        if hipotese_documental is not None:
            historico["hipotese_documental"] = hipotese_documental
            alertas.append(criar_alerta(
                "HIPOTESE_DOCUMENTAL",
                hipotese_documental["aviso"],
                hipotese_documental["fonte"],
            ))
    # 5. Contrato.
    if contrato is not None:
        alertas.append(criar_alerta(
            "CONTRATO_IDENTIFICADO",
            f"Comprador vinculado ao contrato {contrato['numero']}. Verificar exigências contratuais.",
            contrato["fonte"],
        ))
    # 6. Cotações e consultas.
    if pedido.tipo in TIPOS_COMERCIAIS:
        analise_comercial = analisar_consulta(
        pedido=pedido, data_referencia=data_referencia.isoformat()
        )
        avaliacoes = analise_comercial["avaliacoes"]
        for pendencia in analise_comercial["pendencias"]:
            if not any(
                existente["codigo"] == pendencia["codigo"]
                and existente["mensagem"] == pendencia["mensagem"]
                for existente in alertas
            ):
                alertas.append(pendencia)
        return {
            "id": identificador,
            "tipo": pedido.tipo.value,
            "comprador": pedido.comprador,
            "prioridade": prioridade["prioridade"],
            "situacao_prazo": prioridade["situacao_prazo"],
            "prazo_entrega": pedido.prazo_entrega,
            "contrato": contrato,
            "urgencia": urgencia,
            "orcamento": analise_comercial["orcamento"],
            "analise_comercial": analise_comercial,
            "avaliacoes": avaliacoes,
            "alocacoes": [],
            "historico": historico,
            "alertas": alertas,
            "status": "analise_sem_alocacao",
            "requer_confirmacao": (
                prioridade["requer_confirmacao"]
                or analise_comercial["requer_confirmacao"]
                or urgencia.get("requer_confirmacao", False)
            ),
        }
    # 7. Notificações oficiais: checklist documental sem alocação.
    if pedido.tipo == TipoMensagem.NOTIFICACAO_OFICIAL:
        analise_documental = analisar_notificacao(
        pedido=pedido, data_referencia=data_referencia.isoformat()
        )
        for pendencia in analise_documental["pendencias"]:
            if not any(
                existente["codigo"] == pendencia["codigo"]
                and existente["mensagem"] == pendencia["mensagem"]
                for existente in alertas
            ):
                alertas.append(pendencia)
        return {
            "id": identificador,
            "tipo": pedido.tipo.value,
            "comprador": pedido.comprador,
            "prioridade": prioridade["prioridade"],
            "situacao_prazo": prioridade["situacao_prazo"],
            "prazo_entrega": pedido.prazo_entrega,
            "contrato": contrato,
            "urgencia": urgencia,
            "orcamento": None,
            "analise_comercial": None,
            "analise_documental": analise_documental,
            "avaliacoes": [],
            "alocacoes": [],
            "historico": historico,
            "alertas": alertas,
            "status": "analise_sem_alocacao",
            "requer_confirmacao": True,
        }
    # 8. Ofertas de produtores e demais mensagens sem compra.
    if pedido.tipo not in TIPOS_COMPRA:
        return {
            "id": identificador,
            "tipo": pedido.tipo.value,
            "comprador": pedido.comprador,
            "prioridade": prioridade["prioridade"],
            "situacao_prazo": prioridade["situacao_prazo"],
            "prazo_entrega": pedido.prazo_entrega,
            "contrato": contrato,
            "urgencia": urgencia,
            "orcamento": None,
            "analise_comercial": None,
            "avaliacoes": [],
            "alocacoes": [],
            "historico": historico,
            "alertas": alertas,
            "status": "analise_sem_alocacao",
            "requer_confirmacao": (
                prioridade["requer_confirmacao"]
                or historico is not None
                or urgencia.get("requer_confirmacao", False)
            ),
        }
    # 9. Bloqueios de alocação de compras.
    bloqueio_alocacao = (
        prioridade["situacao_prazo"] in {"vencido", "nao_resolvido"}
        or bool(pedido.ambiguidades)
        or historico is not None
    )
    # 10. Avaliação e sugestão de alocação.
    for item in pedido.itens:
        avaliacao = validar_item(
        item=item,
        comprador=pedido.comprador,
        data_entrega=pedido.prazo_entrega,
        data_referencia=data_referencia.isoformat(),
        )
        avaliacoes.append(avaliacao)
        for alerta in avaliacao.get("alertas", []):
            fontes = alerta.get("fontes", [])
            fonte = alerta.get("fonte")
            if not fonte and fontes:
                fonte = "; ".join(str(f) for f in fontes)
            alertas.append({
                "codigo": alerta.get("codigo", "CONFORMIDADE"),
                "mensagem": alerta.get("mensagem", ""),
                "severidade": alerta.get("severidade"),
                "fonte": fonte or "regras.conformidade",
            })
        if bloqueio_alocacao:
            alocacoes.append({
                "produto": item.produto,
                "status": "aguardando_confirmacao",
                "alocacoes": [],
            })
            continue
        if not avaliacao.get("encontrado"):
            alocacoes.append({
                "produto": item.produto,
                "status": "nao_alocavel",
                "alocacoes": [],
            })
            continue
        resultado = alocador.alocar_avaliacao(avaliacao)
        alocacoes.append(resultado)
    # 11. Orçamento consolidado de compras.
    orcamento = consolidar_orcamento(avaliacoes)
    return {
        "id": identificador,
        "tipo": pedido.tipo.value,
        "comprador": pedido.comprador,
        "prioridade": prioridade["prioridade"],
        "situacao_prazo": prioridade["situacao_prazo"],
        "prazo_entrega": pedido.prazo_entrega,
        "contrato": contrato,
        "urgencia": urgencia,
        "orcamento": orcamento,
        "analise_comercial": None,
        "avaliacoes": avaliacoes,
        "alocacoes": alocacoes,
        "historico": historico,
        "alertas": alertas,
        "status": (
            "aguardando_confirmacao"
            if bloqueio_alocacao else "sugestao_nao_confirmada"
        ),
        "requer_confirmacao": (
            prioridade["requer_confirmacao"]
            or historico is not None
            or urgencia.get("requer_confirmacao", False)
        ),
    }


def triar_pendentes(
    data_referencia: str,
    caminho_pedidos: Path = CAMINHO_PEDIDOS,
) -> dict[str, Any]:
    """Gera a fila consolidada para function calling."""

    referencia = date.fromisoformat(data_referencia)

    # 1. Carrega os pedidos estruturados com suas datas originais.
    registros = carregar_pedidos(caminho_pedidos)

    # 2. Considera somente ofertas recebidas até a data da triagem.
    # Ofertas futuras não podem influenciar decisões anteriores.
    ofertas = identificar_ofertas(
        registros,
        data_referencia=referencia,
    )

    # 3. Inicializa o controle de capacidade semanal.
    alocador = AlocadorSemanal()

    # 4. Ordena os registros por prioridade.
    registros.sort(
        key=lambda registro: (
            ORDEM_PRIORIDADE[
                prioridade_do_registro(
                    registro,
                    data_referencia=referencia,
                )["prioridade"]
            ],
            registro["id"],
        )
    )

    # 5. Processa todos os registros da fila.
    fila = [
        processar_pedido(
            registro,
            data_referencia=referencia,
            alocador=alocador,
        )
        for registro in registros
    ]

    # 6. Indexa os registros originais pelo identificador.
    registros_por_id = {
        registro["id"]: registro
        for registro in registros
    }

    # 7. Cruza demandas com ofertas conhecidas.
    for resultado_pedido in fila:
        registro_original = registros_por_id[
            resultado_pedido["id"]
        ]

        correspondencias = cruzar_ofertas(
            registro_original,
            ofertas,
        )

        resultado_pedido[
            "correspondencias_ofertas"
        ] = correspondencias

        # 8. Gera alerta somente para ofertas
        # comprovadamente posteriores ao prazo.
        for correspondencia in correspondencias:
            if (
                correspondencia["compatibilidade_temporal"]
                is False
            ):
                resultado_pedido["alertas"].append(
                    criar_alerta(
                        "OFERTA_POSTERIOR_AO_PRAZO",
                        (
                            f"Oferta {correspondencia['pedido_oferta']} "
                            f"do produtor {correspondencia['produtor_id']} "
                            f"corresponde ao produto "
                            f"{correspondencia['produto']}, mas foi "
                            f"recebida após o prazo original da demanda. "
                            f"Confirmar se o comprador aceita "
                            f"renegociar."
                        ),
                        correspondencia["fonte"],
                    )
                )

    # 9. Retorna a fila consolidada.
    return {
        "data_referencia": referencia.isoformat(),
        "total_registros": len(fila),
        "fila": fila,
        "capacidade_semanal_sugerida": [
            {
                "produtor_id": chave[0],
                "produto": chave[1],
                "unidade": chave[2],
                "semana_inicio": chave[3].isoformat(),
                "quantidade": quantidade,
            }
            for chave, quantidade in alocador.utilizado.items()
        ],
        "confirmacoes_realizadas": False,
        "notificacoes_enviadas": False,
    }
