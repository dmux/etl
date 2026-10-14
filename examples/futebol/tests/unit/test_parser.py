from datetime import date

from etl_futebol.domain.modelos import Status
from etl_futebol.domain.parser import parsear_arquivo

ARQUIVO = "brazil/2025_br1.txt"

CABECALHO = """= Brasileiro Série A 2025

# Date       Sat Mar 29 - Sun Dec 7 2025 (253d)
# Teams      20
# Matches    {total}

"""

HORARIO_HERDADO = (
    CABECALHO.format(total=4)
    + """▪ Matchday 1
  Sat Mar 29 2025
    18:30  São Paulo FC            v SC Recife                0-0
           Cruzeiro EC             v Mirassol FC              2-1 (2-1)
           Grêmio FBPA             v CA Mineiro               2-1 (2-0)
    21:30  Fortaleza EC            v Fluminense FC            2-0 (2-0)
"""
)

DATA_INCOMPLETA = (
    CABECALHO.format(total=2)
    + """▪ Matchday 1
  Sat Mar 29 2025
    18:30  São Paulo FC            v SC Recife                0-0
  Thu Apr 3
    21:30  Grêmio FBPA             v CA Mineiro               1-1 (0-1)
"""
)

DATA_EM_ORDEM_TROCADA = (
    CABECALHO.format(total=3)
    + """▪ Matchday 20
  Thu Jan 28 2021
    20:00  São Paulo FC            v SC Recife                1-0
  Wed Dec 2 2020
    21:30  Grêmio FBPA             v CA Mineiro               1-1
  Thu Dec 3
    19:00  Cruzeiro EC             v Mirassol FC              0-0
"""
)

DATA_SEM_HORARIO = (
    CABECALHO.format(total=3)
    + """▪ Matchday 36
  Fri Nov 20 2026
    21:30  São Paulo FC            v SC Recife
  Sat Nov 21
           CA Paranaense           v Clube do Remo
           CA Mineiro              v CR Vasco da Gama
"""
)

RODADAS = (
    CABECALHO.format(total=3)
    + """▪ 1° Semestre, Matchday 3
  Sat Mar 29 2025
    18:30  São Paulo FC            v SC Recife                0-0
▪ Round 2
  Sun Mar 30 2025
    16:00  Cruzeiro EC             v Mirassol FC              1-0
▪ Copa Sud, Final
  Mon Mar 31 2025
    20:00  Grêmio FBPA             v CA Mineiro               2-2
"""
)

COPA_COM_UF = """= Copa do Brasil 2025

# Matches    1

▪ Round 1
  Tue Feb 18 2025
    18:00  Tocantinópolis TO       v Atlético Mineiro         0-2 (0-0)
"""


def test_cabecalho_define_competicao_e_temporada() -> None:
    """REQ-001: competição e temporada saem do cabeçalho `=`."""
    partida = parsear_arquivo(ARQUIVO, HORARIO_HERDADO).partidas[0]
    assert (partida.competicao, partida.temporada) == ("Brasileiro Série A", 2025)


def test_temporada_vem_do_cabecalho_e_nao_da_data() -> None:
    """REQ-001: uma partida de janeiro de 2021 pertence à temporada declarada no cabeçalho."""
    partida = parsear_arquivo(ARQUIVO, DATA_EM_ORDEM_TROCADA).partidas[0]
    assert (partida.data.year, partida.temporada) == (2021, 2025)


def test_contagem_declarada_e_lida_do_cabecalho() -> None:
    """REQ-005: `# Matches N` é lido para conferência."""
    assert parsear_arquivo(ARQUIVO, HORARIO_HERDADO).declarado == 4


def test_cada_linha_de_partida_vira_uma_partida() -> None:
    """REQ-001: toda linha com ` v ` produz uma partida."""
    assert len(parsear_arquivo(ARQUIVO, HORARIO_HERDADO).partidas) == 4


def test_horario_e_herdado_por_tres_partidas_seguidas() -> None:
    """REQ-001: partida sem horário herda o da última partida com horário na mesma data."""
    horas = [partida.hora for partida in parsear_arquivo(ARQUIVO, HORARIO_HERDADO).partidas]
    assert horas == ["18:30", "18:30", "18:30", "21:30"]


def test_primeira_partida_da_data_sem_horario_fica_com_hora_nula() -> None:
    """REQ-001: o horário nunca é herdado de outra data."""
    horas = [partida.hora for partida in parsear_arquivo(ARQUIVO, DATA_SEM_HORARIO).partidas]
    assert horas == ["21:30", None, None]


def test_data_incompleta_herda_da_ultima_data_completa() -> None:
    """REQ-001: `Thu Apr 3` depois de `Sat Mar 29 2025` é 3 de abril de 2025."""
    assert parsear_arquivo(ARQUIVO, DATA_INCOMPLETA).partidas[1].data == date(2025, 4, 3)


