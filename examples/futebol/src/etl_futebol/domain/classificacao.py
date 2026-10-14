"""Classificação por clube, temporada e competição (REQ-008). Fórmulas do glossário."""

from __future__ import annotations

import decimal
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal

from etl_futebol.domain.modelos import LinhaClassificacao, Partida, Status

# Copa do Brasil é mata-mata: não tem tabela de pontos (fora de escopo no requirements.md).
_PONTOS_CORRIDOS = ("Brasileiro Série A", "Brasileiro Série B")
_STATUS_CONTADOS = (Status.REALIZADA, Status.ATRIBUIDA)
_CASAS = Decimal("0.0001")


@dataclass(slots=True)
class _Acumulado:
    jogos: int = 0
    vitorias: int = 0
    empates: int = 0
    derrotas: int = 0
    gols_pro: int = 0
    gols_contra: int = 0

    def registrar(self, pro: int, contra: int) -> None:
        self.jogos += 1
        self.gols_pro += pro
        self.gols_contra += contra
        if pro > contra:
            self.vitorias += 1
        elif pro == contra:
            self.empates += 1
        else:
            self.derrotas += 1


_Chave = tuple[str, int, str]


def calcular_classificacao(partidas: Sequence[Partida]) -> list[LinhaClassificacao]:
    """Uma linha por clube que aparece em ao menos uma partida, ordenada por competição, temporada e clube."""
    acumulados: dict[_Chave, _Acumulado] = {}
    for partida in partidas:
        if partida.competicao not in _PONTOS_CORRIDOS:
            continue
        for clube, pro, contra in _lados(partida):
            acumulado = acumulados.setdefault((partida.competicao, partida.temporada, clube), _Acumulado())
            if partida.status in _STATUS_CONTADOS and pro is not None and contra is not None:
                acumulado.registrar(pro, contra)
    return [_linha(chave, acumulado) for chave, acumulado in sorted(acumulados.items())]


def _lados(partida: Partida) -> Iterator[tuple[str, int | None, int | None]]:
    """A partida vista pelo mandante e pelo visitante: (clube, gols pró, gols contra)."""
    yield partida.mandante, partida.gols_mandante, partida.gols_visitante
    yield partida.visitante, partida.gols_visitante, partida.gols_mandante


def _linha(chave: _Chave, acumulado: _Acumulado) -> LinhaClassificacao:
    competicao, temporada, clube = chave
    pontos = 3 * acumulado.vitorias + acumulado.empates
    return LinhaClassificacao(
        competicao=competicao,
        temporada=temporada,
        clube=clube,
        jogos=acumulado.jogos,
        vitorias=acumulado.vitorias,
        empates=acumulado.empates,
        derrotas=acumulado.derrotas,
        gols_pro=acumulado.gols_pro,
        gols_contra=acumulado.gols_contra,
        saldo_gols=acumulado.gols_pro - acumulado.gols_contra,
        pontos=pontos,
        aproveitamento=_aproveitamento(pontos, acumulado.jogos),
    )


def _aproveitamento(pontos: int, jogos: int) -> Decimal | None:
    # Zero jogos não é 0% de aproveitamento: é aproveitamento indefinido (glossário).
    if jogos == 0:
        return None
    return (Decimal(pontos) / Decimal(jogos * 3)).quantize(_CASAS, rounding=decimal.ROUND_HALF_UP)
