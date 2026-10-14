---
name: glue-ministack
description: Como escrever, publicar, executar e depurar jobs AWS Glue 4.0 (PySpark + Iceberg) no ministack — sessão pelo GlueContext, argumentos sem JOB_NAME, classpath do Iceberg 1.0, catálogo hadoop com registro no Glue Data Catalog, escrita idempotente com overwritePartitions, o falso SUCCEEDED e onde ler o log. Use antes de escrever qualquer PySpark ou job Glue, ao publicar ou executar no ministack, ou ao depurar NoSuchMethodError do AWS SDK, GlueArgumentError, "security token included in the request is invalid", NoSuchElementException em updateSnapshotLog ou erro de CSV no Athena.
---

# AWS Glue no ministack

Leia `.claude/steering/convencoes-spark.md` — é a regra normativa. Esta skill é o roteiro
operacional: o ciclo completo de um job e o diagnóstico dos erros que aparecem.

## A confusão de origem

O ministack fala a API da AWS, mas não é a AWS. O job Glue roda de verdade (`spark-submit` na
imagem Glue 4.0), e o resto em volta — catálogo, Athena, resultado da execução — tem diferenças
que só aparecem executando. Todas as abaixo foram confirmadas.

## Ambiente

```bash
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
aws --endpoint-url http://localhost:4566 s3 ls          # ministack de pé?
docker ps --filter ancestor=ministackorg/ministack:full  # precisa montar /var/run/docker.sock
```

No zsh, um alias em variável (`A="aws --endpoint-url ..."; $A s3 ls`) não se divide em palavras.
Use uma função: `a() { aws --endpoint-url http://localhost:4566 "$@"; }`.

## O jeito curto: os comandos

| Comando | Faz |
| --- | --- |
| `/glue:executar [projeto]` | publica se algo mudou, executa todas as camadas e a verificação, mostra o resumo e, se falhar, o diagnóstico |
| `/glue:verificar [projeto]` | só lê os totais das tabelas com Spark, sem reprocessar |

Os dois funcionam em qualquer projeto que cumpra o **contrato**: alvos `executar` e `verificar`
no Makefile, um `scripts/glue.sh` que imprime as tabelas de resumo em markdown e a linha
`RESULTADO: sucesso|falha`, e o log filtrado em `dist/ultima-execucao.log`. O exemplo
`examples/futebol/` é a implementação de referência. Abaixo, o que eles fazem por dentro.

## O ciclo completo de um job

```bash
# 1. dado e código no S3
a s3 sync <fonte_local>/ s3://<bucket>/fonte/
(cd src && zip -qr ../dist/<pacote>.zip <pacote>)
a s3 cp dist/<pacote>.zip s3://<bucket>/codigo/<pacote>.zip
a s3 cp glue_job.py s3://<bucket>/scripts/glue_job.py

# 2. job (cria uma vez; depois update-job com o mesmo JobUpdate)
a glue create-job --name <job> --role arn:aws:iam::000000000000:role/glue --glue-version 4.0 \
  --command Name=glueetl,ScriptLocation=s3://<bucket>/scripts/glue_job.py,PythonVersion=3 \
  --default-arguments '{"--extra-py-files":"s3a://<bucket>/codigo/<pacote>.zip","--conf":"<CONF>", ...}'

# 3. executar e esperar
a logs delete-log-stream --log-group-name /aws-glue/jobs/output --log-stream-name spark-stdout-stream
run=$(a glue start-job-run --job-name <job> --query JobRunId --output text)
a glue get-job-run --job-name <job> --run-id "$run" --query JobRun.JobRunState   # até sair de RUNNING

# 4. resultado: pelo marcador no log, não pelo JobRunState
a logs get-log-events --log-group-name /aws-glue/jobs/output --log-stream-name spark-stdout-stream \
  --query 'events[].message' --output text | tr '\t' '\n' | grep '<pacote>: codigo_saida='
```

O `<CONF>` do Iceberg está, completo, em `convencoes-spark.md`. Use `s3a://` em tudo que o Spark
lê ou grava (`--extra-py-files`, fonte, warehouse): o ministack configura o S3A, não o `s3://`.
No registro do Glue Catalog, use `s3://`.

## Diagnóstico

| Sintoma no log | Causa | Correção |
|---|---|---|
| `GlueArgumentError: the following arguments are required: --JOB_NAME` | o ministack não passa `--JOB_NAME` | não peça `JOB_NAME` no `getResolvedOptions` |
| `NoSuchMethodError: software.amazon.awssdk.utils.IoUtils.closeQuietly` | AWS SDK v2 2.29 da imagem na frente do bundle 2.17 do Iceberg | jars do Iceberg **primeiro** no `extraClassPath` |
| `ClassNotFoundException: org.apache.iceberg...` | Iceberg fora do classpath | o `extraClassPath` do `<CONF>`; `--datalake-formats` não põe jars |
| `The security token included in the request is invalid` | algo falou com a AWS real: `GlueCatalog` do Iceberg 1.0 ou o `spark_catalog` Hive | catálogo `iceberg` do tipo `hadoop`; qualifique toda tabela com `iceberg.` |
| `NoSuchNamespaceException: No table bucket found` | REST do Iceberg roteado para o S3 Tables | não use o REST para escrever (ver a próxima linha) |
| `NoSuchElementException` em `TableMetadata$Builder.updateSnapshotLog` | o commit REST do Glue no ministack não grava `snapshot-log` | catálogo `hadoop` + registro via boto3 |
| `Cannot write nullable values to non-null column` | DDL com `NOT NULL` | DDL sem `NOT NULL` |
| Athena: `CSV Error ... This file is not utf-8 encoded` | o Athena do ministack não lê Iceberg | confira com Spark |
| `JobRunState = SUCCEEDED`, mas há `Traceback` no log | a imagem não propaga o código de saída | decida pelo marcador `codigo_saida=` |
| execução termina em segundos, sem log de Spark | ministack sem `/var/run/docker.sock`, ou imagem Glue ausente | suba o ministack com o socket; `docker pull` da imagem |

Para ler só o erro: `... --output text | tr '\t' '\n' | grep -E "Traceback|Caused by|Exception:"`.

## Registro no Glue Data Catalog

Depois de cada escrita, no job:

```python
versao = s3.get_object(Bucket=b, Key=f"warehouse/{banco}/{tabela}/metadata/version-hint.text")["Body"].read()
local = f"s3://{b}/warehouse/{banco}/{tabela}/metadata/v{int(versao)}.metadata.json"
entrada = {"Name": tabela, "TableType": "EXTERNAL_TABLE",
           "Parameters": {"table_type": "ICEBERG", "metadata_location": local},
           "StorageDescriptor": {"Location": f"s3://{b}/warehouse/{banco}/{tabela}"}}
# create_database se faltar; create_table, ou update_table se já existir
```

## Checklist antes de executar

- [ ] script do job não pede `JOB_NAME` e usa `getResolvedOptions`
- [ ] sessão do `GlueContext`, sem `SparkSession.builder`
- [ ] `<CONF>` com os jars do Iceberg na frente do `extraClassPath`
- [ ] toda tabela qualificada como `iceberg.<banco>.<tabela>`; nada no `spark_catalog`
- [ ] caminhos do Spark em `s3a://`
- [ ] escrita com `overwritePartitions`/`overwrite(...)`, nunca `append`
- [ ] registro no Glue Data Catalog depois de cada escrita
- [ ] linha `codigo_saida=` no fim do job, e quem executa lê o log, não o `JobRunState`
- [ ] `logging`, não `print()`
