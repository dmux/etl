"""Adaptadores em memória das portas. Usados nos testes, com a mesma semântica dos reais."""

from __future__ import annotations

from collections.abc import Sequence

from etl_futebol.domain.modelos import Camada, LinhaClassificacao, Particao, Partida, Rejeitado


class FonteMemoria:
    def __init__(self, arquivos: dict[str, bytes]) -> None:
        self.arquivos = arquivos

    def listar(self) -> Sequence[str]:
        return sorted(self.arquivos)

    def ler(self, arquivo: str) -> bytes:
        return self.arquivos[arquivo]


class RepositorioPartidasMemoria:
    def __init__(self) -> None:
        self.camadas: dict[Camada, list[Partida]] = {"bronze": [], "silver": []}

    def substituir_particoes(self, camada: Camada, partidas: Sequence[Partida], particoes: Sequence[Particao]) -> int:
        alvo = set(particoes)
        mantidas = [p for p in self.camadas[camada] if (p.competicao, p.temporada) not in alvo]
        self.camadas[camada] = [*mantidas, *partidas]
        return len(partidas)

    def substituir_tudo(self, camada: Camada, partidas: Sequence[Partida]) -> int:
        self.camadas[camada] = list(partidas)
        return len(partidas)

    def ler(self, camada: Camada) -> list[Partida]:
        return list(self.camadas[camada])


class RepositorioRejeitadosMemoria:
    def __init__(self) -> None:
        self.camadas: dict[Camada, list[Rejeitado]] = {"bronze": [], "silver": []}

    def substituir_arquivos(self, camada: Camada, rejeitados: Sequence[Rejeitado], arquivos: Sequence[str]) -> int:
        alvo = set(arquivos)
        mantidos = [r for r in self.camadas[camada] if r.arquivo not in alvo]
        self.camadas[camada] = [*mantidos, *rejeitados]
        return len(rejeitados)

    def substituir_tudo(self, camada: Camada, rejeitados: Sequence[Rejeitado]) -> int:
        self.camadas[camada] = list(rejeitados)
        return len(rejeitados)

    def ler(self, camada: Camada) -> list[Rejeitado]:
        return list(self.camadas[camada])


class RepositorioClassificacaoMemoria:
    def __init__(self) -> None:
        self.linhas: list[LinhaClassificacao] = []

    def substituir_tudo(self, linhas: Sequence[LinhaClassificacao]) -> int:
        self.linhas = list(linhas)
        return len(linhas)
