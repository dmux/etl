# Estrutura e arquitetura

Arquitetura **hexagonal** (ports & adapters). O objetivo não é purismo: é conseguir testar a
lógica que importa sem subir uma JVM.

O nome do pacote está em `.claude/projeto.toml`, `[projeto] pacote`. Abaixo ele aparece como
`<pacote>`.

## Layout

```
.
├── .claude/
│   ├── projeto.toml         configuração de domínio — o único lugar com nomes do projeto
│   ├── glossario.toml       sinônimos verificáveis pelo pre-commit
│   ├── steering/            regras sempre carregadas (estas)
│   ├── skills/              conhecimento sob demanda
│   ├── agents/              subagentes, um por fase do SDD
│   ├── commands/sdd/        slash commands /sdd:*
│   └── hooks/               scripts dos hooks de sessão
├── specs/NNN-<feature>/     requirements.md, design.md, tasks.md, reviews/
├── src/<pacote>/
│   ├── domain/              regras, parsing, cálculo. Python puro
│   ├── application/         portas (Protocol) e casos de uso
│   ├── infrastructure/      adaptadores: Spark, Iceberg, S3, Glue Data Catalog, HTTP
│   └── cli/                 entrypoint do job
├── tests/{unit,integration,e2e}/
└── tools/precommit/         guardas de commit
```

Os diretórios de dado de origem ficam onde o projeto os colocou e estão declarados em
`[fontes] somente_leitura`. São imutáveis.

## A regra de dependência

As setas de import apontam **para dentro**, sempre:

```
cli ──► infrastructure ──► application ──► domain
                                              ▲
                          (domain não importa ninguém)
```

Concretamente, e isto é verificado pelo guarda `hexagonal-imports`:

- `domain/` **não importa** `pyspark`, `awsglue`, `boto3`, nem `application`,
  `infrastructure` ou `cli`. Só stdlib e bibliotecas de tipo/validação.
- `application/` **não importa** `pyspark`, `awsglue`, `boto3` nem `infrastructure`.
  Depende de `domain` e das suas próprias portas.
- `infrastructure/` pode importar tudo. É a única camada que conhece framework.

Se você precisou importar `pyspark` no domínio, o desenho está errado — a operação que você
está tentando fazer pertence a um adaptador.

## Portas

Uma porta é um `Protocol` em `application/portas.py`, declarado com `@runtime_checkable`,
tipado **em termos do domínio** — nunca em termos de `DataFrame`:

```python
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from <pacote>.domain.modelos import Registro


@runtime_checkable
class EscritorTabelaPort(Protocol):
    """Persiste registros num destino. Não sabe se é Iceberg, parquet ou memória."""

    def escrever(self, registros: Sequence[Registro], destino: str) -> int:
        """Retorna quantos registros foram gravados."""
        ...
```

Toda porta tem no mínimo dois adaptadores: o real (`infrastructure/*_spark.py`) e um fake em
memória usado nos testes. Se só existe um adaptador, a porta provavelmente não deveria existir
— era uma função.

## Nomes

- Idioma dos identificadores: `.claude/projeto.toml`, `[idioma] codigo`. Siga o idioma do
  schema de dados que já existe; traduzir cria um dicionário a mais para manter errado.
- Pastas de arquitetura sempre em **inglês** (`domain`, `application`, `infrastructure`, `cli`)
  — são termos do padrão, não do domínio.
- Módulos, funções e variáveis em `snake_case`. Classes em `PascalCase`.
- Portas terminam em `Port`. Adaptadores dizem o que são: `EscritorIcebergSpark`,
  `LeitorArquivosFs`, `EscritorMemoria`.
- Nomes de entidade e coluna vêm do `glossario-dados.md`. Não invente sinônimo — o guarda
  `glossario` barra no commit.

## Testes espelham o código

Cada módulo de `src/` tem um `tests/unit/test_<módulo>.py` correspondente. A localização do
teste é derivável do nome do arquivo testado — sem exceção e sem criatividade.
