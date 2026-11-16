# Fila de Triagem Inteligente

**Data de referência:** 2026-10-30
**Total de registros:** 15

> Relatório de análise. Nenhum pedido, produção ou disponibilidade foi confirmado automaticamente.

## Ordem de prioridade

| Ordem | Pedido | Comprador | Prioridade | Status | Prazo |
|---:|---|---|---|---|---|
| 1 | PED-2026-006 | Rede SuperBom Atacado | alta | aguardando_confirmacao | 2026-10-29 |
| 2 | PED-2026-003 | Chef Amanda - Bistrô Sertão Gourmet | alta | aguardando_confirmacao | 2026-10-29 |
| 3 | PED-2026-001 | Restaurante Raízes | alta | aguardando_confirmacao | 2026-11-01 |
| 4 | PED-2026-014 | ADAGRO - Agência de Defesa Agropecuária | alta | analise_sem_alocacao | 2026-11-12 |
| 5 | PED-2026-005 | Dona Cremilda - Lanchonete da Feira | media | aguardando_confirmacao | 2026-10-31 |
| 6 | PED-2026-004 | Prefeitura de Garanhuns - PNAE | media | sugestao_nao_confirmada | 2026-11-04 |
| 7 | PED-2026-002 | Mercado Bom Preço | media | aguardando_confirmacao | 2026-11-04 |
| 8 | PED-2026-007 | Hotel Fazenda Serra Negra | media | analise_sem_alocacao | 2026-11-08 |
| 9 | PED-2026-009 | Hospital São Francisco | media | analise_sem_alocacao | Não informado |
| 10 | PED-2026-013 | SESC - Unidade Garanhuns | media | analise_sem_alocacao | jan/2027 |
| 11 | PED-2026-015 | Cícero (Produtor P003) | analise | analise_sem_alocacao | 2026-10-31 |
| 12 | PED-2026-012 | Maria das Graças (Produtora P001) | analise | analise_sem_alocacao | Não informado |
| 13 | PED-2026-008 | Marcos - Sorveteria Tropical | baixa | analise_sem_alocacao | Não informado |
| 14 | PED-2026-010 | João Pedro - Feira Orgânica do Recife | baixa | analise_sem_alocacao | Não informado |
| 15 | PED-2026-011 | Tropical Fruits Exportadora | baixa | analise_sem_alocacao | Não informado |

## Análise por registro

### PED-2026-006 — Rede SuperBom Atacado

**Tipo:** compra_urgente
**Prioridade:** alta
**Status:** aguardando_confirmacao
**Prazo:** 2026-10-29
**Requer confirmação:** Sim

#### Sugestões de alocação

- **queijo coalho:** 200.0 kg — Produtor P003. Fonte: `fichas_tecnicas/queijo_coalho.txt`. **Reserva condicionada à confirmação.**
- **mel silvestre:** 40.0 kg — Produtor P002. Fonte: `fichas_tecnicas/mel_silvestre.txt`. **Reserva condicionada à confirmação.**
- **goiaba paluma:** 300.0 kg — Produtor P001. Fonte: `fichas_tecnicas/goiaba_paluma.txt`. **Reserva condicionada à confirmação.**

#### Correspondências de ofertas

