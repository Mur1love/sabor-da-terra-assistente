# 05 — Avaliação ponta a ponta (etapa 14)

> O gabarito da #6 (`tests/gabarito/`, 37 casos e 501 critérios) rodado contra o
> assistente integrado — roteamento, ferramentas, composição e a interface de
> fontes da #13 —, medido por desafio e por requisito funcional do `docs/01` §6.
> Os números alimentam o slide de "resultados e limitações" (#18) e o
> documento de arquitetura (#16).

## Resultados

> **Rodada 3** (19/11/2026, prompt do assistente 1.5.0, juiz v1.0.0), comparada
> com as rodadas 1 (18/11, prompt 1.2.0) e 2 (18–19/11, prompt 1.4.0).
> Roteamento, composição e juiz rodaram no **Flash-Lite**: a cota do Flash
> (20/dia) não comporta uma rodada. Detalhe de cada turno e de cada critério em
> `docs/avaliacao/`.

### Critérios de aceite da #14

| Critério | Resultado (rodada 3) | Situação |
|---|---|---|
| Gabarito com um comando (`pytest tests/test_gabarito.py`) | Roda offline, sem cota: 14 dos 37 casos e 3 das 5 variações aprovados; as 25 reprovações ficam como falhas conhecidas, cada uma com a causa | ✅ |
| 100% dos casos de anti-alucinação | 5/5 | ✅ |
| 100% das respostas documentais com citação válida | 13/13 | ✅ |
| ≥ 85% de acerto geral | **89,0%** (446/501) | ✅ |
| Demo cabe na cota, ou plano B decidido | Cabe: 16 de 500 no Flash-Lite e 6 de 20 no Flash por demo | ✅ |

### Evolução entre as rodadas

| | Rodada 1 | Rodada 2 | **Rodada 3** |
|---|---|---|---|
| Prompt do assistente | 1.2.0 | 1.4.0 | 1.5.0 |
| Casos avaliados | 35 de 37 (2 fora da conta por 503) | 37 de 37 | 37 de 37 |
| Acerto por critério | 81,8% (368/450) | 82,8% (415/501) | **89,0% (446/501)** |
| Casos aprovados | 6/35 (17,1%) | 10/37 (27,0%) | 14/37 (37,8%) |
| Funções esperadas chamadas | 13/35 | 21/37 | 22/37 |
| Critérios `nao_deve_conter` que ocorreram | 2 de 168 | 3 de 185 | 3 de 185 |
| Anti-alucinação aprovados | 3/5 | 4/5 | **5/5** |
| Respostas documentais com citação válida | 12/13 | 12/13 | **13/13** |

### Por desafio e por requisito funcional (rodada 3)

| Recorte | Avaliados | Acerto por critério | Casos aprovados | Rodada 2 (acerto) |
|---|---|---|---|---|
| Comunicação com produtores | 7 | 84,0% (79/94) | 2/7 | 84,0% |
| Consulta documental | 17 | 91,2% (166/182) | 6/17 | 84,6% |
| Triagem de pedidos | 13 | 89,3% (201/225) | 6/13 | 80,9% |
| RF2 — português coloquial | 15 | 90,3% (270/299) | 5/15 | 80,3% |
| RF3 — documental com fonte | 17 | 91,2% (166/182) | 6/17 | 84,6% |
| RF4 — relatórios e notificações | 4 | 83,7% (36/43) | 2/4 | 83,7% |
| RF5 — contexto na sessão | 3 | 66,7% (14/21) | 0/3 | 66,7% |
| RF6 — não inventar | 5 | 100% (32/32) | 5/5 | 96,9% |

### O que mudou da rodada 2 para a 3

A rodada 2 mostrou que as falhas da triagem vinham do próprio assistente, não
do modelo: o turno parava antes de terminar as consultas e a regra de
composição mandava deixar detalhes de fora. Três correções (prompt 1.5.0):

1. **Teto de chamadas por turno de 8 para 24** (`MAX_CHAMADAS_POR_TURNO`). Com
   uma verificação de conformidade por item, um pedido de 9 itens esgotava o
   teto: 5 dos 15 casos de triagem paravam exatamente em 8 chamadas. As funções
   depois da triagem são locais, sem LLM, então o teto maior não gasta cota.
2. **Próximos passos no resultado do `triar_pedido`.** A saída da triagem diz ao
   roteamento o que consultar em seguida: conformidade de cada item, preço e
   disponibilidade numa cotação, documentos numa notificação oficial. A
   orientação não chega ao compositor, que só vê dados.
3. **Regra de composição da triagem.** Antes ela pedia só o tipo e os itens, e
   a notificação da ADAGRO (`TRI-014`, sem itens) era respondida com uma linha.
   Agora entram também entrega, nota fiscal, pagamento, observações e, sem
   itens, o resumo do que a mensagem pede.
4. **Lacunas do RAG à vista.** Quando os documentos respondem só parte da
   pergunta, a resposta passa a dizer o que eles não cobrem e pede conferência
   caso a caso (`DOC-004`: "todos os produtores têm DAP/CAF?").

As mudanças valem só para turnos com triagem ou com resposta documental
direta. Os demais turnos ficaram idênticos à rodada 2 e foram reavaliados a
partir das gravações, sem custo.

### Robustez (5 variações coloquiais fora do gabarito)

89,5% de acerto (17/19) e 3/5 casos aprovados, igual à rodada 2 (nenhuma das
variações passa por triagem). As gírias e abreviações ("msm", "qm", "da pra")
foram entendidas em todos os casos. As duas reprovações não são de
entendimento: `ROB-003` omite a quantidade e a data de entrega do lote, e
`ROB-005` acerta a resposta (P015 inativo, P005 como alternativa), mas por
outra função. Arquivo: `docs/avaliacao/robustez-rodada-3.json`.

### Causa de cada falha (rodada 3)

| Causa | Casos | Exemplos |
|---|---|---|
| **Orquestração**: a função esperada não é chamada | 16 | `TRI-008`, `TRI-010`, `CERT-003`, `DOC-001`: resposta certa (todos os critérios), mas por outra função; `TRI-012`, `TRI-015`: mensagem de produtor sem `triar_pedido` |
| **Composição**: o dado estava no turno e a resposta omite | 5 | `TRI-007`, `TRI-013`: item opcional, volume do evento e restrição de produtor ficam de fora |
| **Recuperação**: o trecho certo não chega ao modelo | 2 | `DOC-002`, `DOC-006` (e parte do `DOC-003`) |
| **Contexto**: o segundo turno perde o que o primeiro estabeleceu | 2 | `CTX-001`, `CTX-002` |
| **Extração** (triagem) | 0 | |
| **Regra** (motor de regras) | 0 | |

As 25 falhas estão listadas com a causa em `tests/test_gabarito.py`
(`LIMITACOES_CONHECIDAS`). Nenhuma está no código determinístico: extração,
regras, cálculos e citações saem certos quando as funções são chamadas. Em 5
dos 16 casos de orquestração a resposta acertou todos os critérios e o caso
reprovou só porque a função usada não era a do gabarito.

### Teste de cota da demo

Roteiro da #18 (triagem do PED-006, consulta documental com citação,
continuidade de contexto, lote inexistente e resumo de produtora), medido por
papel em `docs/avaliacao/cota-demo.json`:

| Papel | Modelo | Por demo | Limite (`docs/03`) | Demos por dia | Pico por turno |
|---|---|---|---|---|---|
| Triagem e roteamento | Flash-Lite | 16 | 500/dia, 15 RPM | 31 | 5 |
| Resposta | Flash | 6 | 20/dia, 5 RPM | 3 | 2 |

A demo cabe na cota. O gargalo é o Flash: cabem **três** demos por dia, então
um ensaio completo no mesmo dia da apresentação já consome um terço. Para não
depender disso, a equipe pode preencher `GEMINI_MODELO_RESPOSTA_FALLBACK` com
o Flash-Lite: se a cota do Flash acabar, o turno continua no Flash-Lite.

### Consumo das rodadas

| Execução | Chamadas reais (Flash-Lite) |
|---|---|
| Rodada 1 (18/11) | 201 |
| Rodada 2 (18/11): 16 casos | 104 |
| Rodada 2 (19/11): 21 casos restantes, robustez e teste de cota | 155 |
| Rodada 3 (19/11): triagem e documentais diretos, robustez e teste de cota | 95 |

Respostas já gravadas são repetidas sem custo (cliente híbrido); só o que muda
vai à API. Em 19/11 o projeto usou 250 das 500 chamadas diárias do Flash-Lite.

## Limitações conhecidas

- **Encadeamento de funções.** Continua sendo a maior causa de falha (16 de
  25). Mensagens de produtor (`TRI-012`, `TRI-015`) não passam pela triagem, e
  pedidos que exigem cadastro, lotes e documentos ao mesmo tempo (`TRI-009`,
  `TRI-014`) ficam com parte das consultas por fazer.
- **Detalhes omitidos em pedidos longos.** Em pedidos com muitos itens e
  exigências (`TRI-007`, `TRI-013`), itens opcionais e dados do evento podem
  ficar de fora da resposta.
- **Contexto entre turnos (RF5).** Em 2 de 3 casos o segundo turno perde
  parte do que o primeiro estabeleceu; não foi corrigido nesta etapa.
- **Recuperação de contratos.** A busca documental não traz os contratos
  institucionais (PNAE) em `DOC-003` nem na notificação da ADAGRO (`TRI-014`),
  que responde que não os encontrou embora existam em `data/contratos/`.
- **Avaliação só no Flash-Lite.** A composição da demo usa o Flash, que não
  foi medido no gabarito por causa da cota. O resultado da demo tende a ser
  igual ou melhor, mas não está medido.
- **Juiz LLM.** Os vereditos são do Flash-Lite, com regras explícitas e a
  evidência de cada critério gravada, mas não foram revisados um a um por uma
  pessoa. No `TRI-014`, por exemplo, o juiz contou nomes e códigos de
  produtores como "dado pessoal exposto", embora a resposta não traga CPF,
  endereço nem dado bancário.
- **Lote inexistente na demo.** Ao não achar o `LOT-2024-089`, o assistente
  sugere o `LOT-2026-0089` e já mostra os dados dele. Está sinalizado ("não foi
  encontrado"), mas o roteiro da #18 deve deixar claro que é uma sugestão.

## Como a avaliação funciona

### O que roda

Cada caso do gabarito vira uma **sessão nova** do `Assistente` (o mesmo da
interface), com o relógio da sessão no dia do caso: a `data_recebimento` do
caso, senão a do pedido em `data/pedidos.json`, senão o dia da demo
(30/10/2026). Casos de contexto (`CTX-*`) rodam os dois turnos na mesma sessão.

### Três frentes de conferência

| Frente | Como | Reprova o caso quando |
|---|---|---|
| Funções | `Assistente.funcoes_do_turno`, somadas na conversa | falta alguma de `funcoes_esperadas` |
| Citações | fontes exibidas pela interface (`fontes_da_resposta`) e marcadores `[fonte: …]` do texto | arquivo inexistente em `data/`, arquivo citado que as funções não devolveram, ou turno de caso documental sem nenhuma fonte |
| Critérios | **juiz LLM** (Flash-Lite, temperatura 0, saída em JSON validada), um veredito por critério | algum `deve_conter` não atendido ou algum `nao_deve_conter` ocorrido |

O gabarito descreve critérios em linguagem natural ("Recusa em inventar
valores", "FIN-2026-013: R$ 4.500,00"); conferir por substring não funciona.
O juiz decide critério a critério só com o que o assistente entregou (resposta,
funções chamadas e fontes exibidas), com regras explícitas: paráfrase vale,
números/datas/códigos precisam bater exatamente, informação ausente é "não
atendido", na dúvida reprova. Prompt versionado em
`sabor_da_terra/prompts/avaliacao.py`. No desenho Google Cloud, este papel é do
**Vertex AI Gen AI Evaluation Service**.

### Definições das métricas

- **Acerto por critério:** critérios cumpridos ÷ critérios avaliados. Cumprir
  = item de `deve_conter` atendido, ou item de `nao_deve_conter` que **não**
  ocorreu. É a métrica do critério de aceite "≥ 85% de acerto geral".
- **Caso aprovado:** todos os critérios cumpridos **e** funções esperadas
  chamadas **e** citações válidas (quando o caso é documental). Mais rígida:
  um critério perdido em 14 reprova o caso inteiro.
- **Resposta documental:** caso do desafio "Consulta documental" que não é
  recusa (os de anti-alucinação podem — e devem — responder sem fonte).
- **Anti-alucinação (RF6):** `ANTI-001` (certificação internacional),
  `ANTI-002` (produto fora da base), `ANTI-003` (produtor inativo), `DOC-004`
  (reconhecer lacunas) e `DOC-005` (lote inexistente).
- **Fora da conta:** caso cujo turno fechou sem composição (cota ou API fora)
  não é acerto nem erro do assistente — é listado à parte e refeito.

### Requisito funcional de cada caso

| RF (docs/01 §6) | Casos |
|---|---|
| RF1 — interface conversacional por texto | todos |
| RF2 — português coloquial | `TRI-*` (as 15 mensagens como chegaram) e `ROB-*` |
| RF3 — documental com fonte | desafio "Consulta documental" |
| RF4 — relatórios e notificações | `PROD-*` |
| RF5 — contexto na sessão | casos multi-turno (`CTX-*`) |
| RF6 — não inventar | `ANTI-*`, `DOC-004`, `DOC-005` |

As regras estão em `sabor_da_terra/avaliacao/gabarito.py` (`requisitos_funcionais`).

## Reproduzir

```bash
pytest tests/test_gabarito.py                 # comando único: replay offline, sem cota
python -m scripts.avaliar_gabarito --relatorio  # tabelas da rodada salva
python -m scripts.avaliar_gabarito --rodada 2   # rodada real (grava só o que falta)
python -m scripts.simular_demo                  # teste de cota da demo (#18)
```

Os resultados de cada rodada ficam em `docs/avaliacao/` (`rodada-N.json`,
`robustez-rodada-N.json`, `cota-demo.json`), com a resposta de cada turno, as
funções chamadas, as fontes e o veredito do juiz para cada critério.
