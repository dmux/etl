"""Schemas explícitos das tabelas e conversão entre modelo do domínio e linha de tabela.

Schema declarado, nunca inferido: é o contrato público das tabelas (design.md).
A ordem das colunas é a ordem dos campos do modelo, e um teste trava essa igualdade.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pyspark.sql.types import DateType, DecimalType, IntegerType, StringType, StructField, StructType

from etl_futebol.domain.modelos import LinhaClassificacao, Partida, Rejeitado, Status


def _texto(nome: str, nulo: bool = False) -> StructField:
    return StructField(nome, StringType(), nulo)


def _inteiro(nome: str, nulo: bool = False) -> StructField:
    return StructField(nome, IntegerType(), nulo)


PARTIDAS = StructType(
    [
        _texto("competicao"),
        _inteiro("temporada"),
        _texto("rodada"),
        _inteiro("rodada_num", nulo=True),
        StructField("data", DateType(), False),
        _texto("hora", nulo=True),
        _texto("mandante"),
        _texto("visitante"),
        _inteiro("gols_mandante", nulo=True),
        _inteiro("gols_visitante", nulo=True),
        _inteiro("gols_mandante_ht", nulo=True),
        _inteiro("gols_visitante_ht", nulo=True),
        _texto("penaltis", nulo=True),
        _texto("status"),
        _texto("arquivo"),
        _inteiro("linha"),
    ]
)

REJEITADOS = StructType([_texto("arquivo"), _inteiro("linha", nulo=True), _texto("texto"), _texto("motivo")])

CLASSIFICACAO = StructType(
    [
        _texto("competicao"),
        _inteiro("temporada"),
        _texto("clube"),
        *(
            _inteiro(nome)
            for nome in ("jogos", "vitorias", "empates", "derrotas", "gols_pro", "gols_contra", "saldo_gols", "pontos")
        ),
        StructField("aproveitamento", DecimalType(5, 4), True),
    ]
)

Linha = tuple[Any, ...]


def linha_de_partida(partida: Partida) -> Linha:
    valores = [getattr(partida, nome) for nome in PARTIDAS.fieldNames()]
    valores[PARTIDAS.fieldNames().index("status")] = partida.status.value
    return tuple(valores)


def partida_de_linha(linha: Sequence[Any]) -> Partida:
    valores = dict(zip(PARTIDAS.fieldNames(), linha, strict=True))
    return Partida(**{**valores, "status": Status(valores["status"])})


def linha_de_rejeitado(rejeitado: Rejeitado) -> Linha:
    return tuple(getattr(rejeitado, nome) for nome in REJEITADOS.fieldNames())


def rejeitado_de_linha(linha: Sequence[Any]) -> Rejeitado:
    return Rejeitado(*linha)


def linha_de_classificacao(classificacao: LinhaClassificacao) -> Linha:
    return tuple(getattr(classificacao, nome) for nome in CLASSIFICACAO.fieldNames())


def classificacao_de_linha(linha: Sequence[Any]) -> LinhaClassificacao:
    return LinhaClassificacao(*linha)
