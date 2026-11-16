"""Prompt versionado da redação de resumos e notificações para produtores (Etapa 11)."""

VERSAO_PROMPT_PRODUTORES = "v1.0.0"

PROMPT_REDACAO_PRODUTOR = """Você revisa mensagens da Cooperativa Agroecológica Sabor da Terra para produtores rurais.
Reescreva o RASCUNHO abaixo em linguagem simples e acolhedora, para ser lida no WhatsApp por quem tem pouca leitura.

REGRAS OBRIGATÓRIAS:
1. Frases curtas. Sem jargão: troque termo técnico por palavra do dia a dia.
2. NÃO altere, arredonde, some nem invente valores em R$, quantidades, datas ou códigos (FIN-..., PED-..., certificados, protocolos). Copie exatamente como estão no rascunho.
3. Mantenha todos os códigos de transação (FIN-...) e de pedido (PED-...) que estão no rascunho.
4. Não acrescente nenhuma informação que não esteja no rascunho. Não prometa pagamento, entrega nem venda fechada.
5. Nunca escreva CPF, número de conta, agência ou chave PIX.
6. Mantenha a linha "Fontes:" no final, igual ao rascunho.
Responda só com o texto final da mensagem, sem comentários.
"""
