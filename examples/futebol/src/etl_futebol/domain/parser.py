"""Parser do formato openfootball: texto entra, `ArquivoProcessado` sai. Sem I/O.

O significado de uma linha depende das anteriores (data, hora e rodada vigentes), então o
parser carrega um estado de leitura imutável, substituído a cada linha.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date

from etl_futebol.domain.modelos import ArquivoProcessado, Partida, Rejeitado, Resultado
from etl_futebol.domain.resultado import interpretar_resultado

_CABECALHO = re.compile(r"^=\s*(.+?)\s+(\d{4})$")
_CONTAGEM = re.compile(r"^#\s*Matches\s+(\d+)")
_NUMERO_RODADA = re.compile(r"\b(?:Matchday|Round)\s+(\d+)")
_DATA = re.compile(r"^[A-Z][a-z]{2}\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?$")
_HORA = re.compile(r"^(\d{1,2}:\d{2})\s+(.*)$")
_SEPARADOR = re.compile(r"(?:^|\s+)v(?:\s+|$)")
_PLACAR_NO_NOME = re.compile(r"\d+-\d*|[\[(]")
_MESES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True, slots=True)
class _Estado:
    competicao: str | None = None
    temporada: int | None = None
    declarado: int | None = None
    rodada: str = ""
    rodada_num: int | None = None
    data: date | None = None
    hora: str | None = None
    # Não `ano_vigente`: o glossário proíbe `ano` como sinônimo de `temporada`.
    ultima_data_completa: date | None = None


@dataclass(frozen=True, slots=True)
class _Linha:
    arquivo: str
    numero: int
    texto: str


@dataclass(frozen=True, slots=True)
class _Contexto:
    competicao: str
    temporada: int
    data: date
    estado: _Estado


@dataclass(frozen=True, slots=True)
class _Campos:
    hora: str | None
    mandante: str
    visitante: str
    resultado: Resultado


class _LinhaRejeitadaError(Exception):
    """Sinal interno: a linha vira `Rejeitado`. Sempre capturado em `parsear_arquivo`."""

    def __init__(self, motivo: str, estado: _Estado) -> None:
        super().__init__(motivo)
        self.motivo = motivo
        self.estado = estado


def parsear_arquivo(arquivo: str, texto: str) -> ArquivoProcessado:
    """Interpreta um arquivo inteiro. Nenhuma linha some: ou vira partida, ou vira rejeitado."""
    estado = _Estado()
    partidas: list[Partida] = []
    rejeitados: list[Rejeitado] = []
    for numero, conteudo in enumerate(texto.splitlines(), start=1):
        try:
            estado, partida = _ler_linha(estado, _Linha(arquivo, numero, conteudo))
        except _LinhaRejeitadaError as rejeicao:
            estado = rejeicao.estado
            rejeitados.append(Rejeitado(arquivo, numero, conteudo, rejeicao.motivo))
            continue
        if partida is not None:
            partidas.append(partida)
    return ArquivoProcessado(
        arquivo, estado.competicao, estado.temporada, estado.declarado, tuple(partidas), tuple(rejeitados)
    )


def _ler_linha(estado: _Estado, linha: _Linha) -> tuple[_Estado, Partida | None]:
    conteudo = linha.texto.strip()
    if not conteudo:
        return estado, None
    if conteudo.startswith("="):
        return _ler_cabecalho(estado, conteudo), None
    if conteudo.startswith("#"):
        return _ler_metadado(estado, conteudo), None
    if conteudo.startswith("▪"):
        return _ler_rodada(estado, conteudo), None
    if _SEPARADOR.search(conteudo):
        return _ler_partida(estado, linha, conteudo)
    return _ler_data(estado, conteudo), None


def _ler_cabecalho(estado: _Estado, conteudo: str) -> _Estado:
    casamento = _CABECALHO.match(conteudo)
    if casamento is None:
        raise _LinhaRejeitadaError("cabeçalho não reconhecido", estado)
    return replace(estado, competicao=casamento.group(1), temporada=int(casamento.group(2)))


def _ler_metadado(estado: _Estado, conteudo: str) -> _Estado:
    casamento = _CONTAGEM.match(conteudo)
    return replace(estado, declarado=int(casamento.group(1))) if casamento else estado


def _ler_rodada(estado: _Estado, conteudo: str) -> _Estado:
    rodada = conteudo.lstrip("▪").strip()
    numero = _NUMERO_RODADA.search(rodada)
    return replace(estado, rodada=rodada, rodada_num=int(numero.group(1)) if numero else None)


def _ler_data(estado: _Estado, conteudo: str) -> _Estado:
    casamento = _DATA.match(conteudo)
    if casamento is None:
        raise _LinhaRejeitadaError("linha não reconhecida", estado)
    mes, dia, aaaa = casamento.groups()
    # Sem data válida, as partidas seguintes ficam sem data e são rejeitadas, em vez de herdar a anterior.
    sem_data = replace(estado, data=None, hora=None)
    referencia = estado.ultima_data_completa
    if aaaa is not None:
        aaaa_efetivo = int(aaaa)
    elif referencia is not None:
        aaaa_efetivo = referencia.year
    else:
        raise _LinhaRejeitadaError("data sem ano antes de qualquer data completa", sem_data)
    try:
        data = date(aaaa_efetivo, _MESES.index(mes) + 1, int(dia))
    except ValueError as erro:
        raise _LinhaRejeitadaError(f"data inválida: {erro}", sem_data) from erro
    completa = data if aaaa else referencia
    return replace(estado, data=data, hora=None, ultima_data_completa=completa)


def _ler_partida(estado: _Estado, linha: _Linha, conteudo: str) -> tuple[_Estado, Partida]:
    contexto = _contexto(estado)
    campos = _separar_campos(conteudo, estado)
    novo_estado = replace(estado, hora=campos.hora or estado.hora)
    return novo_estado, _montar_partida(replace(contexto, estado=novo_estado), linha, campos)


def _contexto(estado: _Estado) -> _Contexto:
    """O estado com o que toda partida exige; sem isso, a partida é rejeitada."""
    if estado.competicao is None or estado.temporada is None:
        raise _LinhaRejeitadaError("partida sem cabeçalho", estado)
    if estado.data is None:
        raise _LinhaRejeitadaError("partida sem data", estado)
    return _Contexto(estado.competicao, estado.temporada, estado.data, estado)


def _separar_campos(conteudo: str, estado: _Estado) -> _Campos:
    casamento_hora = _HORA.match(conteudo)
    hora = casamento_hora.group(1) if casamento_hora else None
    resto = casamento_hora.group(2) if casamento_hora else conteudo
    mandante, direita = _SEPARADOR.split(resto, maxsplit=1)
    # Nome de clube tem espaço simples; o resultado vem depois de dois ou mais (confirmado no dado).
    partes = re.split(r"\s{2,}", direita.strip(), maxsplit=1)
    visitante, texto_resultado = partes[0], partes[1] if len(partes) > 1 else ""
    _conferir_nomes(mandante.strip(), visitante, estado)
    resultado = interpretar_resultado(texto_resultado)
    if resultado is None:
        raise _LinhaRejeitadaError(f"resultado não reconhecido: {texto_resultado!r}", estado)
    return _Campos(hora, mandante.strip(), visitante, resultado)


def _conferir_nomes(mandante: str, visitante: str, estado: _Estado) -> None:
    if not mandante:
        raise _LinhaRejeitadaError("partida sem mandante", estado)
    if not visitante:
        raise _LinhaRejeitadaError("partida sem visitante", estado)
    # Nenhum nome de clube da origem tem placar, colchete ou parêntese (confirmado no dado).
    if _PLACAR_NO_NOME.search(visitante):
        raise _LinhaRejeitadaError("resultado colado ao nome do visitante", estado)


def _montar_partida(contexto: _Contexto, linha: _Linha, campos: _Campos) -> Partida:
    gols, gols_ht, penaltis = campos.resultado.gols, campos.resultado.gols_ht, campos.resultado.penaltis
    return Partida(
        competicao=contexto.competicao,
        temporada=contexto.temporada,
        rodada=contexto.estado.rodada,
        rodada_num=contexto.estado.rodada_num,
        data=contexto.data,
        hora=contexto.estado.hora,
        mandante=campos.mandante,
        visitante=campos.visitante,
        gols_mandante=gols.mandante if gols else None,
        gols_visitante=gols.visitante if gols else None,
        gols_mandante_ht=gols_ht.mandante if gols_ht else None,
        gols_visitante_ht=gols_ht.visitante if gols_ht else None,
        penaltis=penaltis.como_texto() if penaltis else None,
        status=campos.resultado.status,
        arquivo=linha.arquivo,
        linha=linha.numero,
    )
