"""Exportação da fila de triagem para Markdown e JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _texto(valor: Any) -> str:
    """Formata valores para exibição em Markdown."""
    if valor is None:
        return "Não informado"
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    return str(valor).replace("|", "\\|").replace("\n", " ")


def gerar_markdown(resultado: dict[str, Any]) -> str:
    """Gera relatório legível sem modificar a fila original."""

    linhas = [
        "# Fila de Triagem Inteligente",
        "",
        f"**Data de referência:** {resultado['data_referencia']}",
        f"**Total de registros:** {resultado['total_registros']}",
        "",
        "> Relatório de análise. Nenhum pedido, produção ou "
        "disponibilidade foi confirmado automaticamente.",
        "",
        "## Ordem de prioridade",
        "",
        "| Ordem | Pedido | Comprador | Prioridade | Status | Prazo |",
        "|---:|---|---|---|---|---|",
    ]

    for ordem, pedido in enumerate(resultado["fila"], start=1):
        linhas.append(
            f"| {ordem} | {_texto(pedido['id'])} "
            f"| {_texto(pedido['comprador'])} "
            f"| {_texto(pedido['prioridade'])} "
            f"| {_texto(pedido['status'])} "
            f"| {_texto(pedido['prazo_entrega'])} |"
        )

    linhas.extend(["", "## Análise por registro", ""])

    for pedido in resultado["fila"]:
        linhas.extend([
            f"### {pedido['id']} — {_texto(pedido['comprador'])}",
            "",
            f"**Tipo:** {_texto(pedido['tipo'])}",
            f"**Prioridade:** {_texto(pedido['prioridade'])}",
            f"**Status:** {_texto(pedido['status'])}",
            f"**Prazo:** {_texto(pedido['prazo_entrega'])}",
            f"**Requer confirmação:** "
            f"{_texto(pedido['requer_confirmacao'])}",
            "",
            "#### Sugestões de alocação",
            "",
        ])

        encontrou_alocacao = False

        for item in pedido.get("alocacoes", []):
            for alocacao in item.get("alocacoes", []):
                encontrou_alocacao = True
                linhas.append(
                    f"- **{_texto(item.get('produto'))}:** "
                    f"{_texto(alocacao.get('quantidade'))} "
                    f"{_texto(alocacao.get('unidade'))} "
                    f"— Produtor {_texto(alocacao.get('produtor_id'))}. "
                    f"Fonte: `{_texto(alocacao.get('fonte'))}`. "
                    + (
                        "**Reserva condicionada à confirmação.**"
                        if alocacao.get("condicionada")
                        else "**Sugestão não confirmada.**"
                    )
                )

        if not encontrou_alocacao:
            linhas.append("- Nenhuma alocação sugerida.")

        linhas.extend(["", "#### Correspondências de ofertas", ""])

        correspondencias = pedido.get("correspondencias_ofertas", [])

        if not correspondencias:
            linhas.append("- Nenhuma correspondência identificada.")

        for oferta in correspondencias:
            linhas.append(
                f"- **{_texto(oferta['produto'])}:** "
                f"{_texto(oferta['quantidade_potencial'])} "
                f"{_texto(oferta['unidade'])} "
                f"do produtor {_texto(oferta['produtor_id'])}, "
                f"oferta {_texto(oferta['pedido_oferta'])}. "
                f"Compatibilidade temporal: "
                f"{_texto(oferta['compatibilidade_temporal'])}. "
                f"{_texto(oferta['observacao'])} "
                f"Fonte: `{_texto(oferta['fonte'])}`."
            )

        linhas.extend(["", "#### Histórico", ""])

        historico = pedido.get("historico")

        if historico is None:
            linhas.append("- Não aplicável.")
        else:
            for hipotese in historico.get("hipoteses", []):
                linhas.append(f"- Hipótese histórica: {_texto(hipotese)}")

            documental = historico.get("hipotese_documental")

            if documental:
                linhas.append(
                    f"- **Hipótese documental:** "
                    f"{_texto(documental['produto'])}. "
                    f"{_texto(documental['aviso'])} "
                    f"Fonte: `{_texto(documental['fonte'])}`."
                )

            if historico.get("requer_confirmacao"):
                linhas.append("- Histórico pendente de confirmação.")

        linhas.extend(["", "#### Alertas e fontes", ""])

        alertas = pedido.get("alertas", [])

        if not alertas:
            linhas.append("- Nenhum alerta.")

        for alerta in alertas:
            linhas.append(
                f"- **{_texto(alerta.get('codigo'))}:** "
                f"{_texto(alerta.get('mensagem'))} "
                f"Fonte: `{_texto(alerta.get('fonte'))}`."
            )

        linhas.append("")

    linhas.extend([
        "## Demanda da semana × capacidade documentada",
        "",
        "| Produto | Semana | Demanda | Pedidos | Capacidade máx. | Excede? |",
        "|---|---|---:|---|---:|---|",
    ])

    for linha in resultado.get("demanda_semanal", []):
        linhas.append(
            f"| {_texto(linha['produto'])} "
            f"| {_texto(linha['semana_inicio'])} "
            f"| {_texto(linha['demanda_total'])} {_texto(linha['unidade'])} "
            f"| {_texto(', '.join(linha['pedidos']))} "
            f"| {_texto(linha['capacidade_maxima_documentada'])} "
            f"| {_texto(linha['excede_capacidade'])} |"
        )

    linhas.extend([
        "",
        "## Capacidade semanal sugerida",
        "",
        "| Produtor | Produto | Quantidade | Unidade | Semana |",
        "|---|---|---:|---|---|",
    ])

    for capacidade in resultado.get("capacidade_semanal_sugerida", []):
        linhas.append(
            f"| {_texto(capacidade['produtor_id'])} "
            f"| {_texto(capacidade['produto'])} "
            f"| {_texto(capacidade['quantidade'])} "
            f"| {_texto(capacidade['unidade'])} "
            f"| {_texto(capacidade['semana_inicio'])} |"
        )

    linhas.extend([
        "",
        f"**Confirmações realizadas:** "
        f"{_texto(resultado['confirmacoes_realizadas'])}",
        "",
        f"**Notificações enviadas:** "
        f"{_texto(resultado['notificacoes_enviadas'])}",
        "",
    ])

    return "\n".join(linhas)


def salvar_markdown(
    resultado: dict[str, Any],
    destino: str | Path = "exemplos/fila_triagem.md",
) -> Path:
    """Salva a fila em Markdown."""
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        gerar_markdown(resultado),
        encoding="utf-8",
    )
    return caminho


def salvar_json(
    resultado: dict[str, Any],
    destino: str | Path = "exemplos/fila_triagem.json",
) -> Path:
    """Salva a fila em JSON (a mesma estrutura de `triar_pendentes`)."""
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return caminho
