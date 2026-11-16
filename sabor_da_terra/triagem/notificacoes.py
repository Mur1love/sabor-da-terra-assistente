"""Análise documental de notificações oficiais."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.triagem.schema import PedidoTriado, TipoMensagem


DOCUMENTOS_EXIGIDOS = {
    "cadastro_produtores": {
        "descricao": "Cadastro de produtores",
        "arquivos": ["produtores.csv"],
    },
    "certificacoes_organicas": {
        "descricao": "Certificações orgânicas",
        "prefixos": ["cert_organica_"],
    },
    "laudos_sanitarios": {
        "descricao": "Laudos sanitários",
        "prefixos": ["laudo_sanitario_"],
    },
    "rastreabilidade": {
        "descricao": "Registros de rastreabilidade",
        "arquivos": ["lotes.csv"],
    },
    "contratos_institucionais": {
        "descricao": "Contratos institucionais",
        "prefixos": ["contrato_"],
    },
}


def _pasta_data_padrao() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def _localizar_evidencias(
    pasta_data: Path,
    documentos: list[dict[str, Any]],
    arquivos: list[str],
    prefixos: list[str],
) -> list[str]:
    """Localiza evidências sem afirmar validade documental."""

    encontrados = []

    for nome in arquivos:
        caminho = pasta_data / nome
        if caminho.is_file() and caminho.stat().st_size > 0:
            encontrados.append(nome)

    for documento in documentos:
        nome = documento["arquivo"]

        if any(nome.startswith(prefixo) for prefixo in prefixos):
            encontrados.append(documento["caminho"])

    return sorted(set(encontrados))


def analisar_notificacao(
    pedido: PedidoTriado,
    data_referencia: str,
    pasta_data: Path | None = None,
) -> dict[str, Any]:
    """Gera checklist documental para uma notificação oficial."""

    if pedido.tipo != TipoMensagem.NOTIFICACAO_OFICIAL:
        raise ValueError(
            "A análise aceita apenas notificações oficiais."
        )

    referencia = date.fromisoformat(data_referencia)
    pasta = pasta_data or _pasta_data_padrao()

    documentos = carregar_documentos(pasta)

    checklist = []
    pendencias = []

    for codigo, configuracao in DOCUMENTOS_EXIGIDOS.items():
        fontes = _localizar_evidencias(
            pasta_data=pasta,
            documentos=documentos,
            arquivos=configuracao.get("arquivos", []),
            prefixos=configuracao.get("prefixos", []),
        )

        situacao = (
            "evidencia_localizada"
            if fontes
            else "evidencia_nao_localizada"
        )

        checklist.append({
            "codigo": codigo,
            "descricao": configuracao["descricao"],
            "situacao": situacao,
            "fontes": fontes,
            "validade_comprovada": False,
            "aceite_oficial_confirmado": False,
        })

        pendencias.append({
            "codigo": (
                "VALIDACAO_DOCUMENTAL_PENDENTE"
                if fontes
                else "DOCUMENTO_NAO_LOCALIZADO"
            ),
            "mensagem": (
                f"Verificar documentação: "
                f"{configuracao['descricao']}."
            ),
            "fonte": (
                "; ".join(f"data/{fonte}" for fonte in fontes)
                if fontes
                else "pedido_estruturado.observacoes"
            ),
        })

    prazo = None
    situacao_prazo = "nao_informado"

    if pedido.prazo_entrega:
        try:
            prazo = date.fromisoformat(pedido.prazo_entrega)
            situacao_prazo = (
                "vencido"
                if prazo < referencia
                else "no_prazo"
            )
        except ValueError:
            situacao_prazo = "nao_resolvido"

    risco_sie = any(
        "suspensão do sie" in observacao.casefold()
        for observacao in pedido.observacoes
    )

    return {
        "orgao": pedido.comprador,
        "tipo": pedido.tipo.value,
        "data_referencia": data_referencia,
        "prazo": pedido.prazo_entrega,
        "situacao_prazo": situacao_prazo,
        "checklist": checklist,
        "total_documentos_exigidos": len(checklist),
        "total_categorias_com_evidencias": sum(
            bool(item["fontes"]) for item in checklist
        ),
        "pendencias": pendencias,
        "risco_suspensao_sie_informado": risco_sie,
        "resposta_oficial_enviada": False,
        "inspecao_concluida": False,
        "documentacao_aprovada": False,
        "requer_confirmacao": True,
        "aviso": (
            "Checklist preliminar. A existência de arquivos "
            "não comprova sua validade, completude ou aceitação "
            "pela autoridade fiscalizadora."
        ),
    }
