# CONTRIBUTING — Convenções de trabalho

> Como vamos trabalhar neste repositório. Vale para toda issue, branch,
> commit e Pull Request do projeto Sabor da Terra.
> Definido na Etapa 1 (#1), seguindo o padrão já usado no histórico do repo.

## 1. Fluxo de trabalho

1. **Issue primeiro:** toda mudança nasce de uma issue criada pelo template
   `.github/ISSUE_TEMPLATE/etapa-do-desafio.md`, com responsável, label e milestone.
2. **Branch dedicada:** o trabalho acontece em branch, nunca direto na `main`.
3. **Pull Request:** ao abrir o PR, descrição do que muda e `Closes #N`
   referenciando a(s) issue(s) que ele resolve.
4. **Revisão:** o PR só entra na `main` com **ao menos 1 aprovação de outro
   integrante**. Ninguém aprova o próprio PR.
5. **Quadro:** mover o card no GitHub Projects
   (Backlog → Em andamento → Em revisão → Concluído) conforme o estado real.

## 2. Branches

- Formato: **`etapa-N/descricao-curta`** (kebab-case), onde `N` é o número da issue.
  - Ex.: `etapa-3/ambiente-gemini`
- Quando um PR resolve **mais de uma issue**, usar os números das duas etapas:
  - Ex.: `etapa-1-2/kickoff-e-arquitetura`
- Branch é descartável: criada da `main` atualizada, vida curta, apagada após o merge.

## 3. Commits

- Formato igual ao do histórico do repositório: **`Tema: descrição em português`**
  — tema curto no imperativo, descrição direta.
- Corpo em tópicos (`- item`) quando o commit precisar de detalhe.
- Um tema lógico por commit; sem commit vazio e sem misturar frentes não relacionadas.

Exemplo (do histórico):

```
Diretriz de arquitetura: estratégia de custo da API Gemini (free tier)

- Regras de divisão de modelos e plano B documentadas
```

## 4. Pull Requests

- Título no mesmo formato do commit (`Tema: descrição em português`).
- Corpo com: o que muda, por quê, e `Closes #N` para cada issue resolvida.
- **Ao menos 1 revisão/aprovação** de outro integrante antes do merge.
- Sem push direto na `main`: a branch está protegida
  (PR obrigatório, 1 aprovação, resolução de comentários, sem force-push).

## 5. Confidencialidade (regra do `docs/01`)

- O **PDF original do projeto é confidencial**: nenhum trecho dele vai para fora
  deste repositório privado — não colar em issues, PRs, sites, chats públicos
  ou apresentações de terceiros.
- O dataset em `data/` é fictício, mas contém **CPF, PIX e dados bancários
  simulados**: o repositório **deve permanecer privado**; nunca subir cópia
  dos dados para outro lugar.
- Chaves de API nunca entram no repositório (ver `docs/03` §Regras de desenvolvimento).
- **Hook de pre-commit** (bloqueia `.env` trackeado e chave `AIza...` no commit):
  instale uma vez por clone com
  `install -m 0755 scripts/hooks/pre-commit .git/hooks/pre-commit`.
  A checagem fica no hook (não no pytest): a suíte roda em qualquer máquina,
  com ou sem `.git`, sem varrer o histórico inteiro a cada execução.

## 6. Issues

- Uma issue = uma etapa, criada pelo template, **em ordem**.
- Toda issue tem: responsável(is), label e milestone.
- Dúvidas de leitura dos `docs/01`–`03` viram comentário na issue correspondente.
