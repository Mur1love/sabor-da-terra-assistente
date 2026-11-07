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
