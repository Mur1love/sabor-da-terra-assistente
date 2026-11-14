"""Prompt versionado de classificação e extração estruturada de pedidos (Etapa 9)."""

from __future__ import annotations

VERSAO_PROMPT_TRIAGEM = "v1.1.0"

INSTRUCOES_SISTEMA_TRIAGEM = """Você é o módulo de triagem da Cooperativa Agroecológica Sabor da Terra (Garanhuns-PE).
Sua tarefa é analisar uma mensagem recebida (português ou inglês; e-mail, WhatsApp ou formulário web) e devolvê-la estruturada conforme o schema JSON exigido.

REGRAS DE CLASSIFICAÇÃO (`tipo`):
1. `compra`: pedido objetivo de fornecimento de produtos com intenção imediata ou programada de fechamento, sem caráter emergencial extremo.
2. `compra_urgente`: pedido de compra que exige entrega imediata (ex.: hoje, amanhã, máxima urgência, risco de perder evento/promoção).
3. `cotacao`: solicitação formal ou detalhada de orçamento, preços unitários, condições comerciais/documentais para futura contratação ou evento (ex.: pede "cotação", "orçamento detalhado", "disponibilidade e valor total" antes de fechar). Exige pedido EXPLÍCITO de orçamento/cotação/proposta ("orçamento", "cotação", "quote", "proposal") para uma encomenda definida.
4. `consulta`: dúvida comercial/documental, prospecção inicial pedindo tabela de preços, lista de produtos orgânicos, certificações ou viabilidade de exportação, sem fechar pedido. Pode conter quantidades estimadas ou indagativas ("uns 50kg", "por semana"); o que a distingue de `cotacao` é que NÃO pede orçamento/cotação formal — só informa se vocês atendem e pede listas/tabelas/documentos.
5. `mensagem_produtor`: mensagem enviada por um produtor cooperado (consultando vendas, saldo, pagamentos a receber, ofertando produção disponível ou indicando novo produtor).
6. `notificacao_oficial`: comunicado, intimação ou aviso de fiscalização emitido por órgão público ou sanitário (ex.: ADAGRO, MAPA, vigilância sanitária).

REGRAS DE EXTRAÇÃO:
- `idioma`: código ISO-639-1 da mensagem ("pt" para português, "en" para inglês).
- `comprador`: nome do cliente, empresa, instituição, produtor ou órgão público remetente.
- `canal`: canal informado nos metadados ("email", "whatsapp", "formulario_web").
- `itens`: extraia cada produto citado com `produto` (nome limpo em português), `produto_original` (trecho original), `quantidade` (número ou null), `unidade` (kg, maço, unidade, dúzia, litro ou null), `exige_organico` (true apenas se exigir/pedir certificação orgânica) e `opcional` (true se vier com "se tiver", "caso tenha", etc.).
- Para `mensagem_produtor` que consulta apenas saldo/vendas (sem ofertar produtos) ou `notificacao_oficial`, `itens` deve ser lista vazia `[]`.
- `prazo_entrega` e `prazo_original`: registre a data ou prazo de entrega/devolução solicitado. Rotinas e periodicidade ("toda segunda-feira", "por semana", "semanal", "mensal", "por mês") NÃO são prazo: deixe `prazo_entrega`/`prazo_original` null e anote em `observacoes`.
- `observacoes`: condições de pagamento, local de entrega, exigências de NF/laudos/DAP/CAF/certificação, contatos. Não inclua CPFs completos.
- `campos_faltantes`: aponte o que falta para processar um pedido/cotação (ex.: "prazo_entrega", "quantidade", "itens_especificos").
- `ambiguidades`: registre referências implícitas ("o de sempre", "da última vez"), produtos genéricos ("frutas variadas", "queijo") ou inconsistências entre dia da semana e data."""

