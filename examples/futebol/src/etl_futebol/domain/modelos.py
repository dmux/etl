"""Modelos de domínio. Nomes de campo vêm de steering/glossario-dados.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal


class Status(str, Enum):
    """Situação da partida, derivada dos marcadores da origem.

    `str, Enum` em vez de `StrEnum`: o job roda em Python 3.10 (ADR-004).
    """

    REALIZADA = "realizada"
    AGENDADA = "agendada"
    ATRIBUIDA = "atribuida"
    ADIADA = "adiada"
    CANCELADA = "cancelada"
    ABANDONADA = "abandonada"


@dataclass(frozen=True, slots=True)
class Placar:
    mandante: int
    visitante: int

    def __post_init__(self) -> None:
        if self.mandante < 0 or self.visitante < 0:
            raise ValueError(f"placar negativo: {self.mandante}-{self.visitante}")

    def como_texto(self) -> str:
        return f"{self.mandante}-{self.visitante}"


@dataclass(frozen=True, slots=True)
class Resultado:
    gols: Placar | None
    gols_ht: Placar | None
    penaltis: Placar | None
    status: Status


@dataclass(frozen=True, slots=True)
class Partida:
    """Uma linha por partida. Invariantes são validadas em silver, não aqui (REQ-007)."""

    competicao: str
    temporada: int
    rodada: str
    rodada_num: int | None
    data: date
    hora: str | None
    mandante: str
    visitante: str
    gols_mandante: int | None
    gols_visitante: int | None
    gols_mandante_ht: int | None
    gols_visitante_ht: int | None
    penaltis: str | None
    status: Status
    arquivo: str
    linha: int


@dataclass(frozen=True, slots=True)
class Rejeitado:
    """Linha, partida ou arquivo não aceito. `linha` nula = o arquivo inteiro."""

    arquivo: str
    linha: int | None
    texto: str
    motivo: str


@dataclass(frozen=True, slots=True)
class ArquivoProcessado:
    """Resultado do parser. Competição e temporada nulas = arquivo sem cabeçalho `=`."""

    arquivo: str
    competicao: str | None
    temporada: int | None
    declarado: int | None
    partidas: tuple[Partida, ...]
    rejeitados: tuple[Rejeitado, ...]


@dataclass(frozen=True, slots=True)
class LinhaClassificacao:
    competicao: str
    temporada: int
    clube: str
    jogos: int
    vitorias: int
    empates: int
    derrotas: int
    gols_pro: int
    gols_contra: int
    saldo_gols: int
    pontos: int
    aproveitamento: Decimal | None


# Camadas que guardam partidas e rejeitados. Gold guarda classificação e tem porta própria.
Camada = Literal["bronze", "silver"]

# Chave de idempotência de bronze: cada arquivo do escopo é exatamente uma partição (ADR-006).
Particao = tuple[str, int]