- **queijo coalho:** 200.0 kg do produtor P003, oferta PED-2026-015. Compatibilidade temporal: Não. Oferta posterior ao prazo original. Confirmar se a demanda continua aberta e se o comprador aceita renegociar. Fonte: `tests/fixtures/triagem_15_pedidos.json:PED-2026-015`.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **PRAZO_VENCIDO:** Prazo vencido. Confirmar validade da solicitação. Fonte: `pedido_estruturado.prazo_entrega`.
- **REGISTRO_SANITARIO:** P011 (Pedro Henrique Albuquerque) não tem registro SIE para queijo coalho. A ficha técnica limita a venda dele ao consumidor final. Compradores que exigem registro sanitário, como o PNAE, não aceitam; confirme se Rede SuperBom Atacado aceita. Fonte: `fichas_tecnicas/queijo_coalho.txt`.
- **CAPACIDADE:** O pedido de 200 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: de 350 a 480 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/queijo_coalho.txt`.
- **SEM_CONTRATO:** Não há contrato registrado com 'Rede SuperBom Atacado': vale a tabela geral de preços. Fonte: `tabela_precos_outubro_2026.csv`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em kg para queijo manteiga nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P003 (Cícero Romão de Almeida) fornece queijo manteiga: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **SEM_CONTRATO:** Não há contrato registrado com 'Rede SuperBom Atacado': vale a tabela geral de preços. Fonte: `tabela_precos_outubro_2026.csv`.
- **CERTIFICACAO_VENCIDA:** P008 (Josefa Alves de Souza): a certificação orgânica ORG-PE-2024-003876 não vale em 29/10/2026; venceu em 30/09/2026. A renovação foi pedida em 15/09/2026 (protocolo REN-2026-0456) e a auditoria está marcada para 15/11/2026. O pedido de renovação não libera a venda como orgânico. Não pode vender mel silvestre como orgânico. Fonte: `certificacoes/cert_organica_josefa_souza_P008.txt`.
- **REGISTRO_SANITARIO:** P018 (Débora Cristina de Melo) tem o SIE pendente para mel silvestre. Compradores que exigem registro sanitário, como o PNAE, não aceitam; confirme se Rede SuperBom Atacado aceita. Fonte: `fichas_tecnicas/mel_silvestre.txt`.
- **CAPACIDADE:** O pedido de 40 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 116,7 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/mel_silvestre.txt`.
- **SEM_CONTRATO:** Não há contrato registrado com 'Rede SuperBom Atacado': vale a tabela geral de preços. Fonte: `tabela_precos_outubro_2026.csv`.
- **CAPACIDADE:** O pedido de 300 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 800 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/goiaba_paluma.txt`.
- **SEM_CONTRATO:** Não há contrato registrado com 'Rede SuperBom Atacado': vale a tabela geral de preços. Fonte: `tabela_precos_outubro_2026.csv`.
- **OFERTA_POSTERIOR_AO_PRAZO:** Oferta PED-2026-015 do produtor P003 corresponde ao produto queijo coalho, mas foi recebida após o prazo original da demanda. Confirmar se o comprador aceita renegociar. Fonte: `tests/fixtures/triagem_15_pedidos.json:PED-2026-015`.

### PED-2026-003 — Chef Amanda - Bistrô Sertão Gourmet

**Tipo:** compra_urgente
**Prioridade:** alta
**Status:** aguardando_confirmacao
**Prazo:** 2026-10-29
**Requer confirmação:** Sim

#### Sugestões de alocação

- **mel de jandaíra:** 3.0 kg — Produtor P002. Fonte: `certificacoes/cert_organica_jose_santos_P002.txt`. **Reserva condicionada à confirmação.**

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- **Hipótese documental:** queijo coalho. Possível queijo coalho artesanal, conforme ficha técnica. Não foi encontrado histórico anterior deste comprador. Confirmar o produto solicitado antes de qualquer alocação. Fonte: `data/fichas_tecnicas/queijo_coalho.txt`.
- Histórico pendente de confirmação.

#### Alertas e fontes

- **AMBIGUIDADE:** Referência implícita ao queijo da última vez ('o mais artesanal') Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Referência implícita detectada ('da última vez'): necessário consultar pedidos/lotes anteriores do comprador. Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Nenhum produto do catálogo corresponde a 'queijo artesanal'. Fonte: `pedido_estruturado.ambiguidades`.
- **PRAZO_VENCIDO:** Prazo vencido. Confirmar validade da solicitação. Fonte: `pedido_estruturado.prazo_entrega`.
- **CONFIRMAR_HISTORICO:** Nenhum histórico correspondente foi encontrado. Solicitar esclarecimento ao comprador. Fonte: `data/financeiro.csv; data/lotes.csv`.
- **HIPOTESE_DOCUMENTAL:** Possível queijo coalho artesanal, conforme ficha técnica. Não foi encontrado histórico anterior deste comprador. Confirmar o produto solicitado antes de qualquer alocação. Fonte: `data/fichas_tecnicas/queijo_coalho.txt`.
- **CAPACIDADE:** O pedido de 3 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 3,5 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `certificacoes/cert_organica_jose_santos_P002.txt`.
- **PRODUTOR_EXCLUSIVO:** Só P002 (José Antônio dos Santos) fornece mel de jandaíra: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **SEM_CONTRATO:** Não há contrato registrado com 'Chef Amanda - Bistrô Sertão Gourmet': vale a tabela geral de preços. Fonte: `tabela_precos_outubro_2026.csv`.

### PED-2026-001 — Restaurante Raízes

**Tipo:** compra
**Prioridade:** alta
**Status:** aguardando_confirmacao
**Prazo:** 2026-11-01
**Requer confirmação:** Sim

#### Sugestões de alocação

- **queijo coalho:** 30.0 kg — Produtor P007. Fonte: `fichas_tecnicas/queijo_coalho.txt`. **Reserva condicionada à confirmação.**
- **manteiga de garrafa:** 10.0 kg — Produtor P007. Fonte: `certificacoes/cert_organica_antonio_lima_P007.txt`. **Reserva condicionada à confirmação.**
- **mel silvestre:** 5.0 kg — Produtor P002. Fonte: `fichas_tecnicas/mel_silvestre.txt`. **Reserva condicionada à confirmação.**

#### Correspondências de ofertas

- **queijo coalho:** 30.0 kg do produtor P003, oferta PED-2026-015. Compatibilidade temporal: Sim. Oferta recebida até a data-limite da demanda; confirmar disponibilidade e condições. Fonte: `tests/fixtures/triagem_15_pedidos.json:PED-2026-015`.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **AMBIGUIDADE:** Conflito de data: mensagem informa 'sexta' junto com 01/11/2026, mas 01/11/2026 cai em domingo (a sexta-feira correspondente seria 30/10/2026). Fonte: `pedido_estruturado.ambiguidades`.
- **CONTRATO_IDENTIFICADO:** Comprador vinculado ao contrato 008/2026. Verificar exigências contratuais. Fonte: `contratos/contrato_restaurante_raizes.txt`.
- **REGISTRO_SANITARIO:** P011 (Pedro Henrique Albuquerque) não tem registro SIE para queijo coalho. A ficha técnica limita a venda dele ao consumidor final. Compradores que exigem registro sanitário, como o PNAE, não aceitam; confirme se Restaurante Raízes aceita. Fonte: `fichas_tecnicas/queijo_coalho.txt`.
- **CAPACIDADE:** O pedido de 30 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: de 350 a 480 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/queijo_coalho.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 008/2026 com Restaurante Raízes: pagamento por PIX no ato da entrega; entrega no restaurante até as 10h; prioridade para produtos orgânicos e de produtores locais. Fonte: `contratos/contrato_restaurante_raizes.txt`.
- **CAPACIDADE:** O pedido de 10 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 40 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `certificacoes/cert_organica_antonio_lima_P007.txt`.
- **PRODUTOR_EXCLUSIVO:** Só P007 (Antônio Carlos Pereira Lima) fornece manteiga de garrafa: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 008/2026 com Restaurante Raízes: pagamento por PIX no ato da entrega; entrega no restaurante até as 10h; prioridade para produtos orgânicos e de produtores locais. Fonte: `contratos/contrato_restaurante_raizes.txt`.
- **REGISTRO_SANITARIO:** P008 (Josefa Alves de Souza) tem o SIE pendente para mel silvestre. Compradores que exigem registro sanitário, como o PNAE, não aceitam; confirme se Restaurante Raízes aceita. Fonte: `fichas_tecnicas/mel_silvestre.txt`.
- **REGISTRO_SANITARIO:** P018 (Débora Cristina de Melo) tem o SIE pendente para mel silvestre. Compradores que exigem registro sanitário, como o PNAE, não aceitam; confirme se Restaurante Raízes aceita. Fonte: `fichas_tecnicas/mel_silvestre.txt`.
- **CAPACIDADE:** O pedido de 5 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 151,7 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/mel_silvestre.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 008/2026 com Restaurante Raízes: pagamento por PIX no ato da entrega; entrega no restaurante até as 10h; prioridade para produtos orgânicos e de produtores locais. Fonte: `contratos/contrato_restaurante_raizes.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em maço para coentro nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P004 (Ana Lúcia Bezerra da Costa) fornece coentro: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 008/2026 com Restaurante Raízes: pagamento por PIX no ato da entrega; entrega no restaurante até as 10h; prioridade para produtos orgânicos e de produtores locais. Fonte: `contratos/contrato_restaurante_raizes.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em maço para cebolinha nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P004 (Ana Lúcia Bezerra da Costa) fornece cebolinha: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 008/2026 com Restaurante Raízes: pagamento por PIX no ato da entrega; entrega no restaurante até as 10h; prioridade para produtos orgânicos e de produtores locais. Fonte: `contratos/contrato_restaurante_raizes.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em kg para ricota nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P003 (Cícero Romão de Almeida) fornece ricota: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 008/2026 com Restaurante Raízes: pagamento por PIX no ato da entrega; entrega no restaurante até as 10h; prioridade para produtos orgânicos e de produtores locais. Fonte: `contratos/contrato_restaurante_raizes.txt`.

