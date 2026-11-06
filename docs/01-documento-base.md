# 01 — Documento Base: Projeto Intermediário "Assistente Inteligente para Gestão de Cooperativa Agrícola"

> Fonte: PDF *"Projeto Intermediário — Sabor da Terra"* (Sauter Tecnologia e Serviços Ltda, Novembro/2026).
> Este arquivo é a interpretação fiel e integral do documento ofical — é a **fonte de verdade do escopo**.
> O documento original é **confidencial**: nada dele deve ser colado em repositório público, issues ou apresentações de terceiros.

---

## 1. Identificação

| Item | Valor |
|------|-------|
| Projeto | Intermediário da disciplina de **IA Generativa e Agentes** |
| Parceria | **Universidade de Pernambuco (Campus Garanhuns)** × **Sauter Tecnologia** |
| Data do documento | Novembro de 2026 |
| Produto | Assistente de IA conversacional para a **Cooperativa Sabor da Terra** (cooperativa fictícia) |
| Confidencialidade | Material do programa; uso interno; reprodução sem permissão da Sauter é proibida |

**Quem é a Sauter (contexto do documento):** consultoria de tecnologia com foco em IA, transformação digital, Cloud Computing, Engenharia de Dados, Machine Learning e DevOps. Sede em São Paulo e operação em **Garanhuns (PE)**; um dos principais parceiros Google Cloud no Brasil (Partner of the Year pelo 2º ano); possui Cloud Operation Center com suporte 24/7. Parcerias: Google Cloud, Wibx, Databricks, Commvault.

---

## 2. Resumo Executivo (do documento)

Equipes recebem um conjunto de **dados simulados** da Cooperativa Sabor da Terra e devem entregar um **protótipo funcional com demonstração ao vivo**, aplicando o conhecimento das aulas de **Engenharia de Prompt, RAG, Agentes e Google Cloud**.

---

## 3. Cenário (narrativa)

A **Sabor da Terra** reúne **180 pequenos produtores rurais** em **12 municípios** do interior de Pernambuco. Comercializa frutas, hortaliças, queijos artesanais e mel para **restaurantes, mercados e programas de compra governamental (PNAE, PAA)**. Nos últimos dois anos a **demanda cresceu 40%**, mas a operação continua **artesanal**.

> **Nota dataset:** a narrativa cita 180 produtores/12 municípios, mas o material entregue contém **18 produtores cadastrados (P001–P018)** em 7 municípios. O dataset é uma **amostra representativa** para o protótipo — o sistema deve funcionar com os dados fornecidos.

---

## 4. O Problema

São **três dores simultâneas** na operação:

### 4.1 Pedidos chegam por canais e formatos imprevisíveis
- Entre **60 e 100 pedidos de compra por dia**, via **e-mail, formulário web e mensagens de texto** (WhatsApp).
- Raramente estruturados — ex.: restaurante escreve *"preciso de 30kg de queijo coalho e umas caixas de goiaba pra sexta"*.
- Hoje: **Dona Lúcia e Seu Antônio** fazem a triagem manualmente e levam **o dia inteiro**; erros de alocação geram **perdas de perecíveis** e clientes insatisfeitos.

### 4.2 O acervo documental é grande e a resposta é lenta
- Centenas de documentos: **certificações orgânicas por produtor, laudos sanitários, fichas técnicas, tabelas de sazonalidade, contratos, relatórios de inspeção sanitária (ADAGRO)**.
- Perguntas típicas de compradores institucionais: *"quais produtores têm certificação orgânica vigente para mel?"* e *"qual é a origem e rastreabilidade do queijo do lote 2024-089?"* — hoje exigem **horas** vasculhando pastas físicas e digitais.

### 4.3 Produtores ficam cegos
- Querem saber **quanto venderam no mês**, **pagamentos pendentes** e ser **avisados de pedidos** dos seus produtos.
- Hoje isso é repassado **por ligação telefônica, um a um**.

---

## 5. O Desafio

Construir **um assistente de IA** que resolva os três gargalos (o documento os enumera como 4.1–4.3 do desafio, espelhando as dores):

### Desafio A — Interpretação e Triagem de Pedidos
1. Receber pedidos em **linguagem natural**, mesmo **incompletos ou ambíguos**.
2. **Extrair** informação relevante: produtos, quantidades, prazos, dados do comprador.
3. **Classificar** (urgência, tipo) e **organizar de forma estruturada**.
4. **Sinalizar** pedidos urgentes ou com problema: produto **fora de safra**, quantidade **acima da capacidade** de atendimento.

