#!/usr/bin/env python3
"""Guardas de pre-commit específicos para jobs AWS Glue (PySpark + Iceberg) sobre o ministack.

Cada guarda codifica uma regra das steering rules que, se violada, só falharia em runtime —
normalmente dentro de um container, com stack trace inútil. Aqui falha no commit.

Uso:
    python tools/precommit/guardas_spark.py --guarda <nome> <arquivo>...

Guardas disponíveis: ver GUARDAS no fim do arquivo.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

# Camadas que a regra de dependência protege (ver .claude/steering/estrutura.md).
CAMADAS_PURAS = ("domain", "application")
FRAMEWORKS_PROIBIDOS = ("pyspark", "awsglue", "boto3", "pyiceberg")

# Construções que o Athena do ministack não entende: ele roda em DuckDB, não em Trino.
# Vale para arquivos .sql de consulta; o Spark SQL dentro do job Glue é Spark de verdade.
SQL_INCOMPATIVEL = {
    r"\bMERGE\s+INTO\b": "MERGE INTO não existe no Athena do ministack (DuckDB)",
    r"\bLATERAL\s+VIEW\b": "LATERAL VIEW não existe no DuckDB — use unnest()",
    r"\bOPTIMIZE\b": "OPTIMIZE não existe no Athena do ministack (DuckDB)",
    r"\bVACUUM\b": "VACUUM não existe no Athena do ministack (DuckDB)",
    r"\bDESCRIBE\s+HISTORY\b": "DESCRIBE HISTORY não existe no Athena do ministack (DuckDB)",
    r"\bVERSION\s+AS\s+OF\b": "time travel não existe no Athena do ministack (DuckDB)",
    r"\bexplode\s*\(": "explode() não existe no DuckDB — use unnest()",
    r"\bdate_format\s*\(": "date_format() não existe no DuckDB — use strftime()",
    r"\bfrom_unixtime\s*\(": "from_unixtime() não existe no DuckDB — use to_timestamp()",
    r"\bcollect_list\s*\(": "collect_list() não existe no DuckDB — use list()",
    r"\barray_contains\s*\(": "array_contains() não existe no DuckDB — use list_contains()",
}

METODOS_DRIVER = ("collect", "toPandas", "count")

# O glossário é do projeto, não do framework: os sinônimos vêm de .claude/glossario.toml.
CONFIG_GLOSSARIO = Path(".claude/glossario.toml")


def carregar_sinonimos(config: Path = CONFIG_GLOSSARIO) -> dict[str, str]:
    """Lê o mapa termo-proibido -> termo-canônico de .claude/glossario.toml.

    Ausência do arquivo, ou seção vazia, desliga o guarda — um projeto novo começa sem
    glossário e não deve ser barrado por isso.
    """
    if not config.is_file():
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
        return {}
    try:
        dados = tomllib.loads(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as erro:
        # Falhar alto: um glossário quebrado desligaria o guarda em silêncio, que é
        # exatamente o modo de falha que este guarda existe para evitar.
        raise SystemExit(f"{config}: glossário ilegível — {erro}") from erro
    secao = dados.get("sinonimos", {})
    return {str(k).lower(): str(v) for k, v in secao.items() if isinstance(v, str)}


class Achado:
    """Uma violação encontrada, com localização e explicação."""

    def __init__(self, arquivo: Path, linha: int, regra: str, detalhe: str) -> None:
        self.arquivo = arquivo
        self.linha = linha
        self.regra = regra
        self.detalhe = detalhe

    def __str__(self) -> str:
        return f"{self.arquivo}:{self.linha}: [{self.regra}] {self.detalhe}"


def _e_camada_pura(arquivo: Path) -> bool:
    """O arquivo está em domain/ ou application/, onde framework é proibido?"""
    return any(parte in CAMADAS_PURAS for parte in arquivo.parts)


def _e_teste(arquivo: Path) -> bool:
    return "tests" in arquivo.parts or arquivo.name.startswith("test_")


def _e_producao(arquivo: Path) -> bool:
    return "src" in arquivo.parts and not _e_teste(arquivo)


def _palavras(identificador: str) -> list[str]:
    """Quebra um identificador em palavras, por `_` e por mudança de caixa.

    'score_home' -> ['score', 'home'] · 'scoreHome' -> ['score', 'home']
    """
    separado = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", identificador)
    return [parte for parte in re.split(r"[_\W]+", separado.lower()) if parte]


def _parsear(arquivo: Path) -> ast.Module | None:
    """Devolve a AST, ou None se o arquivo não parseia (o ruff reporta a sintaxe)."""
    try:
        return ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    except (SyntaxError, UnicodeDecodeError):
        return None


# --------------------------------------------------------------------------
# guardas
# --------------------------------------------------------------------------


def _modulos_importados(no: ast.AST) -> list[tuple[str, int]]:
    """Módulos importados por um nó, com a linha. Vazio se o nó não for import."""
    if isinstance(no, ast.Import):
        return [(alias.name, no.lineno) for alias in no.names]
    if isinstance(no, ast.ImportFrom) and no.module:
        return [(no.module, no.lineno)]
    return []


def guarda_imports_hexagonais(arquivos: Iterable[Path]) -> list[Achado]:
    """domain/ e application/ não importam pyspark, delta nem databricks."""
    achados: list[Achado] = []
    for arquivo in arquivos:
        if not _e_camada_pura(arquivo):
            continue
        arvore = _parsear(arquivo)
        if arvore is None:
            continue
        for no in ast.walk(arvore):
            for modulo, linha in _modulos_importados(no):
                if modulo.split(".")[0] not in FRAMEWORKS_PROIBIDOS:
                    continue
                achados.append(
                    Achado(
                        arquivo,
                        linha,
                        "hexagonal-imports",
                        f"'{modulo}' não pode ser importado em domain/ nem application/. "
                        "Essa operação pertence a um adaptador em infrastructure/.",
                    )
                )
    return achados


def guarda_sem_print(arquivos: Iterable[Path]) -> list[Achado]:
    """print() não entra em src/ — em job Spark o stdout é canal de saída."""
    achados: list[Achado] = []
    for arquivo in arquivos:
        if not _e_producao(arquivo):
            continue
        arvore = _parsear(arquivo)
        if arvore is None:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "print":
                achados.append(
                    Achado(
                        arquivo,
                        no.lineno,
                        "spark-no-print",
                        "use logging. Em job Spark o stdout é o canal de saída capturado.",
                    )
                )
    return achados


def guarda_sem_collect(arquivos: Iterable[Path]) -> list[Achado]:
    """collect/toPandas/count fora de infrastructure trazem o dado todo para o driver."""
    achados: list[Achado] = []
    for arquivo in arquivos:
        if not _e_producao(arquivo) or not _e_camada_pura(arquivo):
            continue
        arvore = _parsear(arquivo)
        if arvore is None:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) and no.func.attr in METODOS_DRIVER:
                achados.append(
                    Achado(
                        arquivo,
                        no.lineno,
                        "spark-no-driver-collect",
                        f".{no.func.attr}() materializa no driver. Só em infrastructure/ ou testes.",
                    )
                )
    return achados


def guarda_sessao_glue(arquivos: Iterable[Path]) -> list[Achado]:
    """Em job Glue a sessão vem do GlueContext; `SparkSession.builder` perde a configuração do Glue."""
    achados: list[Achado] = []
    for arquivo in arquivos:
        if not _e_producao(arquivo):
            continue
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for numero, linha in enumerate(linhas, 1):
            if "SparkSession.builder" in linha and not linha.lstrip().startswith("#"):
                achados.append(
                    Achado(
                        arquivo,
                        numero,
                        "glue-sessao",
                        "use GlueContext(SparkContext.getOrCreate()).spark_session. "
                        "Ver .claude/steering/convencoes-spark.md.",
                    )
                )
    return achados


def guarda_dialeto_sql(arquivos: Iterable[Path]) -> list[Achado]:
    """Construções que o Athena do ministack (DuckDB) não entende, em arquivos .sql."""
    achados: list[Achado] = []
    for arquivo in arquivos:
        if arquivo.suffix != ".sql":
            continue
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for numero, linha in enumerate(linhas, 1):
            if linha.lstrip().startswith("#"):
                continue
            for padrao, motivo in SQL_INCOMPATIVEL.items():
                if re.search(padrao, linha, re.IGNORECASE):
                    achados.append(Achado(arquivo, numero, "athena-sql-dialect", motivo))
    return achados


def guarda_select_estrela(arquivos: Iterable[Path]) -> list[Achado]:
    """select("*") e SELECT * quebram o contrato de schema em silêncio."""
    achados: list[Achado] = []
    padroes = (re.compile(r"""\.select\(\s*['"]\*['"]"""), re.compile(r"\bSELECT\s+\*", re.IGNORECASE))
    for arquivo in arquivos:
        if not _e_producao(arquivo):
            continue
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for numero, linha in enumerate(linhas, 1):
            if linha.lstrip().startswith("#"):
                continue
            for padrao in padroes:
                if padrao.search(linha):
                    achados.append(
                        Achado(
                            arquivo,
                            numero,
                            "spark-no-select-star",
                            "declare as colunas explicitamente — '*' esconde mudança de schema.",
                        )
                    )
    return achados