### PED-2026-014 — ADAGRO - Agência de Defesa Agropecuária

**Tipo:** notificacao_oficial
**Prioridade:** alta
**Status:** analise_sem_alocacao
**Prazo:** 2026-11-12
**Requer confirmação:** Sim

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **VALIDACAO_DOCUMENTAL_PENDENTE:** Verificar documentação: Cadastro de produtores. Fonte: `data/produtores.csv`.
- **VALIDACAO_DOCUMENTAL_PENDENTE:** Verificar documentação: Certificações orgânicas. Fonte: `data/certificacoes/cert_organica_ana_bezerra_P004.txt; data/certificacoes/cert_organica_antonio_lima_P007.txt; data/certificacoes/cert_organica_debora_melo_P018.txt; data/certificacoes/cert_organica_jose_santos_P002.txt; data/certificacoes/cert_organica_josefa_souza_P008.txt; data/certificacoes/cert_organica_luciana_gomes_P012.txt; data/certificacoes/cert_organica_marcos_rocha_P009.txt; data/certificacoes/cert_organica_maria_silva_P001.txt; data/certificacoes/cert_organica_mariana_cordeiro_P014.txt`.
- **VALIDACAO_DOCUMENTAL_PENDENTE:** Verificar documentação: Laudos sanitários. Fonte: `data/certificacoes/laudo_sanitario_apiario_jose_P002.txt; data/certificacoes/laudo_sanitario_queijaria_cicero_P003.txt`.
- **VALIDACAO_DOCUMENTAL_PENDENTE:** Verificar documentação: Registros de rastreabilidade. Fonte: `data/lotes.csv`.
- **VALIDACAO_DOCUMENTAL_PENDENTE:** Verificar documentação: Contratos institucionais. Fonte: `data/contratos/contrato_mercado_bom_preco.txt; data/contratos/contrato_pnae_garanhuns.txt; data/contratos/contrato_restaurante_raizes.txt`.

### PED-2026-005 — Dona Cremilda - Lanchonete da Feira

**Tipo:** compra
**Prioridade:** media
**Status:** aguardando_confirmacao
**Prazo:** 2026-10-31
**Requer confirmação:** Sim

#### Sugestões de alocação

- **queijo coalho:** 10.0 kg — Produtor P007. Fonte: `fichas_tecnicas/queijo_coalho.txt`. **Reserva condicionada à confirmação.**

#### Correspondências de ofertas

- **queijo coalho:** 10.0 kg do produtor P003, oferta PED-2026-015. Compatibilidade temporal: Sim. Oferta recebida até a data-limite da demanda; confirmar disponibilidade e condições. Fonte: `tests/fixtures/triagem_15_pedidos.json:PED-2026-015`.

#### Histórico

- Hipótese histórica: {'produto': 'queijo coalho', 'quantidade_kg': 20.0, 'data': '2026-10-15', 'fonte': 'data/financeiro.csv', 'registro_id': 'FIN-2026-026', 'confirmado': False}
- Hipótese histórica: {'produto': 'banana prata', 'quantidade_kg': 60.0, 'data': '2026-09-12', 'fonte': 'data/financeiro.csv', 'registro_id': 'FIN-2026-010', 'confirmado': False}
- Histórico pendente de confirmação.

#### Alertas e fontes

