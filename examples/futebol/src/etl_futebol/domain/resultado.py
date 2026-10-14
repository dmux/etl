"""Interpretação do resultado de uma linha de partida.

As formas são testadas da mais específica para a mais genérica (skill `openfootball-format`).
Na ordem inversa, `5-3 pen. (1-1, 0-1)` casaria com `N-N` e os pênaltis virariam gols, sem erro.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from etl_futebol.domain.modelos import Placar, Resultado, Status

_PLACAR = r"(\d+)-(\d+)"

_MARCADORES = {
    "[postponed]": Status.ADIADA,
    "[cancelled]": Status.CANCELADA,
    "[abandoned]": Status.ABANDONADA,
}

# O placar `a.e.t.`, quando existe, é ignorado: na origem ele repete o dos pênaltis (REQ-002.5).
_PENALTIS = re.compile(rf"^{_PLACAR}\s+pen\.\s+(?:{_PLACAR}\s+a\.e\.t\.\s+)?\({_PLACAR}(?:,\s*{_PLACAR})?\)$")
_ATRIBUIDO = re.compile(rf"^{_PLACAR}\s+\[awarded\]$")
_FINAL = re.compile(rf"^{_PLACAR}(?:\s+\({_PLACAR}\))?$")


def _placar(grupos: tuple[str | None, ...], inicio: int) -> Placar | None:
    mandante, visitante = grupos[inicio], grupos[inicio + 1]
    if mandante is None or visitante is None:
        return None
    return Placar(int(mandante), int(visitante))


def _de_penaltis(grupos: tuple[str | None, ...]) -> Resultado:
    # Um placar só entre parênteses, numa disputa de pênaltis, é o do jogo (REQ-002.4).
    return Resultado(_placar(grupos, 4), _placar(grupos, 6), _placar(grupos, 0), Status.REALIZADA)


def _de_atribuido(grupos: tuple[str | None, ...]) -> Resultado:
    return Resultado(_placar(grupos, 0), None, None, Status.ATRIBUIDA)


def _de_final(grupos: tuple[str | None, ...]) -> Resultado:
    return Resultado(_placar(grupos, 0), _placar(grupos, 2), None, Status.REALIZADA)


_FORMAS: tuple[tuple[re.Pattern[str], Callable[[tuple[str | None, ...]], Resultado]], ...] = (
    (_PENALTIS, _de_penaltis),
    (_ATRIBUIDO, _de_atribuido),
    (_FINAL, _de_final),
)


def interpretar_resultado(texto: str) -> Resultado | None:
    """Converte o trecho de resultado de uma linha; `None` se não casar com nenhuma forma."""
    limpo = texto.strip()
    if not limpo:
        return Resultado(None, None, None, Status.AGENDADA)
    if limpo in _MARCADORES:
        return Resultado(None, None, None, _MARCADORES[limpo])
    for padrao, construir in _FORMAS:
        casamento = padrao.match(limpo)
        if casamento:
            return construir(casamento.groups())
    return None
