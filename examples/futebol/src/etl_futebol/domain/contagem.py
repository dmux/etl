"""Conferência da contagem declarada: a asserção mais barata e a que mais pega linha perdida."""

from __future__ import annotations

from etl_futebol.domain.modelos import ArquivoProcessado


def conferir_contagem(processado: ArquivoProcessado) -> str | None:
    """Motivo da falha, ou `None` se partidas + rejeitados batem com `# Matches N`."""
    if processado.declarado is None:
        return "contagem não declarada"
    partidas, rejeitados = len(processado.partidas), len(processado.rejeitados)
    if partidas + rejeitados == processado.declarado:
        return None
    return (
        f"contagem divergente: {partidas} partidas + {rejeitados} rejeitados = {partidas + rejeitados}, "
        f"declarado {processado.declarado}"
    )