- **AMBIGUIDADE:** o de sempre ne Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Referência implícita detectada ('o de sempre'): necessário consultar histórico do comprador. Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** 'manteiga' pode ser: manteiga de garrafa, queijo manteiga. Pergunte qual. Fonte: `pedido_estruturado.ambiguidades`.
- **CONFIRMAR_HISTORICO:** Hipótese baseada no histórico. Confirmar produto e quantidade com o comprador. Fonte: `data/financeiro.csv; data/lotes.csv`.
- **REGISTRO_SANITARIO:** P011 (Pedro Henrique Albuquerque) não tem registro SIE para queijo coalho. A ficha técnica limita a venda dele ao consumidor final. Compradores que exigem registro sanitário, como o PNAE, não aceitam; confirme se Dona Cremilda - Lanchonete da Feira aceita. Fonte: `fichas_tecnicas/queijo_coalho.txt`.
- **CAPACIDADE:** O pedido de 10 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: de 350 a 480 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/queijo_coalho.txt`.
- **SEM_CONTRATO:** Não há contrato registrado com 'Dona Cremilda - Lanchonete da Feira': vale a tabela geral de preços. Fonte: `tabela_precos_outubro_2026.csv`.

### PED-2026-004 — Prefeitura de Garanhuns - PNAE

**Tipo:** compra
**Prioridade:** media
**Status:** sugestao_nao_confirmada
**Prazo:** 2026-11-04
**Requer confirmação:** Não

#### Sugestões de alocação

- **macaxeira:** 150.0 kg — Produtor P005. Fonte: `fichas_tecnicas/tuberculos_graos.txt`. **Sugestão não confirmada.**
- **inhame:** 80.0 kg — Produtor P005. Fonte: `fichas_tecnicas/tuberculos_graos.txt`. **Sugestão não confirmada.**

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **CONTRATO_IDENTIFICADO:** Comprador vinculado ao contrato 045/2026-PNAE. Verificar exigências contratuais. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **DAP_CAF_NAO_COMPROVADA:** P006 (Severina Maria do Nascimento): nenhum documento comprova DAP ou CAF vigente, e o contrato 045/2026-PNAE exige. Comprove antes de faturar. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em kg para banana prata nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P006 (Severina Maria do Nascimento) fornece banana prata: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 3,80/kg por banana prata pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **DAP_CAF_NAO_COMPROVADA:** P001 (Maria das Graças Silva Ferreira): a DAP/CAF (SDR/PE-2019-0047821) aparece no documento sem validade, e o contrato 045/2026-PNAE exige DAP ou CAF vigente. Comprove antes de faturar. Fonte: `certificacoes/cert_organica_maria_silva_P001.txt`.
- **DAP_CAF_NAO_COMPROVADA:** P010 (Raimunda Nonata de Lima): nenhum documento comprova DAP ou CAF vigente, e o contrato 045/2026-PNAE exige. Comprove antes de faturar. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **CAPACIDADE:** O pedido de 100 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 800 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/goiaba_paluma.txt`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 5,20/kg por goiaba paluma pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **PRODUTOR_INATIVO:** P015 (Geraldo Manoel Barbosa) está inativo no cadastro e não recebe alocação. Fonte: `produtores.csv`.
- **CAPACIDADE:** O pedido de 150 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 400 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/tuberculos_graos.txt`.
- **PRODUTOR_EXCLUSIVO:** Só P005 (Francisco de Assis Cordeiro) fornece macaxeira: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 3,50/kg por macaxeira pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **CAPACIDADE:** O pedido de 80 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 200 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/tuberculos_graos.txt`.
- **PRODUTOR_EXCLUSIVO:** Só P005 (Francisco de Assis Cordeiro) fornece inhame: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 5,00/kg por inhame pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **DAP_CAF_NAO_COMPROVADA:** P004 (Ana Lúcia Bezerra da Costa): a DAP/CAF (SDR/PE-2020-0058934) aparece no documento sem validade, e o contrato 045/2026-PNAE exige DAP ou CAF vigente. Comprove antes de faturar. Fonte: `certificacoes/cert_organica_ana_bezerra_P004.txt`.
- **DAP_CAF_NAO_COMPROVADA:** P009 (Marcos Vinícius da Rocha): a DAP/CAF (SDR/PE-2021-0072345) aparece no documento sem validade, e o contrato 045/2026-PNAE exige DAP ou CAF vigente. Comprove antes de faturar. Fonte: `certificacoes/cert_organica_marcos_rocha_P009.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em unidade para alface nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 2,80/unidade por alface pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **DAP_CAF_NAO_COMPROVADA:** P004 (Ana Lúcia Bezerra da Costa): a DAP/CAF (SDR/PE-2020-0058934) aparece no documento sem validade, e o contrato 045/2026-PNAE exige DAP ou CAF vigente. Comprove antes de faturar. Fonte: `certificacoes/cert_organica_ana_bezerra_P004.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em maço para coentro nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P004 (Ana Lúcia Bezerra da Costa) fornece coentro: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 2,00/maço por coentro pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **DAP_CAF_NAO_COMPROVADA:** P012 (Luciana Ferreira Gomes): a DAP/CAF (SDR/PE-2020-0064512) aparece no documento sem validade, e o contrato 045/2026-PNAE exige DAP ou CAF vigente. Comprove antes de faturar. Fonte: `certificacoes/cert_organica_luciana_gomes_P012.txt`.
- **CAPACIDADE:** O pedido de 50 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 400 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/hortalicas.txt`.
- **PRODUTOR_EXCLUSIVO:** Só P012 (Luciana Ferreira Gomes) fornece tomate: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 7,00/kg por tomate pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **CERTIFICACAO_VENCIDA:** P008 (Josefa Alves de Souza): a certificação orgânica ORG-PE-2024-003876 não vale em 04/11/2026; venceu em 30/09/2026. A renovação foi pedida em 15/09/2026 (protocolo REN-2026-0456) e a auditoria está marcada para 15/11/2026. O pedido de renovação não libera a venda como orgânico. Não pode vender mel silvestre como orgânico. Fonte: `certificacoes/cert_organica_josefa_souza_P008.txt`.
- **SIE_EXIGIDO:** P018 (Débora Cristina de Melo) tem o SIE pendente, e o contrato 045/2026-PNAE exige SIE, SIM ou SISBI para produto de origem animal. Fonte: `fichas_tecnicas/mel_silvestre.txt`.
- **DAP_CAF_NAO_COMPROVADA:** P002 (José Antônio dos Santos): a DAP/CAF (SDR/PE-2018-0031456) aparece no documento sem validade, e o contrato 045/2026-PNAE exige DAP ou CAF vigente. Comprove antes de faturar. Fonte: `certificacoes/cert_organica_jose_santos_P002.txt`.
- **CAPACIDADE:** O pedido de 20 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 70 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/mel_silvestre.txt`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 58,00/kg por mel silvestre pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **CONTRATO_EXIGE_ORGANICO:** O contrato 045/2026-PNAE compra mel silvestre orgânico; o item foi avaliado como orgânico. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **SIE_EXIGIDO:** P017 (Wellington da Silva Monteiro) não tem registro SIE, e o contrato 045/2026-PNAE exige SIE, SIM ou SISBI para produto de origem animal. Ovos só dispensam o SIE na venda direta ao consumidor final. Fonte: `certificacoes/inspecao_adagro_2026.txt`.
- **SEM_PRODUTOR_ELEGIVEL:** Nenhum produtor pode atender ovos caipira: os motivos de cada produtor estão nos outros alertas (P017). Fonte: `produtores.csv`.
- **PRODUTOR_EXCLUSIVO:** Só P017 (Wellington da Silva Monteiro) fornece ovos caipira: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **PRECO_CONTRATO:** Prefeitura de Garanhuns (PNAE) paga R$ 18,00/dúzia por ovos caipira pelo contrato 045/2026-PNAE, não pela tabela geral. Fonte: `contratos/contrato_pnae_garanhuns.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 045/2026-PNAE com Prefeitura de Garanhuns (PNAE): produto orgânico só com certificação válida; nota fiscal individual por produtor; entrega semanal conforme o cardápio da nutricionista; pagamento por empenho em até 45 dias após o atesto. Fonte: `contratos/contrato_pnae_garanhuns.txt`.

### PED-2026-002 — Mercado Bom Preço

**Tipo:** compra
**Prioridade:** media
**Status:** aguardando_confirmacao
**Prazo:** 2026-11-04
**Requer confirmação:** Sim

#### Sugestões de alocação

- **goiaba paluma:** 50.0 kg — Produtor P001. Fonte: `fichas_tecnicas/goiaba_paluma.txt`. **Reserva condicionada à confirmação.**
- **macaxeira:** 60.0 kg — Produtor P005. Fonte: `fichas_tecnicas/tuberculos_graos.txt`. **Reserva condicionada à confirmação.**
- **inhame:** 30.0 kg — Produtor P005. Fonte: `fichas_tecnicas/tuberculos_graos.txt`. **Reserva condicionada à confirmação.**
- **tomate:** 20.0 kg — Produtor P012. Fonte: `fichas_tecnicas/hortalicas.txt`. **Reserva condicionada à confirmação.**

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **AMBIGUIDADE:** Conflito de data: mensagem informa 'terça' junto com 04/11/2026, mas 04/11/2026 cai em quarta-feira (a terça-feira correspondente seria 03/11/2026). Fonte: `pedido_estruturado.ambiguidades`.
- **CONTRATO_IDENTIFICADO:** Comprador vinculado ao contrato 012/2026. Verificar exigências contratuais. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **ENTREGA_FORA_DO_DIA:** O contrato 012/2026 prevê entrega só às terças e sextas; 04/11/2026 é quarta. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **CAPACIDADE:** O pedido de 50 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 800 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/goiaba_paluma.txt`.
- **EXIGENCIAS_CONTRATO:** Contrato 012/2026 com Mercado Bom Preço: entrega das 6h às 10h no CD do Mercado Bom Preço (Rod. BR-423 km 3); pagamento por boleto com vencimento em 30 dias; multa de 2% ao dia por atraso na entrega; produto fora do padrão é devolvido sem custo para o comprador. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **ENTREGA_FORA_DO_DIA:** O contrato 012/2026 prevê entrega só às terças e sextas; 04/11/2026 é quarta. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em kg para banana prata nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P006 (Severina Maria do Nascimento) fornece banana prata: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 012/2026 com Mercado Bom Preço: entrega das 6h às 10h no CD do Mercado Bom Preço (Rod. BR-423 km 3); pagamento por boleto com vencimento em 30 dias; multa de 2% ao dia por atraso na entrega; produto fora do padrão é devolvido sem custo para o comprador. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **ENTREGA_FORA_DO_DIA:** O contrato 012/2026 prevê entrega só às terças e sextas; 04/11/2026 é quarta. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em kg para maracujá nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P006 (Severina Maria do Nascimento) fornece maracujá: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 012/2026 com Mercado Bom Preço: entrega das 6h às 10h no CD do Mercado Bom Preço (Rod. BR-423 km 3); pagamento por boleto com vencimento em 30 dias; multa de 2% ao dia por atraso na entrega; produto fora do padrão é devolvido sem custo para o comprador. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **ENTREGA_FORA_DO_DIA:** O contrato 012/2026 prevê entrega só às terças e sextas; 04/11/2026 é quarta. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **PRODUTOR_INATIVO:** P015 (Geraldo Manoel Barbosa) está inativo no cadastro e não recebe alocação. Fonte: `produtores.csv`.
- **CAPACIDADE:** O pedido de 60 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 400 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/tuberculos_graos.txt`.
- **PRODUTOR_EXCLUSIVO:** Só P005 (Francisco de Assis Cordeiro) fornece macaxeira: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 012/2026 com Mercado Bom Preço: entrega das 6h às 10h no CD do Mercado Bom Preço (Rod. BR-423 km 3); pagamento por boleto com vencimento em 30 dias; multa de 2% ao dia por atraso na entrega; produto fora do padrão é devolvido sem custo para o comprador. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **ENTREGA_FORA_DO_DIA:** O contrato 012/2026 prevê entrega só às terças e sextas; 04/11/2026 é quarta. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **CAPACIDADE:** O pedido de 30 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 200 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/tuberculos_graos.txt`.
- **PRODUTOR_EXCLUSIVO:** Só P005 (Francisco de Assis Cordeiro) fornece inhame: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 012/2026 com Mercado Bom Preço: entrega das 6h às 10h no CD do Mercado Bom Preço (Rod. BR-423 km 3); pagamento por boleto com vencimento em 30 dias; multa de 2% ao dia por atraso na entrega; produto fora do padrão é devolvido sem custo para o comprador. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **ENTREGA_FORA_DO_DIA:** O contrato 012/2026 prevê entrega só às terças e sextas; 04/11/2026 é quarta. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **CAPACIDADE:** O pedido de 20 kg cabe na capacidade. Capacidade documentada dos elegíveis em 7 dias: 400 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/hortalicas.txt`.
- **PRODUTOR_EXCLUSIVO:** Só P012 (Luciana Ferreira Gomes) fornece tomate: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **EXIGENCIAS_CONTRATO:** Contrato 012/2026 com Mercado Bom Preço: entrega das 6h às 10h no CD do Mercado Bom Preço (Rod. BR-423 km 3); pagamento por boleto com vencimento em 30 dias; multa de 2% ao dia por atraso na entrega; produto fora do padrão é devolvido sem custo para o comprador. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **ENTREGA_FORA_DO_DIA:** O contrato 012/2026 prevê entrega só às terças e sextas; 04/11/2026 é quarta. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em unidade para alface nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **EXIGENCIAS_CONTRATO:** Contrato 012/2026 com Mercado Bom Preço: entrega das 6h às 10h no CD do Mercado Bom Preço (Rod. BR-423 km 3); pagamento por boleto com vencimento em 30 dias; multa de 2% ao dia por atraso na entrega; produto fora do padrão é devolvido sem custo para o comprador. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **ENTREGA_FORA_DO_DIA:** O contrato 012/2026 prevê entrega só às terças e sextas; 04/11/2026 é quarta. Fonte: `contratos/contrato_mercado_bom_preco.txt`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em maço para rúcula nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **EXIGENCIAS_CONTRATO:** Contrato 012/2026 com Mercado Bom Preço: entrega das 6h às 10h no CD do Mercado Bom Preço (Rod. BR-423 km 3); pagamento por boleto com vencimento em 30 dias; multa de 2% ao dia por atraso na entrega; produto fora do padrão é devolvido sem custo para o comprador. Fonte: `contratos/contrato_mercado_bom_preco.txt`.

### PED-2026-007 — Hotel Fazenda Serra Negra

**Tipo:** cotacao
**Prioridade:** media
**Status:** analise_sem_alocacao
**Prazo:** 2026-11-08
**Requer confirmação:** Sim

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **AMBIGUIDADE:** 'mel' pode ser: mel de jandaíra, mel silvestre. Pergunte qual. Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Nenhum produto do catálogo corresponde a 'goma de tapioca'. Fonte: `pedido_estruturado.ambiguidades`.
- **REGISTRO_SANITARIO:** P011 (Pedro Henrique Albuquerque) não tem registro SIE para queijo coalho. A ficha técnica limita a venda dele ao consumidor final. Compradores que exigem registro sanitário, como o PNAE, não aceitam; confirme se Hotel Fazenda Serra Negra aceita. Fonte: `fichas_tecnicas/queijo_coalho.txt`.
- **CAPACIDADE:** O pedido de 25 kg cabe na capacidade. Capacidade documentada dos elegíveis em 9 dias: de 450,1 a 617,1 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/queijo_coalho.txt`.
- **SEM_CONTRATO:** Não há contrato registrado com 'Hotel Fazenda Serra Negra': vale a tabela geral de preços. Fonte: `tabela_precos_outubro_2026.csv`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em kg para queijo manteiga nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P003 (Cícero Romão de Almeida) fornece queijo manteiga: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **ITEM_NAO_AVALIADO:** 'mel' pode ser: mel de jandaíra, mel silvestre. Pergunte qual. Fonte: `catalogo; pedido_estruturado.itens`.
- **CAPACIDADE:** O pedido de 20 kg cabe na capacidade. Capacidade documentada dos elegíveis em 9 dias: 1028,6 kg. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `fichas_tecnicas/goiaba_paluma.txt`.
- **SAFRA_BAIXA:** Cajá tem disponibilidade baixa em novembro; confirme a quantidade com os produtores. Safra muito curta: nov-jan. Fonte: `sazonalidade.csv`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em kg para cajá nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P010 (Raimunda Nonata de Lima) fornece cajá: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **CAPACIDADE_SEM_DADO:** Não há capacidade documentada em kg para rapadura nos produtores elegíveis; confirme a quantidade com eles. Fonte: `fichas_tecnicas/`.
- **PRODUTOR_EXCLUSIVO:** Só P016 (Terezinha de Jesus Oliveira) fornece rapadura: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **ITEM_NAO_AVALIADO:** Nenhum produto do catálogo corresponde a 'goma de tapioca'. Fonte: `catalogo; pedido_estruturado.itens`.
- **NAO_CONFORMIDADE_SANITARIA:** NC-001 (ADAGRO-AM-2026-0189): P017 (Wellington da Silva Monteiro), produtor de frango caipira sem registro no SIE. Por isso a cooperativa deve suspender a intermediação até o produtor obter o registro; até lá, só é permitida a venda direta ao consumidor final. Fonte: `certificacoes/inspecao_adagro_2026.txt`.
- **SEM_PRODUTOR_ELEGIVEL:** Nenhum produtor pode atender frango caipira: os motivos de cada produtor estão nos outros alertas (P017). Fonte: `produtores.csv`.
- **PRODUTOR_EXCLUSIVO:** Só P017 (Wellington da Silva Monteiro) fornece frango caipira: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.
- **REGISTRO_SANITARIO:** P017 (Wellington da Silva Monteiro) não tem registro SIE para ovos caipira. Ovos só dispensam o SIE na venda direta ao consumidor final. Compradores que exigem registro sanitário, como o PNAE, não aceitam; confirme se Hotel Fazenda Serra Negra aceita. Fonte: `certificacoes/inspecao_adagro_2026.txt`.
- **CAPACIDADE:** O pedido de 30 dúzias cabe na capacidade. Capacidade documentada dos elegíveis em 9 dias: 154,3 dúzias. Capacidade de produção não é estoque: confirme a disponibilidade com os produtores. Fonte: `sazonalidade.csv`.
- **PRODUTOR_EXCLUSIVO:** Só P017 (Wellington da Silva Monteiro) fornece ovos caipira: não há outro produtor se ele não puder atender. Fonte: `produtores.csv`.

