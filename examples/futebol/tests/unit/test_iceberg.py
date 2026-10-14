from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from etl_futebol.application.portas import (
    RepositorioClassificacaoPort,
    RepositorioPartidasPort,
    RepositorioRejeitadosPort,
)
from etl_futebol.domain.modelos import LinhaClassificacao, Partida, Rejeitado, Status
from etl_futebol.infrastructure import esquemas
from etl_futebol.infrastructure.iceberg import (
    RepositorioClassificacaoIceberg,
    RepositorioPartidasIceberg,
    RepositorioRejeitadosIceberg,
)

PARTIDA = Partida(
    "Brasileiro Série A", 2025, "Matchday 1", 1, date(2025, 3, 29), "18:30", "Cruzeiro EC", "Mirassol FC",
    2, 1, 2, 1, None, Status.REALIZADA, "brazil/2025_br1.txt", 10,
)  # fmt: skip
REJEITADO = Rejeitado("brazil/2025_br1.txt", 12, "linha ruim", "resultado não reconhecido: '2 a 1'")
LINHA = LinhaClassificacao("Brasileiro Série A", 2025, "Cruzeiro EC", 1, 1, 0, 0, 2, 1, 1, 3, Decimal("1.0000"))
SERIE_A = [("Brasileiro Série A", 2025)]


@pytest.fixture(autouse=True)
def funcoes() -> object:
    """`pyspark.sql.functions` exige um SparkContext ativo; no host as colunas são falsas."""
    with patch("etl_futebol.infrastructure.iceberg.F") as falso:
        yield falso


@pytest.fixture
def spark() -> MagicMock:
    return MagicMock()


@pytest.fixture
def registro() -> MagicMock:
    return MagicMock()


def _escritor(spark: MagicMock) -> MagicMock:
    escritor: MagicMock = spark.createDataFrame.return_value.writeTo.return_value
    return escritor


def _sqls(spark: MagicMock) -> list[str]:
    return [chamada.args[0] for chamada in spark.sql.call_args_list]