### Desafio B — Consulta Inteligente à Base Documental
1. Atender **compradores, auditores e a equipe** com perguntas sobre **certificações, rastreabilidade, sazonalidade e histórico de lotes**.
2. Respostas **fundamentadas nos documentos reais** — "não em suposições".
3. **Citar as fontes** de cada informação.

### Desafio C — Comunicação com Produtores
1. Gerar **resumos personalizados por produtor**: vendas, pedidos alocados, pendências financeiras.
2. Redigir **notificações claras** de novos pedidos para seus produtos.

---

## 6. Requisitos Funcionais (transcrição integral)

1. O assistente deve funcionar como **interface conversacional**: o usuário (equipe da cooperativa) interage por **texto**.
2. Deve processar pedidos escritos em **português coloquial**, com **abreviações, erros de digitação e informações implícitas**.
3. Deve responder perguntas sobre o acervo documental **com precisão, indicando de qual documento veio a informação**.
4. Deve gerar **relatórios e notificações de forma autônoma** quando solicitado.
5. Deve **manter o contexto da conversa** ao longo de uma sessão.
6. Quando **não souber a resposta** ou **não encontrar a informação nos documentos**, deve **dizer claramente, sem inventar**.

> O requisito 6 é o critério de **anti-alucinação** — provavelmente será avaliado na demo (ver seção 10).

---

## 7. Entregáveis

| # | Entregável | Detalhe |
|---|-----------|---------|
| 1 | **Protótipo funcional** | Com **demonstração ao vivo** |
| 2 | **Apresentação de 10 minutos** | Explicar **decisões técnicas**: por que cada abordagem, **quais alternativas consideraram**, **limitações** do sistema |
| 3 | **Arquitetura** | Entrega **obrigatória em 19/11/2026**; qualquer modificação no projeto **a partir dessa data será desconsiderada** |

---

## 8. Datas Importantes

| Data | Evento |
|------|--------|
| **05/11/2026** | Divulgação da formação dos grupos |
| **19/11/2026** | Entrega obrigatória da **arquitetura do projeto** *(o PDF possui um erro de digitação: "19/111/2026")* |
| **20/11/2026 a 21/11/2026** | Apresentação e demonstração do **protótipo funcional** |

**Consequência prática:** tudo que for implementado precisa estar **congelado e documentado até 19/11**; nos dias 20–21 só demonstração.

---

## 9. Dados Fornecidos (referência)

O documento remete ao dataset simulado (detalhado em **`02-dataset.md`**):

| Arquivo/Pasta | Conteúdo |
|---------------|----------|
| `produtores.csv` | Cadastro dos **18 produtores** com produtos e certificações |
| `pedidos.json` | **15 pedidos** recebidos em linguagem natural variada |
| `financeiro.csv` | Histórico de transações (set–out/2026) |
| `sazonalidade.csv` | Calendário de disponibilidade por mês |
| `tabela_precos_outubro_2026.csv` | Preços convencional/orgânico |
| `lotes.csv` | Rastreabilidade dos últimos lotes |
| `certificacoes/` | Certificações orgânicas, laudos e inspeção ADAGRO |
| `contratos/` | Mercado Bom Preço, PNAE e Restaurante Raízes |
| `fichas_tecnicas/` | Queijo coalho, mel, goiaba, hortaliças, tubérculos |

---

## 10. Observações, inconsistências e sinais de avaliação

Fatos observados ao cruzar o documento com o dataset — úteis para a apresentação e para a arquitetura:

1. **180 vs 18 produtores e 60–100 vs 15 pedidos:** o PDF descreve a cooperativa "em escala"; o dataset entregue é uma **amostra** (18 produtores, 15 pedidos entre 28 e 30/10/2026). Assumir a amostra como "a realidade do protótipo".
2. **Nem todo "pedido" é pedido de compra:** o `pedidos.json` mistura **compras, cotações/consultas de prospecção, mensagens de produtores e notificação oficial (ADAGRO)** — a triagem precisa **classificar tipos**, não apenas extrair produtos. (Detalhado em `02-dataset.md`.)
3. **O texto pede explicitamente "citar fontes" e "sem inventar":** são os requisitos de **RAG com referências e anti-hallucination** — candidatos a critério de avaliação na demo (perguntas sobre certificação vigente e rastreabilidade de lote aparecem no próprio PDF).
4. **Título/tema do projeto assume interface textual:** nada no documento exige canais reais (e-mail/WhatsApp); os canais aparecem só como **conteúdo do dataset**.
5. **"Pedidos urgentes ou com problemas devem ser sinalizados":** a capacidade de **cruzar pedidos com sazonalidade, capacidades e certificações** está no enunciado como requisito, não como extra.
6. **Data com erro de digitação** no PDF ("19/111/2026") — comparar com o calendário oficial da disciplina em caso de dúvida (tratamos como **19/11/2026**).
