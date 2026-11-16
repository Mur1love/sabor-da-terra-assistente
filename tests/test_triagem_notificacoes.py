"""Testes da análise documental do PED-014."""

from sabor_da_terra.triagem.fila import triar_pendentes


def obter_ped014(data_referencia="2026-10-30"):
    resultado = triar_pendentes(data_referencia)

    return next(
        pedido
        for pedido in resultado["fila"]
        if pedido["id"] == "PED-2026-014"
    )


def test_ped014_tem_analise_documental():
    pedido = obter_ped014()

    assert pedido["tipo"] == "notificacao_oficial"
    assert pedido["prioridade"] == "alta"
    assert pedido["analise_documental"] is not None


def test_ped014_possui_cinco_categorias():
    analise = obter_ped014()["analise_documental"]

    assert analise["total_documentos_exigidos"] == 5
    assert len(analise["checklist"]) == 5


def test_ped014_localiza_evidencias():
    analise = obter_ped014()["analise_documental"]

    assert analise["total_categorias_com_evidencias"] == 5

    for documento in analise["checklist"]:
        assert documento["fontes"]
        assert documento["situacao"] == "evidencia_localizada"


def test_ped014_nao_aprova_documentos():
    analise = obter_ped014()["analise_documental"]

    assert analise["documentacao_aprovada"] is False
    assert analise["resposta_oficial_enviada"] is False
    assert analise["inspecao_concluida"] is False


def test_ped014_registra_risco_sie():
    analise = obter_ped014()["analise_documental"]

    assert analise["risco_suspensao_sie_informado"] is True
    assert analise["requer_confirmacao"] is True


def test_ped014_nao_reserva_capacidade():
    pedido = obter_ped014()

    assert pedido["alocacoes"] == []
    assert pedido["orcamento"] is None
    assert pedido["status"] == "analise_sem_alocacao"


def test_ped014_prazo_nao_vencido():
    analise = obter_ped014()["analise_documental"]

    assert analise["prazo"] == "2026-11-12"
    assert analise["situacao_prazo"] == "no_prazo"


def test_ped014_pendencias_possuem_fontes():
    analise = obter_ped014()["analise_documental"]

    assert analise["pendencias"]

    for pendencia in analise["pendencias"]:
        assert pendencia["codigo"]
        assert pendencia["mensagem"]
        assert pendencia["fonte"]
