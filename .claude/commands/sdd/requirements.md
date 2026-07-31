---
description: Escreve ou revisa o requirements.md de uma spec (fase 1)
argument-hint: [NNN ou nome da spec]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# Fase 1 — Requisitos

Produz ou revisa `requirements.md` da spec $ARGUMENTS.

## Passos

1. Identifique a spec. Sem argumento, liste as existentes e pergunte:

   ```bash
   for d in specs/*/; do echo "$d -> $(ls "$d" | tr '\n' ' ')"; done
   ```

2. Se `requirements.md` já existir, leia antes. Esta rodada é **revisão**, não reescrita do
   zero — preserve os ids `REQ-###` existentes. Requisito removido não é apagado: marque como
   `[REMOVIDO em NNN]` com o motivo.

3. Delegue ao subagente `spec-analista`, passando:
   - o caminho da spec;
   - o feedback do usuário, se for revisão;
   - o `requirements.md` atual, se existir.

4. Quando ele voltar, apresente:
   - a lista de requisitos, um por linha;
   - o que mudou nesta rodada, se for revisão;
   - as decisões que ele tomou sozinho e que podem ser revertidas;
   - as dúvidas em aberto.

5. **Gate.** Pergunte se aprova ou o que ajustar. Não siga para o design. Se aprovar, informe
   que o próximo passo é `/sdd:design`.
