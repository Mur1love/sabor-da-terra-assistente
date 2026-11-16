"""Etapa 12: orquestração do assistente — estado da sessão, mascaramento, ferramentas e turno."""

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from google.genai import types
from tests.dobles import ClienteFake, ModeloFake

from sabor_da_terra.assistente.estado import EstadoSessao, data_referencia_padrao
from sabor_da_terra.assistente.ferramentas import FERRAMENTAS, NOME_PARA_FUNCAO, declarar_ferramentas
from sabor_da_terra.assistente.mascaramento import mascarar_dados_sensiveis
from sabor_da_terra.assistente.orquestrador import Assistente
from sabor_da_terra.assistente.prompt import PROMPT_RESPOSTA_FINAL, PROMPT_SISTEMA
from sabor_da_terra.llm.cliente import LLMClient
from sabor_da_terra.dados import obter_repositorio

RAIZ = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Estado da sessão
# ---------------------------------------------------------------------------


def test_estado_atualiza_produtor_em_foco_por_identificar():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("identificar_produtor", {}, {"encontrado": True, "produtor": {"produtor_id": "P008", "nome": "Josefa Alves de Souza"}})
    assert estado.produtor_em_foco == {"produtor_id": "P008", "nome": "Josefa Alves de Souza"}


def test_estado_atualiza_produto_por_buscar_e_por_conformidade_dict():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("buscar_produtores", {}, {"produto": "mel silvestre"})
    assert estado.produto_em_foco == "mel silvestre"
    estado.atualizar("verificar_conformidade", {}, {"produto": {"produto": "goiaba paluma", "quantidade": 300}})
    assert estado.produto_em_foco == "goiaba paluma"  # quirk: "produto" é dict na conformidade


def test_estado_atualiza_pedido_em_foco_pelo_id_na_mensagem():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("triar_pedido", {"mensagem": "300kg de goiaba para PED-2026-006, urgente"}, {"itens": [{"produto": "goiaba paluma"}]})
    assert estado.pedido_em_foco == "PED-2026-006"
    assert estado.produto_em_foco == "goiaba paluma"


def test_estado_rastrear_lote_atualiza_produto():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("rastrear_lote", {}, {"encontrado": True, "lote": {"lote_id": "LOT-2026-0089", "produto": "queijo coalho"}})
    assert estado.produto_em_foco == "queijo coalho"


def test_estado_ignora_resultados_sem_foco():
    estado = EstadoSessao(data_referencia="2026-10-30")
    estado.atualizar("triar_pendentes", {}, {"total_registros": 15})
    estado.atualizar("consultar_documentos", {}, {"resposta": "x"})
    estado.atualizar("notificar_produtores", {}, {"notificacoes": []})
    estado.atualizar("identificar_produtor", {}, {"encontrado": False, "aviso": "não existe"})
    assert (estado.produtor_em_foco, estado.pedido_em_foco, estado.produto_em_foco) == (None, None, None)


def test_data_referencia_padrao_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("DATA_REFERENCIA", "2026-10-30")
    assert data_referencia_padrao() == "2026-10-30"
    monkeypatch.delenv("DATA_REFERENCIA", raising=False)
    assert data_referencia_padrao() == date.today().isoformat()


def test_contexto_bloco_legivel_e_serializacao_idempotente():
    estado = EstadoSessao(data_referencia="2026-10-30", pedido_em_foco="PED-2026-006")
    estado.atualizar("identificar_produtor", {}, {"encontrado": True, "produtor": {"produtor_id": "P008", "nome": "Josefa Alves de Souza"}})
    bloco = estado.contexto()
    assert "2026-10-30" in bloco and "P008" in bloco and "PED-2026-006" in bloco
    assert EstadoSessao.from_dict(estado.to_dict()) == estado


# ---------------------------------------------------------------------------
# Mascaramento de dados sensíveis
# ---------------------------------------------------------------------------


def test_mascara_cpf_pix_conta_e_telefone_em_payload_aninhado():
    cadastro = obter_repositorio().produtores()
    cpf, pix = str(cadastro.iloc[0]["cpf"]), str(cadastro.iloc[0]["chave_pix"])
    conta, telefone = str(cadastro.iloc[0]["conta_corrente"]), str(cadastro.iloc[0]["telefone"])
    payload = {"a": [f"CPF {cpf} e PIX {pix}", {"conta": conta, "tel": telefone}]}
    texto = json.dumps(mascarar_dados_sensiveis(payload), ensure_ascii=False)
    assert cpf not in texto and pix not in texto and conta not in texto and telefone not in texto
    assert "***" in texto


