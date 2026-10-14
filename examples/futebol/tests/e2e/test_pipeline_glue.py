"""Pipeline inteiro como job AWS Glue no ministack (T-28). Lento: duas execuções de minutos."""

import re
import subprocess
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "glue.sh"
CAMADAS = "bronze,silver,gold,verificacao"


def _ministack_de_pe() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:4566/_ministack/health", timeout=3):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def execucoes() -> list[str]:
    """Publica e executa o job duas vezes; devolve a saída de cada execução."""
    if not _ministack_de_pe():
        pytest.skip("ministack fora do ar em localhost:4566 — rode `make up` na raiz")
    subprocess.run([SCRIPT, "publicar"], check=True, cwd=RAIZ)
    saidas = []
    for _ in range(2):
        resultado = subprocess.run([SCRIPT, "executar", CAMADAS], capture_output=True, text=True, cwd=RAIZ)
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr
        saidas.append(resultado.stdout)
    return saidas


def _totais(saida: str) -> dict[str, int]:
    return {nome: int(valor) for nome, valor in re.findall(r"etl_futebol: verificacao (\w+)=(\d+)", saida)}


def test_bronze_tem_as_6552_partidas_declaradas(execucoes: list[str]) -> None:
    """REQ-005: o total ingerido bate com a soma dos `# Matches` dos 18 arquivos."""
    assert _totais(execucoes[0])["bronze_partidas"] == 6552


def test_os_18_arquivos_do_escopo_chegam_a_bronze(execucoes: list[str]) -> None:
    """REQ-010: os 18 arquivos do escopo são carregados; os demais, não."""
    assert _totais(execucoes[0])["bronze_arquivos"] == 18


def test_nenhum_arquivo_do_escopo_falha(execucoes: list[str]) -> None:
    """REQ-009: o relatório de bronze não tem arquivo reprovado."""
    assert "  falhou  " not in execucoes[0]


def test_serie_a_2025_tem_20_clubes_com_38_jogos(execucoes: list[str]) -> None:
    """REQ-008: a classificação da temporada encerrada tem os 20 clubes com 38 jogos cada."""
    totais = _totais(execucoes[0])
    assert (totais["serie_a_2025_clubes"], totais["serie_a_2025_clubes_com_38_jogos"]) == (20, 20)


def test_executar_de_novo_mantem_todos_os_totais(execucoes: list[str]) -> None:
    """REQ-006: reprocessar a mesma fonte não duplica nem perde nada, em nenhuma camada."""
    assert _totais(execucoes[1]) == _totais(execucoes[0])
