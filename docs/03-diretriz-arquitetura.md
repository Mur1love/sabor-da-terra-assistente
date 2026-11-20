# 03 — Diretriz de Arquitetura: desenho focado no ecossistema Google

> **Diretriz permanente do projeto.** Vale para toda e qualquer decisão de arquitetura — desenho, revisão, issues e apresentação.
>
> Motivo de existir agora: a arquitetura é entregável **obrigatório em 19/11/2026** e, a partir dessa data, qualquer modificação no projeto é **desconsiderada** (ver `01-documento-base.md` §7–8). A diretriz precisa estar registrada antes da sprint de arquitetura começar.

## Contexto e justificativa da diretriz

- A **Sauter Tecnologia**, empresa parceira do desafio, é **um dos principais parceiros Google Cloud no Brasil** (Partner of the Year pelo 2º ano), e o projeto aplica o conteúdo das aulas de **IA Generativa e Agentes e Google Cloud** (`01-documento-base.md` §1).
- O entregável de arquitetura alimenta a **apresentação de 10 minutos**, que exige explicar **decisões técnicas, alternativas consideradas e limitações** (`01-documento-base.md` §7).
- Desenhar a arquitetura já no contexto Google mantém o projeto coerente com a identidade técnica da parceira e produz matéria-prima direta para a apresentação.

## O princípio

1. **Toda decisão de arquitetura é tomada pensando no ecossistema Google** — Google Cloud, Vertex AI, Gemini e afins. Nenhum componente entra no desenho sem responder: *"como isso executaria no Google Cloud?"*
2. **O protótipo executa local, sem serviços do Google Cloud.** Isso é uma decisão prática da fase de protótipo — custo zero, zero conta externa, demo reproduzível — e **não invalida a diretriz seguinte**.
3. **O desenho da arquitetura (entregável de 19/11) deve, para cada componente, mencionar o serviço Google Cloud correspondente, com justificativa da decisão:**
   - qual serviço Google Cloud exerceria esse papel em produção;
   - **justificativa** da escolha (por que este serviço e não outro);
   - **alternativa considerada** — dentro e fora do ecossistema Google — e o motivo de não segui-la.

## Como aplicar

- **Documento de arquitetura:** cada componente (triagem de pedidos, RAG documental, comunicação com produtores, orquestração, dados, interface) em uma tabela no formato do exemplo abaixo.
- **Diagrama:** desenhado no mundo Google (visão de produção), com a execução local do protótipo indicada como simplificação da fase de demonstração.
- **Issues de arquitetura:** seguem o template `.github/ISSUE_TEMPLATE/etapa-do-desafio.md` e citam esta diretriz.

## Exemplo ilustrativo do mapeamento

> Formato esperado no documento de arquitetura. A decisão real por componente não é feita aqui — é feita na etapa de arquitetura.

| Componente no protótipo (local) | Serviço Google Cloud (produção) | Justificativa | Alternativa considerada |
|---|---|---|---|
| Triagem/extração de pedidos em linguagem natural | Gemini via Vertex AI | Modelo gerenciado, forte em PT-BR coloquial, sem operar Infra de modelo na demo | Modelos hospedados localmente (ex. Ollama) — requeria infraestrutura de GPU e manutenção fora do escopo do protótipo |

---

## Estratégia de custo — API do Gemini (free tier)

> Política de execução do protótipo. Pesquisada e confirmada em out–nov/2026; **os limites do free tier mudam com frequência** — antes de qualquer decisão, confirmar os números vigentes no [AI Studio](https://aistudio.google.com).

### Divisão de trabalho entre modelos

O princípio é: **volume barato no Flash-Lite, qualidade no Flash, e nada de quota desperdiçada em teste**.

| Papel no assistente | Modelo no protótipo | Por quê |
|---|---|---|
| Triagem, classificação (pedido vs cotação vs notificação), extração estruturada | **Gemini Flash-Lite** | Free tier com folga: ~15 RPM / **500 pedidos/dia** — aguenta o volume do assistente e os testes |
| Resposta final conversacional (RAG, relatórios, comunicação com produtores) | **Gemini Flash** (linha nova) | Free tier apertado (~5 RPM / **20 pedidos/dia**) — reservar para o que importa e para a demo |
| Embeddings do RAG | **Gemini Embedding** | ~1.000 pedidos/dia — indexar os ~35 documentos do dataset é trivial |

### Regras de desenvolvimento

1. **Não gastar cota do Flash com iteração de prompt.** Testes de triagem/extração usam Flash-Lite; regressões repetem execução com **fixtures gravadas** (respostas mockadas), não com chamadas reais.
2. **Dados no free tier podem ser usados para treinar os produtos do Google.** Aceitável aqui porque o dataset é fictício — **nunca enviar dado real de pessoa** pelo free tier.
3. **Chave de API restrita, sempre.** Desde jun/2026 o endpoint recusa chaves sem restrição; as chaves criadas no AI Studio já saem restritas por padrão — não remover a restrição.
4. **Confirmar limites no próprio projeto** (AI Studio → Usage and billing) antes da semana de ajuste fino — os números acima não são garantidos e variam por projeto/modelo.

### Limites confirmados no projeto

> Consulta em **AI Studio → Rate limits** (https://aistudio.google.com/rate-limit),
> projeto `sabor-da-terra`, nível gratuito, em **10/11/2026**.
> Limites são **por projeto**, não por chave, e o RPD reseta à meia-noite do
> horário do Pacífico (fonte: https://ai.google.dev/gemini-api/docs/rate-limits).
> Reconfirmar antes da semana de ajuste fino (#14).

| Modelo | RPM | TPM | RPD | Observação |
|---|---|---|---|---|
| Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`) | 15 | 250K | 500 | Confirma a estimativa da tabela acima |
| Gemini 3.8 Flash (`gemini-3.8-flash`) | 5 | 250K | 20 | Confirma a estimativa da tabela acima; em 10/11 estava com 503 intermitente (alta demanda) |
| Gemini Embedding (`gemini-embedding-001`) | 100 | 30K | 1.000 | Indexar os ~20 documentos do dataset é trivial |
| Gemini Embedding 2 (`gemini-embedding-2`) | 100 | 30K | 1.000 | Novo multimodal (abr/2026); **não usado no protótipo** (corpus só de texto) |

> Com esses limites, o protótipo roda folgado no free tier: a triagem esbarra em
> 500 pedidos/dia do Flash-Lite, e o Flash de 20/dia exige o modo fixture em
> testes e iteração de prompts (regra 1 acima) — a demo cabe no RPD com folga,
> mas não desperdice chamadas.

### Plano B e vias que NÃO contar no plano

- **Plano B de contingência (decisão registrada na etapa #17, 19/11/2026):** ativar billing com prepay mínimo **(US$ 5)** → Tier 1 pago: limites maiores, sem uso para treinar. Uma demo inteira de respostas em Flash a preço pago custa centavos — o $5 é seguro de apresentação, não custo esperado. A chave reserva em outro projeto **não** foi adotada: um projeto só, com o fallback da composição já configurado (`GEMINI_MODELO_RESPOSTA_FALLBACK` → Flash-Lite) e, por baixo de tudo, o modo `fixture` do roteiro da demo (`scripts/gravar_roteiro_demo.py`), que reproduz a apresentação sem **nenhuma** chamada de API.
- **Não contar com créditos de estudante:** o free trial de US$ 300 do Google Cloud **não paga Gemini API** (desde mar/2026); o plano de estudante do Google AI dá limites no app/UI, **não cota de API**; créditos educacionais vêm pelo professor e são bônus, não baseline.
