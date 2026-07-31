# Stack técnica

Esta lista é fechada. Adicionar uma dependência nova é uma decisão de design que vai numa ADR
dentro do `design.md` da spec que precisa dela — não é escolha de implementação.

## Runtime

| Item | Versão | Observação |
|---|---|---|
| Python | 3.11 | fixado em `.python-version`; PySpark 3.5 tem problemas conhecidos no 3.12 |
| PySpark | 3.5.3 | mesma versão da imagem que o minilake usa nos containers de job |
| Delta Lake | 3.2.1 | `delta-spark`, compatível com Spark 3.5 |
| pydantic | >=2 | validação nas fronteiras (entrada de config, contratos de porta) |
| click | >=8.1 | CLI do job |

## Ferramentas

| Item | Papel |
|---|---|
| **uv** | gerenciador de pacotes e ambiente. Todo comando roda via `uv run` |
| **ruff** | linter e formatter, `line-length = 120`, `target-version = "py311"` |
| **mypy** | `strict = true` sobre `src/` |
| **pytest** | testes; markers `unit`, `integration`, `e2e` |
| **pytest-cov** | cobertura com `fail_under = 95` — é gate, não relatório |
| **pre-commit** | guardas de commit, incluindo hooks específicos de pipeline Spark |

## Infraestrutura

**minilake** é o alvo de execução. É um emulador local da API do Databricks, **não** é o
Databricks. As diferenças que importam:

- SQL roda em **DuckDB**, não em Spark SQL.
- Jobs PySpark rodam de verdade, por `spark-submit`, em containers Spark irmãos.
- Delta Lake é real, em arquivos no volume compartilhado `/data/`.
- **DLT / Delta Live Tables não existe** (`NOT_IMPLEMENTED`). Orquestração é Jobs.

As restrições operacionais completas estão em `convencoes-spark.md` e na skill
`minilake-spark`. Leia antes de escrever qualquer PySpark ou SQL.

Endpoint: `http://localhost:8000` — registrado em `.mcp.json`, sobe com `make up`.

## Ambiente local

Java **não** está instalado no host. Consequência prática:

- Testes marcados `integration` (que sobem uma `SparkSession` local) são **pulados** por padrão
  via `skipif` — não falham, não mentem sobre cobertura.
- O adaptador Spark é coberto por testes unitários com `unittest.mock`, verificando as chamadas
  feitas ao builder e ao writer.
- A validação com Spark de verdade acontece contra o minilake (`make e2e` ou
  `mcp__minilake__run_python_script`), que traz o próprio runtime no container.

Quem quiser rodar Spark local: `brew install openjdk@17`. É opcional.

## Comandos

```bash
make install   # dependências + hooks de git
make check     # lint + mypy + cobertura (o gate)
make test      # testes rápidos, sem e2e
make up        # sobe o minilake
make e2e       # testes contra o minilake real
```

Nunca invoque `pip`, `python` ou `pytest` direto — sempre `uv run` ou o alvo do Makefile.
