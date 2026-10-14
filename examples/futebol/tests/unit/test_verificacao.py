from unittest.mock import MagicMock

from etl_futebol.infrastructure.verificacao import TOTAIS, contar_resultados


def _spark(valores: list[int]) -> MagicMock:
    spark = MagicMock()
    spark.sql.return_value.collect.side_effect = [[(valor,)] for valor in valores]
    return spark


def test_conta_cada_total_por_sql_nas_tabelas_iceberg() -> None:
    """REQ-005: a conferência lê as tabelas com o leitor Iceberg de verdade, não arquivos crus."""
    spark = _spark(list(range(len(TOTAIS))))
    contar_resultados(spark)
    consultas = [chamada.args[0] for chamada in spark.sql.call_args_list]
    assert all("iceberg.futebol_" in consulta for consulta in consultas)


def test_devolve_um_valor_por_total_na_ordem_declarada() -> None:
    """REQ-009: cada total tem nome estável, para o e2e conferir pelo log."""
    resultado = contar_resultados(_spark(list(range(len(TOTAIS)))))
    assert resultado == {nome: indice for indice, nome in enumerate(TOTAIS)}


def test_total_inclui_a_classificacao_da_serie_a_2025() -> None:
    """REQ-008: o e2e confere clubes e jogos da Série A 2025."""
    assert {"serie_a_2025_clubes", "serie_a_2025_clubes_com_38_jogos"} <= set(TOTAIS)


def test_total_inclui_arquivos_de_bronze() -> None:
    """REQ-005: o e2e confere quantos arquivos chegaram a bronze."""
    assert "bronze_arquivos" in TOTAIS
