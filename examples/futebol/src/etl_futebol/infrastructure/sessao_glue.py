"""Sessão Spark de um job AWS Glue. Construir a sessão pelo builder perderia a configuração do Glue."""

from __future__ import annotations

from typing import Any

from pyspark.context import SparkContext


def criar_sessao_glue() -> Any:
    """A `spark_session` do `GlueContext`. `awsglue` só existe na imagem do Glue, daí o import tardio."""
    from awsglue.context import GlueContext

    return GlueContext(SparkContext.getOrCreate()).spark_session
