# Etapa 18 — Apresentação e demonstração final

## 1. Objetivo

Apresentar as decisões técnicas, a arquitetura proposta para Google Cloud, as alternativas consideradas, os resultados e as limitações do assistente Sabor da Terra, acompanhados de demonstração ao vivo.

**Data:** 20–21/11/2026  
**Duração:** 10 minutos  
**Versão:** `v1.0-entrega`  
**Slides:** [INSERIR LINK DOS SLIDES]

## 2. Roteiro da apresentação

| Tempo | Slides | Conteúdo | Responsável |
|---|---|---|---|
| 0:00–1:15 | 1–2 | Introdução e arquitetura Google Cloud | Pessoa 1 |
| 1:15–2:45 | 3–4 | Decisões técnicas, alternativas e implantação | Pessoa 2 |
| 2:45–4:05 | 5–6 | Prevenção de alucinações e estimativa de custos | Pessoa 3 |
| 4:05–5:45 | 7–8 | Resultados, limitações e contingência | Pessoa 4 |
| 5:45–6:00 | 9 | Transição para demonstração | Pessoa 4 |
| 6:00–10:00 | — | Demonstração ao vivo | Equipe |

## 3. Decisões técnicas principais

- **Interface:** Streamlit pela rapidez de prototipação. Alternativa: Gradio. Produção proposta: Cloud Run.
- **Orquestração:** function calling direto, evitando abstrações desnecessárias. Alternativas: ADK e LangChain.
- **Triagem:** Gemini com saída JSON estruturada. Alternativas: regex, spaCy e Ollama.
- **Documentos:** RAG com citações. Produção proposta: Agent Search e Cloud Storage.
- **Dados:** pandas e SQLite no protótipo. Produção proposta: BigQuery.
- **Regras:** funções determinísticas em Python. Produção proposta: Workflows e Cloud Run functions.

A infraestrutura Google Cloud apresentada representa uma arquitetura proposta, não uma implantação concluída.

## 4. Roteiro da demonstração

### Caso 1 — Triagem com problemas

**Entrada:** PED-006 ou PED-007.

Demonstrar a interpretação do pedido, identificação de pendências, verificação das regras e resposta fundamentada.

### Caso 2 — Consulta documental

**Pergunta:** "Quais são os requisitos vigentes para comercialização de mel orgânico?"

Verificar se a resposta apresenta referências documentais e evita afirmações sem fonte.

### Caso 3 — Anti-alucinação

**Pergunta:** "Rastreie o lote 2024-089."

Resultado esperado: informar que não existem dados suficientes para rastrear o lote, sem inventar informações.

### Caso 4 — Resumo de produtor

**Entrada:** PED-012.

Demonstrar o acesso a dados estruturados e a elaboração de um resumo fundamentado.

### Caso 5 — Continuidade de contexto

Fazer uma pergunta de seguimento sobre o pedido anterior, sem repetir seu identificador.

Demonstrar a capacidade de preservar o contexto da conversa e reconhecer ambiguidades quando necessário.

**Observação:** as entradas e saídas devem ser previamente conferidas com `tests/gabarito/`.

## 5. Resultados da avaliação

Rodada 3 — 19/11/2026.

- Acerto geral: 89,0% (446/501).
- Citações documentais válidas: 13/13.
- Casos anti-alucinação: 5/5.
- Triagem: 89,3%.
- Consulta documental: 91,2%.
- Produtores: 84,0%.
- Continuidade de contexto: 66,7%.

Fonte: `docs/05-avaliacao.md`.

## 6. Limitações

- Dados simulados e ausência de implantação real.
- Dificuldades de encadeamento de funções.
- Limitações na continuidade de contexto.
- Recuperação documental ainda sujeita a falhas.
- Avaliação automatizada sem revisão humana integral.
- Estimativa de custos parcial, sem todos os serviços de produção.

## 7. Plano de contingência

Em caso de indisponibilidade da API, internet ou problemas de execução, utilizar o modo fixture preparado na Etapa 17.

Se a demonstração não puder continuar, apresentar o vídeo de backup da versão congelada, informando à banca a mudança de modalidade.

## 8. Checklist do dia

### Ambiente

- [ ] Confirmar versão `v1.0-entrega` — Responsável: Pessoa 1
- [ ] Validar execução do Streamlit — Responsável: Pessoa 1
- [ ] Verificar internet — Responsável: Pessoa 1
- [ ] Verificar chave e cota Gemini — Responsável: Pessoa 2
- [ ] Confirmar data de referência — Responsável: Pessoa 2

### Demonstração

- [ ] Conferir entradas com o gabarito — Responsável: Pessoa 2
- [ ] Testar cinco interações — Responsável: Pessoa 3
- [ ] Verificar modo fixture — Responsável: Pessoa 3
- [ ] Abrir vídeo de backup — Responsável: Pessoa 3

### Apresentação

- [ ] Abrir slides e conferir diagramas — Responsável: Pessoa 4
- [ ] Confirmar exibição dos logos UPE e Sauter — Responsável: Pessoa 4
- [ ] Realizar ensaio 1 cronometrado — Responsável: Equipe
- [ ] Realizar ensaio 2 na máquina da apresentação — Responsável: Equipe
- [ ] Confirmar duração máxima de 10 minutos — Responsável: Equipe

## 9. Ensaios

| Ensaio | Duração | Ambiente | Resultado |
|---|---|---|---|
| 1 | Pendente | Ambiente de desenvolvimento | Pendente |
| 2 | Pendente | Máquina da apresentação | Pendente |

Os resultados devem ser preenchidos após cada execução.

## 10. Evidências de entrega

- Slides finalizados.
- Roteiro de apresentação e demonstração.
- Checklist com responsáveis.
- Dois ensaios cronometrados.
- Versão congelada do protótipo.
- Plano de contingência preparado.

**Referências:** `docs/04-arquitetura.md`, `docs/05-avaliacao.md`, `tests/gabarito/` e Etapa 17.

## Slides da apresentação

[Visualizar apresentação](slides/Sabor_da_Terra.pptx)