"""Esboço de integração com o Google Vertex AI Search.

Arquitetura prevista:
    Documentos TXT -> Cloud Storage -> Vertex AI Search.

O adaptador não realiza chamadas reais à nuvem.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracaoVertexSearch:
    """Configuração de um data store no Google Cloud."""

    projeto_id: str
    localizacao: str
    data_store_id: str
    bucket_documentos: str

    @property
    def caminho_data_store(self) -> str:
        return (
            f"projects/{self.projeto_id}"
            f"/locations/{self.localizacao}"
            "/collections/default_collection"
            f"/dataStores/{self.data_store_id}"
        )

    @property
    def uri_documentos(self) -> str:
        return f"gs://{self.bucket_documentos}"


class VertexSearchAdapter:
    """Interface futura de recuperação pelo Vertex AI Search."""

    def __init__(self, configuracao: ConfiguracaoVertexSearch):
        self.configuracao = configuracao

    def buscar_documentos(
        self,
        pergunta: str,
        filtros: dict | None = None,
        k: int = 3,
    ) -> list[dict]:
        """Busca documental ainda não implementada.

        A implementação futura deverá:
        - Consultar o data store do Vertex AI Search.
        - Aplicar filtros por metadados.
        - Recuperar os trechos dos documentos.
        - Retornar arquivo, trecho, metadados e score.
        """

        if not pergunta.strip():
            raise ValueError("A pergunta não pode estar vazia.")

        if k < 1:
            raise ValueError("O valor de k deve ser maior que zero.")

        if filtros is not None and not isinstance(filtros, dict):
            raise TypeError("Os filtros devem ser um dicionário.")

        raise NotImplementedError(
            "A integração com Vertex AI Search está "
            "documentada, mas ainda não está ativa."
        )
