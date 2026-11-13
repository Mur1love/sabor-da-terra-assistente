"""Formato único dos alertas: código, severidade, mensagem e fonte.

Severidades: "grave" é uma não conformidade documentada (vender assim
descumpre regra, contrato ou fiscalização); "atencao" pede confirmação antes
de fechar; "info" só informa. A fonte é o arquivo de data/ que sustenta o
alerta; quando são vários, vêm separados por "; ".
"""

from __future__ import annotations

from dataclasses import dataclass

GRAVE = "grave"
ATENCAO = "atencao"
INFO = "info"
SEVERIDADES = (GRAVE, ATENCAO, INFO)

# Códigos que impedem atender o item, não só um produtor.
BLOQUEANTES = frozenset({"SEM_PRODUTOR_ELEGIVEL", "FORA_DE_SAFRA", "CAPACIDADE_EXCEDIDA"})


@dataclass(frozen=True)
class Alerta:
    codigo: str
    severidade: str
    mensagem: str
    fonte: str

    # Recusa alerta sem fonte, sem mensagem ou com severidade desconhecida.
    def __post_init__(self):
        if self.severidade not in SEVERIDADES:
            raise ValueError(f"Severidade desconhecida: {self.severidade!r}")
        if not self.codigo or not self.mensagem:
            raise ValueError("Alerta precisa de código e mensagem.")
        if not self.fonte or not self.fonte.strip():
            raise ValueError(f"Alerta {self.codigo} sem fonte.")

    # Formato que vai no JSON da ferramenta.
    def como_dict(self) -> dict[str, str]:
        return {"codigo": self.codigo, "severidade": self.severidade, "mensagem": self.mensagem, "fonte": self.fonte}

    # Lista dos arquivos citados na fonte.
    def arquivos(self) -> list[str]:
        return [parte.strip() for parte in self.fonte.split(";") if parte.strip()]


# Do mais grave para o menos grave, sem repetidos e mantendo a ordem de chegada em cada nível.
def ordenar(alertas: list[Alerta]) -> list[Alerta]:
    unicos = list(dict.fromkeys(alertas))
    return sorted(unicos, key=lambda a: SEVERIDADES.index(a.severidade))