def test_cpf_solto_em_texto_e_mascarado_e_texto_limpo_passa_igual():
    assert mascarar_dados_sensiveis("CPF 123.456.789-09 aqui") == "CPF ***.***.***-** aqui"
    assert mascarar_dados_sensiveis({"msg": "300kg de goiaba para PED-2026-006"}) == {"msg": "300kg de goiaba para PED-2026-006"}


def test_tipos_nao_string_ficam_intactos():
    assert mascarar_dados_sensiveis({"qtd": 300, "ok": True, "nada": None}) == {"qtd": 300, "ok": True, "nada": None}


# ---------------------------------------------------------------------------
# Declaração das ferramentas
# ---------------------------------------------------------------------------

NOMES_ESPERADOS = {
    "triar_pedido", "triar_pendentes", "consultar_documentos", "resumo_produtor",
    "notificar_produtores", "rastrear_lote", "buscar_produtores", "preco",
    "disponibilidade", "verificar_conformidade", "identificar_produtor",
}


def test_ferramentas_sao_as_da_issue_mais_identificar_produtor():
    assert {f.__name__ for f in FERRAMENTAS} == NOMES_ESPERADOS
    assert set(NOME_PARA_FUNCAO) == NOMES_ESPERADOS


def test_declaracao_e_deterministica_e_esconde_interno_da_fila():
    d1, d2 = declarar_ferramentas().model_dump(), declarar_ferramentas().model_dump()
    assert d1 == d2  # determinística — o hash de fixture depende disso
    nomes = {f["name"] for f in d1["function_declarations"]}
    assert nomes == NOMES_ESPERADOS
    pendentes = next(f for f in d1["function_declarations"] if f["name"] == "triar_pendentes")
    assert list(pendentes["parameters"]["properties"]) == ["data_referencia"]  # sem caminho_pedidos


def test_adaptador_triar_pendentes_delega_na_real(monkeypatch):
    chamadas = []
    monkeypatch.setattr("sabor_da_terra.assistente.ferramentas._triar_pendentes_real",
                        lambda data_referencia, **k: chamadas.append(data_referencia) or {"ok": True})
    assert NOME_PARA_FUNCAO["triar_pendentes"]("2026-10-30") == {"ok": True}
    assert chamadas == ["2026-10-30"]


# ---------------------------------------------------------------------------
# Prompts de sistema e de resposta final
# ---------------------------------------------------------------------------


def test_prompt_sistema_tem_as_regras_da_issue():
    texto = PROMPT_SISTEMA.lower()
    for trecho in ("sabor da terra", "português", "não invente", "não envia", "nada foi enviado",
                   "não cadastra", "cpf", "pix", "fonte"):
        assert trecho in texto, trecho


def test_prompt_resposta_final_manda_preservar_citacoes_e_usar_so_resultados():
    texto = PROMPT_RESPOSTA_FINAL.lower()
    assert "fontes_permitidas" in texto and "não invente" in texto
    assert "citaç" in texto


# ---------------------------------------------------------------------------
# Turno do assistente: laço de function calling
# ---------------------------------------------------------------------------


@dataclass
class Script:
    """Um script de resposta do modelo: texto e/ou function_call."""

    texto: str | None = None
    function_call: dict | None = None


def ROTEADOR(nome: str, args: dict | None = None) -> Script:
    """Script de roteamento que manda o assistente chamar uma função."""
    return Script(function_call={"name": nome, "args": args or {}})


class FilaControlada:
    """Fila FIFO por papel COMPARTILHADA entre roteador e ferramentas aninhadas.

    A ordem dos scripts é a ordem real das chamadas; `prompts`/`configs` capturam
    tudo que foi enviado a cada papel (qualquer instância do cliente grava aqui).
    """

    def __init__(self, scripts: dict[str, list[Script]] | None = None):
        self.scripts = scripts or {}
        self.prompts: dict[str, list[str]] = {}
        self.configs: dict[str, list[dict]] = {}

    def pop(self, papel: str) -> Script | None:
        fila = self.scripts.get(papel.value if hasattr(papel, "value") else papel)
        return fila.pop(0) if fila else None


