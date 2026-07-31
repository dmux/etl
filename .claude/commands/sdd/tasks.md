---
description: Escreve ou revisa o tasks.md de uma spec (fase 3)
argument-hint: [NNN ou nome da spec]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# Fase 3 — Tarefas

Produz ou revisa `tasks.md` da spec $ARGUMENTS.

## Pré-condição

`requirements.md` e `design.md` precisam existir e estar aprovados. Faltando algum, **pare** e
indique a fase que falta.

## Passos

1. Identifique a spec e leia os dois artefatos anteriores.

2. Se `tasks.md` já existir, leia antes. **Nunca renumere tarefas já concluídas** — os ids
   `T-NN` são referenciados em commits e relatórios de validação. Tarefa nova entra no fim.

3. Delegue ao subagente `spec-planejador`.

4. Quando ele voltar, apresente:
   - a lista de tarefas, uma linha cada, com dependências;
   - a matriz REQ → tarefas, destacando REQ com cobertura fraca;
   - qual tarefa ele considera a mais arriscada.

5. **Gate.** Pergunte se aprova ou o que ajustar. Se algum REQ ficou sem tarefa, isso é bug do
   plano — resolva antes de aprovar. Se aprovar, informe que o próximo passo é `/sdd:impl`.
