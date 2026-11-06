# 02 — Dataset: Cooperativa Sabor da Terra (dados operacionais)

> **Origem:** material fornecido para o projeto (`~/Downloads/Facepe`), copiado **sem alterações** para `data/` neste repositório. O material original não deve ser modificado.
> **Nível de sigilo:** os dados são **fictícios**, mas usam CPF, PIX e dados bancários realistas — **repositório privado obrigatório**.
> Este arquivo é o **mapa do dataset**: o que existe, onde está, e as armadilhas propositalmente escondidas nele.

---

## 1. Visão geral

| Local | Conteúdo | Volume |
|-------|----------|--------|
| `data/produtores.csv` | Cadastro dos produtores (produtos, certificações, dados bancários) | 18 produtores (P001–P018) |
| `data/pedidos.json` | Pedidos, consultas e notificações recebidos em linguagem natural | 15 registros (28–30/10/2026) |
| `data/financeiro.csv` | Histórico de transações set–out/2026 | 30 transações |
| `data/sazonalidade.csv` | Disponibilidade por produto × mês | 50 produtos × 12 meses |
| `data/tabela_precos_outubro_2026.csv` | Preços convencional/orgânico + atacado | 52 produtos |
| `data/lotes.csv` | Rastreabilidade dos últimos lotes | 20 lotes (LOT-2026-0089…0108) |
| `data/certificacoes/` | Certificados orgânicos, laudos sanitários, inspeção ADAGRO | 12 arquivos |
| `data/contratos/` | Contratos com os 3 principais compradores | 3 arquivos |
| `data/fichas_tecnicas/` | Fichas técnicas dos principais produtos | 5 arquivos |
| `data/LEIA-ME.txt` | Descrição oficial da estrutura do material | — |

Afastamento da narrativa do PDF: o texto cita 180 produtores e 60–100 pedidos/dia; o dataset é uma **amostra representativa** (18 produtores; 15 pedidos em 3 dias). Ver `01-documento-base.md` §10.

---

## 2. `produtores.csv` — 18 produtores

**Campos:** `id, nome_completo, cpf, data_nascimento, telefone, email, endereco, municipio, produtos, certificacao_organica, validade_certificacao, chave_pix, banco, agencia, conta_corrente, status`.

**Fatos relevantes:**

- **Municípios:** Garanhuns, Brejão, Caetés, Jucati, Lajedo, Bom Conselho, Águas Belas (7 — a narrativa cita 12).
- **Certificação orgânica:** 9 produtores → **P001** (Garanhuns, goiaba/acerola/manga), **P002** (Brejão, mel/jandaíra/própolis), **P004** (Jucati, hortaliças folhosas), **P007** (Lajedo, queijo), **P008** (Águas Belas, mel/geleias — **VENCIDA**, ver §7), **P009** (Garanhuns, folhosas), **P012** (Garanhuns, frutas/hortaliças), **P014** (Garanhuns, berries — morango/amora/mirtilo/framboesa), **P018** (Águas Belas, mel/cera/pólen).
- Validade vigente mais próxima: **P004 → 01/12/2026** (ainda válida durante todo o prazo do projeto).
- **Sem** certificação: P003, P005, P006, P010, P011, P013, P016, P017.
- **P015 (Geraldo Barbosa) está `inativo`** (macaxeira/feijão/milho/fava).
- **P017** (frango/ovos caipira, Garanhuns) — sem SIE, ver §7.
- Campos bancários e `chave_pix` por produtor: usados na comunicação do Desafio C (pagamentos).

---

## 3. `pedidos.json` — 15 registros (28–30/10/2026)

**Campos:** `id, data_recebimento, canal, remetente, comprador, mensagem_original, status`. Canais presentes: `email`, `formulario_web`, `whatsapp`. Todos `status: "pendente"`.

⚠️ **Nem tudo aqui é pedido de compra.** Tipologia dos 15 registros:

