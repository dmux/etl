"""Repositórios Iceberg no catálogo Spark `iceberg` (tipo hadoop, warehouse no S3) — ADR-009.

Só traduzem modelo ↔ linha e gravam; nenhuma regra mora aqui (ADR-003). Idempotência por
substituição, nunca `append` (ADR-006): `overwritePartitions()` em bronze, `overwrite(filtro)`
nos rejeitados e `overwrite(true)` no resto. Depois de cada escrita, o Glue Data Catalog é
atualizado pelo `RegistroCatalogoGlue`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from pyspark.sql import functions as F  # noqa: N812 — convenção do PySpark
from pyspark.sql.types import StructType

from etl_futebol.domain.modelos import Camada, LinhaClassificacao, Particao, Partida, Rejeitado
from etl_futebol.infrastructure import esquemas

CATALOGO = "iceberg"
PREFIXO = "futebol"
# Colunas de `[dados] particionamento` em examples/futebol/projeto.toml.
PARTICIONAMENTO = ("temporada", "competicao")


class Registro(Protocol):
    def registrar(self, banco: str, tabela: str, colunas: Sequence[tuple[str, str]]) -> None: ...


@dataclass(frozen=True, slots=True)
class _Destino:
    banco: str
    tabela: str
    schema: StructType
    particionamento: tuple[str, ...] = ()

    @property
    def nome(self) -> str:
        return f"{CATALOGO}.{self.banco}.{self.tabela}"

    @property
    def colunas(self) -> list[tuple[str, str]]:
        return [(campo.name, campo.dataType.simpleString()) for campo in self.schema.fields]


def _coluna_java(coluna: Any) -> Any:
    """O objeto Java de uma Column.

    No PySpark 3.3 (o do Glue 4.0), `DataFrameWriterV2.overwrite(condition)` repassa a Column do
    Python direto ao JVM e quebra com `TypeError: Column is not iterable`. Entregar `_jc` é o que a
    versão corrigida do PySpark faz por dentro.
    """
    return coluna._jc


def _literal(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


class _TabelaIceberg:
    def __init__(self, spark: Any, destino: _Destino, registro: Registro) -> None:
        self._spark = spark
        self._destino = destino
        self._registro = registro

    def substituir_particoes(self, linhas: Sequence[esquemas.Linha]) -> int:
        return self._escrever(linhas, lambda escritor: escritor.overwritePartitions())

    def substituir_onde(self, linhas: Sequence[esquemas.Linha], condicao: str) -> int:
        return self._escrever(linhas, lambda escritor: escritor.overwrite(_coluna_java(F.expr(condicao))))

    def substituir_tudo(self, linhas: Sequence[esquemas.Linha]) -> int:
        return self._escrever(linhas, lambda escritor: escritor.overwrite(_coluna_java(F.lit(True))))

    def ler(self, converter: Callable[[Sequence[Any]], Any]) -> list[Any]:
        if not self._existe():
            return []
        tabela = self._spark.table(self._destino.nome).select(*self._destino.schema.fieldNames())
        return [converter(linha) for linha in tabela.collect()]

    def _escrever(self, linhas: Sequence[esquemas.Linha], operacao: Callable[[Any], None]) -> int:
        self._garantir()
        operacao(self._spark.createDataFrame(list(linhas), self._destino.schema).writeTo(self._destino.nome))
        self._registro.registrar(self._destino.banco, self._destino.tabela, self._destino.colunas)
        return len(linhas)

    def _garantir(self) -> None:
        destino = self._destino
        colunas = ", ".join(f"{nome} {tipo}" for nome, tipo in destino.colunas)
        particao = f" PARTITIONED BY ({', '.join(destino.particionamento)})" if destino.particionamento else ""
        self._spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {CATALOGO}.{destino.banco}")
        self._spark.sql(f"CREATE TABLE IF NOT EXISTS {destino.nome} ({colunas}) USING iceberg{particao}")

    def _existe(self) -> bool:
        # Por catálogo, e não capturando AnalysisException: a exceção do PySpark exige JVM até para
        # ser construída, e um teste no host não conseguiria simular o caso.
        bancos = [linha[0] for linha in self._spark.sql(f"SHOW NAMESPACES IN {CATALOGO}").collect()]
        if self._destino.banco not in bancos:
            return False
        tabelas = self._spark.sql(f"SHOW TABLES IN {CATALOGO}.{self._destino.banco}").collect()
        return self._destino.tabela in [linha[1] for linha in tabelas]


def _banco(camada: str) -> str:
    return f"{PREFIXO}_{camada}"


class RepositorioPartidasIceberg:
    def __init__(self, spark: Any, registro: Registro) -> None:
        self._spark = spark
        self._registro = registro

    def substituir_particoes(self, camada: Camada, partidas: Sequence[Partida], particoes: Sequence[Particao]) -> int:
        if not particoes:
            return 0
        return self._tabela(camada).substituir_particoes([esquemas.linha_de_partida(p) for p in partidas])

    def substituir_tudo(self, camada: Camada, partidas: Sequence[Partida]) -> int:
        return self._tabela(camada).substituir_tudo([esquemas.linha_de_partida(p) for p in partidas])

    def ler(self, camada: Camada) -> list[Partida]:
        return self._tabela(camada).ler(esquemas.partida_de_linha)

    def _tabela(self, camada: Camada) -> _TabelaIceberg:
        destino = _Destino(_banco(camada), "partidas", esquemas.PARTIDAS, PARTICIONAMENTO)
        return _TabelaIceberg(self._spark, destino, self._registro)


class RepositorioRejeitadosIceberg:
    def __init__(self, spark: Any, registro: Registro) -> None:
        self._spark = spark
        self._registro = registro

    def substituir_arquivos(self, camada: Camada, rejeitados: Sequence[Rejeitado], arquivos: Sequence[str]) -> int:
        if not arquivos:
            return 0
        condicao = f"arquivo IN ({', '.join(_literal(arquivo) for arquivo in arquivos)})"
        return self._tabela(camada).substituir_onde([esquemas.linha_de_rejeitado(r) for r in rejeitados], condicao)

    def substituir_tudo(self, camada: Camada, rejeitados: Sequence[Rejeitado]) -> int:
        return self._tabela(camada).substituir_tudo([esquemas.linha_de_rejeitado(r) for r in rejeitados])

    def _tabela(self, camada: Camada) -> _TabelaIceberg:
        return _TabelaIceberg(self._spark, _Destino(_banco(camada), "rejeitados", esquemas.REJEITADOS), self._registro)


class RepositorioClassificacaoIceberg:
    def __init__(self, spark: Any, registro: Registro) -> None:
        destino = _Destino(_banco("gold"), "classificacao", esquemas.CLASSIFICACAO, PARTICIONAMENTO)
        self._tabela = _TabelaIceberg(spark, destino, registro)

    def substituir_tudo(self, linhas: Sequence[LinhaClassificacao]) -> int:
        return self._tabela.substituir_tudo([esquemas.linha_de_classificacao(linha) for linha in linhas])
