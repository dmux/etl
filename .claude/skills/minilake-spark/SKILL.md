---
name: minilake-spark
description: Restrições reais do minilake ao escrever PySpark, SQL ou Delta — dialeto DuckDB (sem MERGE INTO, OPTIMIZE, VACUUM, explode, date_format), template obrigatório de SparkSession com as configs Delta, escrita por path e registro de tabela EXTERNAL. Use antes de escrever qualquer código PySpark, qualquer SQL, ao criar ou consultar tabela no minilake, ou ao depurar erro de DATA_SOURCE_NOT_FOUND, ClassNotFoundException ou erro de parser do DuckDB.
---

# PySpark e SQL no minilake

Leia `.claude/steering/convencoes-spark.md` — é a regra completa e normativa. Esta skill é o
roteiro operacional para não errar nos casos que mais aparecem.

## A confusão de origem

O minilake fala a API do Databricks, mas por baixo são **duas engines diferentes**:

- **SQL** (`run_sql`, warehouse) → **DuckDB**
- **Jobs / `run_python_script`** → **Spark de verdade**, em container irmão

Quase todo erro vem de escrever Spark SQL e mandar para o caminho do DuckDB.

## Antes de escrever, escolha o caminho

| Você quer | Use | Por quê |
|---|---|---|
| carregar volume de dados | `run_python_script(delta=True)`, escrita por path | rápido, é Spark de verdade |
| consultar, agregar, conferir | `run_sql` com nome de três partes | o minilake reescreve para `delta_scan()` |
| alterar poucas linhas de uma EXTERNAL | `run_sql` com `UPDATE`/`DELETE` | funciona, mas cada comando vira um job Spark — segundos |
| alterar muitas linhas | `run_python_script` | nunca faça carga em volume por SQL |

## Template de sessão

Não existe `spark` global. Sempre construa, sempre com as duas configs:

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .getOrCreate()
)
```

E do lado da chamada: `run_python_script(script=..., delta=True, timeout_seconds=600)`.

## Diagnóstico de erro

| Erro | Causa | Correção |
|---|---|---|
| `DATA_SOURCE_NOT_FOUND: delta` | faltou `delta=True` na chamada | a imagem base não tem os jars |
| `ClassNotFoundException: io.delta.sql.DeltaSparkSessionExtension` | faltaram as configs de sessão | use o template acima |
| `Parser Error` / `Catalog Error` do DuckDB | Spark SQL onde só roda DuckDB | traduza a função; a tabela abaixo lista as equivalências |
| tabela "sumiu" depois de reiniciar | metadados são em memória | registre de novo; os arquivos em `/data/` continuam lá |
| Spark não enxerga a tabela | ela é MANAGED | só EXTERNAL Delta é visível ao Spark; consulte por `run_sql` |
| primeira execução estoura o timeout | resolução de jars no Maven | aumente `timeout_seconds`; depois fica em cache |

## Traduções de SQL obrigatórias

`MERGE INTO` → leia, calcule e reescreva a partição · `explode()`/`LATERAL VIEW` → `unnest()` ·
`date_format()` → `strftime()` · `from_unixtime()` → `to_timestamp()` · `collect_list()` →
`list()` · `array_contains()` → `list_contains()`.

Não existem: `OPTIMIZE`, `VACUUM`, `DESCRIBE HISTORY`, `VERSION AS OF`.

## O ciclo completo de uma tabela

```python
# 1. escrever por path, sob /data/ (o volume compartilhado)
caminho = "/data/delta/<catalogo>/bronze/<tabela>"
(df.write.format("delta")
   .mode("overwrite")
   .partitionBy(*PARTICIONAMENTO)   # de [dados] particionamento
   .save(caminho))
```

```sql
-- 2. registrar uma vez como EXTERNAL
CREATE TABLE <catalogo>.bronze.<tabela> (
  <coluna> STRING, <coluna> INT
) USING DELTA LOCATION '/data/delta/<catalogo>/bronze/<tabela>';
```

```sql
-- 3. consultar por nome
SELECT <coluna>, count(*) FROM <catalogo>.bronze.<tabela> GROUP BY 1 ORDER BY 1;
```

## Checklist antes de rodar

- [ ] `delta=True` na chamada e as duas configs na sessão
- [ ] caminho começa com `/data/` — é o único volume que o container de job enxerga
- [ ] schema explícito, sem `inferSchema`, sem `select("*")`
- [ ] particionado pelas colunas de `[dados] particionamento` (baixa cardinalidade, muito usadas em filtro)
- [ ] `logging`, não `print()` (exceto o `print` final de resultado, que é o canal de retorno)
- [ ] nenhuma função da lista de traduções sobrou no SQL
- [ ] reprocessar a mesma janela não duplica — `replaceWhere` na partição

## O que não existe

DLT/pipelines, serving, model registry, feature store, vector search, data quality, dashboards,
alerts, query history, sharing, Repos/Git, notebooks `.ipynb`, tarefas dbt. Retornam
`NOT_IMPLEMENTED` e insistir não muda. Orquestração é **Jobs** com `depends_on`; clusters são só
máquina de estados, sem compute.