| ID | Remetente | Tipo real | Observações |
|----|-----------|-----------|-------------|
| PED-001 | Restaurante Raízes (Carlos) | Compra | Para sexta 01/nov; queijo 30kg, manteiga 10kg, mel silvestre 5kg, coentro 20 maços, cebolinha 10, ricota 5kg "se tiver" |
| PED-002 | Mercado Bom Preço | Compra semanal | Estruturado; entrega terça 04/nov; NF com CNPJ; entrega no CD |
| PED-003 | Chef Amanda — Bistrô Sertão Gourmet | Compra urgente | Coloquial e ambíguo: "daquele queijo mais artesanal da última vez" 15kg; mel de jandaíra 3kg (exclusivo P002); para o dia seguinte, PIX na hora |
| PED-004 | Prefeitura Garanhuns — **PNAE** | Pedido oficial (contrato 045/2026) | 9 itens, mel silvestre **"com certificação orgânica" obrigatória**; exigências de NF/certificação |
| PED-005 | Dona Cremilda — Lanchonete da Feira | Compra informal | "o de sempre" (sem especificar): queijo 10kg, manteiga 5kg |
| PED-006 | Rede SuperBom Atacado | Compra **URGENTE** | "HOJE (29/10)": queijo 200kg + manteiga 50kg + mel silvestre **orgânico** 40kg + goiaba 300kg — volume e prazo extremos |
| PED-007 | Hotel Fazenda Serra Negra | Pedido + cotação | Evento 08/nov (120 convidados); inclui **cajá "se tiver"** (safra só nov–jan), frango/ovos caipira |
| PED-008 | Sorveteria Tropical (Marcos) | **Consulta** de prospecção | 50kg/semana de morango e amora, **exige orgânico**; pede tabela de preços |
| PED-009 | Hospital São Francisco | **Cotação** | Requisitos duros: certificação orgânica, laudo sanitário, rastreabilidade completa, fichas técnicas, dados CAF dos produtores |
| PED-010 | Feira Orgânica do Recife (João Pedro) | **Consulta** | Quer lista completa de produtos orgânicos, produtores, validades e preços — resposta puramente documental |
| PED-011 | Tropical Fruits Exportadora | **Consulta** em **inglês** | Exportação UE: manga/goiaba/maracujá orgânicos; pede certificação *international equivalent*, fitossanitários, dados bancários |
| PED-012 | Maria das Graças (**produtora P001**) | Mensagem de **produtor** | Quanto vendeu no mês; pagamento do Mercado Bom Preço de setembro caiu? |
| PED-013 | SESC Garanhuns | **Cotação** grande | Colônia de férias jan/2027; exige orçamento detalhado e pergunta se **todos têm DAP/CAF ativa** |
| PED-014 | **ADAGRO** | **Notificação oficial** | Inspeção em 11–12/11/2026; lista de documentos a disponibilizar; risco de suspensão do SIE |
| PED-015 | Cícero (**produtor P003**) | Oferta de **produtor** | 200kg de queijo prontos; pede aviso de pedidos "até amanhã"; propõe cadastro de novo produtor (Sebastião) |

**Uso do artefato:** mensagens 8–11 são consultas (não geram alocação), 12 e 15 partem de produtores (Desafio C + ações fora do escopo dos dados), 14 é órgão fiscalizador — triagem precisa **classificar tipo antes de extrair itens**.

---

## 4. `financeiro.csv` — 30 transações (set–out/2026)

**Campos:** `id_transacao, data, produtor_id, produtor_nome, produtor_cpf, comprador, tipo, produto, quantidade_kg, valor_unitario, valor_total, forma_pagamento, status_pagamento, data_vencimento, data_pagamento, chave_pix_deposito, observacao`.

**Fatos relevantes:**

- Formas de pagamento: `pix`, `boleto 30 dias`, `empenho 45 dias` (PNAE/SESC, com nº de empenho na observação), `transferência`.
- **Pendências antigas ainda "pendente"**: FIN-005/006/007 (vencidas em 23/10 — empenhos da PNAE), FIN-013/014 (**"ATRASADO - cobrar"**, vencidas 18/10 — SuperBom, produtor P003), FIN-023 (vence 05/11), FIN-024/025 (10/11), FIN-027 (30/11), FIN-030 (09/12).
- FIN-008/009 pagas **com 2 dias de atraso** (observação no registro).
- Preço por dúzia nos ovos (FIN-019 anota "Preço por dúzia" no campo `quantidade_kg` = 40).

---

## 5. `sazonalidade.csv` — 50 produtos × 12 meses

**Níveis:** `alta | media | baixa | nenhuma` + observação por linha.

**Fatos relevantes (out–nov/2026):**

- **Alta em out/nov:** goiaba paluma, banana prata (ano todo), acerola, coco, folhosas (alface, coentro, cebolinha, rúcula, espinafre, couve, hortelã, manjericão), tomate, pimentão, pepino, queijos/tubérculos/processados, frango (~80kg/sem) e ovos (~120 dz/sem).
- **Cruza com pedidos:** manga `media` em out (safra out–mar; PED-011 pede 500kg/mês); **cajá `baixa` em nov** (PED-007); mel silvestre `media` em out (florada abr–jun); morango/amora `media` (PED-008).
- **`nenhuma` em nov:** umbu, mirtilo, framboesa; **cajá** entra em `baixa` (safra curta nov–jan).

