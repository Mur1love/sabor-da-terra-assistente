# Gabarito de Avaliação (Golden Set) — Sabor da Terra

Este diretório contém os casos de teste versionados em YAML utilizados para avaliar o assistente de IA da Cooperativa Sabor da Terra nas etapas de implementação (#8 a #12) e na avaliação ponta a ponta (#14).

## Estrutura dos arquivos

- `casos-triagem.yaml` — Cobertura dos 15 registros de `data/pedidos.json` (`TRI-001` a `TRI-015`).
- `casos-certificacoes.yaml` — Validade de certificações orgânicas, certificação vencida de P008 e restrições sanitárias ADAGRO/SIE (`CERT-001` a `CERT-005`).
- `casos-consulta-documental.yaml` — Consultas documentais com citação de fonte, contratos, rastreabilidade de lotes (`LOT-2026-0089`), DAP/CAF e sazonalidade (`DOC-001` a `DOC-007`).
- `casos-produtores.yaml` — Extratos financeiros com valores exatos de `data/financeiro.csv`, títulos atrasados e notificações personalizadas por produtor (`PROD-001` a `PROD-004`).
- `casos-contexto.yaml` — Diálogos multi-turno testando retenção de contexto na sessão (`CTX-001` a `CTX-003`).
- `anti-alucinacao.yaml` — Recusa a inventar certificações internacionais, itens fora do catálogo e alocação de produtores inativos (`ANTI-001` a `ANTI-003`).

## Esquema de cada caso YAML

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | `string` | Identificador único do caso (`TRI-*`, `CERT-*`, `DOC-*`, `PROD-*`, `CTX-*`, `ANTI-*`). |
| `pedido_id` | `string` (opcional) | ID correspondente em `data/pedidos.json`, quando aplicável. |
| `data_recebimento` | `string` (opcional) | Timestamp de referência para interpretar prazos relativos ("hoje", "amanhã", "sábado"). |
| `desafio` | `string` | Gargalo avaliado: `Triagem de pedidos`, `Consulta documental` ou `Comunicação com produtores`. |
| `requisito` | `string` | Requisito funcional ou regra de negócio específica testada. |
| `entrada` | `string` | Mensagem ou diálogo (turno único ou multi-turno) enviado ao assistente. |
| `esperado` | `string` | Comportamento e critérios completos esperados na resposta. |
| `funcoes_esperadas` | `list[string]` | Funções/ferramentas esperadas na orquestração (preenchido nas etapas #8–#12). |
| `deve_conter` | `list[string]` | Evidências, valores, alertas ou citações obrigatórias na resposta. |
| `nao_deve_conter` | `list[string]` | Falhas críticas, alucinações ou violações de regra proibidas. |
| `fonte` | `list[string]` | Arquivos de `data/` e `docs/` que comprovam o gabarito. |

## Cobertura

- **Total:** 37 casos de teste (mínimo exigido: 35).
- **Pedidos:** 100% dos 15 registros de `data/pedidos.json` cobertos.
- **Requisitos funcionais:** linguagem coloquial, citação documental, relatórios/notificações, contexto de sessão multi-turno e recusa a inventar dados (anti-alucinação).

## Preenchimento na etapa #12

`funcoes_esperadas` ficou vazio quando o gabarito foi escrito (as ferramentas ainda não existiam).
A etapa #12 preencheu os 37 casos com o mapeamento pergunta → ferramenta da orquestração
(`tests/test_assistente.py::test_gabarito_cobre_todos_os_casos_com_funcoes_da_superficie` guarda
a regra: nenhum caso vazio e toda função listada declarada no assistente). Para dar conta do
gabarito, a etapa também declarou `consultar_pedido`, `consultar_lotes` e
`relatorio_pendencias_vencidas` além da lista original da issue #12 — desvio registrado na issue.
A avaliação ponta a ponta (#14) roda cada pergunta contra o modelo real e verifica as funções
esperadas no log.
