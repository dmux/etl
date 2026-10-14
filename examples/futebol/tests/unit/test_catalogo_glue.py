import io
from typing import Any

import pytest

from etl_futebol.infrastructure.catalogo_glue import RegistroCatalogoGlue

WAREHOUSE = "s3a://futebol-lake/warehouse"
COLUNAS = [("competicao", "string"), ("temporada", "int")]


class _ClienteAwsError(Exception):
    """Imita o ClientError do botocore: o código do erro vem em `response`."""

    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.response = {"Error": {"Code": codigo}}


class _S3:
    def __init__(self, versao: bytes = b"3\n") -> None:
        self.versao = versao
        self.chaves: list[tuple[str, str]] = []

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803 — assinatura do boto3
        self.chaves.append((Bucket, Key))
        return {"Body": io.BytesIO(self.versao)}


class _Glue:
    def __init__(self, bancos: set[str] | None = None, tabelas: set[str] | None = None) -> None:
        self.bancos = bancos or set()
        self.tabelas = tabelas or set()
        self.chamadas: list[tuple[str, dict[str, Any]]] = []

    def create_database(self, DatabaseInput: dict[str, Any]) -> None:  # noqa: N803
        if DatabaseInput["Name"] in self.bancos:
            raise _ClienteAwsError("AlreadyExistsException")
        self.chamadas.append(("create_database", DatabaseInput))

    def create_table(self, DatabaseName: str, TableInput: dict[str, Any]) -> None:  # noqa: N803
        if TableInput["Name"] in self.tabelas:
            raise _ClienteAwsError("AlreadyExistsException")
        self.chamadas.append(("create_table", TableInput))

    def update_table(self, DatabaseName: str, TableInput: dict[str, Any]) -> None:  # noqa: N803
        self.chamadas.append(("update_table", TableInput))


def _registrar(glue: _Glue, s3: _S3 | None = None) -> None:
    RegistroCatalogoGlue(s3 or _S3(), glue, WAREHOUSE).registrar("futebol_bronze", "partidas", COLUNAS)


def test_metadata_location_vem_do_version_hint() -> None:
    """REQ-006: o catálogo aponta para a versão de metadata que a última escrita gerou."""
    glue = _Glue()
    _registrar(glue)
    tabela = glue.chamadas[1][1]
    assert tabela["Parameters"] == {
        "table_type": "ICEBERG",
        "metadata_location": "s3://futebol-lake/warehouse/futebol_bronze/partidas/metadata/v3.metadata.json",
    }


def test_le_o_version_hint_da_tabela_no_warehouse() -> None:
    """REQ-006: o version-hint é lido no bucket e prefixo do warehouse."""
    s3 = _S3()
    _registrar(_Glue(), s3)
    assert s3.chaves == [("futebol-lake", "warehouse/futebol_bronze/partidas/metadata/version-hint.text")]


def test_cria_o_banco_quando_falta() -> None:
    """REQ-006: a primeira escrita de uma camada cria o banco no Glue Data Catalog."""
    glue = _Glue()
    _registrar(glue)
    assert glue.chamadas[0] == ("create_database", {"Name": "futebol_bronze"})


def test_banco_existente_nao_e_erro() -> None:
    """REQ-006: registrar de novo numa camada que já existe segue normalmente."""
    glue = _Glue(bancos={"futebol_bronze"})
    _registrar(glue)
    assert [nome for nome, _ in glue.chamadas] == ["create_table"]


def test_tabela_existente_e_atualizada() -> None:
    """REQ-006: a segunda escrita atualiza o registro em vez de falhar."""
    glue = _Glue(bancos={"futebol_bronze"}, tabelas={"partidas"})
    _registrar(glue)
    assert [nome for nome, _ in glue.chamadas] == ["update_table"]


def test_registro_leva_colunas_e_local_da_tabela() -> None:
    """REQ-006: o registro descreve as colunas e o local da tabela, como o GlueCatalog faria."""
    glue = _Glue()
    _registrar(glue)
    descritor = glue.chamadas[1][1]["StorageDescriptor"]
    assert descritor == {
        "Location": "s3://futebol-lake/warehouse/futebol_bronze/partidas",
        "Columns": [{"Name": "competicao", "Type": "string"}, {"Name": "temporada", "Type": "int"}],
    }


def test_outro_erro_do_glue_propaga() -> None:
    """REQ-006: só 'já existe' é tratado; qualquer outro erro do catálogo derruba o job."""

    class _GlueQuebrado(_Glue):
        def create_database(self, DatabaseInput: dict[str, Any]) -> None:  # noqa: N803
            raise _ClienteAwsError("AccessDeniedException")

    with pytest.raises(_ClienteAwsError, match="AccessDenied"):
        _registrar(_GlueQuebrado())
