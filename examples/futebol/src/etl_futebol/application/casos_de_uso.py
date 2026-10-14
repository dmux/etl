"""Casos de uso: orquestram domínio e portas, sem saber quem implementa as portas."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from etl_futebol.application.portas import (
    FontePort,
    RepositorioClassificacaoPort,
    RepositorioPartidasPort,
    RepositorioRejeitadosPort,
)
from etl_futebol.application.relatorio import EntradaRelatorio, RelatorioExecucao
from etl_futebol.domain.classificacao import calcular_classificacao
from etl_futebol.domain.contagem import conferir_contagem
from etl_futebol.domain.escopo import no_escopo
from etl_futebol.domain.invariantes import deduplicar, validar
from etl_futebol.domain.modelos import ArquivoProcessado, Particao, Rejeitado
from etl_futebol.domain.parser import parsear_arquivo

logger = logging.getLogger(__name__)


class ColisaoDeParticaoError(Exception):
    """Dois arquivos apontam para a mesma (competição, temporada): gravar um apagaria o outro."""


@dataclass(frozen=True, slots=True)
class _Avaliacao:
    entrada: EntradaRelatorio
    aprovado: ArquivoProcessado | None = None
    rejeitado_de_arquivo: Rejeitado | None = None


def _particao(processado: ArquivoProcessado) -> Particao:
    # Só arquivos aprovados chegam aqui, e aprovação exige cabeçalho.
    assert processado.competicao is not None and processado.temporada is not None
    return processado.competicao, processado.temporada


class IngerirBronze:
    """Lê a fonte, parseia, confere a contagem e grava os arquivos aprovados em bronze."""

    def __init__(
        self, fonte: FontePort, partidas: RepositorioPartidasPort, rejeitados: RepositorioRejeitadosPort
    ) -> None:
        self._fonte = fonte
        self._partidas = partidas
        self._rejeitados = rejeitados

    def executar(self) -> RelatorioExecucao:
        avaliacoes = [self._avaliar(arquivo) for arquivo in self._fonte.listar()]
        aprovados = [avaliacao.aprovado for avaliacao in avaliacoes if avaliacao.aprovado is not None]
        _conferir_particoes(aprovados)
        ilegiveis = [a.rejeitado_de_arquivo for a in avaliacoes if a.rejeitado_de_arquivo is not None]
        self._gravar(aprovados, ilegiveis)
        return RelatorioExecucao(tuple(avaliacao.entrada for avaliacao in avaliacoes))

    def _avaliar(self, arquivo: str) -> _Avaliacao:
        if not no_escopo(arquivo):
            return _Avaliacao(EntradaRelatorio(arquivo, None, 0, 0, "nao_carregado", "fora do escopo"))
        try:
            texto = self._fonte.ler(arquivo).decode("utf-8")
        except UnicodeDecodeError as erro:
            rejeitado = Rejeitado(arquivo, None, "", f"arquivo não é UTF-8: {erro}")
            return _Avaliacao(EntradaRelatorio(arquivo, None, 0, 1, "falhou", rejeitado.motivo), None, rejeitado)
        return _avaliar_processado(parsear_arquivo(arquivo, texto))

    def _gravar(self, aprovados: Sequence[ArquivoProcessado], ilegiveis: Sequence[Rejeitado]) -> None:
        if aprovados:
            partidas = [partida for processado in aprovados for partida in processado.partidas]
            gravadas = self._partidas.substituir_particoes("bronze", partidas, [_particao(p) for p in aprovados])
            logger.info("bronze: %d partidas de %d arquivos", gravadas, len(aprovados))
        rejeitados = [rejeitado for processado in aprovados for rejeitado in processado.rejeitados]
        arquivos = [processado.arquivo for processado in aprovados] + [r.arquivo for r in ilegiveis]
        if arquivos:
            self._rejeitados.substituir_arquivos("bronze", [*rejeitados, *ilegiveis], arquivos)


def _avaliar_processado(processado: ArquivoProcessado) -> _Avaliacao:
    partidas, rejeitados = len(processado.partidas), len(processado.rejeitados)
    motivo = "cabeçalho ausente" if processado.competicao is None else conferir_contagem(processado)
    if motivo is not None:
        logger.warning("%s falhou: %s", processado.arquivo, motivo)
        return _Avaliacao(EntradaRelatorio(processado.arquivo, processado.declarado, 0, rejeitados, "falhou", motivo))
    entrada = EntradaRelatorio(processado.arquivo, processado.declarado, partidas, rejeitados, "ok")
    return _Avaliacao(entrada, processado)


def _conferir_particoes(aprovados: Sequence[ArquivoProcessado]) -> None:
    contagem = Counter(_particao(processado) for processado in aprovados)
    repetidas = {particao for particao, vezes in contagem.items() if vezes > 1}
    if repetidas:
        arquivos = sorted(p.arquivo for p in aprovados if _particao(p) in repetidas)
        raise ColisaoDeParticaoError(f"arquivos na mesma partição {sorted(repetidas)}: {arquivos}")


class RefinarSilver:
    """Lê bronze, barra o que viola invariante, remove duplicata e reescreve silver inteira."""

    def __init__(self, partidas: RepositorioPartidasPort, rejeitados: RepositorioRejeitadosPort) -> None:
        self._partidas = partidas
        self._rejeitados = rejeitados

    def executar(self) -> RelatorioExecucao:
        bronze = self._partidas.ler("bronze")
        validas, invalidas = validar(bronze)
        unicas, duplicadas = deduplicar(validas)
        gravadas = self._partidas.substituir_tudo("silver", unicas)
        rejeitadas = self._rejeitados.substituir_tudo("silver", [*invalidas, *duplicadas])
        logger.info("silver: %d partidas, %d rejeitadas", gravadas, rejeitadas)
        entrada = EntradaRelatorio("futebol.silver.partidas", len(bronze), gravadas, rejeitadas, "ok")
        return RelatorioExecucao((entrada,))


class CalcularGold:
    """Lê silver e reescreve a classificação inteira."""

    def __init__(self, partidas: RepositorioPartidasPort, classificacao: RepositorioClassificacaoPort) -> None:
        self._partidas = partidas
        self._classificacao = classificacao

    def executar(self) -> RelatorioExecucao:
        silver = self._partidas.ler("silver")
        gravadas = self._classificacao.substituir_tudo(calcular_classificacao(silver))
        logger.info("gold: %d linhas de classificação", gravadas)
        return RelatorioExecucao((EntradaRelatorio("futebol.gold.classificacao", len(silver), gravadas, 0, "ok"),))