class _LLMControlado(LLMClient):
    """Modo fixture com fila FIFO por papel: grava sob demanda em tmp_path e reproduz.

    Ordem das chamadas = ordem real do turno: roteador do assistente → chamadas
    aninhadas das ferramentas com LLM → rascunho do roteamento → composição final.
    """

    def __init__(self, tmp_path: Path, fila: FilaControlada):
        super().__init__(modo="fixture", pasta_fixtures=tmp_path)
        self._fila = fila

    def gerar(self, papel, prompt, **config_geracao):
        nome_papel = papel.value if hasattr(papel, "value") else str(papel)
        self._fila.prompts.setdefault(nome_papel, []).append(prompt if isinstance(prompt, str) else str(prompt))
        self._fila.configs.setdefault(nome_papel, []).append(config_geracao)
        script = self._fila.pop(papel)
        if script is not None:
            fake = ClienteFake(ModeloFake(texto=script.texto, function_call=script.function_call))
            LLMClient(modo="gravar", pasta_fixtures=self._pasta_fixtures, cliente=fake, dormir=lambda _: None).gerar(
                papel, prompt, **config_geracao
            )
        return super().gerar(papel, prompt, **config_geracao)


def _fabrica(tmp_path: Path, fila: FilaControlada):
    """Fábrica de clientes ligados à MESMA fila (roteador + ferramentas aninhadas)."""

    def fabrica(*_args, **_kwargs):
        return _LLMControlado(tmp_path, fila)

    return fabrica


def _fila_vazia(fila: FilaControlada):
    """Assert de fim: nenhuma script sobrando (nada foi consumido silenciosamente)."""
    sobrando = {papel: len(scripts) for papel, scripts in fila.scripts.items() if scripts}
    assert not sobrando, f"scripts não consumidos: {sobrando}"


def _assistente(cliente_llm, **kwargs):
    return Assistente(cliente_llm=cliente_llm, estado=EstadoSessao(data_referencia="2026-10-30"), **kwargs)