def _nomes_declarados(no: ast.AST) -> list[tuple[str, int]]:
    """Identificadores introduzidos por um nó, com a linha."""
    if isinstance(no, ast.Name):
        return [(no.id, no.lineno)]
    if isinstance(no, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return [(no.name, no.lineno)]
    if isinstance(no, ast.arg):
        return [(no.arg, no.lineno)]
    return []


def guarda_glossario(arquivos: Iterable[Path], config: Path = CONFIG_GLOSSARIO) -> list[Achado]:
    """Sinônimos divergentes do glossário do projeto em nomes de identificador."""
    sinonimos = carregar_sinonimos(config)
    if not sinonimos:
        return []
    achados: list[Achado] = []
    for arquivo in arquivos:
        if not (_e_producao(arquivo) or _e_teste(arquivo)):
            continue
        arvore = _parsear(arquivo)
        if arvore is None:
            continue
        achados.extend(_sinonimos_no_arquivo(arquivo, arvore, sinonimos, config))
    return achados


def _sinonimos_no_arquivo(arquivo: Path, arvore: ast.Module, sinonimos: dict[str, str], config: Path) -> list[Achado]:
    """Identificadores do arquivo que usam um termo proibido pelo glossário."""
    achados: list[Achado] = []
    for no in ast.walk(arvore):
        for nome, linha in _nomes_declarados(no):
            for termo in _palavras(nome):
                if termo not in sinonimos:
                    continue
                achados.append(
                    Achado(
                        arquivo,
                        linha,
                        "glossario",
                        f"'{termo}' em '{nome}' — o glossário do projeto manda usar "
                        f"'{sinonimos[termo]}'. Ver {config}.",
                    )
                )
    return achados


def guarda_excecao_engolida(arquivos: Iterable[Path]) -> list[Achado]:
    """except: pass esconde falha de pipeline."""
    achados: list[Achado] = []
    for arquivo in arquivos:
        if not _e_producao(arquivo):
            continue
        arvore = _parsear(arquivo)
        if arvore is None:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.ExceptHandler) and all(isinstance(corpo, ast.Pass) for corpo in no.body):
                achados.append(
                    Achado(
                        arquivo,
                        no.lineno,
                        "sem-excecao-engolida",
                        "ou trate o erro, ou propague com contexto. Silenciar esconde perda de dado.",
                    )
                )
    return achados


GUARDAS = {
    "hexagonal-imports": guarda_imports_hexagonais,
    "spark-no-print": guarda_sem_print,
    "spark-no-driver-collect": guarda_sem_collect,
    "glue-sessao": guarda_sessao_glue,
    "athena-sql-dialect": guarda_dialeto_sql,
    "spark-no-select-star": guarda_select_estrela,
    "glossario": guarda_glossario,
    "sem-excecao-engolida": guarda_excecao_engolida,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guarda", required=True, choices=sorted(GUARDAS))
    parser.add_argument(
        "--glossario",
        type=Path,
        default=CONFIG_GLOSSARIO,
        help="glossário a usar na guarda `glossario`; útil quando o projeto não está na raiz do repositório",
    )
    parser.add_argument("arquivos", nargs="*", type=Path)
    args = parser.parse_args(argv)

    if args.guarda == "glossario":
        achados = guarda_glossario(args.arquivos, args.glossario)
    else:
        achados = GUARDAS[args.guarda](args.arquivos)
    for achado in achados:
        print(achado, file=sys.stderr)
    return 1 if achados else 0


if __name__ == "__main__":
    raise SystemExit(main())
