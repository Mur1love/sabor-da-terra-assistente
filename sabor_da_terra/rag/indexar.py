"""Indexação documental persistente para o RAG."""

from functools import lru_cache
from pathlib import Path

from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.schema import TextNode

from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.rag.chunking import dividir_em_trechos
from sabor_da_terra.rag.embeddings import GeradorEmbeddings
from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.rag.sanitizacao import sanitizar_trechos


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
PASTA_DADOS = RAIZ_PROJETO / "data"
PASTA_INDICE = RAIZ_PROJETO / ".cache" / "rag" / "indice"
ARQUIVO_CACHE = RAIZ_PROJETO / ".cache" / "rag" / "embeddings.json"


def texto_para_embedding(texto: str, metadados: dict) -> str:
    """Põe o contexto do documento antes do trecho, só para o embedding.

    Sem isso, um trecho como "RESULTADO GERAL: APROVADO" não diz de qual
    documento ou produtor é. O texto guardado no nó continua sem o cabeçalho.
    """

    contexto = [
        metadados["tipo_documento"].replace("_", " "),
        metadados["arquivo"],
    ]

    if metadados.get("produtor_id"):
        contexto.append(f"produtor {metadados['produtor_id']}")

    if metadados.get("produto"):
        contexto.append("produtos: " + ", ".join(metadados["produto"]))

    contexto.append(f"seção {metadados['secao'].replace('_', ' ')}")

    return " | ".join(contexto) + "\n\n" + texto


def preparar_nos(
    documentos: list[dict],
    gerador: GeradorEmbeddings,
) -> list[TextNode]:
    """Converte os documentos em nós com embeddings reutilizáveis."""

    nos = []

    for documento in documentos:
        trechos = sanitizar_trechos(dividir_em_trechos(documento))

        for posicao, trecho in enumerate(trechos):
            if not trecho["texto"].strip():
                continue

            vetor = gerador.gerar(
                texto_para_embedding(trecho["texto"], trecho["metadados"])
            )

            metadados = {
                chave: valor
                for chave, valor in trecho["metadados"].items()
                if valor is not None
            }

            no = TextNode(
                # ID fixo: o mesmo trecho mantém o ID ao reindexar.
                id_=f"{documento['arquivo']}#{posicao:03d}",
                text=trecho["texto"],
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

    try:
        nos = preparar_nos(documentos, gerador)
    finally:
        # Grava o cache uma vez, mesmo se a API falhar no meio.
        gerador.cache.gravar()

    if not nos:
        raise ValueError(
            "Nenhum trecho disponível para indexação."
        )

    dimensao = len(nos[0].embedding)

    if dimensao == 0:
        raise ValueError(
            "O embedding não pode ser vazio."
        )

    if any(len(no.embedding) != dimensao for no in nos):
        raise ValueError(
            "Os embeddings possuem dimensões incompatíveis."
        )

    # Os vetores já foram gerados pelo GeradorEmbeddings.
    # O MockEmbedding evita criar outro cliente externo.
    indice = VectorStoreIndex(
        nodes=nos,
        embed_model=MockEmbedding(embed_dim=dimensao),
        show_progress=False,
    )

    pasta_indice = Path(pasta_indice)
    pasta_indice.mkdir(
        parents=True,
        exist_ok=True,
    )

    indice.storage_context.persist(
        persist_dir=str(pasta_indice),
    )

    # O índice em memória ficou velho.
    obter_indice.cache_clear()

    return indice


def carregar_indice(
    pasta_indice: Path,
) -> VectorStoreIndex:
    """Carrega um índice persistido sem gerar novos embeddings."""

    pasta_indice = Path(pasta_indice)

    if not pasta_indice.is_dir():
        raise FileNotFoundError(
            f"Diretório do índice não encontrado: {pasta_indice}"
        )

    arquivos_necessarios = (
        "docstore.json",
        "index_store.json",
        "default__vector_store.json",
    )

    for nome in arquivos_necessarios:
        caminho = pasta_indice / nome

        if not caminho.is_file():
            raise FileNotFoundError(
                f"Arquivo necessário do índice não encontrado: {caminho}"
            )

    storage_context = StorageContext.from_defaults(
        persist_dir=str(pasta_indice),
    )

    # Usado somente para carregar o índice.
    # Não deve gerar embeddings de perguntas reais.
    indice = load_index_from_storage(
        storage_context,
        embed_model=MockEmbedding(embed_dim=1),
    )

    return indice


@lru_cache(maxsize=4)
def obter_indice(pasta_indice: Path) -> VectorStoreIndex:
    """Carrega o índice uma vez e reaproveita nas perguntas seguintes."""

    return carregar_indice(pasta_indice)


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
