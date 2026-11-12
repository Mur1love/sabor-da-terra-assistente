"""Consulta documental com citação de fonte e anti-alucinação (Etapas 7 e 8)."""

from sabor_da_terra.rag.responder import (
    Citacao,
    RespostaDocumental,
    TrechoRecuperado,
    buscar_trechos_locais,
    consultar_documentos,
    responder_consulta_documental,
)

__all__ = [
    "Citacao",
    "RespostaDocumental",
    "TrechoRecuperado",
    "buscar_trechos_locais",
    "consultar_documentos",
    "responder_consulta_documental",
]
