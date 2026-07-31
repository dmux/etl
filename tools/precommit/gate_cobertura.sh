#!/usr/bin/env bash
# Gate de cobertura, no estágio de pre-push.
#
# Só roda quando existe código de produção. Num repositório recém-instanciado, `src/` ainda não
# nasceu — a primeira spec é que o cria — e exigir 95% de cobertura de zero arquivo tornaria o
# próprio template impossível de publicar.
#
# A partir do momento em que existe um .py em src/, o gate passa a valer e não abre exceção.
set -euo pipefail

if ! find src -name '*.py' -print -quit 2>/dev/null | grep -q .; then
  echo "gate de cobertura: src/ ainda não tem código — nada a cobrir, pulando."
  exit 0
fi

exec uv run pytest -m "not e2e" --cov --cov-report=term-missing
