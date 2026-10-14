"""Registro das tabelas Iceberg no Glue Data Catalog (ADR-009).

O Spark escreve pelo catálogo `hadoop`; este registro faz o que o `GlueCatalog` do Iceberg faria:
aponta o Glue para o `metadata.json` da última escrita. Na AWS real, é o que o Athena lê.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import urlparse

_JA_EXISTE = "AlreadyExistsException"


def _codigo_do_erro(erro: Exception) -> str:
    resposta = getattr(erro, "response", None) or {}
    return str(resposta.get("Error", {}).get("Code", ""))


class RegistroCatalogoGlue:
    """Clientes `boto3` de S3 e Glue injetados; no job eles já apontam para o ministack."""

    def __init__(self, s3: Any, glue: Any, warehouse: str) -> None:
        self._s3 = s3
        self._glue = glue
        endereco = urlparse(warehouse)
        self._bucket = endereco.netloc
        self._prefixo = endereco.path.strip("/")

    def registrar(self, banco: str, tabela: str, colunas: Sequence[tuple[str, str]]) -> None:
        local = f"s3://{self._bucket}/{self._prefixo}/{banco}/{tabela}"
        entrada = {
            "Name": tabela,
            "TableType": "EXTERNAL_TABLE",
            "Parameters": {"table_type": "ICEBERG", "metadata_location": self._metadata_atual(banco, tabela)},
            "StorageDescriptor": {
                "Location": local,
                "Columns": [{"Name": nome, "Type": tipo} for nome, tipo in colunas],
            },
        }
        self._criar_se_faltar(lambda: self._glue.create_database(DatabaseInput={"Name": banco}))
        criada = self._criar_se_faltar(lambda: self._glue.create_table(DatabaseName=banco, TableInput=entrada))
        if not criada:
            self._glue.update_table(DatabaseName=banco, TableInput=entrada)

    def _metadata_atual(self, banco: str, tabela: str) -> str:
        chave = f"{self._prefixo}/{banco}/{tabela}/metadata/version-hint.text"
        versao = int(self._s3.get_object(Bucket=self._bucket, Key=chave)["Body"].read().decode().strip())
        return f"s3://{self._bucket}/{self._prefixo}/{banco}/{tabela}/metadata/v{versao}.metadata.json"

    @staticmethod
    def _criar_se_faltar(criar: Callable[[], object]) -> bool:
        """True se criou; False se já existia. Qualquer outro erro propaga."""
        try:
            criar()
        except Exception as erro:
            if _codigo_do_erro(erro) != _JA_EXISTE:
                raise
            return False
        return True
