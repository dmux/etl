import sys
from unittest.mock import MagicMock

import pytest

from etl_futebol.infrastructure.sessao_glue import criar_sessao_glue

SPARK_CONTEXT = MagicMock(name="SparkContext")


@pytest.fixture
def glue(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """`awsglue` só existe na imagem do Glue; no host entra um módulo falso."""
    modulo = MagicMock()
    monkeypatch.setitem(sys.modules, "awsglue", MagicMock())
    monkeypatch.setitem(sys.modules, "awsglue.context", modulo)
    # Sem JVM no host: o SparkContext do job é um objeto qualquer.
    monkeypatch.setattr("pyspark.context.SparkContext.getOrCreate", lambda: SPARK_CONTEXT)
    return modulo


def test_sessao_e_a_do_glue_context(glue: MagicMock) -> None:
    """REQ-009: a sessão vem do GlueContext, com a configuração que o Glue injeta."""
    assert criar_sessao_glue() is glue.GlueContext.return_value.spark_session


def test_glue_context_recebe_o_spark_context_existente(glue: MagicMock) -> None:
    """REQ-009: o contexto do Glue é criado sobre o SparkContext do job, sem criar um segundo."""
    criar_sessao_glue()
    glue.GlueContext.assert_called_once_with(SPARK_CONTEXT)