### PED-2026-009 — Hospital São Francisco

**Tipo:** cotacao
**Prioridade:** media
**Status:** analise_sem_alocacao
**Prazo:** Não informado
**Requer confirmação:** Sim

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **AMBIGUIDADE:** Quantidades informadas como totais para grupos de frutas e hortaliças sem especificação individual por produto Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Não há produto chamado 'frutas variadas' no catálogo. O mais próximo é geleia de frutas: confirme com a pessoa antes de usar. Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Nenhum produto do catálogo corresponde a 'hortaliças variadas'. Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** 'mel puro' pode ser: mel de jandaíra, mel silvestre. Pergunte qual. Fonte: `pedido_estruturado.ambiguidades`.
- **CAMPO_FALTANTE:** Campo pendente: prazo_entrega Fonte: `pedido_estruturado.campos_faltantes`.
- **CAMPO_FALTANTE:** Campo pendente: quantidades_por_subproduto Fonte: `pedido_estruturado.campos_faltantes`.
- **PRAZO_ENTREGA_AUSENTE:** Informar a data de entrega para avaliar safra, capacidade e certificações na data. Fonte: `pedido_estruturado.prazo_entrega`.
- **CAMPO_FALTANTE:** Confirmar campo: prazo_entrega. Fonte: `pedido_estruturado.campos_faltantes`.
- **CAMPO_FALTANTE:** Confirmar campo: quantidades_por_subproduto. Fonte: `pedido_estruturado.campos_faltantes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: dap_caf. Fonte: `pedido_estruturado.observacoes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: certificacao_organica. Fonte: `pedido_estruturado.observacoes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: rastreabilidade. Fonte: `pedido_estruturado.observacoes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: laudo_sanitario. Fonte: `pedido_estruturado.observacoes`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de frutas depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de hortaliças depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de ovos caipira depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de mel depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.

