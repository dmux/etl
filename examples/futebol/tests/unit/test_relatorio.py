from etl_futebol.application.relatorio import EntradaRelatorio, RelatorioExecucao

OK = EntradaRelatorio("brazil/2025_br1.txt", declarado=380, gravadas=380, rejeitadas=0, situacao="ok")
FALHOU = EntradaRelatorio(
    "brazil/2025_br2.txt",
    declarado=380,
    gravadas=0,
    rejeitadas=0,
    situacao="falhou",
    motivo="contagem divergente: 379 partidas + 0 rejeitados = 379, declarado 380",
)
NAO_CARREGADO = EntradaRelatorio("argentina/2024_ar1.txt", None, 0, 0, "nao_carregado", "fora do escopo")


def test_sem_falha_o_codigo_de_saida_e_zero() -> None:
    """REQ-009: execução sem falha termina com código 0."""
    assert RelatorioExecucao((OK,)).codigo_saida == 0


def test_com_uma_falha_o_codigo_de_saida_e_um() -> None:
    """REQ-009: basta um arquivo falhar para a execução terminar com erro."""
    assert RelatorioExecucao((OK, FALHOU)).codigo_saida == 1


def test_arquivo_nao_carregado_nao_conta_como_falha() -> None:
    """REQ-010: arquivo fora do escopo é reportado, mas não falha a execução."""
    assert RelatorioExecucao((OK, NAO_CARREGADO)).codigo_saida == 0


def test_texto_traz_declarado_gravadas_e_rejeitadas_por_arquivo() -> None:
    """REQ-009: o resumo mostra, por arquivo, o total declarado, o gravado e o rejeitado."""
    assert "brazil/2025_br1.txt  ok  declarado=380 gravadas=380 rejeitadas=0" in RelatorioExecucao((OK,)).como_texto()


def test_texto_traz_o_motivo_da_falha() -> None:
    """REQ-009: arquivo que falhou aparece com o motivo."""
    assert "contagem divergente" in RelatorioExecucao((FALHOU,)).como_texto()


def test_texto_traz_os_totais() -> None:
    """REQ-009: o resumo fecha com os totais da execução."""
    assert RelatorioExecucao((OK, FALHOU)).como_texto().splitlines()[-1] == (
        "total: 2 arquivos, 1 falharam, gravadas=380 rejeitadas=0"
    )


def test_juntar_relatorios_soma_as_entradas() -> None:
    """REQ-009: o relatório do Job junta o de cada camada."""
    assert RelatorioExecucao((OK,)).juntar(RelatorioExecucao((FALHOU,))) == RelatorioExecucao((OK, FALHOU))
