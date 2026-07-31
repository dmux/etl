---
description: Cria uma nova spec e inicia a fase de requisitos
argument-hint: <nome-da-feature em kebab-case>
allowed-tools: Read, Write, Bash, Glob, Agent
---

# Nova spec: $ARGUMENTS

Cria a estrutura de uma spec nova e dispara a primeira fase do fluxo SDD.

## Passos

1. Determine o próximo número sequencial:

   ```bash
   ls -d specs/*/ 2>/dev/null | sed 's|specs/||;s|/||' | sort | tail -1
   ```

   O próximo é o maior + 1, com três dígitos. Se não existe nenhuma, comece em `001`.

2. Se `$ARGUMENTS` estiver vazio, pergunte ao usuário qual é a feature antes de continuar.
   Normalize para kebab-case, sem acento, no idioma de `[idioma] docs`: `ingestao-vendas`.

3. Se já existir uma spec com nome parecido, **pare** e mostre a existente. Duas specs para o
   mesmo assunto é o começo de dois vocabulários.

4. Crie `specs/NNN-<nome>/` e `specs/NNN-<nome>/reviews/`.

5. Antes de delegar, colete o essencial com o usuário, em poucas perguntas objetivas:
   - qual problema esta feature resolve;
   - quem consome o resultado;
   - o que está explicitamente fora de escopo.

   Não faça entrevista longa. O `spec-analista` aprofunda.

6. Delegue ao subagente `spec-analista` com o brief coletado, dizendo o caminho exato da spec.

7. Quando ele voltar, apresente o resumo dos requisitos e **pare no gate**: pergunte se aprova
   ou o que ajustar. Não siga para o design.
