import dataclasses
from datetime import date

import pytest

from etl_futebol.domain.modelos import Partida, Placar, Status

PARTIDA = Partida(
    competicao="Brasileiro Série A",
    temporada=2025,
    rodada="Matchday 1",
    rodada_num=1,
    data=date(2025, 3, 29),
    hora="18:30",
    mandante="São Paulo FC",
    visitante="SC Recife",
    gols_mandante=0,
    gols_visitante=0,
    gols_mandante_ht=None,
    gols_visitante_ht=None,
    penaltis=None,
    status=Status.REALIZADA,
    arquivo="brazil/2025_br1.txt",
    linha=12,
)


def test_status_tem_os_seis_valores_do_glossario() -> None:
    """REQ-003: o status da partida assume exatamente os seis valores do glossário."""
    assert {status.value for status in Status} == {
        "realizada",
        "agendada",
        "atribuida",
        "adiada",
        "cancelada",
        "abandonada",
    }


def test_status_se_compara_como_texto() -> None:
    """REQ-003: o status é gravado como texto, então se compara com a string do glossário."""
    assert Status.ATRIBUIDA == "atribuida"


def test_partida_e_imutavel() -> None:
    """REQ-001: uma partida lida do arquivo não muda depois de criada."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        PARTIDA.mandante = "Outro"  # type: ignore[misc]  # o teste é justamente a atribuição proibida


def test_placar_negativo_e_recusado() -> None:
    """REQ-002: gols nunca são negativos."""
    with pytest.raises(ValueError, match="negativo"):
        Placar(mandante=-1, visitante=0)


def test_placar_formata_como_mandante_traco_visitante() -> None:
    """REQ-002: o placar dos pênaltis é guardado no formato M-V."""
    assert Placar(mandante=5, visitante=3).como_texto() == "5-3"