def test_data_incompleta_segue_a_ultima_data_completa_mesmo_em_ordem_trocada() -> None:
    """REQ-001: depois de `Wed Dec 2 2020`, `Thu Dec 3` é de 2020, mesmo após uma data de 2021."""
    assert parsear_arquivo(ARQUIVO, DATA_EM_ORDEM_TROCADA).partidas[2].data == date(2020, 12, 3)


def test_rodada_composta_guarda_o_rotulo_inteiro_e_o_numero() -> None:
    """REQ-001: `1° Semestre, Matchday 3` é a rodada, e 3 é o número."""
    partida = parsear_arquivo(ARQUIVO, RODADAS).partidas[0]
    assert (partida.rodada, partida.rodada_num) == ("1° Semestre, Matchday 3", 3)


def test_rodada_com_rotulo_em_ingles_tem_numero() -> None:
    """REQ-001: `Round 2` tem número 2."""
    assert parsear_arquivo(ARQUIVO, RODADAS).partidas[1].rodada_num == 2


def test_rodada_sem_numero_fica_nula_e_nunca_zero() -> None:
    """REQ-001: fase sem numeração deixa `rodada_num` nulo."""
    assert parsear_arquivo(ARQUIVO, RODADAS).partidas[2].rodada_num is None


def test_nome_de_clube_e_preservado_com_acento_e_uf() -> None:
    """REQ-001: o nome do clube fica exatamente como no arquivo."""
    partida = parsear_arquivo("brazil/2025_brcup.txt", COPA_COM_UF).partidas[0]
    assert (partida.mandante, partida.visitante) == ("Tocantinópolis TO", "Atlético Mineiro")


def test_resultado_e_status_vem_da_linha() -> None:
    """REQ-002: placar final e do primeiro tempo são gravados nas colunas do glossário."""
    partida = parsear_arquivo(ARQUIVO, HORARIO_HERDADO).partidas[1]
    placares = (partida.gols_mandante, partida.gols_visitante, partida.gols_mandante_ht, partida.gols_visitante_ht)
    assert (placares, partida.status) == ((2, 1, 2, 1), Status.REALIZADA)


def test_partida_sem_placar_e_agendada() -> None:
    """REQ-003: linha sem placar é partida agendada."""
    assert parsear_arquivo(ARQUIVO, DATA_SEM_HORARIO).partidas[0].status == Status.AGENDADA


def test_partida_guarda_arquivo_e_numero_da_linha() -> None:
    """REQ-001: cada partida aponta para o arquivo e a linha de origem."""
    partida = parsear_arquivo(ARQUIVO, HORARIO_HERDADO).partidas[0]
    assert (partida.arquivo, partida.linha) == (ARQUIVO, 9)


def test_arquivo_vazio_nao_produz_nada() -> None:
    """REQ-001: arquivo vazio não produz partida nem rejeitado."""
    processado = parsear_arquivo(ARQUIVO, "")
    assert (processado.partidas, processado.rejeitados, processado.declarado) == ((), (), None)


LINHA_RUIM_NO_MEIO = (
    CABECALHO.format(total=3)
    + """▪ Matchday 1
  Sat Mar 29 2025
    18:30  São Paulo FC            v SC Recife                0-0
           Cruzeiro EC             v Mirassol FC              2 a 1
           Grêmio FBPA             v CA Mineiro               2-1 (2-0)
"""
)

PARTIDA_SEM_DATA = (
    CABECALHO.format(total=1)
    + """▪ Matchday 1
    18:30  São Paulo FC            v SC Recife                0-0
"""
)

PARTIDA_SEM_CABECALHO = """▪ Matchday 1
  Sat Mar 29 2025
    18:30  São Paulo FC            v SC Recife                0-0
"""

LINHA_TRUNCADA = (
    CABECALHO.format(total=2)
    + """▪ Matchday 1
  Sat Mar 29 2025
    18:30  São Paulo FC            v
           Grêmio FBPA             v CA Mineiro 2-1 (2-
"""
)

LINHA_ESTRANHA = (
    CABECALHO.format(total=0)
    + """▪ Matchday 1
  Sábado, 29 de março
"""
)

DATA_INCOMPLETA_SEM_REFERENCIA = (
    CABECALHO.format(total=1)
    + """▪ Matchday 1
  Thu Apr 3
    21:30  Grêmio FBPA             v CA Mineiro               1-1 (0-1)
"""
)

CABECALHO_MALFORMADO = """= Brasileiro Série A

  Sat Mar 29 2025
    18:30  São Paulo FC            v SC Recife                0-0
"""


