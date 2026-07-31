# O processo: Spec-Driven Development

Este repositório é desenvolvido por specs. A regra que governa todas as outras:

> **Nenhuma linha de código de produção nasce sem uma spec aprovada.**

## O ciclo

Três fases sequenciais, cada uma com um artefato e um **gate humano** ao final. O gate não é
formalidade: a fase seguinte só começa depois que o usuário aprovou explicitamente a anterior.

```
ideia
  │
  ├─ /sdd:spec <nome>          cria specs/NNN-<nome>/
  │
  ├─ /sdd:requirements  ──►  requirements.md   user stories + critérios EARS
  │                          [GATE: usuário aprova]
  │
  ├─ /sdd:design        ──►  design.md         portas, adaptadores, ADRs
  │                          [GATE: usuário aprova]
  │
  ├─ /sdd:tasks         ──►  tasks.md          tarefas rastreáveis a REQ-###
  │                          [GATE: usuário aprova]
  │
  ├─ /sdd:impl          ──►  código + testes, uma tarefa por vez, em TDD
  │
  └─ /sdd:check         ──►  lint + tipos + cobertura + matriz de rastreabilidade
```

## Estrutura de uma spec

```
specs/
└── 001-<nome-da-feature>/
    ├── requirements.md   O QUE o sistema deve fazer, e como se prova que faz
    ├── design.md         COMO será construído — decisões técnicas e contratos
    ├── tasks.md          EM QUE ORDEM — tarefas pequenas, verificáveis, rastreadas
    └── reviews/          relatórios do spec-validador, um por rodada de gate
```

Numeração sequencial de três dígitos, nome em kebab-case e em português.

## Rastreabilidade

É a espinha dorsal do processo. Cada elo aponta para o anterior:

- Todo requisito tem um id `REQ-###` em `requirements.md`.
- Toda tarefa em `tasks.md` declara quais `REQ-###` atende.
- Todo teste declara no docstring qual `REQ-###` cobre.
- `/sdd:check` monta a matriz **requisito → tarefa → teste → arquivo** e falha se algum
  requisito ficar sem teste.

Um requisito sem teste é um requisito não entregue, independente do que o código faça.

## Regras de conduta

- **Não pule fases.** Se pedirem "só implementa rápido", responda apontando a fase que falta
  e ofereça rodá-la. A pressa é exatamente o que este processo existe para conter.
- **Não invente requisito durante o design ou a implementação.** Se descobrir um requisito
  faltante, pare, registre em `requirements.md` e volte ao gate. Escopo cresce por decisão
  explícita do usuário, não por iniciativa do agente.
- **Uma tarefa por vez.** `/sdd:impl` implementa uma única tarefa e para. Isso mantém o
  diff revisável e o TDD honesto.
- **Mudou o requisito, atualiza a spec antes do código.** A spec é a fonte da verdade; código
  que diverge dela é bug de processo, não decisão de implementação.
- **O dado de origem é imutável.** Os diretórios em `[fontes] somente_leitura` de
  `.claude/projeto.toml` nunca são editados, movidos ou reescritos — um hook bloqueia a
  tentativa.

## Quando o processo não se aplica

Correção de typo, ajuste de formatação, mudança em documentação, ou consertar um teste que
quebrou por flakiness. Nesses casos vá direto. Na dúvida entre "é pequeno" e "é uma mudança
de comportamento": se muda comportamento observável, é spec.
