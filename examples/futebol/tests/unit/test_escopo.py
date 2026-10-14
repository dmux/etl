import pytest

from etl_futebol.domain.escopo import no_escopo

ARQUIVOS_DO_COMMIT = [f"brazil/{temporada}_br1.txt" for temporada in range(2018, 2027)] + [
    f"brazil/{temporada}_br2.txt" for temporada in range(2018, 2026)
]


@pytest.mark.parametrize("arquivo", [*ARQUIVOS_DO_COMMIT, "brazil/2025_brcup.txt"])
def test_arquivos_do_commit_estao_no_escopo(arquivo: str) -> None:
    """REQ-010: Série A, Série B e Copa do Brasil a partir de 2018 são carregadas."""
    assert no_escopo(arquivo)


def test_escopo_tem_os_18_arquivos_do_commit() -> None:
    """REQ-010: são 18 arquivos no commit 119fa17."""
    assert len([*ARQUIVOS_DO_COMMIT, "brazil/2025_brcup.txt"]) == 18


@pytest.mark.parametrize(
    "arquivo",
    ["brazil/2017_br1.txt", "argentina/2024_ar1.txt", "brazil/README.md", "brazil/2025_br3.txt", "2025_br1.txt"],
)
def test_arquivos_alheios_a_lista_sao_ignorados(arquivo: str) -> None:
    """REQ-010: temporada anterior a 2018, outro país ou outro tipo de arquivo não entram."""
    assert not no_escopo(arquivo)
