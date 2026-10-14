from pathlib import Path

import pytest

from etl_futebol.application.portas import FontePort
from etl_futebol.infrastructure.fonte_fs import FonteArquivosFs


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    (tmp_path / "brazil").mkdir()
    (tmp_path / "brazil" / "2025_br2.txt").write_bytes(b"= B\n")
    (tmp_path / "brazil" / "2025_br1.txt").write_bytes("= Brasileiro Série A 2025\n".encode())
    (tmp_path / "README.md").write_text("não é fonte")
    return tmp_path


def test_satisfaz_a_porta(raiz: Path) -> None:
    """REQ-010: o adaptador de filesystem cumpre o contrato da fonte."""
    assert isinstance(FonteArquivosFs(raiz), FontePort)


def test_lista_txt_recursivamente_em_ordem_com_caminho_relativo(raiz: Path) -> None:
    """REQ-010: os arquivos são identificados pelo caminho relativo à raiz da fonte."""
    assert list(FonteArquivosFs(raiz).listar()) == ["brazil/2025_br1.txt", "brazil/2025_br2.txt"]


def test_le_os_bytes_crus(raiz: Path) -> None:
    """REQ-004: a fonte não decodifica; quem decide o que fazer com o encoding é o caso de uso."""
    assert FonteArquivosFs(raiz).ler("brazil/2025_br1.txt") == "= Brasileiro Série A 2025\n".encode()


def test_raiz_inexistente_da_erro_com_o_caminho(tmp_path: Path) -> None:
    """REQ-010: fonte ausente é erro explícito, nunca uma execução vazia que parece sucesso."""
    with pytest.raises(FileNotFoundError, match="nao_existe"):
        FonteArquivosFs(tmp_path / "nao_existe").listar()


def test_caminho_externo_a_raiz_e_recusado(raiz: Path) -> None:
    """REQ-010: a fonte só lê dentro da própria raiz."""
    with pytest.raises(ValueError, match="fora da raiz"):
        FonteArquivosFs(raiz / "brazil").ler("../README.md")


def test_leitura_nao_altera_os_arquivos(raiz: Path) -> None:
    """REQ-010: ler a origem nunca a modifica."""
    arquivo = raiz / "brazil" / "2025_br1.txt"
    antes = (arquivo.stat().st_mtime_ns, arquivo.read_bytes())
    fonte = FonteArquivosFs(raiz)
    for nome in fonte.listar():
        fonte.ler(nome)
    assert (arquivo.stat().st_mtime_ns, arquivo.read_bytes()) == antes
