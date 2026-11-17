"""Interface conversacional do assistente Sabor da Terra (etapa 13, issue #13).

Chat em Streamlit ligado ao assistente orquestrado da etapa 12: o `Assistente`
(dono do histórico de turnos e do `EstadoSessao`) vive no `st.session_state`;
o estado serializado acompanha via `to_dict()`/`from_dict()`. As respostas
documentais já chegam com citações `[fonte: arquivo]` no texto (regra 3 do
prompt de sistema), e a interface extrai esses marcadores para o rodapé de
fontes — sem depender do modelo. A lógica testável mora em
`sabor_da_terra/interface/`; este arquivo é a camada de `st.*`.

Rodar: `streamlit run app.py` (instruções no README).
"""

from __future__ import annotations

import datetime
import os

import streamlit as st
from dotenv import load_dotenv

from sabor_da_terra.assistente import Assistente, EstadoSessao, data_referencia_padrao
from sabor_da_terra.dados import obter_repositorio
from sabor_da_terra.interface import (
    detalhes_da_fila,
    extrair_fontes,
    formatar_fila,
    mensagem_de_erro,
)
from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.produtores import (
    notificar_produtores,
    relatorio_pendencias_vencidas,
    resumo_produtor,
)
from sabor_da_terra.triagem.fila import triar_pendentes

MODOS = ("real", "fixture")

load_dotenv()  # GEMINI_API_KEY, LLM_MODO e DATA_REFERENCIA do .env — antes de ler variáveis

# Chaves do chat/assistente que a "Nova sessão" apaga — os widgets de
# preferência (modo, data, mês) sobrevivem de propósito.
CHAVES_SESSAO = ("assistente", "mensagens", "estado_sessao", "atalho", "modo_da_sessao")

CORES_PRIORIDADE = {"alta": "#ffd7d7", "media": "#fff3c4", "baixa": "#e2f7e5"}

TITULO_ATALHO = {
    "fila": "📋 Fila de triagem",
    "resumo": "📝 Resumo do produtor",
    "notificacoes": "📣 Notificações de novos pedidos",
    "pendencias": "💰 Relatório de pendências vencidas",
}


# --------------------------------------------------------------------------- #
# Helpers de renderização                                                      #
# --------------------------------------------------------------------------- #


def _mostrar_fontes(texto: str) -> None:
    """Rodapé de fontes da resposta documental: os arquivos citados no texto."""
    fontes = extrair_fontes(texto)
    if fontes:
        with st.expander(f"📚 Fontes ({len(fontes)})", expanded=False):
            st.markdown("\n".join(f"- {fonte}" for fonte in fontes))


def _cor_prioridade(valor: str) -> str:
    cor = CORES_PRIORIDADE.get(str(valor), "")
    return f"background-color: {cor};" if cor else ""


def _cor_problemas(valor: int) -> str:
    return "background-color: #ffd7d7;" if int(valor) > 0 else ""


def renderizar_atalho(atalho: dict) -> None:
    """Desenha o resultado do atalho da demo conforme o tipo."""
    tipo, dados = atalho["tipo"], atalho["dados"]

    if tipo == "fila":
        st.caption(
            f"Fila consolidada em {dados.get('data_referencia', data_referencia)} — "
            "ordem canônica da triagem (urgentes no topo). Relatório de análise: "
            "nenhum pedido foi confirmado automaticamente."
        )
        df = formatar_fila(dados)
        if df.empty:
            st.info("Nenhum pedido pendente nesta data de referência.")
            return
        st.dataframe(
            df.style.map(_cor_prioridade, subset=["Prioridade"]).map(_cor_problemas, subset=["Problemas"]),
            width="stretch",
            hide_index=True,
        )
        with st.expander("🔎 Detalhes e alertas por registro", expanded=False):
            for titulo, markdown in detalhes_da_fila(dados):
                st.markdown(f"#### {titulo}")
                st.markdown(markdown)
                st.divider()

    elif tipo == "resumo":
        if not dados.get("encontrado"):
            st.warning(dados.get("aviso", "Produtor não encontrado."))
        else:
            st.caption(
                f"Resumo de {dados.get('produtor', {}).get('nome', '')} — mês {mes}. "
                "Copie para revisão; o envio é da equipe."
            )
            st.code(dados.get("texto", ""), language="markdown")

    elif tipo == "notificacoes":
        if not dados.get("encontrado"):
            st.warning(dados.get("aviso", "Nada para notificar."))
            return
        st.caption(
            f"{dados.get('total', len(dados.get('notificacoes', [])))} notificação(ões) "
            "gerada(s) da fila. Nada foi enviado."
        )
        for notificacao in dados.get("notificacoes") or []:
            produtor = notificacao.get("produtor") or {}
            st.markdown(f"**{produtor.get('nome', produtor.get('produtor_id', 'Produtor'))}**")
            st.code(notificacao.get("texto", ""), language="markdown")

    elif tipo == "pendencias":
        if not dados.get("encontrado"):
            st.warning(dados.get("aviso", "Nada para relatar."))
        else:
            st.caption("Relatório da cooperativa — copiável para a planilha ou o e-mail da equipe.")
            st.code(dados.get("texto", ""), language="markdown")


# --------------------------------------------------------------------------- #
# Página                                                                       #
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="Sabor da Terra — Assistente", page_icon="🌱", layout="wide")

st.title("🌱 Sabor da Terra — Assistente da cooperativa")
st.caption(
    "Protótipo da disciplina IA Generativa e Agentes (UPE × Sauter). Nada é enviado a "
    "produtores ou compradores; as respostas documentais citam o arquivo de origem."
)

