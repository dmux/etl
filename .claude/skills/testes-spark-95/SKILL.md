---
name: testes-spark-95
description: Como estruturar testes num projeto PySpark para atingir 95% de cobertura sem depender de JVM — fakes de porta, mock de SparkSession, fixtures, markers unit/integration/e2e. Use ao escrever testes, quando a cobertura estiver abaixo do gate, ao testar um adaptador Spark, ou quando um teste exigir SparkSession e você suspeitar que a lógica está na camada errada.
---

# Testes e o gate de 95%

## A ideia central

Cobertura alta em projeto Spark não se consegue testando Spark. Consegue-se **tirando a lógica
de dentro do Spark**. O domínio é Python puro: parsing, regras, validação, derivação — tudo
testável em milissegundos. O que sobra na infraestrutura é fino o bastante para mock.

Se para testar uma regra você precisou de `SparkSession`, o problema é o desenho, não o teste.
Mova a regra para `domain/` e teste lá.

## Pirâmide

| Camada | Marker | O que testa | Custo | Peso na cobertura |
|---|---|---|---|---|
| `tests/unit/` | `unit` | domínio e aplicação, com fakes | ms | ~90% |
| `tests/integration/` | `integration` | adaptador Spark real, `local[2]` | segundos | complementar |
| `tests/e2e/` | `e2e` | job Glue contra o ministack | minutos | fumaça |

Java **não** está instalado no host: os testes `integration` são pulados por `skipif` e não
podem ser contados no gate. O adaptador Spark precisa de cobertura por **mock**, no `unit`.

## Fake de porta

Preferido sobre mock sempre que a porta permitir. Um fake é código de verdade, verificável:

```python
class EscritorMemoria:
    """Adaptador em memória de EscritorTabelaPort, para teste."""

    def __init__(self) -> None:
        self.gravadas: list[Registro] = []

    def escrever(self, registros: Sequence[Registro], destino: str) -> int:
        self.gravadas.extend(registros)
        return len(registros)
```

```python
def test_ingestao_grava_todos_os_registros_do_arquivo() -> None:
    """REQ-002: todo registro reconhecido no arquivo é persistido."""
    escritor = EscritorMemoria()
    caso = Ingestao(leitor=LeitorFalso(CONTEUDO), escritor=escritor)

    total = caso.executar(ORIGEM)

    assert total == TOTAL_ESPERADO
    assert len(escritor.gravadas) == TOTAL_ESPERADO
```

Como o fake implementa a mesma `Protocol`, vale um teste que trave o contrato:

```python
def test_escritor_memoria_satisfaz_a_porta() -> None:
    assert isinstance(EscritorMemoria(), EscritorTabelaPort)
```

## Testando o adaptador Spark sem JVM

Mock da sessão, e asserção sobre as chamadas — é isso que garante que a escrita idempotente e o
nome qualificado da tabela não sejam esquecidos:

```python
from unittest.mock import MagicMock


def test_escritor_substitui_so_as_particoes_reprocessadas() -> None:
    """REQ-006: reprocessar não apaga partições que não vieram nesta execução."""
    spark = MagicMock()
    escritor = EscritorIcebergSpark(spark, banco="<prefixo>_bronze")

    escritor.substituir_particoes([UM_REGISTRO])

    spark.createDataFrame.return_value.writeTo.assert_called_once_with("iceberg.<prefixo>_bronze.<tabela>")
    spark.createDataFrame.return_value.writeTo.return_value.overwritePartitions.assert_called_once_with()
```

`awsglue` não existe no host. Para testar o wiring que cria o `GlueContext`, injete módulos falsos
em `sys.modules` com `monkeypatch.setitem`, e importe `awsglue` só dentro da função que o usa:

```python
def test_sessao_vem_do_glue_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-009: a sessão é a do GlueContext, com a configuração que o Glue injeta."""
    contexto = MagicMock()
    monkeypatch.setitem(sys.modules, "awsglue.context", MagicMock(GlueContext=MagicMock(return_value=contexto)))
    monkeypatch.setitem(sys.modules, "pyspark.context", MagicMock())
    assert criar_sessao_glue() is contexto.spark_session
```

Clientes `boto3` (S3, Glue) entram por injeção no construtor do adaptador; no teste, um fake
simples com os métodos usados.

## Fixture de Spark real, quando houver Java

```python
import pytest

pytestmark = pytest.mark.integration


def _spark_disponivel() -> bool:
    import shutil
    return shutil.which("java") is not None


@pytest.fixture(scope="module")
def spark():
    if not _spark_disponivel():
        pytest.skip("Java não instalado — Spark local indisponível")
    from pyspark.sql import SparkSession

    sessao = (
        SparkSession.builder
        .master("local[2]")
        .appName("testes")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        # Iceberg local precisa do iceberg-spark-runtime-3.3_2.12 no classpath
        # (spark.jars.packages); sem rede, o teste é pulado.
        .getOrCreate()
    )
    sessao.sparkContext.setLogLevel("WARN")
    yield sessao
    sessao.stop()
```

Escreva sempre em `tmp_path`, nunca num caminho fixo — teste que deixa lixo em disco quebra o
seguinte.

## Convenções

- Docstring do teste começa com o requisito: `"""REQ-003: ..."""`. É o que o `/sdd:check`
  colhe para montar a matriz de rastreabilidade.
- Nome descreve o comportamento: `test_registro_sem_data_vira_rejeitado`.
- Um assert conceitual por teste.
- Dado de teste em constante nomeada no topo do módulo, não literal solto no meio do teste.
- Casos de borda são obrigatórios: entrada vazia, campo ausente, valor fora de domínio,
  encoding, arquivo truncado.

## Quando a cobertura fica abaixo de 95%

Rode `uv run pytest -m "not e2e" --cov --cov-report=term-missing` e leia a coluna `Missing`.
Cada linha descoberta cai num destes casos:

| Situação | O que fazer |
|---|---|
| ramo de erro nunca exercitado | escreva o teste do caminho triste — normalmente é um `SE/ENTÃO` da spec sem teste |
| código defensivo inalcançável | remova; se for genuinamente inalcançável, `# pragma: no cover` **com justificativa** |
| adaptador Spark descoberto | teste com mock, como acima |
| wiring do `cli/` | já está em `omit`; se apareceu, tem lógica no lugar errado |
| código morto | apague. É a correção mais comum e a mais ignorada |

Baixar o `fail_under` nunca é a resposta.