def test_turno_chama_funcao_real_e_fechar_com_model(tmp_path):
    fila = FilaControlada({
        "triagem": [ROTEADOR("identificar_produtor", {"termo": "Josefa"}), Script(texto="Peguei, consultando...")],
        "resposta": [Script(texto="A produtora em foco é Josefa Alves de Souza (P008).")],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    final = a.responder("E o da Josefa?")
    assert final == "A produtora em foco é Josefa Alves de Souza (P008)."
    assert a.historico[-1].role == "model"
    assert a.estado.produtor_em_foco == {"produtor_id": "P008", "nome": "Josefa Alves de Souza"}


def test_resposta_de_funcao_va_como_role_tool(tmp_path):
    fila = FilaControlada({
        "triagem": [ROTEADOR("preco", {"produto": "queijo coalho", "organico": False, "quantidade": 150}), Script(texto="ok")],
        "resposta": [Script(texto="R$ 32,00/kg.")],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    a.responder("quanto está o queijo?")
    tools = [c for c in a.historico if c.role == "tool"]
    assert tools and tools[0].parts[0].function_response.name == "preco"
    assert tools[0].parts[0].function_response.response["produto"] == "queijo coalho"


def test_relogio_da_sessao_sobrepoe_o_modelo(tmp_path):
    fila = FilaControlada({
        "triagem": [ROTEADOR("identificar_produtor", {"termo": "P003", "data_referencia": "2020-01-01"}), Script(texto="ok")],
        "resposta": [Script(texto="P003 é Cícero.")],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    a.responder("quem é P003?")
    tools = [c for c in a.historico if c.role == "tool"]
    assert tools[0].parts[0].function_response.response["data_referencia"] == "2026-10-30"


def test_triar_pedido_recebe_data_recebimento_da_sessao(tmp_path, monkeypatch):
    fila = FilaControlada({
        "triagem": [
            ROTEADOR("triar_pedido", {"mensagem": "300kg de goiaba para PED-2026-006, urgente"}),
            Script(texto='{"tipo": "compra", "idioma": "pt", "itens": [{"produto": "goiaba paluma", "quantidade": 300, "unidade": "kg"}]}'),
            Script(texto="extraindo..."),
        ],
        "resposta": [Script(texto="Pedido triado: 300 kg de goiaba.")],
    })
    monkeypatch.setattr("sabor_da_terra.triagem.extrair.LLMClient", _fabrica(tmp_path, fila))
    a = _assistente(_fabrica(tmp_path, fila)())
    a.responder("anota esse pedido")
    assert a.estado.pedido_em_foco == "PED-2026-006"
    extracao = fila.prompts["triagem"][1]
    assert "Metadados" in extracao and "2026-10-30" in extracao  # relógio chegou à extração


def test_funcao_que_lanca_excecao_devolve_erro_honesto_sem_travar(tmp_path):
    fila = FilaControlada({
        "triagem": [ROTEADOR("verificar_conformidade", {"item": {"produto": "mel"}}), Script(texto="não consegui conferir")],
        "resposta": [],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    texto = a.responder("conferir o mel")
    tools = [c for c in a.historico if c.role == "tool"]
    assert "erro" in tools[0].parts[0].function_response.response
    assert isinstance(texto, str)


def test_funcao_desconhecida_devolve_erro(tmp_path):
    fila = FilaControlada({
        "triagem": [ROTEADOR("enviar_whatsapp"), Script(texto="não faço isso")],
        "resposta": [],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    a.responder("manda no zap")
    tools = [c for c in a.historico if c.role == "tool"]
    assert "desconhecida" in tools[0].parts[0].function_response.response["erro"].lower()


def test_limite_responde_erro_e_proximo_turno_funciona(tmp_path):
    fila = FilaControlada({
        "triagem": [
            ROTEADOR("identificar_produtor", {"termo": "P001"}),
            ROTEADOR("identificar_produtor", {"termo": "P001"}),
            ROTEADOR("identificar_produtor", {"termo": "P001"}),
            ROTEADOR("identificar_produtor", {"termo": "P002"}),
            Script(texto="ok"),
        ],
        "resposta": [Script(texto="Duas consultas feitas, a terceira ficou para depois."), Script(texto="P002 é Ana.")],
    })
    a = Assistente(cliente_llm=_fabrica(tmp_path, fila)(), estado=EstadoSessao(data_referencia="2026-10-30"), max_chamadas=2, max_iteracoes=3)
    a.responder("quem é P001?")
    conteudos = list(a.historico)
    for i, conteudo in enumerate(conteudos):  # protocolo válido: nenhuma function_call sem resposta
        if conteudo.role == "model" and any(p.function_call for p in conteudo.parts):
            assert conteudos[i + 1].role == "tool"
    a.responder("e o P002?")  # o turno seguinte ainda funciona
    assert a.estado.produtor_em_foco["produtor_id"] == "P002"


def test_turno_sem_funcao_usa_o_texto_do_flash_lite_e_nao_compoem(tmp_path):
    fila = FilaControlada({"triagem": [Script(texto="Não envio mensagens: o protótipo não faz isso e nada foi enviado.")], "resposta": []})
    a = _assistente(_fabrica(tmp_path, fila)())
    final = a.responder("manda no WhatsApp pra ele")
    assert "nada foi enviado" in final.lower()
    assert [c.role for c in a.historico].count("tool") == 0
    _fila_vazia(fila)


def test_pass_through_nao_chama_o_flash(tmp_path):
    fila = FilaControlada({
        "triagem": [ROTEADOR("resumo_produtor", {"produtor_id": "P008", "mes": "2026-10"}), Script(texto="Segue o resumo.")],
        "resposta": [],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    final = a.responder("manda um resumo pra ela")
    assert final.startswith("Olá, Josefa")  # texto pronto do resumo real, verbatim
    _fila_vazia(fila)  # nenhuma script de resposta consumida → o Flash não foi chamado


def test_resultado_estruturado_vai_ao_flash_com_o_payload(tmp_path):
    fila = FilaControlada({
        "triagem": [ROTEADOR("buscar_produtores", {"produto": "mel silvestre", "organico": True}), Script(texto="P002 e P018, com P008 vencida.")],
        "resposta": [Script(texto="Os produtores com certificação orgânica vigente para mel silvestre são P002 e P018.")],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    final = a.responder("quem tem mel orgânico vigente?")
    assert "P002" in final
    _fila_vazia(fila)
    payload = json.loads(fila.prompts["resposta"][-1].split("CONTEXTO DO TURNO (JSON):\n", 1)[1])
    assert any(r["funcao"] == "buscar_produtores" for r in payload["resultados_das_funcoes"])
    assert payload["estado_da_sessao"]["produto_em_foco"] == "mel silvestre"
    assert payload["fontes_permitidas"] == []


def test_payload_da_composicao_coleciona_fontes_das_saidas(tmp_path):
    fila = FilaControlada({
        "triagem": [ROTEADOR("rastrear_lote", {"lote_id": "LOT-2026-0089"}), Script(texto="lote encontrado")],
        "resposta": [Script(texto="O lote LOT-2026-0089 é de queijo coalho [fonte: data/lotes.csv].")],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    final = a.responder("onde está o lote LOT-2026-0089?")
    assert "queijo coalho" in final
    _fila_vazia(fila)
    payload = json.loads(fila.prompts["resposta"][-1].split("CONTEXTO DO TURNO (JSON):\n", 1)[1])
    assert payload["fontes_permitidas"] == ["lotes.csv"]
    assert payload["estado_da_sessao"]["produto_em_foco"] == "queijo coalho"


def test_config_do_roteamento_declara_as_ferramentas(tmp_path):
    fila = FilaControlada({"triagem": [Script(texto="Olá! Como posso ajudar?")], "resposta": []})
    a = _assistente(_fabrica(tmp_path, fila)())
    a.responder("bom dia")
    config = fila.configs["triagem"][-1]
    assert len(config["tools"][0].function_declarations) == 11
    assert config["system_instruction"] == PROMPT_SISTEMA
    assert config["automatic_function_calling"].disable is True


def test_despacho_mascara_args_e_log(tmp_path, caplog):
    cadastro = obter_repositorio().produtores()
    pix = str(cadastro.iloc[0]["chave_pix"])
    fila = FilaControlada({
        "triagem": [ROTEADOR("identificar_produtor", {"termo": f"meu PIX é {pix}"}), Script(texto="ok")],
        "resposta": [Script(texto="Não encontrei esse produtor.")],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    with caplog.at_level(logging.INFO, logger="sabor_da_terra.assistente"):
        a.responder("nota com dados")
    registro = " ".join(r.getMessage() for r in caplog.records)
    assert pix not in registro and "123.456.789-09" not in registro


def test_log_do_turno_mostra_funcoes_modelo_e_duracao(tmp_path, caplog):
    fila = FilaControlada({
        "triagem": [ROTEADOR("preco", {"produto": "queijo coalho", "organico": False, "quantidade": 150}), Script(texto="ok")],
        "resposta": [Script(texto="R$ 32,00/kg.")],
    })
    a = _assistente(_fabrica(tmp_path, fila)())
    with caplog.at_level(logging.INFO, logger="sabor_da_terra.assistente"):
        a.responder("preço do queijo")
    registro = " ".join(r.getMessage() for r in caplog.records)
    assert "preco" in registro
    assert "turno=1" in registro
    assert "duracao=" in registro or "duracao" in registro


# ---------------------------------------------------------------------------
# Janela de histórico (turnos completos)
# ---------------------------------------------------------------------------


def test_janela_mantem_turnos_completos(tmp_path):
    fila = FilaControlada({"triagem": [Script(texto=f"ok {i}") for i in range(5)], "resposta": []})
    a = Assistente(cliente_llm=_fabrica(tmp_path, fila)(), estado=EstadoSessao(data_referencia="2026-10-30"), janela=2)
    for i in range(5):
        a.responder(f"turno {i}")
    roles = [c.role for c in a.historico]
    assert roles.count("user") == 2 and roles[-1] == "model" and "tool" not in roles


def test_janela_nunca_corta_turno_com_funcao(tmp_path):
    fila = FilaControlada({
        "triagem": [
            ROTEADOR("preco", {"produto": "queijo coalho", "organico": False, "quantidade": 150}),
            Script(texto="t1 fechado"),
        ]
        + [Script(texto=f"ok {i}") for i in range(3)],
        "resposta": [Script(texto="R$ 32,00/kg.")],
    })
    a = Assistente(cliente_llm=_fabrica(tmp_path, fila)(), estado=EstadoSessao(data_referencia="2026-10-30"), janela=2)
    a.responder("preço do queijo")
    for i in range(3):
        a.responder(f"turno {i}")
    conteudos = list(a.historico)
    for i, conteudo in enumerate(conteudos):  # nenhuma tool sem o model de function_calls imediatamente antes
        if conteudo.role == "tool":
            assert i >= 1 and conteudos[i - 1].role == "model"
