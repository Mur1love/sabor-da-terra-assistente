"""Gera os exemplos da etapa 11 em exemplos/produtores/.

Uso:
    python -m scripts.exemplos_produtores            # textos do modelo fixo (sem API)
    python -m scripts.exemplos_produtores --gemini   # passa cada texto pelo Gemini Flash (requer .env)

A data de referência é 30/10/2026, o dia das últimas mensagens do dataset.
Com --gemini, o texto do Gemini só entra se passar na conferência de números
(redacao.py); senão fica o modelo fixo, e o cabeçalho do arquivo diz qual saiu.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

from sabor_da_terra.produtores import (
    notificar_produtores,
    redigir,
    relatorio_pendencias_vencidas,
    responder_mensagem_produtor,
    resumo_produtor,
)

REFERENCIA = "2026-10-30"
PASTA = Path(__file__).resolve().parents[1] / "exemplos" / "produtores"


def _salvar(nome: str, titulo: str, texto: str, usar_gemini: bool) -> None:
    origem, problemas = "modelo fixo", []
    if usar_gemini:
        redacao = redigir(texto)
        texto, origem = redacao["texto"], redacao["origem"].replace("_", " ")
        problemas = redacao["problemas"]
    conteudo = (
        f"# {titulo}\n\n"
        f"Data de referência: {REFERENCIA}. Texto gerado por: {origem}. Nada foi enviado ao produtor.\n\n"
        f"```text\n{texto}\n```\n"
    )
    (PASTA / nome).write_text(conteudo, encoding="utf-8")
    print(f"  {nome} ({origem})")
    for problema in problemas:  # por que o texto do Gemini foi recusado
        print(f"      - {problema}")


def main(argv: list[str]) -> int:
    usar_gemini = "--gemini" in argv
    if usar_gemini:
        load_dotenv()
    PASTA.mkdir(parents=True, exist_ok=True)

    for pid in ("P001", "P003", "P008", "P017"):
        resumo = resumo_produtor(pid, "2026-10", REFERENCIA)
        _salvar(f"resumo_{pid}_2026-10.md", f"Resumo de outubro/2026 — {pid}", resumo["texto"], usar_gemini)

    lote = notificar_produtores(REFERENCIA)
    for notificacao in lote["notificacoes"]:
        pid = notificacao["produtor"]["produtor_id"]
        _salvar(f"notificacao_{pid}.md", f"Notificação de novos pedidos — {pid}", notificacao["texto"], usar_gemini)

    for pedido in ("PED-2026-012", "PED-2026-015"):
        resposta = responder_mensagem_produtor(pedido)
        _salvar(f"resposta_{pedido}.md", f"Resposta à mensagem {pedido}", resposta["texto"], usar_gemini)

    relatorio = relatorio_pendencias_vencidas(REFERENCIA)
    _salvar("pendencias_vencidas.md", "Relatório de pagamentos vencidos", relatorio["texto"], usar_gemini=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
