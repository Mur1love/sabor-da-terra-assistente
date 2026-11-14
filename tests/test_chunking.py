"""Testes de segmentação documental e metadados por trecho."""

from pathlib import Path

from sabor_da_terra.rag.leitor import carregar_documentos
from sabor_da_terra.rag.chunking import (
    dividir_em_trechos,
    identificar_secao,
    juntar_trechos_curtos,
)


BASE_DADOS = Path(__file__).resolve().parents[1] / "data"


def obter_documento(nome: str) -> dict:
    documentos = carregar_documentos(BASE_DADOS)

    return next(
        documento
        for documento in documentos
        if documento["arquivo"] == nome
    )


def test_divisao_certificacao():
    documento = obter_documento(
        "cert_organica_josefa_souza_P008.txt"
    )

    trechos = dividir_em_trechos(documento)

    assert len(trechos) > 1
    assert all(trecho["texto"].strip() for trecho in trechos)


def test_preservar_origem():
    documento = obter_documento(
        "cert_organica_josefa_souza_P008.txt"
    )

    trechos = dividir_em_trechos(documento)

    for trecho in trechos:
        assert trecho["metadados"]["arquivo"] == documento["arquivo"]
        assert trecho["metadados"]["produtor_id"] == "P008"
        assert trecho["metadados"]["tipo_documento"] == "certificacao"


def test_preservar_nao_conformidade():
    documento = obter_documento(
        "inspecao_adagro_2026.txt"
    )

    trechos = dividir_em_trechos(documento)

    assert any(
        "NC-001" in trecho["texto"]
        and "P017" in trecho["texto"]
        for trecho in trechos
    )


def test_preservar_condicoes_contrato():
    documento = obter_documento(
        "contrato_pnae_garanhuns.txt"
    )

    trechos = dividir_em_trechos(documento)

    assert any(
        "CONDIÇÕES OBRIGATÓRIAS" in trecho["texto"]
        and "certificação válida" in trecho["texto"]
        for trecho in trechos
    )


def test_identificar_secao_nao_conformidades():
    documento = obter_documento(
        "inspecao_adagro_2026.txt"
    )

    trechos = dividir_em_trechos(documento)

    nc001 = next(
        trecho for trecho in trechos
        if "NC-001" in trecho["texto"]
    )

    nc002 = next(
        trecho for trecho in trechos
        if "NC-002" in trecho["texto"]
    )

    assert nc001["metadados"]["secao"] == "nao_conformidades"
    assert nc002["metadados"]["secao"] == "nao_conformidades"


def test_identificar_secao_produtores():
    documento = obter_documento(
        "inspecao_adagro_2026.txt"
    )

    trechos = dividir_em_trechos(documento)

    produtor = next(
        trecho for trecho in trechos
        if "P017" in trecho["texto"]
        and "Wellington" in trecho["texto"]
    )

    assert produtor["metadados"]["secao"] == "produtores_vistoriados"


def test_metadados_produtor_p017():
    documento = obter_documento(
        "inspecao_adagro_2026.txt"
    )

    trechos = dividir_em_trechos(documento)

    trecho_p017 = next(
        trecho for trecho in trechos
        if "Wellington" in trecho["texto"]
    )

    assert trecho_p017["metadados"]["produtor_id"] == "P017"
    assert "frango caipira" in trecho_p017["metadados"]["produto"]
    assert "ovos caipira" in trecho_p017["metadados"]["produto"]


def test_identificar_secao_conhecida():
    bloco = """
    NÃO CONFORMIDADES:
    NC-001 (GRAVE): Produtor P017 sem registro SIE.
    """

    assert identificar_secao(bloco.strip()) == "nao_conformidades"


def test_juncao_de_trechos_curtos():
    partes = [
        ("Curto demais.", "introducao"),
        ("Texto corrido " + "y" * 130, "dados_do_produtor"),
    ]

    resultado = juntar_trechos_curtos(partes)

    assert len(resultado) == 1
    assert resultado[0][0].startswith("Curto demais.")
    # Sem título no pedaço seguinte: mantém a seção do primeiro pedaço.
    assert resultado[0][1] == "introducao"


def test_juncao_mantem_secao_do_primeiro_pedaco():
    # Regra intencional (ver comentário em juntar_trechos_curtos): o
    # trecho juntado fica com a seção do primeiro pedaço, mesmo quando o
    # seguinte começa com título. Assim o conteúdo de conformidade (ex.:
    # NC-002) não recebe o rótulo do resultado que vem depois dele.
    partes = [
        ("Curto demais.", "introducao"),
        ("PRODUTOS CERTIFICADOS:\n" + "x" * 130, "produtos_certificados"),
    ]

    resultado = juntar_trechos_curtos(partes)

    assert len(resultado) == 1
    assert resultado[0][1] == "introducao"
    # O texto do título continua presente no trecho.
    assert "PRODUTOS CERTIFICADOS:" in resultado[0][0]


def test_trechos_curtos_consecutivos_se_juntam():
    partes = [
        ("Primeiro curto.", "introducao"),
        ("Segundo curto.", "dados_do_produtor"),
        ("t" * 200, "objeto"),
    ]

    resultado = juntar_trechos_curtos(partes)

    assert len(resultado) == 1
    assert "Primeiro curto." in resultado[0][0]
    assert "Segundo curto." in resultado[0][0]
    assert resultado[0][1] == "introducao"


def test_ultimo_trecho_curto_junta_o_anterior():
    partes = [
        ("A" * 200, "dados_do_produtor"),
        ("Fim curto.", "observacoes"),
    ]

    resultado = juntar_trechos_curtos(partes)

    assert len(resultado) == 1
    assert resultado[0][0].startswith("A" * 200)
    assert resultado[0][0].endswith("Fim curto.")
    assert resultado[0][1] == "dados_do_produtor"


def test_ultimo_trecho_curto_com_titulo_mantem_secao_do_anterior():
    partes = [
        ("A" * 200, "dados_do_produtor"),
        ("VIGÊNCIA: 01/03/2026 a 28/02/2027", "vigencia"),
    ]

    resultado = juntar_trechos_curtos(partes)

    assert len(resultado) == 1
    # Mesma regra da junção para frente: vale a seção do trecho anterior.
    assert resultado[0][1] == "dados_do_produtor"


def test_juncao_de_lista_vazia():
    assert juntar_trechos_curtos([]) == []


def test_bloco_sem_secao_conhecida():
    bloco = "Informações complementares do documento."

    assert identificar_secao(bloco) is None


def test_campos_obrigatorios_em_todos_trechos():
    documentos = carregar_documentos(BASE_DADOS)

    campos_obrigatorios = {
        "arquivo",
        "tipo_documento",
        "produtor_id",
        "produto",
        "data_validade",
        "secao",
    }

    for documento in documentos:
        trechos = dividir_em_trechos(documento)

        for trecho in trechos:
            metadados = trecho["metadados"]

            assert campos_obrigatorios.issubset(
                metadados.keys()
            ), (
                f"Campos ausentes no documento "
                f"{documento['arquivo']}: "
                f"{campos_obrigatorios - metadados.keys()}"
            )


def test_preservar_certificado_e_validade():
    documento = obter_documento(
        "cert_organica_josefa_souza_P008.txt"
    )

    trechos = dividir_em_trechos(documento)

    texto_completo = "\n".join(
        trecho["texto"] for trecho in trechos
    )

    assert "ORG-PE-2024-003876" in texto_completo
    assert "30/09/2026" in texto_completo
    assert "VENCIDA" in texto_completo
