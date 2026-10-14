from dataclasses import fields
from datetime import date
from decimal import Decimal

from etl_futebol.domain.modelos import LinhaClassificacao, Partida, Rejeitado, Status
from etl_futebol.infrastructure import esquemas

PARTIDA = Partida(
    "Brasileiro Série A", 2025, "Matchday 1", 1, date(2025, 3, 29), None, "Cruzeiro EC", "Mirassol FC",
    2, 1, None, None, "5-3", Status.REALIZADA, "brazil/2025_br1.txt", 10,
)  # fmt: skip
LINHA = LinhaClassificacao("Brasileiro Série A", 2025, "Cruzeiro EC", 0, 0, 0, 0, 0, 0, 0, 0, None)
REJEITADO = Rejeitado("brazil/2025_br1.txt", None, "", "arquivo não é UTF-8")


def test_schema_de_partidas_tem_as_colunas_do_modelo_na_mesma_ordem() -> None:
    """REQ-006: o schema da tabela e o modelo do domínio não divergem."""
    assert esquemas.PARTIDAS.fieldNames() == [campo.name for campo in fields(Partida)]


def test_schema_de_classificacao_tem_as_colunas_do_modelo() -> None:
    """REQ-008: a tabela gold tem exatamente as colunas do glossário."""
    assert esquemas.CLASSIFICACAO.fieldNames() == [campo.name for campo in fields(LinhaClassificacao)]


def test_schema_de_rejeitados_tem_as_colunas_do_modelo() -> None:
    """REQ-004: a tabela de rejeitados guarda arquivo, linha, texto e motivo."""
    assert esquemas.REJEITADOS.fieldNames() == [campo.name for campo in fields(Rejeitado)]


def test_aproveitamento_e_decimal_de_quatro_casas() -> None:
    """REQ-008: aproveitamento com 4 casas decimais."""
    assert esquemas.CLASSIFICACAO["aproveitamento"].dataType.simpleString() == "decimal(5,4)"


def test_partida_ida_e_volta() -> None:
    """REQ-006: converter para linha e de volta devolve a mesma partida."""
    assert esquemas.partida_de_linha(esquemas.linha_de_partida(PARTIDA)) == PARTIDA


def test_status_vai_para_a_tabela_como_texto() -> None:
    """REQ-003: o status é gravado como o texto do glossário."""
    assert esquemas.linha_de_partida(PARTIDA)[13] == "realizada"


def test_classificacao_ida_e_volta_com_aproveitamento_nulo() -> None:
    """REQ-008: aproveitamento nulo continua nulo depois de gravado."""
    assert esquemas.classificacao_de_linha(esquemas.linha_de_classificacao(LINHA)) == LINHA


def test_rejeitado_ida_e_volta() -> None:
    """REQ-004: rejeitado sem linha continua sem linha depois de gravado."""
    assert esquemas.rejeitado_de_linha(esquemas.linha_de_rejeitado(REJEITADO)) == REJEITADO


def test_aproveitamento_decimal_e_preservado() -> None:
    """REQ-008: o valor decimal não perde casas na conversão."""
    linha = LinhaClassificacao("Brasileiro Série A", 2025, "Cruzeiro EC", 3, 1, 1, 1, 2, 4, -2, 4, Decimal("0.4444"))
    assert esquemas.classificacao_de_linha(esquemas.linha_de_classificacao(linha)).aproveitamento == Decimal("0.4444")
