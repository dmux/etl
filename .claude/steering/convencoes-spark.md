# Convenções de PySpark e SQL no minilake

O minilake **não é o Databricks**. É um emulador local com DuckDB por baixo do SQL e containers
Spark de verdade para os jobs. Quase todo erro nesse projeto vem de assumir paridade com o
Databricks. As regras abaixo vêm dos recursos `minilake://sql-dialect`,
`minilake://pyspark-guide` e `minilake://capabilities`.

## SQL roda em DuckDB, não em Spark SQL

O minilake reescreve exatamente três coisas antes de entregar ao DuckDB: identificadores com
crase viram aspas duplas, a cauda DDL `) USING DELTA [LOCATION ...]` é removida, e referências
a tabelas EXTERNAL Delta viram `delta_scan('<storage_location>')`. **Todo o resto passa
verbatim.**

Não existem no DuckDB, e portanto não use:

| Não use | Use |
| --- | --- |
| `MERGE INTO` | leia, calcule e reescreva a partição |
| `LATERAL VIEW` / `explode()` | `unnest()` |
| `date_format()` | `strftime()` |
| `from_unixtime()` | `to_timestamp()` |
| `collect_list()` | `list()` |
| `array_contains()` | `list_contains()` |
| `OPTIMIZE`, `VACUUM`, `DESCRIBE HISTORY` | não existem |
| `VERSION AS OF` / time travel | não existe |

Quando uma query falha, leia o erro do DuckDB literalmente — ele nomeia o token ou a função que
não reconheceu. Traduza, não conclua que o minilake está quebrado.

## Template de SparkSession

Não existe `spark` global injetado. Sempre construa a sua, e sempre com as duas configs Delta —
sem elas o erro é `ClassNotFoundException: io.delta.sql.DeltaSparkSessionExtension`:

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

Do lado da chamada, `run_python_script(script=..., delta=True, timeout_seconds=600)`. Sem
`delta=True` o erro é `DATA_SOURCE_NOT_FOUND: delta` — a imagem base não traz os jars. A
primeira execução resolve os jars no Maven e demora; dê folga no timeout.

PySpark sem Delta (`createDataFrame`, agregação, parquet, CSV) não precisa de nada disso.

## Escreva por path, leia por nome

O caminho de menor atrito, e o padrão deste projeto:

1. **Escrever** com PySpark, por path, sob `/data/` — o volume que o minilake e os containers
   de job enxergam:

   ```python
   df.write.format("delta").mode("overwrite").save("/data/delta/<catalogo>/bronze/<tabela>")
   ```

2. **Registrar** a tabela uma vez, como EXTERNAL:

   ```sql
   CREATE TABLE <catalogo>.bronze.<tabela> (...) USING DELTA
   LOCATION '/data/delta/<catalogo>/bronze/<tabela>'
   ```

3. **Ler** por nome de três partes via `run_sql` — o minilake reescreve para `delta_scan()`.

Consequências que valem lembrar:

- Só tabelas **EXTERNAL Delta** são visíveis ao Spark. Uma tabela MANAGED é uma tabela DuckDB
  sem arquivos: não dá para ler nem por nome nem por path — consulte com `run_sql`.
- `spark.table("cat.schema.tabela")` funciona, mas exige o conector Unity Catalog explícito
  (`packages=["io.unitycatalog:unitycatalog-spark_2.12:0.2.1"]` e as configs de catálogo). Use
  só quando o ponto for que o código seja idêntico ao que roda no Databricks real.
- `INSERT`/`UPDATE`/`DELETE` por nome numa EXTERNAL funcionam, mas o minilake executa cada um
  como um job Spark. Custa segundos, não milissegundos. Para carga em volume, sempre
  `run_python_script`.

## Escrita de dados

- Caminho canônico: `<raiz_delta>/<catalogo>/<camada>/<tabela>`, com os valores de
  `.claude/projeto.toml`, seção `[dados]`.
- Particione pelas colunas em `[dados] particionamento`. O critério para escolhê-las:
  aparecem no filtro da maioria das consultas **e** têm cardinalidade baixa. Nunca particione
  por coluna de alta cardinalidade (id, timestamp) — gera milhares de partições minúsculas e
  o pipeline fica mais lento do que sem particionamento nenhum.
- `mode("overwrite")` combinado com `replaceWhere` na partição sendo reprocessada.
  Reprocessar a mesma janela não pode duplicar linha (ver "idempotência" em `produto.md`).
- Schema é explícito, sempre. Nada de `inferSchema`, nada de `select("*")` numa transformação.
- Nomes de coluna vêm do `glossario-dados.md`.

## Logging

`logging`, nunca `print()`. Em job Spark o stdout é o canal de saída capturado — poluí-lo com
depuração atrapalha a leitura do resultado. Log com contexto acionável: quantas linhas, qual
arquivo, qual partição. `logger.info("ingeridos %d registros de %s", n, origem)`.

## Não existe no minilake

`NOT_IMPLEMENTED`, e nenhuma tentativa muda isso: **DLT/pipelines**, serving, model registry,
feature store, vector search, data quality, quality monitor, dashboards, alerts, query history,
marketplace, sharing, Repos/Git, notebooks `.ipynb`, tarefas dbt.

Orquestração neste projeto é **Jobs** com `depends_on`. Clusters existem só como máquina de
estados, sem compute — quem executa Spark de verdade é o Job.

Metadados vivem em memória e somem no restart, a menos que `MINILAKE_PERSIST=1`. Os arquivos em
`/data/` sempre sobrevivem. Se uma tabela "sumiu" depois de reiniciar, ela precisa ser
registrada de novo — o dado está lá.
