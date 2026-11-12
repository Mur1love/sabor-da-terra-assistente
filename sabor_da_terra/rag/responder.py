"""Consulta documental com citação obrigatória de fonte e anti-alucinação (Etapa 8)."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from sabor_da_terra.dados import consultas
from sabor_da_terra.dados import normalizacao as n
from sabor_da_terra.llm.cliente import LLMClient, Papel
from sabor_da_terra.prompts.consulta_documental import (
    PROMPT_PLANEJAMENTO_CONSULTA,
    PROMPT_RESPOSTA_DOCUMENTAL,
    VERSAO_PROMPT_DOCUMENTAL,
)

LIMIAR_RELEVANCIA_PADRAO = 0.20

_SUBPASTAS_DOCUMENTAIS = ("certificacoes", "contratos", "fichas_tecnicas")

_SINONIMOS_BUSCA: dict[str, set[str]] = {
    "mel": {"mel", "apiario", "apicultura", "silvestre", "jandaira", "propolis", "colmeia"},
    "organico": {"organico", "organica", "certificacao", "certificado", "ibd", "sisorg", "mapa"},
    "certificacao": {"certificacao", "certificado", "organica", "organico", "validade", "vencida", "auditoria", "ibd"},
    "sanitario": {"sanitario", "sanitaria", "adagro", "sie", "inspecao", "laudo", "alvara", "queijaria", "apiario"},
    "queijo": {"queijo", "coalho", "queijaria", "sie", "adagro", "laticinio"},
    "goiaba": {"goiaba", "paluma", "polpa", "fruta"},
    "hortalicas": {"hortalica", "hortalicas", "alface", "tomate", "coentro", "folhosas"},
    "tuberculos": {"tuberculo", "tuberculos", "macaxeira", "inhame", "batata", "feijao", "graos"},
    "contrato": {"contrato", "clausula", "fornecimento", "multa", "prazo", "pnae", "bom", "preco", "raizes"},
    "pnae": {"pnae", "merenda", "escolar", "garanhuns", "chamada", "publica"},
    "dap": {"dap", "caf", "declaracao", "aptidao", "pronaf"},
    "lote": {"lote", "rastreabilidade", "colheita", "transporte", "temperatura"},
    "sazonalidade": {"sazonalidade", "safra", "disponibilidade", "calendario", "mes"},
}

_STOPWORDS = {
    "a", "as", "o", "os", "de", "da", "das", "do", "dos", "em", "no", "na", "nos", "nas",
    "para", "por", "com", "sem", "que", "qual", "quais", "quem", "como", "onde", "quando",
    "um", "uma", "uns", "umas", "e", "ou", "se", "ao", "aos", "the", "of", "for", "and",
    "in", "to", "is", "are", "do", "does", "have", "has", "any", "with", "on", "at",
}

_PALAVRAS_INGLES = {
    "what", "which", "who", "where", "when", "how", "does", "have", "has", "any",
    "organic", "certification", "international", "export", "honey", "cheese", "batch",
    "lot", "contract", "traceability", "available", "season", "producer", "producers",
    "certificate", "documents", "please", "need", "required", "requirements",
}


# ---------------------------------------------------------------------------
# Modelos Pydantic (saída estruturada e contexto recuperado)
# ---------------------------------------------------------------------------


class Citacao(BaseModel):
    """Citação vinculando uma afirmação a um documento recuperado."""

    arquivo: str = Field(..., description="Nome do arquivo existente em data/ presente no contexto.")
    trecho: str = Field(..., description="Trecho literal ou fiel extraído do arquivo citado.")


class RespostaDocumental(BaseModel):
    """Saída estruturada da consulta documental (Etapa 8)."""

    resposta: str = Field(..., description="Resposta final em linguagem natural com marcas [fonte: arquivo].")
    citacoes: list[Citacao] = Field(default_factory=list, description="Lista de citações validadas.")
    lacunas: list[str] = Field(
        default_factory=list,
        description="Informações ausentes na base documental ou motivos de exclusão.",
    )


class TrechoRecuperado(BaseModel):
    """Trecho recuperado da base documental pelo retriever (Etapa 7 ou fixture)."""

    arquivo: str
    conteudo: str
    score: float = 1.0


class _PlanoConsulta(BaseModel):
    """Resultado do passo auxiliar no Flash-Lite para estruturar a busca."""

    idioma: str = "pt"
    topico: str = "geral"
    produto: Optional[str] = None
    produtor: Optional[str] = None
    lote_id: Optional[str] = None
    mes: Optional[str] = None
    filtro_organico: Optional[bool] = None


# ---------------------------------------------------------------------------
# Catálogo de arquivos válidos em data/ e retriever local
# ---------------------------------------------------------------------------


def _pasta_data_padrao() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def listar_arquivos_data(pasta_data: Path | None = None) -> dict[str, str]:
    """Mapeia nomes base e caminhos relativos de `data/` para seu identificador canônico."""
    raiz = pasta_data or _pasta_data_padrao()
    mapa: dict[str, str] = {}
    if not raiz.exists():
        return mapa

    for caminho in sorted(raiz.rglob("*")):
        if not caminho.is_file():
            continue
        rel = caminho.relative_to(raiz).as_posix()
        nome = caminho.name
        mapa[rel] = rel
        mapa[rel.lower()] = rel
        if nome not in mapa:
            mapa[nome] = rel
            mapa[nome.lower()] = rel
    return mapa


def _detectar_idioma_heuristico(pergunta: str) -> str:
    tokens = re.findall(r"[a-zA-Z]+", pergunta.lower())
    if not tokens:
        return "pt"
    hits_en = sum(1 for t in tokens if t in _PALAVRAS_INGLES)
    return "en" if hits_en >= 2 or (len(tokens) <= 4 and hits_en >= 1) else "pt"


def _tokens_consulta(texto: str) -> set[str]:
    chave = n.chave(texto)
    base = {tok for tok in chave.split() if len(tok) > 1 and tok not in _STOPWORDS}
    expandidos = set(base)
    for tok in base:
        if tok in _SINONIMOS_BUSCA:
            expandidos.update(_SINONIMOS_BUSCA[tok])
    return expandidos


def buscar_trechos_locais(
    pergunta: str,
    pasta_data: Path | None = None,
    top_k: int = 5,
) -> list[TrechoRecuperado]:
    """Busca lexical local sobre `data/certificacoes`, `contratos` e `fichas_tecnicas`.

    Atua como implementação local padrão enquanto o índice vetorial da Etapa 7
    não está acoplado, mantendo a mesma assinatura esperada pelo pipeline.
    """
    raiz = pasta_data or _pasta_data_padrao()
    tokens_q = _tokens_consulta(pergunta)
    if not tokens_q:
        return []

    ids_produtores = {m.upper() for m in re.findall(r"\bP\d{3}\b", pergunta, flags=re.IGNORECASE)}
    resultados: list[TrechoRecuperado] = []

    for subpasta in _SUBPASTAS_DOCUMENTAIS:
        diretorio = raiz / subpasta
        if not diretorio.exists():
            continue
        for arquivo in sorted(diretorio.glob("*.txt")):
            texto_bruto = arquivo.read_text(encoding="utf-8")
            texto_seguro = n.mascarar_cpf_em_texto(texto_bruto)
            rel = arquivo.relative_to(raiz).as_posix()

            tokens_doc = _tokens_consulta(f"{arquivo.stem.replace('_', ' ')} {texto_seguro}")
            intersecao = tokens_q & tokens_doc
            if not intersecao and not ids_produtores:
                continue

            cobertura = len(intersecao) / max(1, min(len(tokens_q), 8))
            bonus_id = 0.35 if any(pid in arquivo.name.upper() for pid in ids_produtores) else 0.0
            score = round(min(1.0, cobertura + bonus_id), 4)

            if score > 0:
                resultados.append(
                    TrechoRecuperado(
                        arquivo=rel,
                        conteudo=texto_seguro.strip(),
                        score=score,
                    )
                )

    resultados.sort(key=lambda item: (-item.score, item.arquivo))
    return resultados[:top_k]


# ---------------------------------------------------------------------------
# Passo auxiliar (Flash-Lite) e coleta de dados/regras (#4 e #5)
# ---------------------------------------------------------------------------


def _planejar_consulta(
    pergunta: str,
    cliente_llm: LLMClient,
    usar_llm_auxiliar: bool = True,
) -> _PlanoConsulta:
    """Usa o Flash-Lite (`Papel.TRIAGEM`) para classificar a consulta documental."""
    idioma_heur = _detectar_idioma_heuristico(pergunta)

    if usar_llm_auxiliar:
        try:
            prompt_aux = f"{PROMPT_PLANEJAMENTO_CONSULTA}\n\nPergunta: {pergunta}"
            resp = cliente_llm.gerar(
                Papel.TRIAGEM,
                prompt_aux,
                response_mime_type="application/json",
                response_schema=_PlanoConsulta.model_json_schema(),
                temperature=0.0,
            )
            if resp.text:
                plano = _PlanoConsulta.model_validate_json(resp.text)
                if plano.idioma not in ("pt", "en"):
                    plano.idioma = idioma_heur
                return plano
        except Exception:
            pass

    # Fallback determinístico caso a fixture auxiliar não exista ou não seja usada
    texto_norm = n.chave(pergunta)
    topico = "geral"
    if any(k in texto_norm for k in ("certificac", "organico", "organica", "adagro", "sie", "laudo")):
        topico = "certificacao"
    elif any(k in texto_norm for k in ("lote", "rastreab", "2024-", "2026-", "lot-")):
        topico = "rastreabilidade"
    elif any(k in texto_norm for k in ("safra", "sazonal", "disponib")):
        topico = "sazonalidade"
    elif any(k in texto_norm for k in ("contrato", "pnae", "bom preco", "raizes")):
        topico = "contrato"

    produto = None
    for cand in ("mel", "queijo coalho", "goiaba", "hortalicas", "tuberculos", "banana", "cafe"):
        if cand in texto_norm:
            produto = cand
            break

    m_lote = re.search(r"\b(?:LOT[-_]?)?\d{4}[-_]\d{1,4}\b", pergunta, flags=re.IGNORECASE)
    m_prod = re.search(r"\bP\d{3}\b", pergunta, flags=re.IGNORECASE)
    filtro_org = True if ("organico" in texto_norm or "organica" in texto_norm or "organic" in texto_norm) else None

    return _PlanoConsulta(
        idioma=idioma_heur,
        topico=topico,
        produto=produto,
        produtor=m_prod.group(0).upper() if m_prod else None,
        lote_id=m_lote.group(0) if m_lote else None,
        filtro_organico=filtro_org,
    )


def _coletar_dados_e_alertas(
    pergunta: str,
    plano: _PlanoConsulta,
    data_referencia: str,
) -> tuple[list[dict[str, Any]], list[str], set[str]]:
    """Consulta funções estruturadas (#4) e alertas de regras (#5) pertinentes."""
    dados: list[dict[str, Any]] = []
    alertas: list[str] = []
    fontes: set[str] = set()

    # 1. Rastreabilidade de lote (ex.: LOT-2026-0089 ou 2024-089)
    lote_termo = plano.lote_id
    if not lote_termo:
        m = re.search(r"\b(?:LOT[-_]?)?\d{4}[-_]\d{1,4}\b", pergunta, flags=re.IGNORECASE)
        if m:
            lote_termo = m.group(0)

    if lote_termo:
        res_lote = consultas.rastrear_lote(lote_termo)
        dados.append({"ferramenta": "rastrear_lote", "resultado": res_lote})
        fontes.add("lotes.csv")
        if res_lote.get("aviso"):
            alertas.append(str(res_lote["aviso"]))

    # 2. Certificações / produtores por produto
    if plano.produto and (plano.topico in ("certificacao", "geral") or plano.filtro_organico is not None):
        res_prod = consultas.buscar_produtores(
            plano.produto,
            organico=plano.filtro_organico,
            data_referencia=data_referencia,
        )
        if res_prod.get("encontrado"):
            dados.append({"ferramenta": "buscar_produtores", "resultado": res_prod})
            fontes.add("produtores.csv")
            if res_prod.get("aviso"):
                alertas.append(str(res_prod["aviso"]))

    # 3. Produtor específico mencionado
    if plano.produtor:
        res_id = consultas.identificar_produtor(plano.produtor, data_referencia=data_referencia)
        if res_id.get("encontrado"):
            dados.append({"ferramenta": "identificar_produtor", "resultado": res_id})
            fontes.add("produtores.csv")
            if res_id.get("aviso"):
                alertas.append(str(res_id["aviso"]))

    # 4. Sazonalidade quando produto e mês forem mencionados
    if plano.produto and plano.mes:
        res_saz = consultas.disponibilidade(plano.produto, plano.mes)
        if res_saz.get("encontrado"):
            dados.append({"ferramenta": "disponibilidade", "resultado": res_saz})
            fontes.add("sazonalidade.csv")

    # 5. Gancho opcional com motor de regras da Etapa #5 quando disponível
    try:
        import sabor_da_terra.regras as mod_regras

        verificar = getattr(mod_regras, "alertas_documentais", None)
        if callable(verificar):
            extras = verificar(pergunta=pergunta, data_referencia=data_referencia)
            if extras:
                alertas.extend(str(a) for a in extras)
    except Exception:
        pass

    return dados, alertas, fontes


# ---------------------------------------------------------------------------
# Pós-validação das citações e resposta de lacuna
# ---------------------------------------------------------------------------


def _resposta_lacuna(idioma: str, motivo: str) -> RespostaDocumental:
    if idioma == "en":
        texto = (
            "I could not find this information in the cooperative's documents. "
            "No supporting record was found in the available files."
        )
    else:
        texto = (
            "Não encontrei essa informação nos documentos da cooperativa. "
            "Não há registro na base documental que comprove esse dado."
        )
    return RespostaDocumental(resposta=texto, citacoes=[], lacunas=[motivo])


def _resolver_arquivo_permitido(
    arquivo_citado: str,
    fontes_permitidas: set[str],
    mapa_data: dict[str, str],
) -> str | None:
    """Verifica se `arquivo_citado` existe em `data/` e pertence ao contexto recuperado."""
    bruto = arquivo_citado.strip().strip("`\"'[]")
    if bruto.startswith("data/"):
        bruto = bruto[5:]

    canonico = mapa_data.get(bruto) or mapa_data.get(bruto.lower()) or mapa_data.get(Path(bruto).name)
    if not canonico:
        return None

    nome_base = Path(canonico).name
    if canonico in fontes_permitidas or nome_base in fontes_permitidas:
        return canonico if canonico in fontes_permitidas else nome_base
    return None


def _validar_e_sanear_resposta(
    saida: RespostaDocumental,
    fontes_permitidas: set[str],
    mapa_data: dict[str, str],
    idioma: str,
) -> tuple[RespostaDocumental, list[str]]:
    """Garante que 100% das citações apontem para arquivos reais do contexto recuperado."""
    citacoes_validas: list[Citacao] = []
    arquivos_invalidos: list[str] = []

    for cit in saida.citacoes:
        resolvido = _resolver_arquivo_permitido(cit.arquivo, fontes_permitidas, mapa_data)
        if resolvido is None:
            arquivos_invalidos.append(cit.arquivo)
            continue
        trecho_limpo = n.mascarar_cpf_em_texto(cit.trecho).strip()
        citacoes_validas.append(Citacao(arquivo=resolvido, trecho=trecho_limpo))

    texto_limpo = n.mascarar_cpf_em_texto(saida.resposta).strip()

    # Verifica marcas inline [fonte: X] no texto
    def _substituir_marca(match: re.Match[str]) -> str:
        alvo = match.group(1).strip()
        resolvido = _resolver_arquivo_permitido(alvo, fontes_permitidas, mapa_data)
        if resolvido is None:
            arquivos_invalidos.append(alvo)
            return ""
        return f"[fonte: {resolvido}]"

    texto_limpo = re.sub(r"\[fonte:\s*([^\]]+)\]", _substituir_marca, texto_limpo, flags=re.IGNORECASE)
    texto_limpo = re.sub(r"\s{2,}", " ", texto_limpo).strip()

    # Se todas as citações eram inválidas (alucinação de fonte), devolve lacuna segura
    if arquivos_invalidos and not citacoes_validas:
        return (
            _resposta_lacuna(
                idioma,
                f"Citações inválidas removidas (fora do contexto): {', '.join(sorted(set(arquivos_invalidos)))}",
            ),
            arquivos_invalidos,
        )

    # Garante que toda resposta com evidência tenha ao menos uma marca [fonte: arquivo]
    if citacoes_validas and "[fonte:" not in texto_limpo.lower():
        marcas = " ".join(f"[fonte: {c.arquivo}]" for c in citacoes_validas)
        texto_limpo = f"{texto_limpo} {marcas}".strip()

    lacunas = list(saida.lacunas)
    if arquivos_invalidos:
        lacunas.append(
            f"Fontes não presentes no contexto foram descartadas: {', '.join(sorted(set(arquivos_invalidos)))}"
        )

    return (
        RespostaDocumental(
            resposta=texto_limpo,
            citacoes=citacoes_validas,
            lacunas=lacunas,
        ),
        arquivos_invalidos,
    )


# ---------------------------------------------------------------------------
# Pipeline principal (Etapa 8)
# ---------------------------------------------------------------------------


def responder_consulta_documental(
    pergunta: str,
    *,
    data_referencia: Optional[str] = None,
    cliente_llm: LLMClient | None = None,
    buscador: Callable[[str], list[TrechoRecuperado]] | None = None,
    limiar_relevancia: float = LIMIAR_RELEVANCIA_PADRAO,
    pasta_data: Path | None = None,
    usar_llm_auxiliar: bool = True,
) -> RespostaDocumental:
    """Executa o pipeline completo de consulta documental com citação e anti-alucinação."""
    ref_data = n.data(data_referencia) if data_referencia else date.today()
    if ref_data is None:
        return _resposta_lacuna("pt", f"Data de referência inválida: {data_referencia}")
    ref_iso = ref_data.isoformat()

    cliente = cliente_llm or LLMClient()
    raiz_data = pasta_data or _pasta_data_padrao()
    mapa_data = listar_arquivos_data(raiz_data)

    # 1. Passo auxiliar no Flash-Lite (Papel.TRIAGEM)
    plano = _planejar_consulta(pergunta, cliente, usar_llm_auxiliar=usar_llm_auxiliar)

    # 2. Recuperação documental (Etapa 7 / buscador injetado / fallback local)
    recuperados = buscador(pergunta) if buscador is not None else buscar_trechos_locais(pergunta, pasta_data=raiz_data)
    trechos_relevantes = [t for t in recuperados if t.score >= limiar_relevancia]

    # 3. Dados estruturados (#4) e alertas de regras (#5)
    dados_estruturados, alertas, fontes_dados = _coletar_dados_e_alertas(pergunta, plano, ref_iso)

    # 4. Limiar de relevância: sem contexto relevante, retorna lacuna sem chamar o Flash
    if not trechos_relevantes and not dados_estruturados:
        return _resposta_lacuna(
            plano.idioma,
            "Nenhum trecho acima do limiar de relevância nem registro estruturado encontrado.",
        )

    # Normaliza nomes de arquivos permitidos no contexto (apenas arquivos que existem em data/)
    fontes_permitidas: set[str] = set()
    trechos_contexto: list[dict[str, Any]] = []
    for t in trechos_relevantes:
        bruto = t.arquivo[5:] if t.arquivo.startswith("data/") else t.arquivo
        canonico = mapa_data.get(bruto) or mapa_data.get(bruto.lower()) or mapa_data.get(Path(bruto).name)
        if canonico:
            fontes_permitidas.add(canonico)
            fontes_permitidas.add(Path(canonico).name)
            trechos_contexto.append(
                {
                    "arquivo": canonico,
                    "score": t.score,
                    "conteudo": n.mascarar_cpf_em_texto(t.conteudo),
                }
            )

    for f in fontes_dados:
        canonico = mapa_data.get(f) or mapa_data.get(Path(f).name)
        if canonico:
            fontes_permitidas.add(canonico)
            fontes_permitidas.add(Path(canonico).name)

    if not fontes_permitidas:
        return _resposta_lacuna(plano.idioma, "Nenhum arquivo válido de data/ disponível no contexto.")

    # 5. Redação da resposta final no Gemini Flash (`Papel.RESPOSTA`)
    payload_contexto = {
        "versao_prompt": VERSAO_PROMPT_DOCUMENTAL,
        "data_referencia": ref_iso,
        "idioma_resposta": plano.idioma,
        "pergunta": pergunta,
        "arquivos_permitidos": sorted({t["arquivo"] for t in trechos_contexto} | set(fontes_dados)),
        "trechos_documentais": trechos_contexto,
        "dados_estruturados": dados_estruturados,
        "alertas_regras": alertas,
    }

    prompt_final = (
        f"{PROMPT_RESPOSTA_DOCUMENTAL}\n\n"
        f"CONTEXTO RECUPERADO (JSON):\n{json.dumps(payload_contexto, ensure_ascii=False, indent=2)}"
    )

    resp = cliente.gerar(
        Papel.RESPOSTA,
        prompt_final,
        response_mime_type="application/json",
        response_schema=RespostaDocumental.model_json_schema(),
        temperature=0.0,
    )

    if not resp.text:
        return _resposta_lacuna(plano.idioma, "O modelo não retornou conteúdo estruturado.")

    bruta = RespostaDocumental.model_validate_json(resp.text)
    validada, invalidas = _validar_e_sanear_resposta(bruta, fontes_permitidas, mapa_data, plano.idioma)

    # 6. Se o modelo citou fonte fora do contexto, refaz uma vez reforçando a lista permitida
    if invalidas and not validada.citacoes:
        prompt_correcao = (
            f"{prompt_final}\n\n"
            f"CORREÇÃO OBRIGATÓRIA: Você citou arquivos fora do contexto ({', '.join(invalidas)}). "
            f"Refaça usando EXCLUSIVAMENTE os arquivos de `arquivos_permitidos`."
        )
        resp_retry = cliente.gerar(
            Papel.RESPOSTA,
            prompt_correcao,
            response_mime_type="application/json",
            response_schema=RespostaDocumental.model_json_schema(),
            temperature=0.0,
        )
        if resp_retry.text:
            bruta_retry = RespostaDocumental.model_validate_json(resp_retry.text)
            validada, _ = _validar_e_sanear_resposta(bruta_retry, fontes_permitidas, mapa_data, plano.idioma)

    return validada


# ---------------------------------------------------------------------------
# Ferramenta exposta ao function calling (Etapa 12)
# ---------------------------------------------------------------------------


def consultar_documentos(pergunta: str, data_referencia: Optional[str] = None) -> dict:
    """Consulta documentos da cooperativa (certificações orgânicas, laudos sanitários,
    contratos, fichas técnicas, rastreabilidade de lotes e sazonalidade) com citação
    obrigatória da fonte e recusa a inventar informações ausentes na base.
    """
    resultado = responder_consulta_documental(
        pergunta=pergunta,
        data_referencia=data_referencia,
    )
    fontes = list(dict.fromkeys(c.arquivo for c in resultado.citacoes))
    encontrado = len(fontes) > 0
    return {
        "encontrado": encontrado,
        "resposta": resultado.resposta,
        "citacoes": [c.model_dump() for c in resultado.citacoes],
        "fontes": fontes,
        "lacunas": resultado.lacunas,
        "aviso": None if encontrado else (resultado.lacunas[0] if resultado.lacunas else "Informação não encontrada na base."),
    }

