"""Recuperação de trechos documentais a partir do índice RAG."""

from pathlib import Path

from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    VectorStoreQuery,
)

from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.rag.embeddings import GeradorEmbeddings
from sabor_da_terra.rag.indexar import (
    ARQUIVO_CACHE,
    PASTA_INDICE,
    carregar_indice,
)


def buscar_documentos(
    pergunta: str,
    filtros: dict | None = None,
    k: int = 3,
    *,
    cliente=None,
    pasta_indice: Path = PASTA_INDICE,
    arquivo_cache: Path = ARQUIVO_CACHE,
) -> list[dict]:
    """Recupera os trechos mais relevantes do índice persistido.

    Retorna uma lista com:
    arquivo, trecho, metadados e score.
    """

    if not pergunta.strip():
        raise ValueError("A pergunta não pode estar vazia.")

    if k < 1:
        raise ValueError("O valor de k deve ser maior que zero.")

    if cliente is None:
        cliente = LLMClient()

    indice = carregar_indice(pasta_indice)

    gerador = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=arquivo_cache,
    )

    vetor_pergunta = gerador.gerar(pergunta)

    filtros = filtros or {}

    filtros_llama = MetadataFilters(
        filters=[
            MetadataFilter(key=chave, value=valor)
            for chave, valor in filtros.items()
        ]
    ) if filtros else None

    consulta = VectorStoreQuery(
        query_embedding=vetor_pergunta,
        similarity_top_k=k,
        filters=filtros_llama,
    )

    resultado = indice.vector_store.query(consulta)

    documentos = []

    for posicao, identificador in enumerate(resultado.ids or []):
        no = indice.docstore.get_node(identificador)

        score = None

        if resultado.similarities:
            score = resultado.similarities[posicao]

        documentos.append(
            {
                "arquivo": no.metadata.get("arquivo"),
                "trecho": no.text,
                "metadados": no.metadata,
                "score": score,
            }
        )

    return documentos
