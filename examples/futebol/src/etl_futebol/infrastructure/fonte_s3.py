"""Fonte no S3, lida pelo Spark do job Glue (ADR-009). São 540 KB: uma leitura serve a execução."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class FonteS3Spark:
    """Os `.txt` sob uma raiz `s3a://`, lidos uma vez com o leitor `binaryFile`."""

    def __init__(self, spark: Any, raiz: str) -> None:
        self._spark = spark
        self._raiz = raiz.rstrip("/")
        self._arquivos: dict[str, bytes] | None = None

    def listar(self) -> Sequence[str]:
        return sorted(self._carregar())

    def ler(self, arquivo: str) -> bytes:
        return self._carregar()[arquivo]

    def _carregar(self) -> dict[str, bytes]:
        if self._arquivos is None:
            leitor = (
                self._spark.read.format("binaryFile")
                .option("pathGlobFilter", "*.txt")
                .option("recursiveFileLookup", "true")
            )
            linhas = leitor.load(self._raiz).select("path", "content").collect()
            self._arquivos = {self._relativo(caminho): bytes(conteudo) for caminho, conteudo in linhas}
        return self._arquivos

    def _relativo(self, caminho: str) -> str:
        prefixo = self._raiz + "/"
        if not caminho.startswith(prefixo):
            raise ValueError(f"{caminho} está fora da raiz da fonte {self._raiz}")
        return caminho[len(prefixo) :]
