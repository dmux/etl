"""Portas: o que os casos de uso precisam do mundo, em termos do domínio. Nenhum tipo de framework."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from etl_futebol.domain.modelos import Camada, LinhaClassificacao, Particao, Partida, Rejeitado


@runtime_checkable
class FontePort(Protocol):
    """Os arquivos de origem. Só leitura: a fonte é imutável."""

    def listar(self) -> Sequence[str]:
        """Caminhos relativos à raiz da fonte, em ordem estável."""
        ...

    def ler(self, arquivo: str) -> bytes:
        """Bytes crus; decodificar é decisão do caso de uso (REQ-004.4)."""
        ...


@runtime_checkable
class RepositorioPartidasPort(Protocol):
    def substituir_particoes(self, camada: Camada, partidas: Sequence[Partida], particoes: Sequence[Particao]) -> int:
        """Troca o conteúdo das partições dadas pelas partidas; as demais ficam intactas."""
        ...

    def substituir_tudo(self, camada: Camada, partidas: Sequence[Partida]) -> int:
        """Troca o conteúdo inteiro da camada."""
        ...

    def ler(self, camada: Camada) -> list[Partida]: ...


@runtime_checkable
class RepositorioRejeitadosPort(Protocol):
    def substituir_arquivos(self, camada: Camada, rejeitados: Sequence[Rejeitado], arquivos: Sequence[str]) -> int:
        """Troca os rejeitados dos arquivos dados; os de outros arquivos ficam."""
        ...

    def substituir_tudo(self, camada: Camada, rejeitados: Sequence[Rejeitado]) -> int: ...


@runtime_checkable
class RepositorioClassificacaoPort(Protocol):
    def substituir_tudo(self, linhas: Sequence[LinhaClassificacao]) -> int: ...