def test_resultado_irreconhecivel_vira_rejeitado_com_o_texto_original() -> None:
    """REQ-004: a linha que não casa com nenhuma forma vira rejeitado com arquivo, linha e texto."""
    rejeitado = parsear_arquivo(ARQUIVO, LINHA_RUIM_NO_MEIO).rejeitados[0]
    assert (rejeitado.arquivo, rejeitado.linha, rejeitado.texto) == (
        ARQUIVO,
        10,
        "           Cruzeiro EC             v Mirassol FC              2 a 1",
    )


def test_rejeitado_diz_o_motivo() -> None:
    """REQ-004: o rejeitado explica por que não foi aceito."""
    assert parsear_arquivo(ARQUIVO, LINHA_RUIM_NO_MEIO).rejeitados[0].motivo == "resultado não reconhecido: '2 a 1'"


def test_linha_ruim_nao_interrompe_o_arquivo() -> None:
    """REQ-004: as partidas antes e depois de uma linha rejeitada são lidas."""
    linhas = [partida.linha for partida in parsear_arquivo(ARQUIVO, LINHA_RUIM_NO_MEIO).partidas]
    assert linhas == [9, 11]


def test_partida_antes_de_qualquer_data_e_rejeitada() -> None:
    """REQ-004: partida sem data vigente vira rejeitado com o motivo `partida sem data`."""
    assert parsear_arquivo(ARQUIVO, PARTIDA_SEM_DATA).rejeitados[0].motivo == "partida sem data"


def test_partida_sem_cabecalho_e_rejeitada() -> None:
    """REQ-001: sem cabeçalho não há competição nem temporada; a partida é rejeitada."""
    assert parsear_arquivo(ARQUIVO, PARTIDA_SEM_CABECALHO).rejeitados[0].motivo == "partida sem cabeçalho"


def test_linha_sem_visitante_e_rejeitada() -> None:
    """REQ-004: linha truncada logo depois do ` v ` vira rejeitado."""
    assert parsear_arquivo(ARQUIVO, LINHA_TRUNCADA).rejeitados[0].motivo == "partida sem visitante"


def test_resultado_colado_ao_nome_do_visitante_e_rejeitado() -> None:
    """REQ-004: placar sem a separação de colunas não é lido como parte do nome do clube."""
    assert parsear_arquivo(ARQUIVO, LINHA_TRUNCADA).rejeitados[1].motivo == "resultado colado ao nome do visitante"


def test_linha_nao_reconhecida_vira_rejeitado() -> None:
    """REQ-004: nenhuma linha desconhecida some em silêncio."""
    assert parsear_arquivo(ARQUIVO, LINHA_ESTRANHA).rejeitados[0].motivo == "linha não reconhecida"


def test_data_incompleta_sem_referencia_deixa_a_partida_sem_data() -> None:
    """REQ-004: sem data completa anterior não há ano a herdar; a data é rejeitada e a partida também."""
    motivos = [rejeitado.motivo for rejeitado in parsear_arquivo(ARQUIVO, DATA_INCOMPLETA_SEM_REFERENCIA).rejeitados]
    assert motivos == ["data sem ano antes de qualquer data completa", "partida sem data"]


def test_cabecalho_malformado_vira_rejeitado() -> None:
    """REQ-001: cabeçalho sem temporada é rejeitado, e as partidas ficam sem cabeçalho."""
    motivos = [rejeitado.motivo for rejeitado in parsear_arquivo(ARQUIVO, CABECALHO_MALFORMADO).rejeitados]
    assert motivos == ["cabeçalho não reconhecido", "partida sem cabeçalho"]


DATA_INVALIDA = (
    CABECALHO.format(total=1)
    + """▪ Matchday 1
  Sun Feb 30 2025
    21:30  Grêmio FBPA             v CA Mineiro               1-1
"""
)

SEM_MANDANTE = (
    CABECALHO.format(total=1)
    + """▪ Matchday 1
  Sat Mar 29 2025
    18:30  v SC Recife                0-0
"""
)


def test_data_inexistente_e_rejeitada_e_nao_e_herdada() -> None:
    """REQ-004: `Feb 30` é rejeitada, e a partida seguinte fica sem data em vez de herdar outra."""
    motivos = [rejeitado.motivo for rejeitado in parsear_arquivo(ARQUIVO, DATA_INVALIDA).rejeitados]
    assert motivos == ["data inválida: day is out of range for month", "partida sem data"]


def test_linha_sem_mandante_e_rejeitada() -> None:
    """REQ-004: linha de partida sem o nome do mandante vira rejeitado."""
    assert parsear_arquivo(ARQUIVO, SEM_MANDANTE).rejeitados[0].motivo == "partida sem mandante"
