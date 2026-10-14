from unittest.mock import MagicMock

import pytest

from etl_futebol.application.portas import FontePort
from etl_futebol.infrastructure.fonte_s3 import FonteS3Spark

RAIZ = "s3a://futebol-lake/fonte"
LINHAS = [
    (f"{RAIZ}/brazil/2025_br2.txt", bytearray(b"= Brasileiro S\xc3\xa9rie B 2025\n")),
    (f"{RAIZ}/brazil/2025_br1.txt", bytearray(b"\xff\xfe")),
]


def _spark(linhas: list[tuple[str, bytearray]]) -> MagicMock:
    spark = MagicMock()
    leitor = spark.read.format.return_value
    leitor.option.return_value = leitor
    leitor.load.return_value.select.return_value.collect.return_value = linhas
    return spark


def test_satisfaz_a_porta() -> None:
    """REQ-010: a fonte no S3 cumpre o contrato da fonte."""
    assert isinstance(FonteS3Spark(_spark([]), RAIZ), FontePort)


def test_lista_caminhos_relativos_em_ordem() -> None:
    """REQ-010: os arquivos são identificados pelo caminho relativo à raiz, como na fonte local."""
    assert list(FonteS3Spark(_spark(LINHAS), RAIZ).listar()) == ["brazil/2025_br1.txt", "brazil/2025_br2.txt"]


def test_le_os_bytes_crus() -> None:
    """REQ-004: bytes que não são UTF-8 chegam intactos ao caso de uso, que decide o que fazer."""
    assert FonteS3Spark(_spark(LINHAS), RAIZ).ler("brazil/2025_br1.txt") == b"\xff\xfe"


def test_le_so_txt_recursivamente_a_partir_da_raiz() -> None:
    """REQ-010: a leitura pega os .txt de todas as subpastas da raiz."""
    spark = _spark(LINHAS)
    FonteS3Spark(spark, RAIZ + "/").listar()
    leitor = spark.read.format.return_value
    opcoes = {chamada.args[0]: chamada.args[1] for chamada in leitor.option.call_args_list}
    assert (spark.read.format.call_args.args, opcoes, leitor.load.call_args.args) == (
        ("binaryFile",),
        {"pathGlobFilter": "*.txt", "recursiveFileLookup": "true"},
        (RAIZ,),
    )


def test_a_fonte_e_lida_uma_vez_so() -> None:
    """REQ-010: listar e ler vários arquivos não relê o S3."""
    spark = _spark(LINHAS)
    fonte = FonteS3Spark(spark, RAIZ)
    for arquivo in fonte.listar():
        fonte.ler(arquivo)
    spark.read.format.assert_called_once()


def test_caminho_externo_a_raiz_e_erro() -> None:
    """REQ-010: um arquivo que o Spark devolva fora da raiz não é aceito em silêncio."""
    with pytest.raises(ValueError, match="fora da raiz"):
        FonteS3Spark(_spark([("s3a://outro/x.txt", bytearray(b""))]), RAIZ).listar()