### PED-2026-013 — SESC - Unidade Garanhuns

**Tipo:** cotacao
**Prioridade:** media
**Status:** analise_sem_alocacao
**Prazo:** jan/2027
**Requer confirmação:** Sim

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **AMBIGUIDADE:** Frutas variadas Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Hortaliças variadas Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Não há produto chamado 'frutas' no catálogo. O mais próximo é geleia de frutas: confirme com a pessoa antes de usar. Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** Nenhum produto do catálogo corresponde a 'hortaliças'. Fonte: `pedido_estruturado.ambiguidades`.
- **AMBIGUIDADE:** 'mel' pode ser: mel de jandaíra, mel silvestre. Pergunte qual. Fonte: `pedido_estruturado.ambiguidades`.
- **PRAZO_NAO_RESOLVIDO:** Prazo textual exige esclarecimento. Fonte: `pedido_estruturado.prazo_entrega`.
- **PRAZO_ENTREGA_NAO_RESOLVIDO:** O prazo 'jan/2027' precisa ser convertido em uma data exata. Fonte: `pedido_estruturado.prazo_entrega`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: dap_caf. Fonte: `pedido_estruturado.observacoes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: nota_fiscal. Fonte: `pedido_estruturado.observacoes`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de frutas depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de hortaliças depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de queijo coalho depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de mel depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de ovos caipira depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de frango caipira depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de macaxeira depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.

### PED-2026-015 — Cícero (Produtor P003)

**Tipo:** mensagem_produtor
**Prioridade:** analise
**Status:** analise_sem_alocacao
**Prazo:** 2026-10-31
**Requer confirmação:** Sim

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **AMBIGUIDADE:** 'manteiga' pode ser: manteiga de garrafa, queijo manteiga. Pergunte qual. Fonte: `pedido_estruturado.ambiguidades`.

### PED-2026-012 — Maria das Graças (Produtora P001)

**Tipo:** mensagem_produtor
**Prioridade:** analise
**Status:** analise_sem_alocacao
**Prazo:** Não informado
**Requer confirmação:** Não

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- Nenhum alerta.

### PED-2026-008 — Marcos - Sorveteria Tropical

**Tipo:** consulta
**Prioridade:** baixa
**Status:** analise_sem_alocacao
**Prazo:** Não informado
**Requer confirmação:** Sim

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **PRAZO_ENTREGA_AUSENTE:** Informar a data de entrega para avaliar safra, capacidade e certificações na data. Fonte: `pedido_estruturado.prazo_entrega`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: certificacao_organica. Fonte: `pedido_estruturado.observacoes`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de morango depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de amora depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.

### PED-2026-010 — João Pedro - Feira Orgânica do Recife

**Tipo:** consulta
**Prioridade:** baixa
**Status:** analise_sem_alocacao
**Prazo:** Não informado
**Requer confirmação:** Sim

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **AMBIGUIDADE:** tudo que vocês tiverem COM certificação orgânica Fonte: `pedido_estruturado.ambiguidades`.
- **CAMPO_FALTANTE:** Campo pendente: itens_especificos Fonte: `pedido_estruturado.campos_faltantes`.
- **PRAZO_ENTREGA_AUSENTE:** Informar a data de entrega para avaliar safra, capacidade e certificações na data. Fonte: `pedido_estruturado.prazo_entrega`.
- **CAMPO_FALTANTE:** Confirmar campo: itens_especificos. Fonte: `pedido_estruturado.campos_faltantes`.
- **ITENS_NAO_ESPECIFICADOS:** É necessário definir quais produtos serão consultados ou cotados. Fonte: `pedido_estruturado.itens`.
- **DISPONIBILIDADE_FUTURA_A_CONFIRMAR:** Confirmar datas de retirada, disponibilidade e certificações vigentes nessas datas. Fonte: `pedido_estruturado.observacoes; cadastro de produtores`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: certificacao_organica. Fonte: `pedido_estruturado.observacoes`.

### PED-2026-011 — Tropical Fruits Exportadora

**Tipo:** consulta
**Prioridade:** baixa
**Status:** analise_sem_alocacao
**Prazo:** Não informado
**Requer confirmação:** Sim

#### Sugestões de alocação

- Nenhuma alocação sugerida.

#### Correspondências de ofertas

- Nenhuma correspondência identificada.

#### Histórico

- Não aplicável.

#### Alertas e fontes

- **CAMPO_FALTANTE:** Campo pendente: prazo_entrega Fonte: `pedido_estruturado.campos_faltantes`.
- **PRAZO_ENTREGA_AUSENTE:** Informar a data de entrega para avaliar safra, capacidade e certificações na data. Fonte: `pedido_estruturado.prazo_entrega`.
- **CAMPO_FALTANTE:** Confirmar campo: prazo_entrega. Fonte: `pedido_estruturado.campos_faltantes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: certificacao_organica. Fonte: `pedido_estruturado.observacoes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: certificacao_internacional. Fonte: `pedido_estruturado.observacoes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: rastreabilidade. Fonte: `pedido_estruturado.observacoes`.
- **DOCUMENTO_A_COMPROVAR:** Verificar a documentação exigida: certificado_fitossanitario. Fonte: `pedido_estruturado.observacoes`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de manga tommy depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de goiaba paluma depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.
- **AVALIACAO_DEPENDE_DO_PRAZO:** A disponibilidade de maracujá depende da data de entrega. Fonte: `pedido_estruturado.prazo_entrega`.

