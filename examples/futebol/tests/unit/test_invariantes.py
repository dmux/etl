from dataclasses import replace
from datetime import date

from etl_futebol.domain.invariantes import deduplicar, validar
from etl_futebol.domain.modelos import Partida, Status

VALIDA = Partida(
    "Brasileiro Série A", 2025, "Matchday 1", 1, date(2025, 3, 29), "18:30", "Cruzeiro EC", "Mirassol FC",
    2, 1, 2, 1, None, Status.REALIZADA, "brazil/2025_br1.txt", 10,
)  # fmt: skip


def test_partida_valida_passa_intacta() -> None:
    """REQ-007: partida que respeita o glossário chega a silver sem mudança."""
    assert validar([VALIDA]) == ([VALIDA], [])


def test_mandante_igual_ao_visitante_e_rejeitado() -> None:
    """REQ-007: um clube não joga contra si mesmo."""
    _, rejeitados = validar([replace(VALIDA, visitante="Cruzeiro EC")])
    assert [rejeitado.motivo for rejeitado in rejeitados] == ["mandante igual ao visitante"]


def test_primeiro_tempo_maior_que_o_final_e_rejeitado() -> None:
    """REQ-007: gols do primeiro tempo não passam dos gols finais."""
    _, rejeitados = validar([replace(VALIDA, gols_visitante_ht=3)])
    assert [rejeitado.motivo for rejeitado in rejeitados] == ["gols do primeiro tempo maiores que os finais"]


def test_gols_em_partida_que_nao_aconteceu_sao_rejeitados() -> None:
    """REQ-007: partida adiada não pode ter placar."""
    _, rejeitados = validar([replace(VALIDA, status=Status.ADIADA)])
    assert [rejeitado.motivo for rejeitado in rejeitados] == ["gols em partida com status adiada"]


def test_partida_agendada_sem_gols_e_valida() -> None:
    """REQ-007: sem placar, a comparação de primeiro tempo não se aplica."""
    agendada = replace(
        VALIDA,
        gols_mandante=None,
        gols_visitante=None,
        gols_mandante_ht=None,
        gols_visitante_ht=None,
        status=Status.AGENDADA,
    )
    assert validar([agendada]) == ([agendada], [])


def test_rejeitado_de_silver_aponta_arquivo_e_linha_de_origem() -> None:
    """REQ-007: o rejeitado de silver continua rastreável até a linha do arquivo."""
    _, rejeitados = validar([replace(VALIDA, visitante="Cruzeiro EC")])
    assert (rejeitados[0].arquivo, rejeitados[0].linha) == ("brazil/2025_br1.txt", 10)


def test_duplicata_mantem_a_primeira_ocorrencia() -> None:
    """REQ-007: das ocorrências repetidas fica a de menor arquivo e, depois, menor linha."""
    repetida = replace(VALIDA, linha=50)
    unicas, _ = deduplicar([repetida, VALIDA])
    assert unicas == [VALIDA]


def test_demais_ocorrencias_viram_rejeitadas() -> None:
    """REQ-007: a duplicata não some; vai para os rejeitados com o motivo."""
    _, rejeitados = deduplicar([replace(VALIDA, linha=50), VALIDA])
    assert [(rejeitado.linha, rejeitado.motivo) for rejeitado in rejeitados] == [(50, "partida duplicada")]


def test_mesmo_confronto_em_outra_data_nao_e_duplicata() -> None:
    """REQ-007: a chave inclui a data; o returno não é duplicata."""
    returno = replace(VALIDA, data=date(2025, 8, 2), linha=200)
    assert deduplicar([VALIDA, returno]) == ([VALIDA, returno], [])
