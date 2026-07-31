---
description: Escreve ou revisa o design.md de uma spec (fase 2)
argument-hint: [NNN ou nome da spec]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# Fase 2 — Design

Produz ou revisa `design.md` da spec $ARGUMENTS.

## Pré-condição

`requirements.md` precisa existir e estar aprovado. Se não existir, **pare** e mande rodar
`/sdd:requirements` primeiro. Se existir mas o usuário não aprovou nesta sessão, confirme com
ele antes de seguir — design sobre requisito não aprovado é retrabalho garantido.

## Passos

1. Identifique a spec e leia `requirements.md` inteiro.

2. Se `design.md` já existir, leia antes: esta rodada é revisão. Preserve os ids `ADR-###`.

3. Delegue ao subagente `spec-arquiteto`, passando o caminho da spec e o feedback do usuário se
   for revisão.

4. Quando ele voltar, apresente:
   - as portas e adaptadores propostos, uma linha cada;
   - as ADRs, com a decisão em uma frase;
   - onde ele escolheu entre alternativas equivalentes;
   - qualquer requisito que ele apontou como incompleto.

5. **Gate.** Pergunte se aprova ou o que ajustar. Se algum requisito ficou incompleto, o
   caminho é voltar para `/sdd:requirements`, não remendar no design. Se aprovar, informe que o
   próximo passo é `/sdd:tasks`.
