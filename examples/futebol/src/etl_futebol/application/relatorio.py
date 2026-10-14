"""O que uma execução fez, por arquivo ou tabela de origem (REQ-009)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Situacao = Literal["ok", "falhou", "nao_carregado"]


@dataclass(frozen=True, slots=True)
class EntradaRelatorio:
    origem: str
    declarado: int | None
    gravadas: int
    rejeitadas: int
    situacao: Situacao
    motivo: str = ""

    def como_texto(self) -> str:
        declarado = "-" if self.declarado is None else str(self.declarado)
        texto = f"{self.origem}  {self.situacao}  declarado={declarado} gravadas={self.gravadas} rejeitadas={self.rejeitadas}"
        return f"{texto}  motivo: {self.motivo}" if self.motivo else texto


@dataclass(frozen=True, slots=True)
class RelatorioExecucao:
    entradas: tuple[EntradaRelatorio, ...]

    @property
    def falhas(self) -> int:
        return sum(1 for entrada in self.entradas if entrada.situacao == "falhou")

    @property
    def codigo_saida(self) -> int:
        return 1 if self.falhas else 0

    def juntar(self, outro: RelatorioExecucao) -> RelatorioExecucao:
        return RelatorioExecucao(self.entradas + outro.entradas)

    def como_texto(self) -> str:
        gravadas = sum(entrada.gravadas for entrada in self.entradas)
        rejeitadas = sum(entrada.rejeitadas for entrada in self.entradas)
        total = (
            f"total: {len(self.entradas)} arquivos, {self.falhas} falharam, gravadas={gravadas} rejeitadas={rejeitadas}"
        )
        return "\n".join([*(entrada.como_texto() for entrada in self.entradas), total])
