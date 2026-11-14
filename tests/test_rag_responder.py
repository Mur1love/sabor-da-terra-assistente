"""Testes da Etapa 8: consulta documental com citação, limiar de relevância e anti-alucinação."""

from pathlib import Path

from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.rag.responder import (
    Citacao,
    RespostaDocumental,
    TrechoRecuperado,
    _PlanoConsulta,
    _coletar_dados_e_alertas,
    _tokens_consulta,
    _validar_e_sanear_resposta,
    consultar_documentos,
    listar_arquivos_data,
    responder_consulta_documental,
)
from tests.dobles import ClienteFake, ModeloFake

RAIZ = Path(__file__).resolve().parents[1]


def _cliente_fixture_gravado(tmp_path: Path, resposta_json: str) -> LLMClient:
    """Grava uma fixture com `ModeloFake` em `tmp_path` e devolve um `LLMClient` em modo `fixture`."""
    fake = ClienteFake(ModeloFake(texto=resposta_json))
    gravador = LLMClient(modo="gravar", pasta_fixtures=tmp_path, cliente=fake, dormir=lambda _: None)
    # Pré-grava respostas para qualquer prompt que venha a ser chamado usando wrapper
    return gravador


class _LLMClientFixtureControlado(LLMClient):
    """LLMClient offline que grava sob demanda em `tmp_path` e reproduz via `modo='fixture'`."""

    def __init__(self, tmp_path: Path, respostas_por_papel: dict[str, list[str]]) -> None:
        super().__init__(modo="fixture", pasta_fixtures=tmp_path)
        self._tmp = tmp_path
        self._fila = {k: list(v) for k, v in respostas_por_papel.items()}

    def gerar(self, papel, prompt, **config_geracao):
        fila = self._fila.get(papel.value, [])
        if fila:
            texto = fila.pop(0)
            fake = ClienteFake(ModeloFake(texto=texto))
            grav = LLMClient(modo="gravar", pasta_fixtures=self._tmp, cliente=fake, dormir=lambda _: None)
            grav.gerar(papel, prompt, **config_geracao)
        return super().gerar(papel, prompt, **config_geracao)


def test_certificacao_mel_vigente_exclui_p008_e_cita_arquivos_reais(tmp_path):
    plano_json = '{"idioma":"pt","topico":"certificacao","produto":"mel","produtor":null,"lote_id":null,"mes":null,"filtro_organico":true}'
    saida = RespostaDocumental(
        resposta=(
            "Os produtores com certificação orgânica vigente para mel são P002 (José Antônio dos Santos, "
            "validade até 20/03/2027) [fonte: certificacoes/cert_organica_jose_santos_P002.txt] e "
            "P018 (Débora Melo) [fonte: certificacoes/cert_organica_debora_melo_P018.txt]. "
            "A produtora P008 (Josefa Alves de Souza) foi excluída porque sua certificação venceu em "
            "30/09/2026 e aguarda renovação [fonte: certificacoes/cert_organica_josefa_souza_P008.txt]."
        ),
        citacoes=[
            Citacao(
                arquivo="certificacoes/cert_organica_jose_santos_P002.txt",
                trecho="Certificado Nº: ORG-PE-2025-003198 | Data de Validade: 20/03/2027 | Mel silvestre",
            ),
            Citacao(
                arquivo="certificacoes/cert_organica_debora_melo_P018.txt",
                trecho="Certificado de Conformidade Orgânica - Débora Melo - Mel silvestre",
            ),
            Citacao(
                arquivo="certificacoes/cert_organica_josefa_souza_P008.txt",
                trecho="Data de Validade: 30/09/2026 *** VENCIDA ***",
            ),
        ],
        lacunas=["P008 excluída por certificação vencida em 30/09/2026."],
    )

    llm = _LLMClientFixtureControlado(
        tmp_path,
        {
            "triagem": [plano_json],
            "resposta": [saida.model_dump_json()],
        },
    )

    resp = responder_consulta_documental(
        "Quais produtores têm certificação orgânica vigente para mel?",
        data_referencia="2026-10-30",
        cliente_llm=llm,
    )

    arquivos_data = listar_arquivos_data()
    assert "P002" in resp.resposta
    assert "P018" in resp.resposta
    assert "P008" in resp.resposta
    assert "30/09/2026" in resp.resposta or "venc" in resp.resposta.lower()
    assert len(resp.citacoes) >= 1
    assert all(c.arquivo in arquivos_data for c in resp.citacoes)


