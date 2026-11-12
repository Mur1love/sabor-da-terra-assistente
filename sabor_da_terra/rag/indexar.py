"""Indexação documental persistente para o RAG."""

from pathlib import Path

from llama_index.core import VectorStoreIndex
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.schema import TextNode

from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.rag.chunking import dividir_em_trechos
from sabor_da_terra.rag.embeddings import GeradorEmbeddings
from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.rag.sanitizacao import sanitizar_texto


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
PASTA_DADOS = RAIZ_PROJETO / "data"
PASTA_INDICE = RAIZ_PROJETO / ".cache" / "rag" / "indice"
ARQUIVO_CACHE = RAIZ_PROJETO / ".cache" / "rag" / "embeddings.json"


def preparar_nos(
    documentos: list[dict],
    gerador: GeradorEmbeddings,
) -> list[TextNode]:
    """Converte os documentos em nós com embeddings reutilizáveis."""

    nos = []

    for documento in documentos:
        trechos = dividir_em_trechos(documento)

        for trecho in trechos:
            texto_seguro = sanitizar_texto(trecho["texto"])

            if not texto_seguro.strip():
                continue

            vetor = gerador.gerar(texto_seguro)

            metadados = {
                chave: valor
                for chave, valor in trecho["metadados"].items()
                if valor is not None
            }

            no = TextNode(
                text=texto_seguro,
                metadata=metadados,
                embedding=vetor,
            )

            nos.append(no)

    return nos


def construir_indice(
    documentos: list[dict],
    gerador: GeradorEmbeddings,
    pasta_indice: Path,
) -> VectorStoreIndex:
    """Constrói e persiste o índice vetorial local."""

    nos = preparar_nos(documentos, gerador)

    if not nos:
        raise ValueError("Nenhum trecho disponível para indexação.")

    dimensao = len(nos[0].embedding)

    if dimensao == 0:
        raise ValueError("O embedding não pode ser vazio.")

    if any(len(no.embedding) != dimensao for no in nos):
        raise ValueError(
            "Os embeddings possuem dimensões incompatíveis."
        )

    # Os vetores já foram calculados pelo LLMClient.
    # O MockEmbedding evita criar outro cliente externo.
    indice = VectorStoreIndex(
        nodes=nos,
        embed_model=MockEmbedding(embed_dim=dimensao),
        show_progress=False,
    )

    pasta_indice = Path(pasta_indice)
    pasta_indice.mkdir(parents=True, exist_ok=True)

    indice.storage_context.persist(
        persist_dir=str(pasta_indice),
    )

    return indice


def indexar(
    cliente=None,
    pasta_dados: Path = PASTA_DADOS,
    pasta_indice: Path = PASTA_INDICE,
    arquivo_cache: Path = ARQUIVO_CACHE,
) -> VectorStoreIndex:
    """Executa a indexação, reutilizando embeddings do cache."""

    if cliente is None:
        cliente = LLMClient()

    documentos = carregar_documentos(pasta_dados)

    gerador = GeradorEmbeddings(
        cliente=cliente,
        caminho_cache=arquivo_cache,
    )

    return construir_indice(
        documentos=documentos,
        gerador=gerador,
        pasta_indice=pasta_indice,
    )


def main():
    indice = indexar()

    quantidade = len(indice.docstore.docs)

    print("Indexação documental concluída.")
    print(f"Nós armazenados: {quantidade}")
    print(f"Índice persistido em: {PASTA_INDICE}")


if __name__ == "__main__":
    main()
