"""Totais para conferir uma execução, lidos com Spark (ADR-009).

O Athena do ministack não lê Iceberg, então a conferência roda no próprio job, pelo leitor Iceberg.
"""

from __future__ import annotations

from typing import Any

_SERIE_A_2025 = "competicao = 'Brasileiro Série A' AND temporada = 2025"

# Nome do total -> consulta que devolve um único número.
TOTAIS = {
    "bronze_partidas": "SELECT count(*) FROM iceberg.futebol_bronze.partidas",
    "bronze_arquivos": "SELECT count(DISTINCT arquivo) FROM iceberg.futebol_bronze.partidas",
    "bronze_rejeitados": "SELECT count(*) FROM iceberg.futebol_bronze.rejeitados",
    "silver_partidas": "SELECT count(*) FROM iceberg.futebol_silver.partidas",
    "silver_rejeitados": "SELECT count(*) FROM iceberg.futebol_silver.rejeitados",
    "gold_linhas": "SELECT count(*) FROM iceberg.futebol_gold.classificacao",
    "serie_a_2025_clubes": f"SELECT count(*) FROM iceberg.futebol_gold.classificacao WHERE {_SERIE_A_2025}",
    "serie_a_2025_clubes_com_38_jogos": (
        f"SELECT count(*) FROM iceberg.futebol_gold.classificacao WHERE {_SERIE_A_2025} AND jogos = 38"
    ),
}


def contar_resultados(spark: Any) -> dict[str, int]:
    return {nome: int(spark.sql(consulta).collect()[0][0]) for nome, consulta in TOTAIS.items()}
