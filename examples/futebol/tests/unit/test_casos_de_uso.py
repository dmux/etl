from dataclasses import replace

import pytest

from etl_futebol.application.casos_de_uso import CalcularGold, ColisaoDeParticaoError, IngerirBronze, RefinarSilver
from etl_futebol.infrastructure.memoria import (
    FonteMemoria,
    RepositorioClassificacaoMemoria,
    RepositorioPartidasMemoria,
    RepositorioRejeitadosMemoria,
)

SERIE_A = "brazil/2025_br1.txt"
SERIE_B = "brazil/2025_br2.txt"


def _arquivo(cabecalho: str, declarado: int, linhas: str) -> bytes:
    return f"= {cabecalho}\n\n# Matches    {declarado}\n\n▪ Matchday 1\n  Sat Mar 29 2025\n{linhas}".encode()


DUAS_PARTIDAS = """    18:30  São Paulo FC            v SC Recife                0-0
           Cruzeiro EC             v Mirassol FC              2-1 (2-1)
"""
UMA_LINHA_RUIM = """    18:30  São Paulo FC            v SC Recife                0-0
           Cruzeiro EC             v Mirassol FC              2 a 1
"""

SERIE_A_OK = _arquivo("Brasileiro Série A 2025", 2, DUAS_PARTIDAS)
SERIE_B_OK = _arquivo("Brasileiro Série B 2025", 2, DUAS_PARTIDAS)
SERIE_B_CONTAGEM_ERRADA = _arquivo("Brasileiro Série B 2025", 3, DUAS_PARTIDAS)


class _Pipeline:
    def __init__(self, arquivos: dict[str, bytes]) -> None:
        self.fonte = FonteMemoria(arquivos)
        self.partidas = RepositorioPartidasMemoria()
        self.rejeitados = RepositorioRejeitadosMemoria()
        self.caso = IngerirBronze(self.fonte, self.partidas, self.rejeitados)


def test_arquivo_bom_e_gravado_em_bronze() -> None:
    """REQ-001: as partidas de um arquivo aprovado chegam a bronze."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK})
    pipeline.caso.executar()
    assert len(pipeline.partidas.ler("bronze")) == 2


def test_contagem_divergente_nao_grava_aquele_arquivo() -> None:
    """REQ-005: arquivo com contagem divergente não grava nenhuma partida."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK, SERIE_B: SERIE_B_CONTAGEM_ERRADA})
    pipeline.caso.executar()
    assert {partida.arquivo for partida in pipeline.partidas.ler("bronze")} == {SERIE_A}


def test_contagem_divergente_falha_a_execucao() -> None:
    """REQ-009: com um arquivo reprovado, a execução termina com erro."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK, SERIE_B: SERIE_B_CONTAGEM_ERRADA})
    assert pipeline.caso.executar().codigo_saida == 1


def test_relatorio_tem_uma_entrada_por_arquivo() -> None:
    """REQ-009: o relatório traz cada arquivo com declarado, gravadas e rejeitadas."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK, SERIE_B: SERIE_B_CONTAGEM_ERRADA})
    entradas = pipeline.caso.executar().entradas
    assert [(e.origem, e.situacao, e.declarado, e.gravadas) for e in entradas] == [
        (SERIE_A, "ok", 2, 2),
        (SERIE_B, "falhou", 3, 0),
    ]


def test_arquivo_que_nao_e_utf8_vira_um_rejeitado_sem_linha() -> None:
    """REQ-004: arquivo ilegível como UTF-8 é rejeitado inteiro, com o motivo."""
    pipeline = _Pipeline({SERIE_A: b"= Brasileiro S\xe9rie A 2025\n"})
    pipeline.caso.executar()
    rejeitado = pipeline.rejeitados.ler("bronze")[0]
    assert (rejeitado.linha, rejeitado.motivo.startswith("arquivo não é UTF-8")) == (None, True)


def test_arquivo_que_nao_e_utf8_nao_impede_os_demais() -> None:
    """REQ-004: depois de um arquivo ilegível, o próximo é processado."""
    pipeline = _Pipeline({SERIE_A: b"\xff\xfe", SERIE_B: SERIE_B_OK})
    pipeline.caso.executar()
    assert {partida.arquivo for partida in pipeline.partidas.ler("bronze")} == {SERIE_B}


def test_arquivo_alheio_ao_escopo_e_ignorado_e_reportado() -> None:
    """REQ-010: arquivo fora da lista não é carregado e aparece como `nao_carregado`."""
    pipeline = _Pipeline({"argentina/2024_ar1.txt": SERIE_A_OK})
    relatorio = pipeline.caso.executar()
    assert (pipeline.partidas.ler("bronze"), relatorio.entradas[0].situacao) == ([], "nao_carregado")


def test_arquivo_sem_cabecalho_falha() -> None:
    """REQ-001: sem cabeçalho não há competição nem temporada; o arquivo falha."""
    pipeline = _Pipeline({SERIE_A: b"# Matches    0\n"})
    assert pipeline.caso.executar().entradas[0].motivo == "cabeçalho ausente"


