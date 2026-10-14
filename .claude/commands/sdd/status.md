---
description: Mostra o estado de todas as specs e o que fazer em seguida
allowed-tools: Read, Bash, Glob, Grep
---

# Status das specs

Panorama do fluxo SDD neste repositório.

## Passos

1. Colete o estado:

   ```bash
   for d in specs/*/; do
     n=$(basename "$d")
     r=$([ -f "$d/requirements.md" ] && echo "sim" || echo "-")
     g=$([ -f "$d/design.md" ] && echo "sim" || echo "-")
     t=$([ -f "$d/tasks.md" ] && echo "sim" || echo "-")
     ab=$(grep -c '^\s*- \[ \]' "$d/tasks.md" 2>/dev/null || echo 0)
     ok=$(grep -c '^\s*- \[x\]' "$d/tasks.md" 2>/dev/null || echo 0)
     echo "$n | req:$r design:$g tasks:$t | concluídas:$ok abertas:$ab"
   done
   ```

2. Se não houver nenhuma spec, diga isso e explique que o começo é `/sdd:spec <nome>`.

3. Para a spec ativa (a que tem tarefas abertas), mostre as três próximas tarefas pendentes com
   os requisitos que atendem.

4. Verifique se o último veredito ainda vale:

   ```bash
   rg -l 'VERDICT: (PASS|FAIL)' specs/*/reviews/*.md 2>/dev/null | tail -3
   ```

## Formato de saída

```
Specs
  001-ingestao-bronze   req ✓  design ✓  tasks ✓   4/9 concluídas
  002-agregados-gold    req ✓  design -  tasks -   —

Ativa: 001-ingestao-bronze
  T-05  Adaptador de escrita Iceberg    REQ-006, REQ-007
  T-06  Registro da tabela EXTERNAL     REQ-008
  T-07  Wiring do CLI                   REQ-001

Próximo passo: /sdd:impl T-05
```

Seja conciso. Este comando é um panorama, não um relatório — quem quer detalhe roda
`/sdd:check`.
