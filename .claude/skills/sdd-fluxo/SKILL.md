---
name: sdd-fluxo
description: O ciclo Spec-Driven Development deste repositório — requirements, design, tasks, implementação e gates. Use quando o usuário pedir uma funcionalidade nova, um pipeline novo, uma mudança de comportamento, quando perguntar como o processo funciona, ou quando pedir para implementar algo que ainda não tem spec.
---

# O fluxo SDD deste repositório

Antes de qualquer coisa: **este projeto não aceita código sem spec aprovada**. Se o pedido é
uma funcionalidade ou mudança de comportamento, o caminho é o fluxo abaixo — não é uma etapa
burocrática opcional.

## Diagnóstico: em que ponto estamos?

Rode esta verificação antes de decidir o que fazer:

```bash
ls specs/*/ 2>/dev/null && for d in specs/*/; do
  echo "$d: $(ls "$d" | tr '\n' ' ')"
done
```

| O que existe | Próximo passo |
|---|---|
| nenhuma pasta em `specs/` para o assunto | `/sdd:spec <nome>` |
| só `requirements.md` | gate de requisitos → `/sdd:design` |
| `requirements.md` + `design.md` | gate de design → `/sdd:tasks` |
| os três, com tarefas abertas | `/sdd:impl` |
| todas as tarefas fechadas | `/sdd:check` |

## As fases

### 1. Requisitos — `/sdd:requirements`

Delega ao subagente `spec-analista`. Produz `specs/NNN-<nome>/requirements.md` com user stories
e critérios de aceitação em **EARS**. Responde *o que* e *como se prova*, nunca *como fazer*.

Erro comum: escrever solução técnica no requisito. "O sistema deve usar Iceberg particionado por
data" é design, não requisito. O requisito é "reprocessar a mesma janela não deve duplicar
registros".

### 2. Design — `/sdd:design`

Delega ao `spec-arquiteto`. Produz `design.md`: portas, adaptadores, fluxo de dados, schema das
tabelas, tratamento de erro, e ADRs para as decisões não óbvias. Toda decisão referencia o
`REQ-###` que a motiva. Design que não rastreia a requisito é escopo inventado.

### 3. Tarefas — `/sdd:tasks`

Delega ao `spec-planejador`. Produz `tasks.md`: lista de checkboxes, cada tarefa pequena o
bastante para caber num commit, declarando os `REQ-###` que atende e os arquivos que toca.
Ordem: domínio antes de aplicação, aplicação antes de infraestrutura — de dentro para fora.

### 4. Implementação — `/sdd:impl`

Delega ao `spec-implementador`, **uma tarefa por vez**, em TDD: teste vermelho, implementação,
refatoração. Ao final marca a tarefa em `tasks.md` e para. Não emenda a próxima tarefa sozinho.

### 5. Verificação — `/sdd:check`

Delega ao `spec-validador`: roda `make check` e monta a matriz requisito → tarefa → teste →
arquivo. Termina com `VERDICT: PASS` ou `VERDICT: FAIL`.

## Os gates

Entre cada fase existe um gate humano. Ao terminar uma fase:

1. Apresente o artefato produzido, resumido — não cole o arquivo inteiro.
2. Aponte explicitamente as decisões que precisam de confirmação e as dúvidas em aberto.
3. **Pare.** Pergunte se aprova ou o que mudar. Não emende a fase seguinte.

O gate é onde o usuário barata uma spec errada. Pular o gate significa descobrir o erro depois
de implementado.

## Quando o fluxo não se aplica

Typo, formatação, documentação, ou consertar teste flaky: vá direto. O critério é comportamento
observável — se muda, é spec.

## Convenções

- Pastas `specs/NNN-<nome-em-kebab-case>/`, numeração sequencial de três dígitos, nome no
  idioma de `[idioma] docs` em `.claude/projeto.toml`.
- Requisitos são `REQ-001`, `REQ-002`, … Tarefas são `T-01`, `T-02`, …
- Relatórios de gate vão em `specs/NNN-<nome>/reviews/`.
- Um requisito removido não é apagado: marque como `[REMOVIDO em NNN]` e diga por quê. O
  histórico da spec explica decisões futuras.