def test_rejeitados_de_arquivo_aprovado_sao_gravados() -> None:
    """REQ-004: a linha rejeitada de um arquivo cuja contagem confere fica visível em bronze."""
    pipeline = _Pipeline({SERIE_A: _arquivo("Brasileiro Série A 2025", 2, UMA_LINHA_RUIM)})
    pipeline.caso.executar()
    assert [rejeitado.linha for rejeitado in pipeline.rejeitados.ler("bronze")] == [8]


def test_executar_duas_vezes_nao_duplica() -> None:
    """REQ-006: reprocessar os mesmos arquivos termina com o mesmo número de partidas."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK, SERIE_B: SERIE_B_OK})
    pipeline.caso.executar()
    pipeline.caso.executar()
    assert len(pipeline.partidas.ler("bronze")) == 4


def test_arquivo_que_passa_a_falhar_mantem_a_versao_anterior() -> None:
    """REQ-005: um arquivo reprovado não apaga o que já estava gravado dele (ADR-006)."""
    pipeline = _Pipeline({SERIE_B: SERIE_B_OK})
    pipeline.caso.executar()
    pipeline.fonte.arquivos[SERIE_B] = SERIE_B_CONTAGEM_ERRADA
    pipeline.caso.executar()
    assert len(pipeline.partidas.ler("bronze")) == 2


def test_dois_arquivos_na_mesma_particao_falham_antes_de_gravar() -> None:
    """REQ-006: se dois arquivos apontam para a mesma partição, nada é gravado."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK, "brazil/2026_br1.txt": SERIE_A_OK})
    with pytest.raises(ColisaoDeParticaoError, match="2026_br1"):
        pipeline.caso.executar()
    assert pipeline.partidas.ler("bronze") == []


def _bronze_com_uma_partida_invalida() -> _Pipeline:
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK})
    pipeline.caso.executar()
    valida, outra = pipeline.partidas.ler("bronze")
    invalida = replace(outra, visitante=outra.mandante)
    pipeline.partidas.substituir_tudo("bronze", [valida, invalida])
    return pipeline


def test_silver_recebe_so_as_partidas_validas() -> None:
    """REQ-007: partida que viola invariante não chega a silver."""
    pipeline = _bronze_com_uma_partida_invalida()
    RefinarSilver(pipeline.partidas, pipeline.rejeitados).executar()
    assert len(pipeline.partidas.ler("silver")) == 1


def test_partida_invalida_vai_para_os_rejeitados_de_silver() -> None:
    """REQ-007: a partida barrada fica visível em `silver.rejeitados`, com o motivo."""
    pipeline = _bronze_com_uma_partida_invalida()
    RefinarSilver(pipeline.partidas, pipeline.rejeitados).executar()
    assert [r.motivo for r in pipeline.rejeitados.ler("silver")] == ["mandante igual ao visitante"]


def test_silver_executada_duas_vezes_da_o_mesmo_resultado() -> None:
    """REQ-006: silver é reescrita inteira; rodar de novo não duplica."""
    pipeline = _bronze_com_uma_partida_invalida()
    caso = RefinarSilver(pipeline.partidas, pipeline.rejeitados)
    caso.executar()
    caso.executar()
    assert (len(pipeline.partidas.ler("silver")), len(pipeline.rejeitados.ler("silver"))) == (1, 1)


def test_relatorio_de_silver_conta_gravadas_e_rejeitadas() -> None:
    """REQ-009: silver presta contas do que gravou e do que barrou."""
    pipeline = _bronze_com_uma_partida_invalida()
    entrada = RefinarSilver(pipeline.partidas, pipeline.rejeitados).executar().entradas[0]
    assert (entrada.origem, entrada.declarado, entrada.gravadas, entrada.rejeitadas) == (
        "futebol.silver.partidas",
        2,
        1,
        1,
    )


def test_gold_calcula_a_classificacao_a_partir_de_silver() -> None:
    """REQ-008: gold deriva de silver, nunca de bronze."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK})
    pipeline.caso.executar()
    RefinarSilver(pipeline.partidas, pipeline.rejeitados).executar()
    classificacao = RepositorioClassificacaoMemoria()
    CalcularGold(pipeline.partidas, classificacao).executar()
    assert len(classificacao.linhas) == 4


def test_gold_vazia_quando_silver_vazia() -> None:
    """REQ-008: sem silver, a classificação fica vazia, mesmo com bronze preenchida."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK})
    pipeline.caso.executar()
    classificacao = RepositorioClassificacaoMemoria()
    CalcularGold(pipeline.partidas, classificacao).executar()
    assert classificacao.linhas == []


def test_gold_executada_duas_vezes_nao_acumula() -> None:
    """REQ-006: a classificação é reescrita inteira."""
    pipeline = _Pipeline({SERIE_A: SERIE_A_OK})
    pipeline.caso.executar()
    RefinarSilver(pipeline.partidas, pipeline.rejeitados).executar()
    classificacao = RepositorioClassificacaoMemoria()
    caso = CalcularGold(pipeline.partidas, classificacao)
    caso.executar()
    relatorio = caso.executar()
    assert (len(classificacao.linhas), relatorio.entradas[0].gravadas) == (4, 4)
