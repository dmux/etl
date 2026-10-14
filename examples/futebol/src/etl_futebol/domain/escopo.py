"""Quais arquivos da fonte esta spec carrega. Ampliar o escopo é mudar esta regra, com intenção."""

from __future__ import annotations

import re

_PRIMEIRA_TEMPORADA = 2018
_ARQUIVO_NO_ESCOPO = re.compile(r"^brazil/(\d{4})_(?:br1|br2|brcup)\.txt$")


def no_escopo(arquivo: str) -> bool:
    """Série A, Série B e Copa do Brasil, de 2018 em diante (REQ-010.1)."""
    casamento = _ARQUIVO_NO_ESCOPO.match(arquivo)
    return casamento is not None and int(casamento.group(1)) >= _PRIMEIRA_TEMPORADA
