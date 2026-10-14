from dataclasses import replace
from datetime import date
from decimal import Decimal

from etl_futebol.application.portas import (
    FontePort,
    RepositorioClassificacaoPort,
    RepositorioPartidasPort,
    RepositorioRejeitadosPort,
)
from etl_futebol.domain.modelos import LinhaClassificacao, Partida, Rejeitado, Status
from etl_futebol.infrastructure.memoria import (
    FonteMemoria,
    RepositorioClassificacaoMemoria,
    RepositorioPartidasMemoria,
    RepositorioRejeitadosMemoria,
)

SERIE_A_2025 = Partida(
    "Brasileiro Série A", 2025, "Matchday 1", 1, date(2025, 3, 29), "18:30", "Cruzeiro EC", "Mirassol FC",
    2, 1, 2, 1, None, Status.REALIZADA, "brazil/2025_br1.txt", 10,
)  # fmt: skip
SERIE_B_2025 = replace(SERIE_A_2025, competicao="Brasileiro Série B", arquivo="brazil/2025_br2.txt")
REJEITADO = Rejeitado("brazil/2025_br1.txt", 12, "linha ruim", "resultado não reconhecido: '2 a 1'")
LINHA = LinhaClassificacao("Brasileiro Série A", 2025, "Cruzeiro EC", 1, 1, 0, 0, 2, 1, 1, 3, Decimal("1.0000"))


def test_fakes_satisfazem_as_portas() -> None:
    """REQ-006: os fakes cumprem o mesmo contrato dos adaptadores reais."""
    assert all(
        (
            isinstance(FonteMemoria({}), FontePort),
            isinstance(RepositorioPartidasMemoria(), RepositorioPartidasPort),
            isinstance(RepositorioRejeitadosMemoria(), RepositorioRejeitadosPort),
            isinstance(RepositorioClassificacaoMemoria(), RepositorioClassificacaoPort),
        )
    )


def test_fonte_lista_em_ordem_e_le_bytes_crus() -> None:
    """REQ-010: a fonte devolve os arquivos em ordem estável, sem decodificar."""
    fonte = FonteMemoria({"brazil/b.txt": b"\xff", "brazil/a.txt": b"="})
    assert (list(fonte.listar()), fonte.ler("brazil/b.txt")) == (["brazil/a.txt", "brazil/b.txt"], b"\xff")


def test_substituir_particao_preserva_as_outras() -> None:
    """REQ-006: reprocessar um arquivo não toca nas partições dos demais."""
    repositorio = RepositorioPartidasMemoria()
    repositorio.substituir_particoes("bronze", [SERIE_A_2025, SERIE_B_2025], [("Brasileiro Série A", 2025)])
    repositorio.substituir_particoes("bronze", [SERIE_A_2025], [("Brasileiro Série A", 2025)])
    assert repositorio.ler("bronze") == [SERIE_B_2025, SERIE_A_2025]


def test_substituir_particao_duas_vezes_nao_duplica() -> None:
    """REQ-006: gravar a mesma partição duas vezes deixa uma cópia só."""
    repositorio = RepositorioPartidasMemoria()
    for _ in range(2):
        repositorio.substituir_particoes("bronze", [SERIE_A_2025], [("Brasileiro Série A", 2025)])
    assert repositorio.ler("bronze") == [SERIE_A_2025]


def test_substituir_tudo_troca_a_camada_inteira() -> None:
    """REQ-006: silver é reescrita inteira a cada execução."""
    repositorio = RepositorioPartidasMemoria()
    repositorio.substituir_tudo("silver", [SERIE_A_2025])
    repositorio.substituir_tudo("silver", [SERIE_B_2025])
    assert repositorio.ler("silver") == [SERIE_B_2025]


def test_camadas_sao_independentes() -> None:
    """REQ-006: gravar em silver não altera bronze."""
    repositorio = RepositorioPartidasMemoria()
    repositorio.substituir_tudo("silver", [SERIE_A_2025])
    assert repositorio.ler("bronze") == []


def test_rejeitados_substituidos_por_arquivo() -> None:
    """REQ-006: os rejeitados de um arquivo reprocessado são trocados; os de outros ficam."""
    outro = replace(REJEITADO, arquivo="brazil/2025_br2.txt")
    repositorio = RepositorioRejeitadosMemoria()
    repositorio.substituir_arquivos("bronze", [REJEITADO, outro], ["brazil/2025_br1.txt", "brazil/2025_br2.txt"])
    repositorio.substituir_arquivos("bronze", [], ["brazil/2025_br1.txt"])
    assert repositorio.ler("bronze") == [outro]


def test_rejeitados_substituir_tudo() -> None:
    """REQ-006: os rejeitados de silver são reescritos inteiros."""
    repositorio = RepositorioRejeitadosMemoria()
    repositorio.substituir_tudo("silver", [REJEITADO])
    assert repositorio.substituir_tudo("silver", []) == 0


def test_classificacao_substituida_inteira() -> None:
    """REQ-006: a classificação é reescrita inteira, sem acumular execuções."""
    repositorio = RepositorioClassificacaoMemoria()
    repositorio.substituir_tudo([LINHA])
    repositorio.substituir_tudo([LINHA])
    assert repositorio.linhas == [LINHA]