def test_rastreabilidade_lote_inexistente_sugere_mais_proximo(tmp_path):
    plano_json = '{"idioma":"pt","topico":"rastreabilidade","produto":null,"produtor":null,"lote_id":"2024-089","mes":null,"filtro_organico":null}'
    saida = RespostaDocumental(
        resposta=(
            "O lote 2024-089 não existe na base de rastreabilidade da cooperativa. "
            "O lote mais próximo registrado é LOT-2026-0089 [fonte: lotes.csv]."
        ),
        citacoes=[
            Citacao(
                arquivo="lotes.csv",
                trecho="O lote '2024-089' não existe. O mais próximo é LOT-2026-0089.",
            )
        ],
        lacunas=["Lote 2024-089 inexistente em lotes.csv."],
    )

    llm = _LLMClientFixtureControlado(
        tmp_path,
        {
            "triagem": [plano_json],
            "resposta": [saida.model_dump_json()],
        },
    )

    resp = responder_consulta_documental(
        "Rastreabilidade do lote 2024-089",
        data_referencia="2026-10-30",
        cliente_llm=llm,
    )

    assert "não existe" in resp.resposta.lower()
    assert "LOT-2026-0089" in resp.resposta
    assert any(c.arquivo == "lotes.csv" for c in resp.citacoes)


def test_ped_011_ingles_sem_certificacao_internacional_nao_inventa_e_nao_chama_flash(tmp_path):
    plano_json = '{"idioma":"en","topico":"certificacao","produto":"honey","produtor":null,"lote_id":null,"mes":null,"filtro_organico":true}'
    llm = _LLMClientFixtureControlado(
        tmp_path,
        {
            "triagem": [plano_json],
            # Se o Flash fosse chamado indevidamente, estouraria FixtureAusenteError!
        },
    )

    resp = responder_consulta_documental(
        "Do you have international organic certification (USDA NOP or EU Organic) for export?",
        data_referencia="2026-10-30",
        cliente_llm=llm,
        buscador=lambda _: [],  # Nenhum documento sobre certificação internacional
    )

    assert "could not find" in resp.resposta.lower()
    assert "usda" not in resp.resposta.lower()
    assert resp.citacoes == []
    assert len(resp.lacunas) >= 1


def test_pos_validacao_remove_citacao_fora_do_contexto(tmp_path):
    plano_json = '{"idioma":"pt","topico":"contrato","produto":null,"produtor":null,"lote_id":null,"mes":null,"filtro_organico":null}'
    # Modelo tenta alucinar dois arquivos que NÃO vieram no contexto
    saida_alucinada = RespostaDocumental(
        resposta=(
            "O contrato prevê multa de 10% [fonte: contratos/contrato_pnae_garanhuns.txt] "
            "e certificação internacional [fonte: certificacoes/usda_inexistente.txt]."
        ),
        citacoes=[
            Citacao(arquivo="contratos/contrato_pnae_garanhuns.txt", trecho="Multa de 10%"),
            Citacao(arquivo="certificacoes/usda_inexistente.txt", trecho="USDA Organic"),
        ],
        lacunas=[],
    )

    llm = _LLMClientFixtureControlado(
        tmp_path,
        {
            "triagem": [plano_json],
            "resposta": [saida_alucinada.model_dump_json(), saida_alucinada.model_dump_json()],
        },
    )

    # Só recuperamos `contrato_mercado_bom_preco.txt` no contexto
    trechos_contexto = [
        TrechoRecuperado(
            arquivo="contratos/contrato_mercado_bom_preco.txt",
            conteudo="Contrato de fornecimento com Mercado Bom Preço.",
            score=0.9,
        )
    ]

    resp = responder_consulta_documental(
        "Qual a multa do contrato PNAE?",
        data_referencia="2026-10-30",
        cliente_llm=llm,
        buscador=lambda _: trechos_contexto,
    )

    assert resp.citacoes == []
    assert "usda_inexistente.txt" not in resp.resposta
    assert "contrato_pnae_garanhuns.txt" not in resp.resposta
    assert "não encontrei" in resp.resposta.lower()


def test_limiar_relevancia_bloqueia_chamada_ao_flash_quando_contexto_fraco(tmp_path):
    plano_json = '{"idioma":"pt","topico":"geral","produto":null,"produtor":null,"lote_id":null,"mes":null,"filtro_organico":null}'
    llm = _LLMClientFixtureControlado(
        tmp_path,
        {
            "triagem": [plano_json],
        },
    )

    trechos_fracos = [
        TrechoRecuperado(
            arquivo="fichas_tecnicas/mel_silvestre.txt",
            conteudo="Ficha técnica do mel silvestre.",
            score=0.05,  # Abaixo do limiar padrão (0.20)
        )
    ]

    resp = responder_consulta_documental(
        "Qual a previsão do tempo para amanhã?",
        cliente_llm=llm,
        buscador=lambda _: trechos_fracos,
        limiar_relevancia=0.20,
    )

    assert "não encontrei" in resp.resposta.lower()
    assert resp.citacoes == []


