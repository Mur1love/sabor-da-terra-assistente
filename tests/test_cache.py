"""Testes do cache persistente de embeddings."""

from sabor_da_terra.rag.cache import CacheEmbeddings


def test_cache_inicialmente_vazio(tmp_path):
    cache = CacheEmbeddings(tmp_path / "embeddings.json")

    assert cache.obter(
        "Certificação orgânica",
        "gemini-embedding-001",
    ) is None


def test_salvar_e_recuperar_embedding(tmp_path):
    cache = CacheEmbeddings(tmp_path / "embeddings.json")

    vetor = [0.1, 0.2, 0.3]

    cache.salvar(
        "Certificação orgânica",
        "gemini-embedding-001",
        vetor,
    )

    assert cache.obter(
        "Certificação orgânica",
        "gemini-embedding-001",
    ) == vetor


def test_cache_persistente(tmp_path):
    caminho = tmp_path / "embeddings.json"

    cache = CacheEmbeddings(caminho)

    cache.salvar(
        "Frango caipira sem SIE",
        "gemini-embedding-001",
        [0.4, 0.5, 0.6],
    )

    novo_cache = CacheEmbeddings(caminho)

    assert novo_cache.obter(
        "Frango caipira sem SIE",
        "gemini-embedding-001",
    ) == [0.4, 0.5, 0.6]


def test_texto_diferente_nao_reutiliza_embedding(tmp_path):
    cache = CacheEmbeddings(tmp_path / "embeddings.json")

    cache.salvar(
        "Certificação válida",
        "gemini-embedding-001",
        [0.1, 0.2],
    )

    assert cache.obter(
        "Certificação vencida",
        "gemini-embedding-001",
    ) is None


def test_modelo_diferente_nao_reutiliza_embedding(tmp_path):
    cache = CacheEmbeddings(tmp_path / "embeddings.json")

    cache.salvar(
        "Certificação orgânica",
        "gemini-embedding-001",
        [0.1, 0.2],
    )

    assert cache.obter(
        "Certificação orgânica",
        "outro-modelo",
    ) is None
