"""Testes da alocação semanal da Triagem II."""

from datetime import date

from sabor_da_terra.regras.conformidade import (
    ItemPedido,
    verificar_conformidade,
)
from sabor_da_terra.regras.fatos import Capacidade
from sabor_da_terra.triagem.alocar import AlocadorSemanal
from sabor_da_terra.triagem.schema import TipoMensagem


def test_inicio_semana():
    """A semana operacional começa na segunda-feira."""

    resultado = AlocadorSemanal.inicio_semana(
        date(2026, 11, 12)
    )

    assert resultado == date(2026, 11, 9)


def test_capacidade_compartilhada_entre_pedidos():
    """Dois pedidos não podem consumir a mesma capacidade."""

    capacidade = Capacidade(
        produtor_id="P003",
        produtos=("queijo coalho",),
        minimo=150,
        maximo=200,
        unidade="kg",
        periodo="semana",
        meses=None,
        fonte="fichas_tecnicas/queijo_coalho.txt",
    )

    class FatosTeste:
        def capacidades_de(self, produtor_id, produto, mes):
            if (
                produtor_id == "P003"
                and produto == "queijo coalho"
            ):
                return [capacidade]

            return []

    alocador = AlocadorSemanal(fatos=FatosTeste())

    elegiveis = [
        {
            "produtor_id": "P003",
            "pendencias": [],
        }
    ]

    primeiro = alocador.alocar(
        produto="queijo coalho",
        quantidade=120,
        unidade="kg",
        entrega=date(2026, 11, 12),
        elegiveis=elegiveis,
    )

    segundo = alocador.alocar(
        produto="queijo coalho",
        quantidade=100,
        unidade="kg",
        entrega=date(2026, 11, 13),
        elegiveis=elegiveis,
    )

    assert primeiro["quantidade_sugerida"] == 120
    assert primeiro["quantidade_pendente"] == 0

    assert segundo["quantidade_sugerida"] == 80
    assert segundo["quantidade_pendente"] == 20
    assert segundo["atendimento_completo"] is False


def test_nao_alocar_produtor_com_pendencia():
    """Produtores com pendências não são alocados automaticamente."""

    alocador = AlocadorSemanal()

    resultado = alocador.alocar(
        produto="frango caipira",
        quantidade=30,
        unidade="kg",
        entrega=date(2026, 11, 12),
        elegiveis=[
            {
                "produtor_id": "P017",
                "pendencias": ["REGISTRO_SANITARIO"],
            }
        ],
    )

    assert resultado["quantidade_sugerida"] == 0
    assert resultado["quantidade_pendente"] == 30
    assert resultado["alocacoes"] == []
    assert "P017" in resultado["produtores_com_pendencias"]


def test_mensagem_produtor_nao_e_compra():
    """Uma oferta de produtor não é um pedido de compra."""

    tipo = TipoMensagem.MENSAGEM_PRODUTOR

    assert tipo != TipoMensagem.COMPRA
    assert tipo != TipoMensagem.COMPRA_URGENTE


def test_alocacao_respeita_pendencia_sanitaria_real():
    """Integra o alocador às regras reais da Issue #5."""

    avaliacao = verificar_conformidade(
        item=ItemPedido(
            produto="queijo coalho",
            quantidade=200,
            unidade="kg",
            organico=False,
        ),
        data_entrega="2026-11-20",
        comprador="Restaurante Raízes",
        data_referencia="2026-11-15",
    )

    alocador = AlocadorSemanal()
    resultado = alocador.alocar_avaliacao(avaliacao)

    produtores_alocados = {
        alocacao["produtor_id"]
        for alocacao in resultado["alocacoes"]
    }

    assert resultado["atendimento_completo"] is True
    assert resultado["quantidade_sugerida"] == 200

    # P011 possui pendência sanitária.
    assert "P011" not in produtores_alocados

    # Apenas os produtores sem pendências são sugeridos.
    assert produtores_alocados <= {"P003", "P007"}

    assert resultado["status"] == "sugestao_nao_confirmada"
    assert "alertas_conformidade" in resultado


def test_capacidade_acima_do_minimo_exige_confirmacao():
    """Sugestões acima da capacidade mínima exigem confirmação."""

    alocador = AlocadorSemanal()

    resultado = alocador.alocar(
        produto="queijo coalho",
        quantidade=180,
        unidade="kg",
        entrega=date(2026, 11, 20),
        elegiveis=[
            {
                "produtor_id": "P003",
                "pendencias": [],
            }
        ],
    )

    assert resultado["quantidade_sugerida"] == 180
    assert resultado["atendimento_completo"] is True

    alocacao = resultado["alocacoes"][0]

    assert alocacao["produtor_id"] == "P003"
    assert alocacao["confirmar_producao"] is True
    assert alocacao["confirmado"] is False


def test_capacidade_abaixo_do_minimo():
    """Quantidade abaixo do mínimo não ultrapassa a faixa básica."""

    alocador = AlocadorSemanal()

    resultado = alocador.alocar(
        produto="queijo coalho",
        quantidade=100,
        unidade="kg",
        entrega=date(2026, 11, 20),
        elegiveis=[
            {
                "produtor_id": "P003",
                "pendencias": [],
            }
        ],
    )

    assert resultado["quantidade_sugerida"] == 100
    assert resultado["atendimento_completo"] is True

    alocacao = resultado["alocacoes"][0]

    assert alocacao["confirmar_producao"] is False
    assert alocacao["confirmado"] is False


def test_produto_nao_encontrado_nao_e_alocado():
    """Produtos desconhecidos não devem gerar sugestões."""

    alocador = AlocadorSemanal()

    resultado = alocador.alocar_avaliacao({
        "encontrado": False,
        "aviso": "Produto não identificado.",
    })

    assert resultado["status"] == "nao_alocavel"
    assert resultado["alocacoes"] == []