---

## 6. `tabela_precos_outubro_2026.csv` — 52 itens

**Campos:** `produto, unidade, preco_convencional, preco_organico, desconto_atacado_pct, volume_minimo_atacado_kg, observacao`.

**Fatos relevantes:**

- Muitos itens têm orgânico `n/d` (banana, maracujá, tubérculos etc.) — "sem produtor orgânico".
- Itens **exclusivos** anotados na observação: mel de jandaíra e própolis (P002), pólen e cera (P018), rapadura/açúcar/melado (P016), tomate cereja (P004), geleia/doce de goiaba (P008), iogurte (P011, "sem SIE para revenda").
- **Frango caipira:** observação "ATENÇÃO: P017 sem SIE - venda direta apenas".
- Desconto de atacado só vale acima do volume mínimo (ex.: queijo coalho 5% >100kg; goiaba 10% >100kg).

---

## 7. `certificacoes/` — 12 documentos

| Arquivo | Conteúdo / status |
|---------|-------------------|
| `cert_organica_*_P001/P002/P004/P007/P009/P012/P014/P018.txt` | Certificados IBD vigentes (nº ORG-PE-…) |
| `cert_organica_josefa_souza_P008.txt` | **VENCIDA em 30/09/2026** — renovação protocolo `REN-2026-0456` (solicitada 15/09); **auditoria agendada para 15/11/2026**; até lá, produtos **NÃO podem ser vendidos como orgânicos** (mel silvestre, geleias, doce de goiaba) |
| `laudo_sanitario_apiario_jose_P002.txt` | Laudo sanitário do apiário (P002) |
| `laudo_sanitario_queijaria_cicero_P003.txt` | Laudo sanitário da queijaria (P003) |
| `inspecao_adagro_2026.txt` | Relatório **ADAGRO-AM-2026-0189** (15–16/05/2026): coop **aprovada com restrições**; **NC-001 GRAVE: P017 sem registro SIE → suspender intermediação de frango caipira** (venda direta apenas; ovos não exigem SIE p/ venda direta); NC-002 menor: termômetro do veículo DEF-5678 descalibrado; inspecionados na amostragem: P001, P002, P003, P005 (DAP/CAF vigente), P017 |

**Conflito direto com pedidos:** PED-006 (mel silvestre 40kg **"orgânico"**) e PED-008/010 (exigências orgânicas) — a base precisa **não incluir a P008** como orgânica até 15/11.

---

## 8. `contratos/` — 3 contratos

| Contrato | Nº | Vigência | Condições-chave |
|----------|----|----------|-----------------|
| **Mercado Bom Preço** | 012/2026 | 01/01–31/12/2026 (renovável) | Fornecimento semanal p/ 3 filiais; volumes estimados por item (ex.: goiaba 50–80kg, macaxeira 50–80kg, queijo 30–50kg); boleto 30 dias; **entrega ter/sex 6h–10h no CD (BR-423 km 3)**; multa 2%/dia por atraso; padrões → devolução; cancelamento com 60 dias |
| **PNAE — Prefeitura Garanhuns** | 045/2026-PNAE | 01/03/2026–28/02/2027 | **R$ 480.000/ano (R$ 40.000/mês)**; Lei 11.947/2009 + Res. FNDE 06/2020 (30% agricultura familiar); **tabela de preços própria contratada** (ex.: banana R$3,80 — difere da tabela da coop R$3,50; queijo R$34; mel org R$58); exige **DAP/CAF vigente** de todos os produtores, **SIE/SIM/SISBI** p/ origem animal, **NF individual por produtor**; pagamento empenho 45 dias pós-atesto |
| **Restaurante Raízes** | 008/2026 | Indeterminada (aviso 30 dias) | Sob demanda 2–3×/semana; prioridade a orgânicos e produtores locais; **PIX no ato** da entrega; entrega no restaurante até 10h |

**Detalhe fino:** pedidos de PNAE (PED-004) devem ser precificados pela **tabela do contrato**, não pela tabela geral da cooperativa.

---

## 9. `fichas_tecnicas/` — 5 fichas

