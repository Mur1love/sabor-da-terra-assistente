"""Sugestão de alocação com controle de capacidade semanal."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sabor_da_terra.regras.fatos import Contrato, Fatos, obter_fatos
from sabor_da_terra.triagem.historico import normalizar_texto

_PASTA_DADOS = Path(__file__).resolve().parents[2] / "data"
_ENDERECO = re.compile(
    r"Endere[çc]o:.*,\s*([^,\n]+?)\s*-\s*[A-Z]{2}\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def preferencias_do_contrato(contrato: Contrato | None) -> dict[str, Any]:
    """Preferências de alocação declaradas nas condições do contrato.

    O acordo do Restaurante Raízes pede "prioridade para produtos orgânicos
    e de produtores locais"; local = município do endereço do comprador.
    """
    if contrato is None:
        return {"organico": False, "municipio_local": None}

    condicoes = normalizar_texto(" ".join(contrato.condicoes))
    municipio = None

    if "prioridade" in condicoes and "produtores locais" in condicoes:
        caminho = _PASTA_DADOS / contrato.fonte
        if caminho.is_file():
            achado = _ENDERECO.search(caminho.read_text(encoding="utf-8"))
            municipio = achado.group(1).strip() if achado else None

    return {
        "organico": "prioridade" in condicoes and "organic" in condicoes,
        "municipio_local": municipio,
    }


class AlocadorSemanal:
    """Controla capacidade sugerida por produtor, produto e semana."""

    def __init__(self, fatos: Fatos | None = None):
        self.fatos = fatos if fatos is not None else obter_fatos()
        self.utilizado: dict[tuple, float] = {}

    @staticmethod
    def inicio_semana(entrega: date) -> date:
        """Retorna a segunda-feira da semana da entrega."""
        return entrega - timedelta(days=entrega.weekday())

    def capacidade(
        self,
        produtor_id: str,
        produto: str,
        unidade: str,
        entrega: date,
    ) -> dict[str, Any] | None:
        """Consulta a capacidade documentada para sete dias."""

        capacidades = [
            capacidade
            for capacidade in self.fatos.capacidades_de(
                produtor_id,
                produto,
                entrega.month,
            )
            if capacidade.unidade == unidade
        ]

        if not capacidades:
            return None

        capacidade = capacidades[0]
        minimo, maximo = capacidade.na_janela(7)

        return {
            "minimo": minimo,
            "maximo": maximo,
            "fonte": capacidade.fonte,
        }

    def ordenar_por_preferencia(
        self,
        elegiveis: list[dict],
        produto: str,
        entrega: date,
        preferencias: dict[str, Any],
    ) -> list[dict]:
        """Orgânico vigente e produtor local primeiro, quando o contrato pede."""

        local = normalizar_texto(preferencias.get("municipio_local") or "")

        def chave(produtor: dict) -> tuple:
            organico = preferencias.get("organico") and any(
                certificacao.vigente_em(entrega)
                for certificacao in self.fatos.certificacoes_de(
                    produtor["produtor_id"], produto
                )
            )
            eh_local = bool(local) and normalizar_texto(
                str(produtor.get("municipio") or "")
            ) == local
            return (not organico, not eh_local, produtor["produtor_id"])

        return sorted(elegiveis, key=chave)

    def alocar(
        self,
        produto: str,
        quantidade: float,
        unidade: str,
        entrega: date,
        elegiveis: list[dict],
        condicionada: bool = False,
    ) -> dict[str, Any]:
        """Sugere distribuição sem exceder capacidade semanal.

        `condicionada=True`: o pedido ainda depende de confirmação, mas
        reserva a capacidade da semana para não ser ignorado na soma.
        """

        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero.")

        semana = self.inicio_semana(entrega)
        restante = quantidade

        sugestoes = []
        sem_capacidade_documentada = []
        produtores_com_pendencias = []

        for produtor in elegiveis:
            if restante <= 0:
                break

            produtor_id = produtor["produtor_id"]

            # Pendências exigem análise antes da alocação.
            if produtor.get("pendencias"):
                produtores_com_pendencias.append(produtor_id)
                continue

            capacidade = self.capacidade(
                produtor_id,
                produto,
                unidade,
                entrega,
            )

            if capacidade is None:
                sem_capacidade_documentada.append(produtor_id)
                continue

            chave = (
                produtor_id,
                produto,
                unidade,
                semana,
            )

            utilizado = self.utilizado.get(chave, 0.0)

            disponivel = max(
                0.0,
                capacidade["maximo"] - utilizado,
            )

            quantidade_alocada = min(restante, disponivel)

            if quantidade_alocada <= 0:
                continue

            self.utilizado[chave] = utilizado + quantidade_alocada
            restante -= quantidade_alocada

            # Quantidade acima do mínimo exige confirmação.
            excede_minimo = (
                self.utilizado[chave] > capacidade["minimo"]
            )

            sugestoes.append({
                "produtor_id": produtor_id,
                "quantidade": round(quantidade_alocada, 4),
                "unidade": unidade,
                "fonte": capacidade["fonte"],
                "confirmado": False,
                "condicionada": condicionada,
                "confirmar_producao": excede_minimo,
            })

        quantidade_sugerida = quantidade - restante

        return {
            "produto": produto,
            "quantidade_solicitada": quantidade,
            "quantidade_sugerida": round(
                quantidade_sugerida, 4
            ),
            "quantidade_pendente": round(restante, 4),
            "atendimento_completo": restante <= 1e-9,
            "sem_capacidade_documentada": sem_capacidade_documentada,
            "produtores_com_pendencias": produtores_com_pendencias,
            "alocacoes": sugestoes,
            "semana_inicio": semana.isoformat(),
            "status": (
                "aguardando_confirmacao"
                if condicionada
                else "sugestao_nao_confirmada"
            ),
        }

    def alocar_avaliacao(
        self,
        avaliacao: dict,
        condicionada: bool = False,
    ) -> dict:
        """Aloca um item avaliado pelas regras de conformidade."""

        if not avaliacao.get("encontrado"):
            return {
                "status": "nao_alocavel",
                "motivo": "Produto não identificado no catálogo.",
                "alocacoes": [],
            }

        item = avaliacao["item"]

        if not avaliacao.get("pode_atender"):
            return {
                "produto": item["produto"],
                "status": "nao_alocavel",
                "motivo": (
                    "Avaliação de conformidade não permite "
                    "atendimento integral."
                ),
                "alertas": avaliacao.get("alertas", []),
                "alocacoes": [],
            }

        if not item.get("unidade"):
            return {
                "produto": item["produto"],
                "status": "nao_alocavel",
                "motivo": "Unidade de venda não identificada.",
                "alocacoes": [],
            }

        entrega = date.fromisoformat(avaliacao["data_entrega"])
        preferencias = preferencias_do_contrato(
            self.fatos.contrato_do_comprador(avaliacao.get("comprador"))
        )

        resultado = self.alocar(
            produto=item["produto"],
            quantidade=item["quantidade"],
            unidade=item["unidade"],
            entrega=entrega,
            elegiveis=self.ordenar_por_preferencia(
                avaliacao.get("elegiveis", []),
                produto=item["produto"],
                entrega=entrega,
                preferencias=preferencias,
            ),
            condicionada=condicionada,
        )

        resultado["alertas_conformidade"] = avaliacao.get(
            "alertas", []
        )
        resultado["fontes_conformidade"] = avaliacao.get(
            "fontes", []
        )

        return resultado
