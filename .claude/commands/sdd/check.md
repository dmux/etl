---
description: Roda o gate de qualidade e a matriz de rastreabilidade, com veredito PASS/FAIL
argument-hint: [NNN ou nome da spec]
allowed-tools: Read, Write, Bash, Glob, Grep, Agent
---

# Verificação — $ARGUMENTS

Roda o gate completo e confere se a implementação corresponde à spec.

## Passos

1. Identifique a spec. Sem argumento, valide a spec com tarefas mais recentes; se houver mais
   de uma candidata, pergunte.

2. Delegue ao subagente `spec-validador`, passando o caminho da spec.

3. Apresente o resultado do relatório dele:
   - o quadro do gate (ruff, format, mypy, cobertura) com os números reais;
   - os requisitos sem teste, se houver — este é o item mais importante;
   - as violações estruturais, com arquivo e linha;
   - as divergências do design;
   - o veredito.

4. Se `VERDICT: FAIL`, liste em ordem o que precisa acontecer para virar PASS e ofereça
   começar pelo primeiro item. Não conserte nada sem o usuário pedir.

O relatório completo fica em `specs/NNN-<nome>/reviews/validacao.md`.
