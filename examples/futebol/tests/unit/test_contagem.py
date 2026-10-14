from datetime import date

from etl_futebol.domain.contagem import conferir_contagem
from etl_futebol.domain.modelos import ArquivoProcessado, Partida, Rejeitado, Status

ARQUIVO = "brazil/2025_br1.txt"
PARTIDA = Partida(
    "Brasileiro Série A", 2025, "Matchday 1", 1, date(2025, 3, 29), "18:30", "São Paulo FC", "SC Recife",
    0, 0, None, None, None, Status.REALIZADA, ARQUIVO, 9,
)  # fmt: skip
REJEITADO = Rejeitado(ARQUIVO, 10, "linha ruim", "resultado não reconhecido: '2 a 1'")


def _processado(declarado: int | None, partidas: int, rejeitados: int) -> ArquivoProcessado:
    return ArquivoProcessado(
        ARQUIVO, "Brasileiro Série A", 2025, declarado, (PARTIDA,) * partidas, (REJEITADO,) * rejeitados
    )


def test_contagem_certa_nao_tem_motivo_de_falha() -> None:
    """REQ-005: partidas mais rejeitados iguais ao declarado conferem."""
    assert conferir_contagem(_processado(declarado=3, partidas=2, rejeitados=1)) is None


def test_contagem_a_menos_falha_com_os_numeros() -> None:
    """REQ-005: linha perdida faz a soma ficar abaixo do declarado."""
    assert conferir_contagem(_processado(declarado=380, partidas=378, rejeitados=1)) == (
        "contagem divergente: 378 partidas + 1 rejeitados = 379, declarado 380"
    )


def test_contagem_a_mais_tambem_falha() -> None:
    """REQ-005: partida a mais que o declarado também é divergência."""
    assert conferir_contagem(_processado(declarado=1, partidas=2, rejeitados=0)) is not None


def test_arquivo_sem_contagem_declarada_falha() -> None:
    """REQ-005: sem `# Matches`, o arquivo falha com o motivo `contagem não declarada`."""
    assert conferir_contagem(_processado(declarado=None, partidas=2, rejeitados=0)) == "contagem não declarada"
