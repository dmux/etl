from dataclasses import replace
from datetime import date
from decimal import Decimal

from etl_futebol.domain.classificacao import calcular_classificacao
from etl_futebol.domain.modelos import LinhaClassificacao, Partida, Status

SERIE_A = "Brasileiro Série A"
BASE = Partida(
    SERIE_A, 2025, "Matchday 1", 1, date(2025, 3, 29), "18:30", "Cruzeiro EC", "Mirassol FC",
    2, 1, None, None, None, Status.REALIZADA, "brazil/2025_br1.txt", 10,
)  # fmt: skip


def _realizada(mandante: str, visitante: str, gols: tuple[int, int], status: Status = Status.REALIZADA) -> Partida:
    return replace(
        BASE, mandante=mandante, visitante=visitante, gols_mandante=gols[0], gols_visitante=gols[1], status=status
    )


def _agendada(mandante: str, visitante: str) -> Partida:
    return replace(
        BASE, mandante=mandante, visitante=visitante, gols_mandante=None, gols_visitante=None, status=Status.AGENDADA
    )


def _linha(linhas: list[LinhaClassificacao], clube: str) -> LinhaClassificacao:
    return next(linha for linha in linhas if linha.clube == clube)


TRES_JOGOS = [
    _realizada("Cruzeiro EC", "Mirassol FC", (2, 1)),
    _realizada("Mirassol FC", "Cruzeiro EC", (0, 0)),
    _realizada("Cruzeiro EC", "SC Recife", (0, 3)),
]


def test_vitoria_vale_tres_e_empate_um() -> None:
    """REQ-008: pontos = 3 * vitórias + empates."""
    assert _linha(calcular_classificacao(TRES_JOGOS), "Cruzeiro EC").pontos == 4


def test_vitorias_empates_e_derrotas_somam_os_jogos() -> None:
    """REQ-008: cada jogo contado é vitória, empate ou derrota."""
    linha = _linha(calcular_classificacao(TRES_JOGOS), "Cruzeiro EC")
    assert (linha.jogos, linha.vitorias, linha.empates, linha.derrotas) == (3, 1, 1, 1)


def test_gols_somam_mando_e_visita() -> None:
    """REQ-008: gols pró e contra somam as partidas como mandante e como visitante."""
    linha = _linha(calcular_classificacao(TRES_JOGOS), "Cruzeiro EC")
    assert (linha.gols_pro, linha.gols_contra, linha.saldo_gols) == (2, 4, -2)


def test_aproveitamento_tem_quatro_casas() -> None:
    """REQ-008: aproveitamento = pontos / (jogos * 3), 4 casas decimais."""
    assert _linha(calcular_classificacao(TRES_JOGOS), "Cruzeiro EC").aproveitamento == Decimal("0.4444")


def test_clube_sem_jogos_tem_aproveitamento_nulo_e_nunca_zero() -> None:
    """REQ-008: jogos = 0 resulta em aproveitamento nulo."""
    linha = _linha(calcular_classificacao([_agendada("Clube do Remo", "CA Paranaense")]), "Clube do Remo")
    assert (linha.jogos, linha.aproveitamento) == (0, None)


def test_clube_so_com_partidas_agendadas_aparece() -> None:
    """REQ-008: todo clube com ao menos uma partida na temporada está na classificação."""
    clubes = {linha.clube for linha in calcular_classificacao([_agendada("Clube do Remo", "CA Paranaense")])}
    assert clubes == {"Clube do Remo", "CA Paranaense"}


def test_partida_adiada_nao_entra_em_jogos() -> None:
    """REQ-008: só realizada e atribuída contam em `jogos`."""
    adiada = replace(_agendada("Chapecoense AF", "CR Vasco da Gama"), status=Status.ADIADA)
    assert _linha(calcular_classificacao([adiada]), "Chapecoense AF").jogos == 0


def test_resultado_atribuido_entra_em_jogos() -> None:
    """REQ-008: W.O. (`atribuida`) entra na classificação com o placar dado."""
    wo = _realizada("Cuiabá MT", "Figueirense SC", (3, 0), Status.ATRIBUIDA)
    assert _linha(calcular_classificacao([wo]), "Cuiabá MT").pontos == 3


def test_copa_do_brasil_nao_tem_classificacao() -> None:
    """REQ-008: só Série A e Série B, que são de pontos corridos."""
    copa = replace(_realizada("Tocantinópolis TO", "Atlético Mineiro", (0, 2)), competicao="Copa do Brasil")
    assert calcular_classificacao([copa]) == []


def test_temporadas_e_competicoes_sao_separadas() -> None:
    """REQ-008: uma linha por clube, temporada e competição."""
    serie_b = replace(_realizada("Cruzeiro EC", "Mirassol FC", (1, 0)), competicao="Brasileiro Série B")
    outra_temporada = replace(_realizada("Cruzeiro EC", "Mirassol FC", (1, 0)), temporada=2024)
    linhas = calcular_classificacao([TRES_JOGOS[0], serie_b, outra_temporada])
    assert len([linha for linha in linhas if linha.clube == "Cruzeiro EC"]) == 3


def test_sem_partidas_nao_ha_classificacao() -> None:
    """REQ-008: entrada vazia produz classificação vazia."""
    assert calcular_classificacao([]) == []
