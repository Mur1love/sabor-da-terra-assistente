"""Testes do esboço do adaptador Vertex AI Search."""

import pytest

from sabor_da_terra.adaptadores.google.vertex_search import (
    ConfiguracaoVertexSearch,
    VertexSearchAdapter,
)


@pytest.fixture
def adaptador():
    configuracao = ConfiguracaoVertexSearch(
        projeto_id="projeto-teste",
        localizacao="global",
        data_store_id="documentos-cooperativa",
        bucket_documentos="sabor-da-terra-documentos",
    )

    return VertexSearchAdapter(configuracao)


def test_caminho_data_store(adaptador):
    assert adaptador.configuracao.caminho_data_store == (
        "projects/projeto-teste"
        "/locations/global"
        "/collections/default_collection"
        "/dataStores/documentos-cooperativa"
    )


def test_uri_cloud_storage(adaptador):
    assert adaptador.configuracao.uri_documentos == (
        "gs://sabor-da-terra-documentos"
    )


def test_pergunta_vazia(adaptador):
    with pytest.raises(ValueError):
        adaptador.buscar_documentos("")


def test_k_invalido(adaptador):
    with pytest.raises(ValueError):
        adaptador.buscar_documentos("Teste", k=0)


def test_filtros_invalidos(adaptador):
    with pytest.raises(TypeError):
        adaptador.buscar_documentos(
            "Teste",
            filtros=["P002"],
        )


def test_busca_ainda_nao_implementada(adaptador):
    with pytest.raises(NotImplementedError):
        adaptador.buscar_documentos(
            "certificação da Josefa",
            filtros={"produtor_id": "P008"},
            k=3,
        )