## Demanda da semana × capacidade documentada

| Produto | Semana | Demanda | Pedidos | Capacidade máx. | Excede? |
|---|---|---:|---|---:|---|
| alface | 2026-11-02 | 250.0 unidade | PED-2026-002, PED-2026-004 | Não informado | Não |
| banana prata | 2026-11-02 | 240.0 kg | PED-2026-002, PED-2026-004 | Não informado | Não |
| cebolinha | 2026-10-26 | 10.0 maço | PED-2026-001 | Não informado | Não |
| coentro | 2026-10-26 | 20.0 maço | PED-2026-001 | Não informado | Não |
| coentro | 2026-11-02 | 100.0 maço | PED-2026-004 | Não informado | Não |
| goiaba paluma | 2026-10-26 | 300.0 kg | PED-2026-006 | 800.0 | Não |
| goiaba paluma | 2026-11-02 | 150.0 kg | PED-2026-002, PED-2026-004 | 800.0 | Não |
| inhame | 2026-11-02 | 110.0 kg | PED-2026-002, PED-2026-004 | 200.0 | Não |
| macaxeira | 2026-11-02 | 210.0 kg | PED-2026-002, PED-2026-004 | 400.0 | Não |
| manteiga de garrafa | 2026-10-26 | 10.0 kg | PED-2026-001 | 40.0 | Não |
| maracujá | 2026-11-02 | 25.0 kg | PED-2026-002 | Não informado | Não |
| mel de jandaíra | 2026-10-26 | 3.0 kg | PED-2026-003 | 3.4521 | Não |
| mel silvestre | 2026-10-26 | 45.0 kg | PED-2026-001, PED-2026-006 | 151.6667 | Não |
| mel silvestre | 2026-11-02 | 20.0 kg | PED-2026-004 | 70.0 | Não |
| ovos caipira | 2026-11-02 | 100.0 dúzia | PED-2026-004 | Não informado | Não |
| queijo coalho | 2026-10-26 | 240.0 kg | PED-2026-001, PED-2026-005, PED-2026-006 | 480.0 | Não |
| queijo manteiga | 2026-10-26 | 50.0 kg | PED-2026-006 | Não informado | Não |
| ricota | 2026-10-26 | 5.0 kg | PED-2026-001 | Não informado | Não |
| rúcula | 2026-11-02 | 30.0 maço | PED-2026-002 | Não informado | Não |
| tomate | 2026-11-02 | 70.0 kg | PED-2026-002, PED-2026-004 | 400.0 | Não |

## Capacidade semanal sugerida

| Produtor | Produto | Quantidade | Unidade | Semana |
|---|---|---:|---|---|
| P003 | queijo coalho | 200.0 | kg | 2026-10-26 |
| P002 | mel silvestre | 45.0 | kg | 2026-10-26 |
| P001 | goiaba paluma | 300.0 | kg | 2026-10-26 |
| P002 | mel de jandaíra | 3.0 | kg | 2026-10-26 |
| P007 | queijo coalho | 40.0 | kg | 2026-10-26 |
| P007 | manteiga de garrafa | 10.0 | kg | 2026-10-26 |
| P005 | macaxeira | 210.0 | kg | 2026-11-02 |
| P005 | inhame | 110.0 | kg | 2026-11-02 |
| P001 | goiaba paluma | 50.0 | kg | 2026-11-02 |
| P012 | tomate | 20.0 | kg | 2026-11-02 |

**Confirmações realizadas:** Não

**Notificações enviadas:** Não
