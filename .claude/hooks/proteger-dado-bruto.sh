#!/usr/bin/env bash
# PreToolUse (Write|Edit): bloqueia escrita nos diretórios de dado bruto do projeto.
#
# Quais diretórios são protegidos vem de .claude/projeto.toml, seção [fontes]:
#
#   [fontes]
#   somente_leitura = ["dados/raw/", "vendor/"]
#
# O princípio é agnóstico de domínio: dado de origem é imutável. Toda correção acontece na
# transformação, nunca na fonte — senão o pipeline diverge da origem e a próxima
# sincronização apaga a mudança em silêncio.
#
# Protocolo: sai com 2 e escreve em stderr, para o agente ler o motivo e se corrigir.
set -uo pipefail

raiz="${CLAUDE_PROJECT_DIR:-.}"
config="$raiz/.claude/projeto.toml"

entrada=$(cat)
caminho=$(printf '%s' "$entrada" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

[ -z "$caminho" ] && exit 0
[ -f "$config" ] || exit 0

# Extrai os itens de somente_leitura = [...] — uma linha, entre aspas.
protegidos=$(
  sed -n '/^[[:space:]]*somente_leitura[[:space:]]*=/,/]/p' "$config" |
    grep -oE '"[^"]+"' | tr -d '"'
)

[ -z "$protegidos" ] && exit 0

# Normaliza o caminho para relativo à raiz do projeto.
relativo="${caminho#"$raiz"/}"

while IFS= read -r padrao; do
  [ -z "$padrao" ] && continue
  padrao="${padrao%/}"
  case "$relativo" in
    "$padrao"|"$padrao"/*)
      cat >&2 <<MSG
BLOQUEADO: '$padrao' é dado de origem, imutável neste projeto.

Editar a fonte faz o pipeline divergir da origem, e a próxima sincronização apaga a
mudança em silêncio. Configurado em .claude/projeto.toml, seção [fontes].

O que fazer:
  - o dado não parseia      -> trate na camada de domínio (parsing/normalização)
  - o dado está errado      -> registre como registro rejeitado e reporte à origem
  - precisa de um exemplo   -> copie o trecho para uma fixture em tests/
  - a fonte deixou de ser somente-leitura -> mude .claude/projeto.toml, com intenção
MSG
      exit 2
      ;;
  esac
done <<<"$protegidos"

exit 0
