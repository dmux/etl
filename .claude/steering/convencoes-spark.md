# Convenções de PySpark em AWS Glue sobre o ministack

O alvo é um **job AWS Glue 4.0** rodando no **ministack**. Quase todo erro neste projeto vem de
assumir paridade total com a AWS. Cada regra abaixo foi confirmada executando jobs no ministack;
quando a AWS real se comporta diferente, isso está dito.

## Anatomia de um job

| Peça | Onde mora | Observação |
|---|---|---|
| script do job | `s3://<bucket>/scripts/<job>.py` (`Command.ScriptLocation`) | arquivo mínimo: lê argumentos e chama `<pacote>.cli` |
| código do pacote | `s3a://<bucket>/codigo/<pacote>.zip` (`--extra-py-files`) | vira `--py-files` no `spark-submit`; importa normalmente |
| dado de origem | `s3a://<bucket>/fonte/...` | somente leitura |
| tabelas | catálogo Iceberg `iceberg`, warehouse `s3a://<bucket>/warehouse` | registradas no Glue Data Catalog |

Tipo do job: `Command.Name = "glueetl"`, `GlueVersion = "4.0"`. `pythonshell` não roda Spark.

## Sessão e argumentos

A sessão vem do `GlueContext`, nunca de `SparkSession.builder` — o builder perde a configuração
que o Glue injeta (o guarda `glue-sessao` barra):

```python
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["camadas", "fonte"])
spark = GlueContext(SparkContext.getOrCreate()).spark_session
```

- **Não peça `JOB_NAME`.** A AWS sempre passa `--JOB_NAME`; o ministack não passa, e
  `getResolvedOptions(sys.argv, ["JOB_NAME"])` quebra com `GlueArgumentError`.
- `getResolvedOptions` ignora argumentos que não pediu. Use-o, não `argparse.parse_args`: o
  ministack repassa ao script **todos** os `DefaultArguments`, inclusive `--conf` e
  `--extra-py-files`.
- `awsglue` só existe na imagem. Importe dentro de `infrastructure/` ou `cli/`, nunca no topo de
  um módulo que os testes do host importam sem mock.

## Iceberg: a configuração que funciona

A imagem Glue 4.0 traz Iceberg 1.0.0 em `/home/glue_user/aws-glue-libs/datalake-connectors/`,
**fora** do classpath. `--datalake-formats iceberg` no ministack só injeta configuração, não os
jars. O argumento `--conf` do job precisa trazer:

```
spark.driver.extraClassPath=<J>/iceberg-spark-runtime-3.3_2.12-1.0.0.jar:<J>/bundle-2.17.161.jar:<J>/url-connection-client-2.17.161.jar:/home/glue_user/spark/jars/*:/home/glue_user/aws-glue-libs/jars/*
--conf spark.executor.extraClassPath=<o mesmo>
--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
--conf spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog
--conf spark.sql.catalog.iceberg.type=hadoop
--conf spark.sql.catalog.iceberg.warehouse=s3a://<bucket>/warehouse
```

com `<J> = /home/glue_user/aws-glue-libs/datalake-connectors/iceberg-1.0.0`. Por que cada peça:

- **Jars do Iceberg antes do resto no `extraClassPath`.** A imagem traz módulos soltos do AWS SDK
  v2 2.29 (`utils-2.29.29.jar`) que colidem com o `bundle-2.17.161` do Iceberg:
  `NoSuchMethodError: ...IoUtils.closeQuietly`. `spark.jars` não basta, porque entra depois.
- **Catálogo `type=hadoop`, não `GlueCatalog` nem REST.** O `GlueCatalog` do Iceberg 1.0 não tem
  `glue.endpoint` e fala com a AWS real (`security token ... invalid`). O REST do Glue no
  ministack aceita criar tabela, mas o commit dele não grava `snapshot-log`, e o cliente Java
  quebra em toda escrita (`NoSuchElementException` em `updateSnapshotLog`).
- **Registro no Glue Data Catalog via boto3**, depois de cada escrita: `table_type=ICEBERG` e
  `metadata_location` apontando para o `v<N>.metadata.json` lido de `version-hint.text`. É o
  mesmo registro que o `GlueCatalog` faz, e o que o Athena da AWS real lê. No job, o boto3 já
  aponta para o ministack (o boot do ministack injeta o endpoint).
- **Nunca toque o `spark_catalog`.** Na imagem Glue ele é Hive sobre um cliente Glue sem
  endpoint; um `CREATE DATABASE` sem catálogo explícito vai para a AWS real. Qualifique sempre:
  `iceberg.<banco>.<tabela>`.

## Escrita idempotente

| Situação | Operação |
|---|---|
| reprocessar algumas partições | `df.writeTo(t).overwritePartitions()` — troca só as partições presentes no DataFrame |
| trocar as linhas que casam com um filtro | `df.writeTo(t).overwrite(F.expr("arquivo IN (...)"))` |
| reescrever a tabela inteira | `df.writeTo(t).overwrite(F.lit(True))` |

`MERGE INTO` funciona com Iceberg no Spark, mas é desnecessário quando a chave de idempotência é
a partição. Nunca `append` seguido de deduplicação: a tabela fica errada entre as duas etapas.

Crie a tabela antes da primeira escrita, com DDL explícito e `PARTITIONED BY`. Sem `NOT NULL`
no DDL: o DataFrame criado a partir de linhas Python tem colunas anuláveis, e o Iceberg recusa
escrever coluna anulável em coluna obrigatória.

## Resultado e logs

- **Um job que falha pode terminar `SUCCEEDED`.** A imagem do OpenArchFlow canaliza a saída do
  `spark-submit` para o encaminhador de logs sem `pipefail`; o código de saída que vale é o do
  encaminhador. Até isso ser corrigido na imagem, o job registra no log uma linha-marcador
  (`<pacote>: codigo_saida=N`) e quem executa considera sucesso só se ela existir e for 0.
- A saída vai para o CloudWatch Logs, grupo `/aws-glue/jobs/output`, stream
  `spark-stdout-stream` — **um único stream para todas as execuções**. Apague o stream antes de
  executar se for ler o resultado de uma execução só.
- `logging`, nunca `print()`, em `src/`.

## Consultar o resultado

O Athena do ministack roda em DuckDB e lê CSV, JSON e Parquet sob o `LOCATION` de uma tabela do
Glue Catalog. **Ele não lê Iceberg**: lê os arquivos crus como CSV e falha. Confira resultados
com Spark, num passo do próprio job. Na AWS real, o Athena v3 lê o mesmo registro nativamente.

## Particionamento

Particione pelas colunas em `[dados] particionamento` de `.claude/projeto.toml`. O critério:
aparecem no filtro da maioria das consultas **e** têm cardinalidade baixa. Nunca por id ou
timestamp — milhares de partições minúsculas deixam tudo mais lento.

## Schema

Explícito, sempre: `StructType` declarado, nunca inferido, e nunca `select("*")` numa
transformação. Nomes de coluna vêm do `glossario-dados.md`.

## Desempenho no ministack

A imagem Glue é `linux/amd64`. Em Mac ARM ela roda emulada: um job pequeno leva de 1 a 3
minutos, quase tudo de inicialização da JVM. Agrupe as camadas num job só em vez de três jobs
para três subidas de JVM.
