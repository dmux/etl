# Base para pipelines de dados guiados por spec

Template de projeto para engenharia de dados com **Spec-Driven Development** no estilo AWS Kiro,
implementado inteiramente com primitivas nativas do Claude Code — sem spec-kit, sem CLI externo.

Alvo de execução: jobs **AWS Glue 4.0** (PySpark + Iceberg) no [ministack](https://hub.docker.com/r/ministackorg/ministack),
emulador local da AWS. O job roda de verdade, num container da imagem Glue, e as tabelas ficam no
S3 e no Glue Data Catalog do ministack.

**Agnóstico de domínio.** Todo o conteúdo específico de um projeto mora em dois arquivos de
configuração. Os artefatos do framework — steering, skills, agentes, comandos, hooks e guardas —
se especializam lendo deles.

## Propósito

Agentes de IA escrevem código de pipeline rápido demais e sem rastro: a regra de negócio vai
parar dentro do Spark, ninguém sabe qual requisito um teste prova, e o erro só aparece no
container, em produção. Esta base existe para conter isso, em três frentes:

| Frente | Como |
| --- | --- |
| **Processo** | nenhum código nasce sem spec aprovada: requisitos em EARS, design com ADRs e tarefas rastreadas a `REQ-###`, com um gate humano entre cada fase |
| **Arquitetura** | hexagonal: parsing, regras e cálculos em Python puro, testados sem JVM; Spark e AWS só nos adaptadores. É o que torna viável o gate de 95% de cobertura |
| **Guardas** | hooks e pre-commit barram, na hora, os erros que só falhariam em runtime: framework no domínio, `print()`, sessão fora do `GlueContext`, sinônimo fora do glossário, escrita na fonte imutável |

Ela é **agnóstica de domínio**: serve a qualquer pipeline de dados, e um projeto novo começa
preenchendo `.claude/projeto.toml` e o glossário.

`examples/futebol/` mostra a base aplicada a um caso real, de ponta a ponta: um pipeline que lê
os resultados do futebol brasileiro publicados pelo openfootball e os transforma em tabelas
Iceberg, executado como job AWS Glue no ministack. O `PROCESSO.md` dele conta como foi construído,
fase a fase, do ponto de vista de quem desenvolve.

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

/glue:executar          executa o pipeline como job AWS Glue no ministack e mostra cada camada
/glue:verificar         mostra os totais das tabelas, sem reprocessar
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
Glue/ministack e o glossário de dados.

**Skills** (`.claude/skills/`) — `sdd-fluxo`, `spec-ears`, `design-hexagonal`, `glue-ministack`,
`testes-spark-95`, `glossario-dados`.

**Subagentes** (`.claude/agents/`) — um por fase: `spec-analista`, `spec-arquiteto`,
`spec-planejador`, `spec-implementador`, `spec-validador` (emite `VERDICT: PASS|FAIL`).

**Hooks** (`.claude/hooks/`) — bloqueia escrita nas fontes somente-leitura, roda ruff no arquivo
recém-editado, injeta o status das specs no início da sessão.

**Guardas de pre-commit** (`tools/precommit/`) — oito verificações que só falhariam em runtime,
dentro de um container, com stack trace inútil:

| Guarda | Barra |
|---|---|
| `hexagonal-imports` | `pyspark`/`awsglue`/`boto3` em `domain/` ou `application/` |
| `spark-no-driver-collect` | `.collect()`/`.toPandas()`/`.count()` fora de `infrastructure/` |
| `spark-no-print` | `print()` em `src/` |
| `glue-sessao` | `SparkSession.builder` em `src/`: a sessão vem do `GlueContext` |
| `athena-sql-dialect` | em `.sql`: `MERGE INTO`, `OPTIMIZE`, `VACUUM`, `explode`, … que o Athena do ministack (DuckDB) não tem |
| `spark-no-select-star` | `select("*")` e `SELECT *` |
| `glossario` | sinônimos divergentes de `.claude/glossario.toml` |
| `sem-excecao-engolida` | `except: pass` |

## Comandos

```bash
make install   # dependências + hooks de git
make check     # lint + mypy + cobertura (gate de 95%)
make hooks     # pre-commit em todos os arquivos
make up        # sobe o ministack em http://localhost:4566
make e2e       # testes contra o ministack real
```

## Arquitetura

Hexagonal. O domínio é Python puro e não conhece Spark:

```
src/<pacote>/
  domain/          regras, parsing, cálculo — zero dependência de framework
  application/     portas (Protocol) e casos de uso
  infrastructure/  adaptadores: Spark, Iceberg, S3, Glue Data Catalog
  cli/             entrypoint do job
```

Essa separação é o que torna a meta de 95% viável: a complexidade real é testada sem subir uma
`SparkSession`, em milissegundos. Spark aparece só nos adaptadores, cobertos por mock.

## examples/

Material de referência, **não carregado** pelo agente: artefatos de domínio já escritos, para
mostrar como esta base fica depois de instanciada.
