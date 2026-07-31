#!/usr/bin/env bash
# SessionStart: injeta o estado das specs no contexto inicial da sessão.
#
# Faz o agente começar sabendo em que fase o trabalho parou, em vez de precisar descobrir.
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

if [ ! -d specs ] || [ -z "$(ls -A specs 2>/dev/null)" ]; then
  echo "Specs: nenhuma ainda. Feature nova começa com /sdd:spec <nome>."
  exit 0
fi

echo "Estado das specs (SDD):"
for d in specs/*/; do
  [ -d "$d" ] || continue
  nome=$(basename "$d")
  req=$([ -f "$d/requirements.md" ] && echo "req" || echo "---")
  des=$([ -f "$d/design.md" ] && echo "design" || echo "------")
  tsk=$([ -f "$d/tasks.md" ] && echo "tasks" || echo "-----")

  if [ -f "$d/tasks.md" ]; then
    abertas=$(grep -c '^\s*- \[ \]' "$d/tasks.md" 2>/dev/null || true)
    feitas=$(grep -c '^\s*- \[x\]' "$d/tasks.md" 2>/dev/null || true)
    progresso="${feitas:-0} feitas, ${abertas:-0} abertas"
  else
    progresso="sem tarefas"
  fi

  echo "  $nome  [$req $des $tsk]  $progresso"
done

echo "Detalhe: /sdd:status · Gate: /sdd:check"
exit 0
