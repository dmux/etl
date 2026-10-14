"""Fonte em sistema de arquivos. No job, a raiz é /data/dbfs/futebol/fonte (ADR-005)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


class FonteArquivosFs:
    """Lê `.txt` sob uma raiz, só em modo leitura."""

    def __init__(self, raiz: Path) -> None:
        self._raiz = raiz

    def listar(self) -> Sequence[str]:
        if not self._raiz.is_dir():
            raise FileNotFoundError(f"raiz da fonte não encontrada: {self._raiz}")
        return sorted(caminho.relative_to(self._raiz).as_posix() for caminho in self._raiz.rglob("*.txt"))

    def ler(self, arquivo: str) -> bytes:
        caminho = (self._raiz / arquivo).resolve()
        if self._raiz.resolve() not in caminho.parents:
            raise ValueError(f"{arquivo} está fora da raiz da fonte {self._raiz}")
        return caminho.read_bytes()
