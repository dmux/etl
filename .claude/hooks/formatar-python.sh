#!/usr/bin/env bash
# PostToolUse (Write|Edit): roda ruff no arquivo Python recém-tocado.
#
# Formatar na hora evita que o pre-commit reclame depois de um lote de mudanças, quando o
# agente já perdeu o contexto do que escreveu.
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

entrada=$(cat)
caminho=$(printf '%s' "$entrada" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

case "$caminho" in
  *.py) ;;
  *) exit 0 ;;
esac

[ -f "$caminho" ] || exit 0
command -v uv >/dev/null 2>&1 || exit 0

uv run --quiet ruff check --fix --exit-zero "$caminho" >/dev/null 2>&1
uv run --quiet ruff format "$caminho" >/dev/null 2>&1

exit 0
