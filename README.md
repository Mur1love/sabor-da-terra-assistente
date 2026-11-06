# Sabor da Terra — Assistente Inteligente para Gestão de Cooperativa Agrícola

> Projeto intermediário da disciplina de **IA Generativa e Agentes**
> Universidade de Pernambuco (Campus Garanhuns) × **Sauter Tecnologia** — Novembro de 2026

**O que é:** um assistente de IA conversacional (texto, em português) que atua como apoio à operação da **Cooperativa dos Produtores Rurais Sabor da Terra**, cooperativa fictícia do Agreste Meridional de Pernambuco, resolvendo três gargalos:

| # | Gargalo | O que o assistente faz |
|---|---------|------------------------|
| 1 | **Triagem de pedidos** | Interpreta pedidos em linguagem natural coloquial (e-mail, WhatsApp, formulário web), extrai produtos/quantidades/prazos/comprador, classifica urgência e sinaliza problemas (fora de safra, acima da capacidade) |
| 2 | **Consulta documental** | Responde perguntas sobre certificações, rastreabilidade, sazonalidade e contratos **citando o documento de origem** — nada de resposta sem fundamento |
| 3 | **Comunicação com produtores** | Gera resumos personalizados (vendas, pendências, alocações) e notificações de novos pedidos por produtor |

## Regras do jogo (requisitos funcionais)

- Interface **conversacional** por texto para a equipe da cooperativa.
- Entende **português coloquial**: abreviações, erros de digitação, informação implícita.
- Toda resposta documental **indica de qual documento veio**.
- Gera **relatórios e notificações de forma autônoma** quando solicitado.
- Mantém o **contexto da conversa** durante a sessão.
- Quando **não souber a resposta**, diz claramente — **sem inventar**.

## Entregáveis e datas

| Data | Evento |
|------|--------|
| 05/11/2026 | Divulgação da formação dos grupos |
| **19/11/2026** | **Entrega obrigatória da arquitetura** — modificações após esta data são desconsideradas |
| 20–21/11/2026 | Apresentação e demonstração do protótipo funcional |

Entregas finais: **(1)** protótipo funcional com **demonstração ao vivo**; **(2)** apresentação de **10 minutos** explicando decisões técnicas, alternativas consideradas e limitações.

## Estrutura do repositório

```
sabor-da-terra-assistente/
├── README.md                ← este arquivo
├── INTEGRANTES.md           ← equipe do projeto
├── docs/
│   ├── 01-documento-base.md ← interpretação completa do PDF do projeto
│   └── 02-dataset.md        ← inventário detalhado dos dados + armadilhas
└── data/                    ← base de dados da cooperativa (cópia de trabalho)
    ├── LEIA-ME.txt
    ├── produtores.csv · pedidos.json · financeiro.csv
    ├── sazonalidade.csv · tabela_precos_outubro_2026.csv · lotes.csv
    ├── certificacoes/ (12 docs) · contratos/ (3) · fichas_tecnicas/ (5)
```

## Documentação

- **`docs/01-documento-base.md`** — tudo que o documento oficial define: cenário, problema, desafios, requisitos, entregáveis e datas.
- **`docs/02-dataset.md`** — descrição campo a campo dos 8 grupos de dados e das **armadilhas propositalmente escondidas** neles (certificação vencida, produtor sem registro sanitário, pedidos que não são pedidos de compra, pagamentos atrasados…).

## Dados

A base completa está em **`data/`** (cópia não-modificada do material fornecido em `~/Downloads/Facepe`). Todo o conteúdo é **fictício e simulado para avaliação** — porém contém CPFs, chaves PIX e dados bancários simulados: **mantenha este repositório PRIVADO**.

## Equipe

Ver **[INTEGRANTES.md](INTEGRANTES.md)**.