# Barra lateral: modo, relógio da sessão e atalhos da demo ------------------ #

with st.sidebar:
    st.header("⚙️ Sessão")

    modo_padrao = os.getenv("LLM_MODO", "real")
    modo = st.selectbox(
        "Modo do LLM",
        MODOS,
        index=MODOS.index(modo_padrao) if modo_padrao in MODOS else 0,
        key="modo",
        help=(
            "real: chama a API Gemini. fixture: reproduz as respostas gravadas em "
            "tests/fixtures/llm (sem custo). Trocar o modo inicia uma nova sessão."
        ),
    )

    try:
        data_inicial = datetime.date.fromisoformat(data_referencia_padrao())
    except ValueError:
        data_inicial = datetime.date.today()
    data_entrada = st.date_input(
        "Data de referência (relógio da sessão)",
        value=data_inicial,
        key="data_referencia",
        format="DD/MM/YYYY",
        help="A data usada pela triagem e pelos relatórios da demo.",
    )
    data_referencia = data_entrada.isoformat()

    if st.button(
        "🔄 Nova sessão",
        width="stretch",
        help="Apaga o histórico e o estado: o assistente não lembra nada da sessão anterior.",
    ):
        for chave in CHAVES_SESSAO:
            st.session_state.pop(chave, None)
        st.rerun()

    st.divider()
    st.header("🧰 Atalhos da demo")
    st.caption("Chamam as funções reais das etapas 4–11 direto, sem gastar cota do LLM.")

    if st.button("Triar pedidos pendentes", width="stretch"):
        st.session_state["atalho"] = {"tipo": "fila", "dados": triar_pendentes(data_referencia)}
        st.rerun()

    produtores = obter_repositorio().produtores()
    opcoes = [f"{linha.produtor_id} — {linha.nome}" for linha in produtores.itertuples()]
    escolha = st.selectbox("Produtor", opcoes, index=0)
    produtor_id = escolha.split(" — ")[0]
    mes = st.text_input("Mês do resumo (AAAA-MM)", value=data_referencia[:7], key="mes_resumo")

    if st.button("Resumo do produtor", width="stretch"):
        st.session_state["atalho"] = {"tipo": "resumo", "dados": resumo_produtor(produtor_id, mes, data_referencia)}
        st.rerun()
    if st.button("Notificar produtores da fila", width="stretch"):
        st.session_state["atalho"] = {"tipo": "notificacoes", "dados": notificar_produtores(data_referencia)}
        st.rerun()
    if st.button("Relatório de pendências vencidas", width="stretch"):
        st.session_state["atalho"] = {"tipo": "pendencias", "dados": relatorio_pendencias_vencidas(data_referencia)}
        st.rerun()

# Sessão: o Assistente vivo no st.session_state ----------------------------- #


def iniciar_sessao() -> Assistente:
    """Cria (ou recupera) o assistente; trocar o modo renasce a sessão."""
    if st.session_state.get("modo_da_sessao") not in (None, modo):
        for chave in CHAVES_SESSAO:
            st.session_state.pop(chave, None)
    if "assistente" not in st.session_state:
        # O estado serializado da sessão (#12: to_dict/from_dict) renasce o
        # relógio e os focos se o objeto não existir mais.
        dados_estado = st.session_state.get("estado_sessao")
        estado = EstadoSessao.from_dict(dados_estado) if dados_estado else EstadoSessao(data_referencia=data_referencia)
        estado.data_referencia = data_referencia  # o relógio segue a barra lateral
        st.session_state["assistente"] = Assistente(cliente_llm=LLMClient(modo=modo), estado=estado)
        st.session_state["mensagens"] = []
        st.session_state["estado_sessao"] = estado.to_dict()
        st.session_state["modo_da_sessao"] = modo
    return st.session_state["assistente"]


assistente = iniciar_sessao()

# A data mudou na barra lateral? O relógio da sessão acompanha.
if assistente.estado.data_referencia != data_referencia:
    assistente.estado.data_referencia = data_referencia
    st.session_state["estado_sessao"] = assistente.estado.to_dict()

# Resultado do atalho da demo (acima do chat, para a banca ver sem rolar) ---- #

atalho = st.session_state.get("atalho")
if atalho:
    with st.container(border=True):
        coluna_titulo, coluna_fechar = st.columns([0.9, 0.1])
        coluna_titulo.subheader(TITULO_ATALHO.get(atalho["tipo"], "Resultado"))
        if coluna_fechar.button("✖", help="Fechar o resultado do atalho"):
            st.session_state.pop("atalho", None)
            st.rerun()
        renderizar_atalho(atalho)

# Estado da sessão (focos da #12) — visível para a demo --------------------- #

with st.expander("🔍 Estado da sessão (focos do assistente)", expanded=False):
    st.json(assistente.estado.to_dict())

# Chat ---------------------------------------------------------------------- #

for msg in st.session_state["mensagens"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        _mostrar_fontes(msg["content"])

if prompt := st.chat_input("Escreva sua mensagem para o assistente…"):
    st.session_state["mensagens"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Consultando as funções do assistente…"):
            try:
                resposta = assistente.responder(prompt)
            except Exception as erro:  # noqa: BLE001 — nenhum stack trace na tela
                st.error(mensagem_de_erro(erro))
                resposta = None
        if resposta:
            st.markdown(resposta)
            _mostrar_fontes(resposta)
            st.session_state["mensagens"].append({"role": "assistant", "content": resposta})
    st.session_state["estado_sessao"] = assistente.estado.to_dict()
    if resposta:
        st.rerun()
