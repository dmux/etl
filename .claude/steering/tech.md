# Stack técnica

Esta lista é fechada. Adicionar uma dependência nova é uma decisão de design que vai numa ADR
dentro do `design.md` da spec que precisa dela — não é escolha de implementação.

## Runtime: AWS Glue 4.0

O pipeline roda como **job AWS Glue** (`glueetl`, Glue 4.0). A versão de tudo abaixo é a da
imagem do Glue, não a que se escolheria num projeto Python solto.

| Item | Versão | Observação |
|---|---|---|
| Python do job | **3.10** | o da imagem Glue 4.0. O código de `src/` precisa rodar nele: ruff e mypy miram 3.10 |
| Python de desenvolvimento | 3.11 | fixado em `.python-version`; só para ferramentas e testes no host |
| PySpark | 3.3.0 | o do Glue 4.0 (`3.3.0-amzn-1`). No host serve para tipos e mocks; não há JVM |
| Apache Iceberg | 1.0.0 | formato das tabelas. Vem na imagem, fora do classpath padrão (ver `convencoes-spark.md`) |
| awsglue | da imagem | `GlueContext`, `getResolvedOptions`. Não existe no host: importe só dentro de `infrastructure/` e `cli/` |
| boto3 | da imagem | registro no Glue Data Catalog e leitura de S3 no job. Não é dependência do host |
| pydantic | >=2 | validação nas fronteiras (entrada de config, contratos de porta) |

Nada além da stdlib, do PySpark e do que a imagem Glue traz pode ser importado pelo código que
roda no job. Biblioteca nova no job é `--additional-python-modules`, e isso é ADR.

## Ferramentas

| Item | Papel |
|---|---|
| **uv** | gerenciador de pacotes e ambiente. Todo comando roda via `uv run` |
| **ruff** | linter e formatter, `line-length = 120`, `target-version = "py310"` |
| **mypy** | `strict = true` sobre `src/`, `python_version = "3.10"` |
| **pytest** | testes; markers `unit`, `integration`, `e2e` |
| **pytest-cov** | cobertura com `fail_under = 95` — é gate, não relatório |
| **pre-commit** | guardas de commit, incluindo hooks específicos de pipeline Spark |
| **AWS CLI v2** | publicar, executar e inspecionar jobs no ministack (`--endpoint-url`) |

## Infraestrutura: ministack

**ministack** é o alvo de execução: um emulador local de serviços AWS (S3, Glue, Athena,
CloudWatch Logs…) na porta 4566. **Não** é a AWS. Um job Glue roda de verdade, por
`spark-submit --master local[*]`, num container irmão criado a partir da imagem Glue.

```bash
docker run -d -p 4566:4566 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e GLUE_DOCKER_IMAGE=ghcr.io/dmux/openarchflow/ministack_glue_libs_4.0.0_image_01:latest \
  -e S3_PERSIST=1 \
  ministackorg/ministack:full
```

O socket do Docker é obrigatório: sem ele o ministack não cria o container do job e marca a
execução como concluída sem rodar nada.

As diferenças em relação à AWS que mudam o desenho — todas confirmadas executando jobs — estão
em `convencoes-spark.md` e na skill `glue-ministack`. Leia antes de escrever qualquer PySpark.
Em uma linha cada:

- `--JOB_NAME` não é passado ao script; `getResolvedOptions` não pode exigi-lo.
- Um job que falha pode terminar `SUCCEEDED`: o resultado vem de uma linha-marcador no log.
- O `GlueCatalog` do Iceberg 1.0 não aceita endpoint e o REST do ministack não aceita commit do
  Spark: tabelas são escritas por catálogo `hadoop` no S3 e registradas no Glue via boto3.
- O Athena do ministack não lê Iceberg; a conferência de resultado é feita por Spark.
- A imagem Glue é amd64: em Mac ARM roda emulada, e um job leva minutos.

Endpoint: `http://localhost:4566`, credenciais `test`/`test`, região `us-east-1`.

## Ambiente local

Java **não** está instalado no host. Consequência prática:

- Testes marcados `integration` (que sobem uma `SparkSession` local) são **pulados** por padrão
  via `skipif` — não falham, não mentem sobre cobertura.
- Adaptadores Spark e Glue são cobertos por testes unitários com `unittest.mock`, verificando as
  chamadas feitas ao Spark, ao S3 e ao Glue.
- A validação com Spark de verdade acontece no ministack (`make e2e`), que traz o próprio runtime
  na imagem Glue.

## Comandos

```bash
make install   # dependências + hooks de git
make check     # lint + mypy + cobertura (o gate)
make test      # testes rápidos, sem e2e
make up        # sobe o ministack
make e2e       # testes contra o ministack real
```

No Claude Code, `/glue:executar` e `/glue:verificar` executam o job do projeto no ministack e
mostram o resultado por camada (contrato na skill `glue-ministack`).

Nunca invoque `pip`, `python` ou `pytest` direto — sempre `uv run` ou o alvo do Makefile.
