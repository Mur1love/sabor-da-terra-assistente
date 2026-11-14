"""Recuperação híbrida de trechos documentais para o RAG."""

from functools import lru_cache
from pathlib import Path

from llama_index.core.vector_stores import (
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
    VectorStoreQuery,
)

from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.rag.busca_lexical import (
    buscar_por_identificadores,
    extrair_identificadores,
)
from sabor_da_terra.rag.indexar import PASTA_INDICE, obter_indice
from sabor_da_terra.rag.sanitizacao import sanitizar_texto


# Metadados guardados como lista: o filtro é "contém", não "igual".
CAMPOS_LISTA = {"produto"}


@lru_cache(maxsize=1)
def _cliente_padrao() -> LLMClient:
    return LLMClient()


def _filtro(chave: str, valor) -> MetadataFilter:
    if chave in CAMPOS_LISTA:
        return MetadataFilter(
            key=chave,
            value=valor,
            operator=FilterOperator.CONTAINS,
        )

    return MetadataFilter(key=chave, value=valor)


def buscar_documentos(
    pergunta: str,
    filtros: dict | None = None,
    k: int = 3,
    *,
    cliente=None,
    pasta_indice: Path = PASTA_INDICE,
) -> list[dict]:
    """Busca trechos por similaridade vetorial e identificadores."""

    if not pergunta.strip():
        raise ValueError("A pergunta não pode estar vazia.")

    if k < 1:
        raise ValueError("O valor de k deve ser maior que zero.")

    if cliente is None:
        cliente = _cliente_padrao()

    indice = obter_indice(Path(pasta_indice))

    # A pergunta não vai para o cache dos documentos: cada pergunta nova
    # faria o arquivo crescer para sempre.
    vetor_pergunta = cliente.embedar(sanitizar_texto(pergunta))

    filtros = filtros or {}

    filtros_llama = (
        MetadataFilters(
            filters=[
                _filtro(chave, valor)
                for chave, valor in filtros.items()
            ]
        )
        if filtros
        else None
    )

    # Recupera candidatos vetoriais.
    # Buscamos mais do que k para permitir a reordenação.
    consulta = VectorStoreQuery(
        query_embedding=vetor_pergunta,
        similarity_top_k=max(k * 3, 10),
        filters=filtros_llama,
    )

    resultado_vetorial = indice.vector_store.query(consulta)

    candidatos = {}

    for posicao, identificador in enumerate(
        resultado_vetorial.ids or []
    ):
        no = indice.docstore.get_node(identificador)

        score_vetorial = 0.0

        if resultado_vetorial.similarities:
            score_vetorial = (
                resultado_vetorial.similarities[posicao]
            )

        candidatos[identificador] = {
            "arquivo": no.metadata.get("arquivo"),
            "trecho": no.text,
            "metadados": no.metadata,
            "score_vetorial": score_vetorial,
            "score_lexical": 0.0,
        }

    # Busca lexical em todos os nós, para não depender
    # somente dos candidatos recuperados por similaridade.
    identificadores = extrair_identificadores(pergunta)

    if identificadores:
        nos = list(indice.docstore.docs.values())

        resultados_lexicais = buscar_por_identificadores(
            pergunta,
            nos,
            filtros,
        )

        for item in resultados_lexicais:
            identificador = item["id"]

            if identificador in candidatos:
                candidatos[identificador]["score_lexical"] = (
                    item["score_lexical"]
                )
            else:
                candidatos[identificador] = {
                    "arquivo": item["arquivo"],
                    "trecho": item["trecho"],
                    "metadados": item["metadados"],
                    "score_vetorial": 0.0,
                    "score_lexical": item["score_lexical"],
                }

    # Score combinado.
    # O peso lexical é maior quando existe código exato.
    for item in candidatos.values():
        if identificadores:
            score = (
                0.3 * item["score_vetorial"]
                + 0.7 * item["score_lexical"]
            )
        else:
            score = item["score_vetorial"]

        item["score"] = score

    ordenados = sorted(
        candidatos.values(),
        key=lambda item: item["score"],
        reverse=True,
    )

    return [
        {
            "arquivo": item["arquivo"],
            "trecho": item["trecho"],
            "metadados": item["metadados"],
            "score": item["score"],
        }
        for item in ordenados[:k]
    ]