| Arquivo | Fatos-chave |
|---------|-------------|
| `queijo_coalho.txt` | Fornecedores: P003 (SIE PE-0756, **150–200kg/sem**, convencional), P007 (SIE PE-1203, **150–200kg/sem**, **orgânico** ORG-PE-2025-005432 val. 08/2027), P011 (**SEM SIE**, 50–80kg/sem, venda direta); armazenar 2–8°C, validade 30 dias; Selo Arte (Lei 13.680/2018) |
| `mel_silvestre.txt` | Fornecedores: P002 (SIE PE-0892, ~**300kg/mês**, orgânico val. 03/2027), P008 (**SIE pendente**, ~150kg/mês, cert. **vencida** — "não comercializar como orgânico até renovação"), P018 (**SIE pendente**, ~200kg/mês, orgânico val. 02/2027); validade 24 meses, ambiente 15–25°C; qualidade: umidade máx. 20%, HMF máx. 60mg/kg |
| `goiaba_paluma.txt` | Fornecedoras: P001 (orgânico, ~**500kg/sem** na safra out–mar / ~100kg entressafra), P010 (convencional, ~300kg/sem); vida útil 5–7 dias ambiente / 15–20 refrigerado (8–10°C); classificação Extra/Especial/Primeira por tamanho (sendo Extra = restaurantes/hotéis, >250g) |
| `hortalicas.txt` | Linha contínua o ano todo (clima de Garanhuns, ~20°C); produtoresas/es: P004 (~300kg/sem), P009 (~800kg/sem, 4 estufas), P012 (~400kg/sem) — **todos orgânicos**; folhosas validade 3–5 dias (2–5°C), frutos 7–10 dias (8–12°C); preços da ficha já refletem o diferencial orgânico |
| `tuberculos_graos.txt` | Macaxeira P005 (~400kg/sem), inhame P005 (~200kg/sem, pico abr–jul), batata-doce P005 (~150kg/sem); farinha e tapioca/goma P013 (200 / 100kg/sem); **nenhum orgânico**; nota: "todos possuem DAP/CAF vigente" (única referência em lote que responde o PED-013) |

> Estas fichas são fonte esperada de respostas com citação (ex.: capacidades por produtor, armazenamento, ingredientes).

---

## 10. Armadilhas e cruzamentos que os dados já revelam

Fatos derivados **dos próprios arquivos**, úteis para avaliar qualquer resposta do assistente (não é plano de implementação):

1. **Orgânico da P008 está suspenso** (vencido 30/09; auditoria 15/11) — qualquer pergunta "quem tem certificação vigente para mel?" deve excluir P008 ou sinalizar a renovação em curso.
2. **Frango caipira (P017) não pode ser intermedianado** (NC grave ADAGRO) — mas PED-007 (hotel), PED-013 (SESC) e até itens do contrato PNAE incluem frango; **ovos** não exigem SIE para venda direta.
3. **PED-006 (SuperBom)** pede para o **mesmo dia** 200kg de queijo + 50kg de manteiga + 300kg de goiaba + 40kg de mel silvestre *orgânico* — além da urgência, o mel orgânico disponível vem **só** de P002 (a certificação de P008 está vencida) e a goiaba orgânica só existe com P001.
4. **PED-003 e PED-005 são ambíguos de propósito** ("o queijo mais artesanal da última vez", "o de sempre") — precisam de histórico (financeiro/lotes) para desambiguação ou de resposta com hipótese explícita.
5. **PED-011 (exportação)** exige certificações internacionais que **não existem no dataset** — teste natural do requisito "não inventar: dizer que a informação não está disponível".
6. **DAP/CAF:** PED-009 e PED-013 perguntam sobre registro CAF/DAP dos produtores, mas o `produtores.csv` **não tem essa coluna** — só aparece disperso em documentos (ex.: ADAGRO confirma P005 com DAP/CAF vigente; certificado da P008 lista DAP SDR/PE-2019-0051098). Resposta exige varredura documental ou admissão de lacuna.
7. **Mensagens de produtor (PED-012, PED-015)** testam resumos personalizados: extrato do mês, status de pagamento pendente e **cadastrar produtor novo** (ação que foge dos dados entregues).
8. **PED-014 (ADAGRO)** lista exatamente documentos que o dataset contém (cadastro, certificações, laudos últimos 12 meses, rastreabilidade de lotes, contratos institucionais) — consulta documental canônica. A inspeção ocorre **11–12/11**, antes da entrega da arquitetura (19/11).
9. **Preço PNAE ≠ preço da coop** (banana 3,80 vs 3,50; queijo 34 vs 32/38) — orçamentos de PED-004 devem usar o contrato.
10. **Pendências financeiras vencidas:** empenhos PNAE vencidos desde 23/10 (FIN-005/006/007) e boleto SuperBom vencido 18/10 (FIN-013/014, anotado como "ATRASADO - cobrar") — alimentam as pendências do Desafio C.