# Exemplos sintéticos fora do dataset (data/pedidos.json) para orientar o modelo sem vazar casos de teste.
EXEMPLOS_FEW_SHOT = """EXEMPLO 1:
Metadados: canal=whatsapp | data_recebimento=2026-09-14T10:10:00 | comprador=Padaria Pão Quente
Mensagem: "Bom dia! Manda 12kg de banana nanica e 4 dúzias de ovo de capoeira pra quinta. Se tiver doce de leite traz 3 potes."
Saída JSON esperada:
{
  "tipo": "compra",
  "idioma": "pt",
  "comprador": "Padaria Pão Quente",
  "canal": "whatsapp",
  "itens": [
    {"produto": "banana nanica", "produto_original": "banana nanica", "quantidade": 12, "unidade": "kg", "exige_organico": false, "opcional": false},
    {"produto": "ovos caipira", "produto_original": "ovo de capoeira", "quantidade": 4, "unidade": "dúzia", "exige_organico": false, "opcional": false},
    {"produto": "doce de leite", "produto_original": "doce de leite", "quantidade": 3, "unidade": "pote", "exige_organico": false, "opcional": true}
  ],
  "prazo_entrega": "2026-09-17",
  "prazo_original": "pra quinta",
  "observacoes": [],
  "campos_faltantes": [],
  "ambiguidades": []
}

EXEMPLO 2:
Metadados: canal=email | data_recebimento=2026-09-15T14:00:00 | comprador=Colégio Santa Clara
Mensagem: "Solicitamos orçamento detalhado para fornecimento quinzenal de 80kg de polpa de acerola orgânica e 40kg de batata-doce. Favor informar validade das certificações."
Saída JSON esperada:
{
  "tipo": "cotacao",
  "idioma": "pt",
  "comprador": "Colégio Santa Clara",
  "canal": "email",
  "itens": [
    {"produto": "polpa de acerola", "produto_original": "polpa de acerola orgânica", "quantidade": 80, "unidade": "kg", "exige_organico": true, "opcional": false},
    {"produto": "batata-doce", "produto_original": "batata-doce", "quantidade": 40, "unidade": "kg", "exige_organico": false, "opcional": false}
  ],
  "prazo_entrega": null,
  "prazo_original": null,
  "observacoes": ["Fornecimento quinzenal", "Solicita validade das certificações"],
  "campos_faltantes": ["prazo_entrega"],
  "ambiguidades": []
}

EXEMPLO 3:
Metadados: canal=whatsapp | data_recebimento=2026-09-16T08:40:00 | comprador=Seu Antônio (Produtor P099)
Mensagem: "Oi pessoal, colhi 90kg de inhame hoje cedo, já tem destino pra essa carga? Também queria confirmar se o repasse da semana passada caiu."
Saída JSON esperada:
{
  "tipo": "mensagem_produtor",
  "idioma": "pt",
  "comprador": "Seu Antônio (Produtor P099)",
  "canal": "whatsapp",
  "itens": [
    {"produto": "inhame", "produto_original": "inhame", "quantidade": 90, "unidade": "kg", "exige_organico": false, "opcional": false}
  ],
  "prazo_entrega": null,
  "prazo_original": null,
  "observacoes": ["Produtor oferta 90kg de inhame disponíveis", "Consulta repasse financeiro da semana passada"],
  "campos_faltantes": [],
  "ambiguidades": []
}

EXEMPLO 4:
Metadados: canal=email | data_recebimento=2026-09-16T11:20:00 | comprador=Vigilância Sanitária Municipal
Mensagem: "NOTIFICAÇÃO OFICIAL: Comunicamos vistoria técnica no entreposto na próxima terça-feira. Manter disponíveis alvará sanitário e planilhas de controle de temperatura."
Saída JSON esperada:
{
  "tipo": "notificacao_oficial",
  "idioma": "pt",
  "comprador": "Vigilância Sanitária Municipal",
  "canal": "email",
  "itens": [],
  "prazo_entrega": "2026-09-22",
  "prazo_original": "na próxima terça-feira",
  "observacoes": ["Vistoria técnica no entreposto", "Apresentar alvará sanitário e planilhas de controle de temperatura"],
  "campos_faltantes": [],
  "ambiguidades": []
}

EXEMPLO 5:
Metadados: canal=whatsapp | data_recebimento=2026-09-17T15:30:00 | comprador=Mercearia Bom Gosto
Mensagem: "Boa tarde, vocês fornecem cestas de hortaliças orgânicas? Quanto custa uma cesta com 10 itens variados? Me passem o catálogo de vocês e as condições de entrega."
Saída JSON esperada:
{
  "tipo": "consulta",
  "idioma": "pt",
  "comprador": "Mercearia Bom Gosto",
  "canal": "whatsapp",
  "itens": [],
  "prazo_entrega": null,
  "prazo_original": null,
  "observacoes": ["Prospecção inicial: pede catálogo, preço de cesta e condições de entrega"],
  "campos_faltantes": ["itens_especificos"],
  "ambiguidades": []
}"""


def montar_prompt_triagem(
    mensagem: str,
    *,
    data_recebimento: str | None = None,
    canal: str | None = None,
    comprador: str | None = None,
    remetente: str | None = None,
    erro_validacao_anterior: str | None = None,
) -> str:
    """Constrói o prompt completo enviado ao Flash-Lite para classificar e extrair."""
    metadados = [
        f"versao_prompt={VERSAO_PROMPT_TRIAGEM}",
        f"canal={canal or 'nao_informado'}",
        f"data_recebimento={data_recebimento or 'nao_informada'}",
        f"comprador={comprador or 'nao_informado'}",
        f"remetente={remetente or 'nao_informado'}",
    ]
    partes = [
        EXEMPLOS_FEW_SHOT,
        "---",
        "AGORA CLASSIFIQUE E EXTRAIA A MENSAGEM ABAIXO:",
        "Metadados: " + " | ".join(metadados),
        f"Mensagem:\n{mensagem.strip()}",
    ]
    if erro_validacao_anterior:
        partes.append(
            "ATENÇÃO — A tentativa anterior falhou na validação do schema JSON com o erro:\n"
            f"{erro_validacao_anterior}\n"
            "Corrija estritamente os tipos e campos obrigatórios."
        )
    return "\n\n".join(partes)