def test_funcao_consultar_documentos_pronta_para_function_calling(monkeypatch, tmp_path):
    plano_json = '{"idioma":"pt","topico":"rastreabilidade","produto":null,"produtor":null,"lote_id":"2024-089","mes":null,"filtro_organico":null}'
    saida = RespostaDocumental(
        resposta="O lote 2024-089 não existe; o mais próximo é LOT-2026-0089 [fonte: lotes.csv].",
        citacoes=[Citacao(arquivo="lotes.csv", trecho="Sugestão: LOT-2026-0089")],
        lacunas=[],
    )
    llm = _LLMClientFixtureControlado(
        tmp_path,
        {
            "triagem": [plano_json],
            "resposta": [saida.model_dump_json()],
        },
    )
    monkeypatch.setattr("sabor_da_terra.rag.responder.LLMClient", lambda: llm)

    resultado = consultar_documentos("Rastreabilidade do lote 2024-089", data_referencia="2026-10-30")
    assert resultado["encontrado"] is True
    assert "LOT-2026-0089" in resultado["resposta"]
    assert resultado["fontes"] == ["lotes.csv"]


def test_data_referencia_malformada_responde_lacuna_em_vez_de_quebrar(tmp_path):
    llm = _LLMClientFixtureControlado(tmp_path, {})
    resp = responder_consulta_documental(
        "Tem certificação para exportação?",
        data_referencia="outubro/2026",
        cliente_llm=llm,
        buscador=lambda _: [],
        usar_llm_auxiliar=False,
    )
    assert "não encontrei" in resp.resposta.lower()
    assert any("outubro/2026" in lacuna for lacuna in resp.lacunas)


def test_produto_ambiguo_propaga_o_aviso_para_o_contexto():
    plano = _PlanoConsulta(topico="certificacao", produto="mel", filtro_organico=True)
    dados, alertas, fontes = _coletar_dados_e_alertas("Tem mel orgânico?", plano, "2026-10-30")
    assert not dados  # ambiguidade não é evidência: sozinha não deve liberar o Flash
    assert any("jandaíra" in aviso for aviso in alertas)


def test_saneamento_preserva_quebras_de_paragrafo():
    saida = RespostaDocumental(
        resposta="Primeiro parágrafo.\n\nSegundo parágrafo [fonte: ficha.txt].",
        citacoes=[],
        lacunas=[],
    )
    validada, _ = _validar_e_sanear_resposta(saida, {"ficha.txt"}, {"ficha.txt": "ficha.txt"}, "pt")
    assert "\n\n" in validada.resposta
    assert "[fonte: ficha.txt]" in validada.resposta


def test_marca_inline_sem_lista_de_citacoes_e_promovida():
    saida = RespostaDocumental(
        resposta="A validade do certificado da P002 vai até 20/03/2027 [fonte: ficha.txt].",
        citacoes=[],
        lacunas=[],
    )
    validada, _ = _validar_e_sanear_resposta(saida, {"ficha.txt"}, {"ficha.txt": "ficha.txt"}, "pt")
    assert [c.arquivo for c in validada.citacoes] == ["ficha.txt"]
    assert validada.citacoes[0].trecho.strip()


def test_resposta_sem_nenhuma_citacao_valida_vira_lacuna(tmp_path):
    llm = _LLMClientFixtureControlado(
        tmp_path,
        {
            "resposta": [
                '{"resposta":"A cooperativa possui certificação USDA para exportação.","citacoes":[],"lacunas":[]}'
            ]
        },
    )
    trecho = TrechoRecuperado(
        arquivo="certificacoes/cert_organica_jose_santos_P002.txt",
        conteudo="Certificado Nº: ORG-PE-2025-003198. Data de Validade: 20/03/2027.",
        score=0.9,
    )
    resp = responder_consulta_documental(
        "A cooperativa tem certificação internacional?",
        data_referencia="2026-10-30",
        cliente_llm=llm,
        buscador=lambda _: [trecho],
        usar_llm_auxiliar=False,
    )
    assert resp.citacoes == []
    assert "não encontrei" in resp.resposta.lower()
    assert any("citação" in lacuna.lower() for lacuna in resp.lacunas)


def test_docs04_registra_vertex_ai_search_e_check_grounding():
    texto = (RAIZ / "docs" / "04-arquitetura.md").read_text(encoding="utf-8")
    assert "Vertex AI Search" in texto
    assert "Check Grounding API" in texto


def test_tokens_da_consulta_nao_guardam_pontuacao():
    tokens = _tokens_consulta("Quais produtores têm certificação orgânica vigente para mel?")
    assert "mel" in tokens
    assert "mel?" not in tokens
    # IDs com barra não podem ser partidos: os documentos usam o mesmo token.
    assert "045/2026" in _tokens_consulta("Contrato 045/2026 do PNAE")
