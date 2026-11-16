"""Motor de regras de negócio (etapa 5): conformidade, safra, capacidade e preço por contrato.

As regras são determinísticas e testáveis; os fatos tirados dos documentos
ficam em fatos.yaml, cada um com a fonte. A ferramenta para o Gemini é
verificar_conformidade.
"""

from sabor_da_terra.regras.alertas import Alerta
from sabor_da_terra.regras.conformidade import FERRAMENTAS, ItemPedido, avaliar, verificar_conformidade
from sabor_da_terra.regras.fatos import Fatos, FatosInvalidos, carregar_fatos, obter_fatos
from sabor_da_terra.regras.produtor import alertas_do_produtor

__all__ = [
    "FERRAMENTAS",
    "Alerta",
    "Fatos",
    "FatosInvalidos",
    "ItemPedido",
    "avaliar",
    "carregar_fatos",
    "obter_fatos",
    "alertas_do_produtor",
    "verificar_conformidade",
]
