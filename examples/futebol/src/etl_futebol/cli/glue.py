"""Wiring do job AWS Glue: escolhe os adaptadores reais e executa as camadas pedidas (ADR-009).

Roda só dentro da imagem do Glue: `awsglue` e `boto3` são importados aqui, nunca no topo de um
módulo que os testes do host importam.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from etl_futebol.application.casos_de_uso import CalcularGold, IngerirBronze, RefinarSilver
from etl_futebol.application.relatorio import RelatorioExecucao
from etl_futebol.infrastructure.catalogo_glue import RegistroCatalogoGlue
from etl_futebol.infrastructure.fonte_s3 import FonteS3Spark
from etl_futebol.infrastructure.iceberg import (
    RepositorioClassificacaoIceberg,
    RepositorioPartidasIceberg,
    RepositorioRejeitadosIceberg,
)
from etl_futebol.infrastructure.sessao_glue import criar_sessao_glue
from etl_futebol.infrastructure.verificacao import contar_resultados

logger = logging.getLogger("etl_futebol")
CAMADAS = ("bronze", "silver", "gold", "verificacao")
# Sem JOB_NAME: o ministack não o passa ao script (convencoes-spark.md).
ARGUMENTOS = ["camadas", "fonte", "warehouse"]


@dataclass(frozen=True, slots=True)
class _Contexto:
    spark: Any
    fonte: str
    registro: RegistroCatalogoGlue


def _executar(camada: str, contexto: _Contexto) -> RelatorioExecucao:
    partidas = RepositorioPartidasIceberg(contexto.spark, contexto.registro)
    rejeitados = RepositorioRejeitadosIceberg(contexto.spark, contexto.registro)
    if camada == "bronze":
        return IngerirBronze(FonteS3Spark(contexto.spark, contexto.fonte), partidas, rejeitados).executar()
    if camada == "silver":
        return RefinarSilver(partidas, rejeitados).executar()
    return CalcularGold(partidas, RepositorioClassificacaoIceberg(contexto.spark, contexto.registro)).executar()


def _verificar(contexto: _Contexto) -> None:
    for nome, valor in contar_resultados(contexto.spark).items():
        logger.info("etl_futebol: verificacao %s=%d", nome, valor)


def _camadas(texto: str) -> list[str]:
    camadas = [camada.strip() for camada in texto.split(",") if camada.strip()]
    desconhecidas = [camada for camada in camadas if camada not in CAMADAS]
    if desconhecidas:
        raise ValueError(f"camadas desconhecidas: {desconhecidas}; use {', '.join(CAMADAS)}")
    return camadas


def main(argv: Sequence[str]) -> int:
    """Executa as camadas na ordem pedida. Silver roda mesmo se bronze reprovar arquivos (ADR-009)."""
    import boto3
    from awsglue.utils import getResolvedOptions

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    argumentos = getResolvedOptions(list(argv), ARGUMENTOS)
    registro = RegistroCatalogoGlue(boto3.client("s3"), boto3.client("glue"), argumentos["warehouse"])
    contexto = _Contexto(criar_sessao_glue(), argumentos["fonte"], registro)
    codigo = 0
    for camada in _camadas(argumentos["camadas"]):
        if camada == "verificacao":
            _verificar(contexto)
            continue
        relatorio = _executar(camada, contexto)
        logger.info("relatório da camada %s:\n%s", camada, relatorio.como_texto())
        codigo = max(codigo, relatorio.codigo_saida)
    # O ministack pode marcar SUCCEEDED um job que falhou; quem executa decide por esta linha.
    logger.info("etl_futebol: codigo_saida=%d", codigo)
    return codigo
