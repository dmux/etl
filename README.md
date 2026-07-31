# Base para pipelines de dados guiados por spec

Template de projeto para engenharia de dados com **Spec-Driven Development** no estilo AWS Kiro,
implementado inteiramente com primitivas nativas do Claude Code — sem spec-kit, sem CLI externo.

Alvo de execução: [minilake](https://github.com/rafaelsales/minilake), emulador local da API do
Databricks (PySpark + Delta reais, SQL em DuckDB).

**Agnóstico de domínio.** Todo o conteúdo específico de um projeto mora em dois arquivos de
configuração. Os artefatos do framework — steering, skills, agentes, comandos, hooks e guardas —
se especializam lendo deles.

## Como o desenvolvimento funciona aqui

Nenhuma linha de código de pipeline nasce sem uma spec aprovada:

```
/sdd:spec <feature>     cria specs/NNN-<feature>/
/sdd:requirements       requirements.md  — user stories + critérios EARS   [gate humano]
/sdd:design             design.md        — portas, adaptadores, ADRs       [gate humano]
/sdd:tasks              tasks.md         — tarefas rastreáveis a REQ-###   [gate humano]
/sdd:impl               implementa UMA tarefa, em TDD
/sdd:check              lint + tipos + cobertura + matriz de rastreabilidade
/sdd:status             onde cada spec parou
/sdd:steering           revisa as regras do projeto
```

## Instanciando num projeto novo

1. **`.claude/projeto.toml`** — nome do pacote, catálogo, camadas, particionamento, diretórios
   de origem somente-leitura, idioma dos identificadores.
2. **`.claude/glossario.toml`** — sinônimos proibidos. Começa vazio; cresce a cada spec.
3. **`.claude/steering/produto.md`** — o que o pipeline entrega e para quem. Tem placeholders.
4. **`.claude/steering/glossario-dados.md`** — a linguagem ubíqua. Tem placeholders.
5. `pyproject.toml` — troque o nome do pacote e reative o bloco de build quando `src/` nascer.

Nada mais precisa ser tocado. Se você se pegar editando uma skill ou um agente para falar do seu
domínio, provavelmente a informação deveria estar num desses arquivos.

## O que vem junto

**Steering** (`.claude/steering/`) — cinco regras sempre carregadas: o processo SDD, o produto,
a stack, a estrutura hexagonal e os critérios de qualidade. Mais duas sob demanda: convenções de
Spark/minilake e o glossário de dados.

**Skills** (`.claude/skills/`) — `sdd-fluxo`, `spec-ears`, `design-hexagonal`, `minilake-spark`,
`testes-spark-95`, `glossario-dados`.

**Subagentes** (`.claude/agents/`) — um por fase: `spec-analista`, `spec-arquiteto`,
`spec-planejador`, `spec-implementador`, `spec-validador` (emite `VERDICT: PASS|FAIL`).

**Hooks** (`.claude/hooks/`) — bloqueia escrita nas fontes somente-leitura, roda ruff no arquivo
recém-editado, injeta o status das specs no início da sessão.

**Guardas de pre-commit** (`tools/precommit/`) — oito verificações que só falhariam em runtime,
dentro de um container, com stack trace inútil:

| Guarda | Barra |
|---|---|
| `hexagonal-imports` | `pyspark`/`delta`/`databricks` em `domain/` ou `application/` |
| `spark-no-driver-collect` | `.collect()`/`.toPandas()`/`.count()` fora de `infrastructure/` |
| `spark-no-print` | `print()` em `src/` |
| `spark-delta-config` | `SparkSession` sem as duas configs do Delta |
| `minilake-sql-dialect` | `MERGE INTO`, `OPTIMIZE`, `VACUUM`, `explode`, `date_format`, … |
| `spark-no-select-star` | `select("*")` e `SELECT *` |
| `glossario` | sinônimos divergentes de `.claude/glossario.toml` |
| `sem-excecao-engolida` | `except: pass` |

## Comandos

```bash
make install   # dependências + hooks de git
make check     # lint + mypy + cobertura (gate de 95%)
make hooks     # pre-commit em todos os arquivos
make up        # sobe o minilake em http://localhost:8000
make e2e       # testes contra o minilake real
```

## Arquitetura

Hexagonal. O domínio é Python puro e não conhece Spark:

```
src/<pacote>/
  domain/          regras, parsing, cálculo — zero dependência de framework
  application/     portas (Protocol) e casos de uso
  infrastructure/  adaptadores: Spark, Delta, filesystem, catálogo
  cli/             entrypoint do job
```

Essa separação é o que torna a meta de 95% viável: a complexidade real é testada sem subir uma
`SparkSession`, em milissegundos. Spark aparece só nos adaptadores, cobertos por mock.

## examples/

Material de referência, **não carregado** pelo agente: artefatos de domínio já escritos, para
mostrar como esta base fica depois de instanciada.
