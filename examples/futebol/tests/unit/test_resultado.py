from etl_futebol.domain.modelos import Placar, Resultado, Status
from etl_futebol.domain.resultado import interpretar_resultado


def test_final_e_primeiro_tempo() -> None:
    """REQ-002: `N-N (N-N)` grava o placar final e o do primeiro tempo."""
    assert interpretar_resultado("2-1 (2-0)") == Resultado(Placar(2, 1), Placar(2, 0), None, Status.REALIZADA)


def test_so_placar_final_deixa_primeiro_tempo_nulo() -> None:
    """REQ-002: `N-N` sem parênteses deixa o primeiro tempo nulo."""
    assert interpretar_resultado("0-0") == Resultado(Placar(0, 0), None, None, Status.REALIZADA)


def test_sem_placar_e_agendada() -> None:
    """REQ-003: linha sem placar nem marcador é uma partida agendada, sem gols."""
    assert interpretar_resultado("") == Resultado(None, None, None, Status.AGENDADA)


def test_penaltis_com_dois_placares_entre_parenteses() -> None:
    """REQ-002: `pen. (N-N, N-N)` separa pênaltis, placar do jogo e primeiro tempo."""
    assert interpretar_resultado("5-3 pen. (1-1, 0-1)") == Resultado(
        Placar(1, 1), Placar(0, 1), Placar(5, 3), Status.REALIZADA
    )


def test_penaltis_nunca_viram_gols() -> None:
    """REQ-002: o placar antes de `pen.` é dos pênaltis, nunca dos gols."""
    resultado = interpretar_resultado("5-3 pen. (1-1, 0-1)")
    assert resultado is not None
    assert resultado.gols == Placar(1, 1)


def test_penaltis_com_um_placar_so_e_o_placar_da_partida() -> None:
    """REQ-002: em `pen. (N-N)` o placar entre parênteses é o do jogo; primeiro tempo nulo."""
    assert interpretar_resultado("5-3 pen. (0-0)") == Resultado(Placar(0, 0), None, Placar(5, 3), Status.REALIZADA)


def test_penaltis_com_prorrogacao_e_dois_placares() -> None:
    """REQ-002: `pen. N-N a.e.t. (N-N, N-N)` usa os parênteses para gols e primeiro tempo."""
    assert interpretar_resultado("1-4 pen. 1-4 a.e.t. (1-1, 0-0)") == Resultado(
        Placar(1, 1), Placar(0, 0), Placar(1, 4), Status.REALIZADA
    )


def test_placar_aet_e_ignorado_com_um_placar_so() -> None:
    """REQ-002: o placar `a.e.t.` é ignorado; vale o placar entre parênteses."""
    assert interpretar_resultado("4-3 pen. 4-3 a.e.t. (0-0)") == Resultado(
        Placar(0, 0), None, Placar(4, 3), Status.REALIZADA
    )


def test_resultado_atribuido_guarda_o_placar() -> None:
    """REQ-003: `[awarded]` é resultado atribuído, com o placar informado."""
    assert interpretar_resultado("3-0    [awarded]") == Resultado(Placar(3, 0), None, None, Status.ATRIBUIDA)


def test_adiada_nao_tem_gols() -> None:
    """REQ-003: `[postponed]` é partida adiada, sem gols."""
    assert interpretar_resultado("[postponed]") == Resultado(None, None, None, Status.ADIADA)


def test_cancelada_nao_tem_gols() -> None:
    """REQ-003: `[cancelled]` é partida cancelada, sem gols."""
    assert interpretar_resultado("[cancelled]") == Resultado(None, None, None, Status.CANCELADA)


def test_abandonada_nao_tem_gols() -> None:
    """REQ-003: `[abandoned]` é partida abandonada, sem gols."""
    assert interpretar_resultado("[abandoned]") == Resultado(None, None, None, Status.ABANDONADA)


def test_espacos_nas_bordas_sao_ignorados() -> None:
    """REQ-002: o alinhamento em colunas do arquivo não muda a interpretação."""
    assert interpretar_resultado("  2-1 (2-0)  ") == Resultado(Placar(2, 1), Placar(2, 0), None, Status.REALIZADA)


def test_texto_irreconhecivel_nao_e_interpretado() -> None:
    """REQ-004: resultado que não casa com nenhuma forma não é adivinhado."""
    assert interpretar_resultado("2 a 1") is None


def test_marcador_desconhecido_nao_e_interpretado() -> None:
    """REQ-004: marcador fora da lista conhecida não é adivinhado."""
    assert interpretar_resultado("[suspended]") is None


def test_placar_truncado_nao_e_interpretado() -> None:
    """REQ-004: linha cortada no meio do resultado não vira placar."""
    assert interpretar_resultado("2-1 (2-") is None