def test_adaptadores_satisfazem_as_portas(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: os adaptadores Iceberg cumprem o contrato das portas."""
    assert all(
        (
            isinstance(RepositorioPartidasIceberg(spark, registro), RepositorioPartidasPort),
            isinstance(RepositorioRejeitadosIceberg(spark, registro), RepositorioRejeitadosPort),
            isinstance(RepositorioClassificacaoIceberg(spark, registro), RepositorioClassificacaoPort),
        )
    )


def test_partidas_vao_para_a_tabela_qualificada_no_catalogo_iceberg(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: toda tabela é qualificada pelo catálogo `iceberg`; nada passa pelo spark_catalog."""
    RepositorioPartidasIceberg(spark, registro).substituir_particoes("bronze", [PARTIDA], SERIE_A)
    spark.createDataFrame.return_value.writeTo.assert_called_once_with("iceberg.futebol_bronze.partidas")


def test_dataframe_usa_o_schema_explicito(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: schema declarado, nunca inferido."""
    RepositorioPartidasIceberg(spark, registro).substituir_particoes("bronze", [PARTIDA], SERIE_A)
    spark.createDataFrame.assert_called_once_with([esquemas.linha_de_partida(PARTIDA)], esquemas.PARTIDAS)


def test_bronze_substitui_so_as_particoes_reprocessadas(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: reprocessar um arquivo troca só a partição dele."""
    RepositorioPartidasIceberg(spark, registro).substituir_particoes("bronze", [PARTIDA], SERIE_A)
    _escritor(spark).overwritePartitions.assert_called_once_with()


def test_tabela_e_criada_antes_com_ddl_particionado(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: a tabela nasce com schema e partição declarados, antes da primeira escrita."""
    RepositorioPartidasIceberg(spark, registro).substituir_particoes("bronze", [PARTIDA], SERIE_A)
    namespace, ddl = _sqls(spark)
    assert (
        namespace,
        ddl.startswith("CREATE TABLE IF NOT EXISTS iceberg.futebol_bronze.partidas ("),
        ddl.endswith(") USING iceberg PARTITIONED BY (temporada, competicao)"),
    ) == ("CREATE NAMESPACE IF NOT EXISTS iceberg.futebol_bronze", True, True)


def test_ddl_declara_os_tipos_sem_not_null(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: sem NOT NULL; o Iceberg recusaria colunas anuláveis do DataFrame."""
    RepositorioClassificacaoIceberg(spark, registro).substituir_tudo([LINHA])
    ddl = _sqls(spark)[1]
    assert ("data date" not in ddl, "aproveitamento decimal(5,4)" in ddl, "NOT NULL" not in ddl) == (True, True, True)


def test_sem_particoes_nada_e_gravado(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: substituir zero partições não toca na tabela."""
    assert RepositorioPartidasIceberg(spark, registro).substituir_particoes("bronze", [], []) == 0
    spark.createDataFrame.assert_not_called()


def test_silver_e_reescrita_inteira(spark: MagicMock, registro: MagicMock, funcoes: MagicMock) -> None:
    """REQ-006: silver deriva inteira de bronze e é sobrescrita por completo."""
    RepositorioPartidasIceberg(spark, registro).substituir_tudo("silver", [PARTIDA])
    _escritor(spark).overwrite.assert_called_once_with(funcoes.lit.return_value._jc)
    funcoes.lit.assert_called_once_with(True)


def test_rejeitados_substituidos_por_arquivo(spark: MagicMock, registro: MagicMock, funcoes: MagicMock) -> None:
    """REQ-006: rejeitados de bronze são trocados só nos arquivos reprocessados."""
    RepositorioRejeitadosIceberg(spark, registro).substituir_arquivos(
        "bronze", [REJEITADO], ["brazil/2025_br1.txt", "D'Ouro.txt"]
    )
    funcoes.expr.assert_called_once_with("arquivo IN ('brazil/2025_br1.txt', 'D''Ouro.txt')")


def test_rejeitados_nao_sao_particionados(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-004: dezenas de linhas não justificam partição."""
    RepositorioRejeitadosIceberg(spark, registro).substituir_tudo("silver", [REJEITADO])
    assert _sqls(spark)[1].endswith(") USING iceberg")


def test_rejeitados_sem_arquivos_nada_e_gravado(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: substituir zero arquivos não toca na tabela."""
    assert RepositorioRejeitadosIceberg(spark, registro).substituir_arquivos("bronze", [], []) == 0
    spark.createDataFrame.assert_not_called()


def test_classificacao_vai_para_gold(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-008: a classificação é a tabela gold."""
    assert RepositorioClassificacaoIceberg(spark, registro).substituir_tudo([LINHA]) == 1
    spark.createDataFrame.return_value.writeTo.assert_called_once_with("iceberg.futebol_gold.classificacao")


def test_cada_escrita_registra_a_tabela_no_glue(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: depois de escrever, o Glue Data Catalog aponta para a nova versão da tabela."""
    RepositorioPartidasIceberg(spark, registro).substituir_particoes("bronze", [PARTIDA], SERIE_A)
    banco, tabela, colunas = registro.registrar.call_args.args
    assert (banco, tabela, colunas[0]) == ("futebol_bronze", "partidas", ("competicao", "string"))


def _catalogo_com(spark: MagicMock, bancos: list[str], tabelas: list[str]) -> None:
    def sql(comando: str) -> MagicMock:
        resultado = MagicMock()
        if comando.startswith("SHOW NAMESPACES"):
            resultado.collect.return_value = [(banco,) for banco in bancos]
        elif comando.startswith("SHOW TABLES"):
            resultado.collect.return_value = [("futebol_bronze", tabela, False) for tabela in tabelas]
        return resultado

    spark.sql.side_effect = sql


def test_ler_converte_as_linhas_em_partidas(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: a leitura devolve modelos do domínio, nunca DataFrame."""
    _catalogo_com(spark, ["futebol_bronze"], ["partidas"])
    spark.table.return_value.select.return_value.collect.return_value = [esquemas.linha_de_partida(PARTIDA)]
    assert RepositorioPartidasIceberg(spark, registro).ler("bronze") == [PARTIDA]


def test_ler_seleciona_as_colunas_explicitamente(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: leitura com colunas declaradas, nunca `*`."""
    _catalogo_com(spark, ["futebol_bronze"], ["partidas"])
    RepositorioPartidasIceberg(spark, registro).ler("bronze")
    spark.table.return_value.select.assert_called_once_with(*esquemas.PARTIDAS.fieldNames())


def test_ler_sem_o_banco_devolve_vazio(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: silver antes da primeira gravação é vazia, não um erro."""
    _catalogo_com(spark, [], [])
    assert RepositorioPartidasIceberg(spark, registro).ler("silver") == []


def test_ler_sem_a_tabela_devolve_vazio(spark: MagicMock, registro: MagicMock) -> None:
    """REQ-006: banco criado por outra tabela, mas sem esta, também é vazio."""
    _catalogo_com(spark, ["futebol_bronze"], ["rejeitados"])
    assert RepositorioPartidasIceberg(spark, registro).ler("bronze") == []


def test_filtro_vai_ao_iceberg_como_coluna_java(spark: MagicMock, registro: MagicMock, funcoes: MagicMock) -> None:
    """REQ-006: o PySpark 3.3 do Glue 4.0 repassa a Column do Python sem converter; o adaptador entrega a Java."""
    RepositorioRejeitadosIceberg(spark, registro).substituir_arquivos("bronze", [REJEITADO], ["brazil/2025_br1.txt"])
    _escritor(spark).overwrite.assert_called_once_with(funcoes.expr.return_value._jc)
