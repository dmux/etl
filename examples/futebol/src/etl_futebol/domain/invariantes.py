"""Regras que uma partida precisa cumprir para chegar a silver (REQ-007).

Bronze guarda a partida como o arquivo diz; é aqui que ela é julgada.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from etl_futebol.domain.modelos import Partida, Rejeitado, Status

_STATUS_DISPUTADOS = (Status.REALIZADA, Status.ATRIBUIDA)


def _mesmo_clube(partida: Partida) -> str | None:
    return "mandante igual ao visitante" if partida.mandante == partida.visitante else None


def _primeiro_tempo_maior(partida: Partida) -> str | None:
    pares = (
        (partida.gols_mandante_ht, partida.gols_mandante),
        (partida.gols_visitante_ht, partida.gols_visitante),
    )
    for primeiro_tempo, final in pares:
        if primeiro_tempo is not None and final is not None and primeiro_tempo > final:
            return "gols do primeiro tempo maiores que os finais"
    return None


def _gols_sem_partida_disputada(partida: Partida) -> str | None:
    tem_gols = partida.gols_mandante is not None or partida.gols_visitante is not None
    if tem_gols and partida.status not in _STATUS_DISPUTADOS:
        return f"gols em partida com status {partida.status.value}"
    return None


_REGRAS: tuple[Callable[[Partida], str | None], ...] = (
    _mesmo_clube,
    _primeiro_tempo_maior,
    _gols_sem_partida_disputada,
)


def descrever(partida: Partida) -> str:
    """Texto do rejeitado de silver: não há linha original, então a partida é descrita."""
    placar = f"{partida.gols_mandante}-{partida.gols_visitante}" if partida.gols_mandante is not None else "sem placar"
    return f"{partida.data.isoformat()} {partida.mandante} v {partida.visitante} {placar} ({partida.status.value})"


def _rejeitar(partida: Partida, motivo: str) -> Rejeitado:
    return Rejeitado(partida.arquivo, partida.linha, descrever(partida), motivo)


def validar(partidas: Sequence[Partida]) -> tuple[list[Partida], list[Rejeitado]]:
    """Separa as partidas válidas das que violam alguma regra; a primeira regra violada dá o motivo."""
    validas: list[Partida] = []
    rejeitados: list[Rejeitado] = []
    for partida in partidas:
        motivo = next((m for regra in _REGRAS if (m := regra(partida)) is not None), None)
        if motivo is None:
            validas.append(partida)
        else:
            rejeitados.append(_rejeitar(partida, motivo))
    return validas, rejeitados


def deduplicar(partidas: Sequence[Partida]) -> tuple[list[Partida], list[Rejeitado]]:
    """Uma partida por (competição, temporada, mandante, visitante, data); fica a de menor arquivo e linha."""
    unicas: dict[tuple[object, ...], Partida] = {}
    rejeitados: list[Rejeitado] = []
    for partida in sorted(partidas, key=lambda p: (p.arquivo, p.linha)):
        chave = (partida.competicao, partida.temporada, partida.mandante, partida.visitante, partida.data)
        if chave in unicas:
            rejeitados.append(_rejeitar(partida, "partida duplicada"))
        else:
            unicas[chave] = partida
    return list(unicas.values()), rejeitados
