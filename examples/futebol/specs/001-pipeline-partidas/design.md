# Design — pipeline de partidas

## Visão geral

Um job **AWS Glue 4.0** no ministack que executa as três camadas do medalhão em sequência
(ADR-009). O Spark só lê e grava tabelas **Iceberg**, registradas no Glue Data Catalog; toda
interpretação e todo cálculo acontecem em funções puras de `domain/`, chamadas por casos de uso de
`application/` que conhecem apenas portas.

*Revisado em 2026-10-13 pela ADR-009: a primeira versão deste design mirava Delta no minilake.
Domínio, portas e casos de uso não mudaram com a troca de plataforma — só os adaptadores, o
entrypoint e a forma de publicar.*

- **bronze:** lê os `.txt` da fonte, o parser transforma cada arquivo em partidas e registros
  rejeitados, a contagem é conferida contra `# Matches N`, e cada arquivo aprovado substitui a
  sua partição.
- **silver:** lê as partidas de bronze, rejeita as que violam invariante, remove duplicata e
  reescreve a tabela.
- **gold:** lê as partidas de silver e calcula a classificação da Série A e da Série B.

O volume atual cabe com folga na memória do driver: 6.552 partidas, 1,6 MB de texto. Isso
sustenta a ADR-003, que mantém o cálculo em Python puro.

## Fluxo de dados

```
south-america/brazil/*.txt  (clone fixo, somente leitura)
        │  make publicar: aws s3 sync → s3://futebol-lake/fonte/
        ▼
FonteS3Spark ──► IngerirBronze ──► parser.parsear_arquivo ──► contagem.conferir
                      │
                      ├──► RepositorioPartidasIceberg  → iceberg.futebol_bronze.partidas   (overwritePartitions)
                      └──► RepositorioRejeitadosIceberg → iceberg.futebol_bronze.rejeitados (overwrite por arquivo)
                                      │
RepositorioPartidasIceberg (bronze) ──► RefinarSilver ──► invariantes.validar + invariantes.deduplicar
                      ├──► iceberg.futebol_silver.partidas    (overwrite total)
                      └──► iceberg.futebol_silver.rejeitados  (overwrite total)
                                      │
RepositorioPartidasIceberg (silver) ──► CalcularGold ──► classificacao.calcular
                      └──► iceberg.futebol_gold.classificacao (overwrite total)

cada escrita ──► RegistroCatalogoGlue ──► Glue Data Catalog (table_type=ICEBERG, metadata_location)
```

## Layout do exemplo

```
examples/futebol/
├── pyproject.toml          pacote etl_futebol (ADR-001, ADR-004)
├── Makefile                fonte, install, check, publicar, executar, verificar, e2e
├── glue_job.py             script do job Glue (ScriptLocation); chama etl_futebol.cli.glue
├── scripts/glue.sh         publicar, executar e verificar no ministack com o AWS CLI (ADR-009)
├── south-america/          clone fixo da fonte, fora do git (ADR-002)
├── specs/001-pipeline-partidas/
├── src/etl_futebol/
│   ├── domain/             modelos, resultado, parser, contagem, invariantes, classificacao, escopo
│   ├── application/        portas, casos_de_uso, relatorio
│   ├── infrastructure/     fonte_fs, fonte_s3, iceberg, catalogo_glue, sessao_glue, esquemas, memoria
│   └── cli/                glue (wiring do job)
└── tests/{unit,e2e}/
```

## Modelos de domínio

Todos `@dataclass(frozen=True, slots=True)` em `domain/modelos.py`. Nomes de campo vêm do
glossário.

| Modelo | Campos | Invariantes |
| --- | --- | --- |
| `Status` | `StrEnum`-equivalente (ver ADR-004): `realizada`, `agendada`, `atribuida`, `adiada`, `cancelada`, `abandonada` | — |
| `Placar` | `mandante: int`, `visitante: int` | ambos ≥ 0 |
| `Resultado` | `gols: Placar \| None`, `gols_ht: Placar \| None`, `penaltis: Placar \| None`, `status: Status` | `gols` preenchido ⟺ `status` ∈ (`realizada`, `atribuida`) |
| `Partida` | `competicao`, `temporada`, `rodada`, `rodada_num`, `data`, `hora`, `mandante`, `visitante`, `gols_mandante`, `gols_visitante`, `gols_mandante_ht`, `gols_visitante_ht`, `penaltis`, `status`, `arquivo`, `linha` | os do glossário; validados em silver, não na construção |
| `Rejeitado` | `arquivo: str`, `linha: int \| None`, `texto: str`, `motivo: str` | `linha` nula só quando o arquivo inteiro foi rejeitado |
| `ArquivoProcessado` | `arquivo`, `competicao`, `temporada`, `declarado: int \| None`, `partidas: tuple[Partida, ...]`, `rejeitados: tuple[Rejeitado, ...]` | — |
| `LinhaClassificacao` | `competicao`, `temporada`, `clube`, `jogos`, `vitorias`, `empates`, `derrotas`, `gols_pro`, `gols_contra`, `saldo_gols`, `pontos`, `aproveitamento: Decimal \| None` | `aproveitamento` nulo ⟺ `jogos = 0` |

`Partida` não valida invariantes no construtor de propósito: bronze precisa conseguir guardar a
partida como o arquivo diz (REQ-007, nota), e a validação é responsabilidade de silver.

## Módulos de domínio

| Módulo | Função pública | Atende |
| --- | --- | --- |
| `resultado.py` | `interpretar_resultado(texto) -> Resultado \| None`, testando as formas na ordem da skill do formato | REQ-002, REQ-003 |
| `parser.py` | `parsear_arquivo(arquivo, texto) -> ArquivoProcessado`, carregando hora, data e rodada vigentes num estado de leitura imutável | REQ-001, REQ-004.1–3 |
| `contagem.py` | `conferir_contagem(processado) -> str \| None`, que devolve o motivo da falha ou nada | REQ-005 |
| `invariantes.py` | `validar(partidas) -> tuple[list[Partida], list[Rejeitado]]` e `deduplicar(partidas)` | REQ-007 |
| `classificacao.py` | `calcular_classificacao(partidas) -> list[LinhaClassificacao]` | REQ-008 |
| `escopo.py` | `no_escopo(arquivo) -> bool`, pelo padrão `brazil/AAAA_br1.txt`, `_br2.txt`, `_brcup.txt`, a partir de 2018 | REQ-010.1–2 |

O guarda `glossario` barra `ano` como sinônimo de `temporada`. Por isso a herança do ano da data
(REQ-001.5) é guardada como `ultima_data_completa: date`, e o ano sai de `.year`. O guarda molda
o nome antes mesmo do primeiro commit.

## Portas

Em `application/portas.py`, todas `@runtime_checkable`, tipadas só com modelos do domínio.

| Porta | Métodos | Contrato | Adaptadores |
| --- | --- | --- | --- |
| `FontePort` | `listar() -> Sequence[str]` · `ler(arquivo) -> bytes` | caminhos relativos à raiz da fonte; `ler` devolve bytes crus, e a decodificação é do caso de uso (REQ-004.4) | `FonteS3Spark`, `FonteArquivosFs`, `FonteMemoria` |
| `RepositorioPartidasPort` | `substituir_particoes(camada, partidas, particoes) -> int` · `substituir_tudo(camada, partidas) -> int` · `ler(camada) -> list[Partida]` | `particoes` é uma sequência de `(competicao, temporada)`; o que estava nelas some, o resto fica intacto | `RepositorioPartidasIceberg`, `RepositorioPartidasMemoria` |
| `RepositorioRejeitadosPort` | `substituir_arquivos(camada, rejeitados, arquivos) -> int` · `substituir_tudo(camada, rejeitados) -> int` | mesma semântica, chave `arquivo` | `RepositorioRejeitadosIceberg`, `RepositorioRejeitadosMemoria` |
| `RepositorioClassificacaoPort` | `substituir_tudo(linhas) -> int` | — | `RepositorioClassificacaoIceberg`, `RepositorioClassificacaoMemoria` |

`camada` é um `Literal["bronze", "silver"]` do domínio, não um caminho.

## Casos de uso

Em `application/casos_de_uso.py`. Cada um recebe as portas no construtor e devolve um
`RelatorioExecucao` (`application/relatorio.py`).

| Caso de uso | Faz | Atende |
| --- | --- | --- |
| `IngerirBronze` | para cada arquivo no escopo: decodifica, parseia, confere a contagem; grava os aprovados numa única chamada por porta; os reprovados não gravam nada | REQ-001–006, REQ-009, REQ-010 |
| `RefinarSilver` | lê bronze, valida, deduplica, reescreve silver e `silver.rejeitados` | REQ-006, REQ-007 |
| `CalcularGold` | lê silver, calcula, reescreve a classificação | REQ-006, REQ-008 |

`RelatorioExecucao` traz, por arquivo: `declarado`, `gravadas`, `rejeitadas`, `situacao`
(`ok`, `falhou`, `fora_de_escopo`) e `motivo`. Expõe `codigo_saida` como 0 ou 1 (REQ-009.2).
Atenção: `fora` é termo proibido pelo glossário (sinônimo de `visitante`), então a situação se
chama `nao_carregado` no código.

## Adaptadores

### `FonteS3Spark` e `FonteArquivosFs`
**Implementam** `FontePort`. `FonteS3Spark` lê os `.txt` sob `s3a://futebol-lake/fonte` com o
leitor `binaryFile` do Spark, uma vez, e serve listagem e bytes a partir dessa leitura (540 KB).
`FonteArquivosFs` lê de um diretório local; serve para rodar o domínio contra o clone sem Spark.
**Pode falhar:** raiz inexistente (erro fatal com o caminho).

### `RepositorioPartidasIceberg`, `RepositorioRejeitadosIceberg`, `RepositorioClassificacaoIceberg`
**Implementam** as portas de repositório, em `infrastructure/iceberg.py`. **Responsabilidade:**
criar a tabela se faltar (DDL explícito, `PARTITIONED BY`), converter modelos em linhas com
`StructType` declarado, gravar com a operação idempotente da ADR-009 e ler de volta.
**Dependências:** `SparkSession` e `RegistroCatalogoGlue` injetados. **Pode falhar:** erro de
escrita (propaga; o job falha). Ler com `.collect()` é permitido aqui, e só aqui (ADR-003).

### `RegistroCatalogoGlue` (`infrastructure/catalogo_glue.py`)
Depois de cada escrita, registra a tabela no Glue Data Catalog como o `GlueCatalog` do Iceberg
faria: `table_type=ICEBERG` e `metadata_location` do `version-hint.text` (ADR-009). Clientes S3 e
Glue do `boto3` injetados. **Pode falhar:** `version-hint.text` ausente (erro com o caminho).

### `criar_sessao_glue` (`infrastructure/sessao_glue.py`)
Devolve a `spark_session` do `GlueContext`. É função, não porta: só existe uma forma de obter a
sessão num job Glue.

### `scripts/glue.sh`
Lado do host, com o AWS CLI apontado para o ministack: publica fonte, código e script; cria ou
atualiza o job; executa e espera; decide o resultado pela linha-marcador do log (ADR-009).
`garantir` publica só quando muda a impressão digital (código, script, definição do job e commit
da fonte), guardada no próprio S3 do ministack: um ministack recriado sem estado também força a
publicação. `executar` grava o log filtrado em `dist/ultima-execucao.log` e imprime só o resumo
em markdown, que os comandos `/glue:executar` e `/glue:verificar` mostram.

## Schema das tabelas

Catálogo Iceberg `iceberg`, warehouse `s3a://futebol-lake/warehouse`, bancos `futebol_<camada>`, de `projeto.toml`.

### `futebol_bronze.partidas` e `futebol_silver.partidas`

| Coluna | Tipo | Nulo? | Origem |
| --- | --- | --- | --- |
| `competicao` | STRING | não | cabeçalho `=` |
| `temporada` | INT | não | cabeçalho `=` |
| `rodada` | STRING | não | rótulo `▪` vigente |
| `rodada_num` | INT | sim | número do rótulo |
| `data` | DATE | não | linha de data vigente |
| `hora` | STRING | sim | linha de partida, ou herdada na mesma data |
| `mandante` | STRING | não | antes de ` v ` |
| `visitante` | STRING | não | depois de ` v ` |
| `gols_mandante` | INT | sim | resultado |
| `gols_visitante` | INT | sim | resultado |
| `gols_mandante_ht` | INT | sim | resultado |
| `gols_visitante_ht` | INT | sim | resultado |
| `penaltis` | STRING | sim | resultado, formato `M-V` |
| `status` | STRING | não | marcador ou presença de placar |
| `arquivo` | STRING | não | caminho relativo à raiz da fonte |
| `linha` | INT | não | número da linha no arquivo, a partir de 1 |

**Tabela** `iceberg.futebol_{bronze,silver}.partidas` · **Particionamento** `temporada`,
`competicao` · **Chave de idempotência** a partição `(competicao, temporada)`: cada arquivo do
escopo corresponde a exatamente uma, e o caso de uso falha a execução se dois arquivos
apontarem para a mesma.

### `futebol_bronze.rejeitados` e `futebol_silver.rejeitados`

| Coluna | Tipo | Nulo? |
| --- | --- | --- |
| `arquivo` | STRING | não |
| `linha` | INT | sim |
| `texto` | STRING | não |
| `motivo` | STRING | não |

**Tabela** `iceberg.futebol_{bronze,silver}.rejeitados` · **Particionamento** nenhum
(dezenas de linhas) · **Chave de idempotência** `arquivo` em bronze; tabela inteira em silver.

### `futebol_gold.classificacao`

| Coluna | Tipo | Nulo? |
| --- | --- | --- |
| `competicao` | STRING | não |
| `temporada` | INT | não |
| `clube` | STRING | não |
| `jogos` | INT | não |
| `vitorias` | INT | não |
| `empates` | INT | não |
| `derrotas` | INT | não |
| `gols_pro` | INT | não |
| `gols_contra` | INT | não |
| `saldo_gols` | INT | não |
| `pontos` | INT | não |
| `aproveitamento` | DECIMAL(5,4) | sim |

**Tabela** `iceberg.futebol_gold.classificacao` · **Particionamento** `temporada`,
`competicao` · **Chave de idempotência** tabela inteira, sobrescrita a cada execução.

## Tratamento de erro

| Situação | Comportamento | Atende |
| --- | --- | --- |
| linha de partida que não casa com nenhuma forma | `Rejeitado` com arquivo, linha, texto e motivo; o parser segue | REQ-004.1–2 |
| partida antes de qualquer data | `Rejeitado`, motivo `partida sem data` | REQ-004.3 |
| arquivo que não decodifica como UTF-8 | um `Rejeitado` com `linha` nula; arquivo marcado `falhou`; segue para o próximo | REQ-004.4 |
| partidas + rejeitados ≠ `# Matches N` | arquivo marcado `falhou`; nada dele é gravado | REQ-005.2 |
| arquivo sem `# Matches` | arquivo marcado `falhou`, motivo `contagem não declarada` | REQ-005.3 |
| arquivo fora do escopo | ignorado, marcado `nao_carregado` no relatório; não conta como falha | REQ-010.2 |
| dois arquivos na mesma partição | execução inteira falha antes de gravar, com os dois nomes | REQ-006.2 |
| `mandante = visitante`, `_ht` > final, gols com status sem jogo | `Rejeitado` em `silver.rejeitados` | REQ-007.1–3 |
| partida duplicada | primeira ocorrência fica (menor `arquivo`, depois menor `linha`); demais em `silver.rejeitados` | REQ-007.4 |
| `jogos = 0` | `aproveitamento` nulo | REQ-008.6 |
| qualquer arquivo `falhou` | tarefa bronze termina com código 1, depois de gravar os demais | REQ-009.2 |
| erro de escrita Iceberg, ministack fora | propaga com contexto; o job falha | — |
| o ministack marca `SUCCEEDED` um job que falhou | o job registra `etl_futebol: codigo_saida=N` no log; `scripts/glue.sh` só aceita o marcador com 0 | REQ-009.2 |

## Decisões (ADR)

### ADR-001 — O exemplo é um projeto autocontido em `examples/futebol/`

**Contexto.** A raiz é o template agnóstico; o código de futebol não pode ir para o `src/` dela.
**Decisão.** `examples/futebol/` ganha `pyproject.toml`, `Makefile`, `src/` e `tests/` próprios.
Reaproveita as guardas de `tools/precommit/` da raiz, chamadas pelo `Makefile` do exemplo.
**Alternativas descartadas.** Código no `src/` da raiz: contamina o template, que é agnóstico.
Um `.claude/` aninhado em `examples/futebol/`: o Claude Code passaria a carregar as skills de
lá, quebrando a promessa do `examples/README.md` de que nada ali é carregado.
**Consequências.** O guarda `glossario` lê `.claude/glossario.toml` relativo ao diretório
corrente, que no exemplo não existe. Ganha uma opção `--glossario <caminho>`, com o
comportamento padrão inalterado. É a única mudança fora de `examples/`.
**Atende** REQ-010.

### ADR-002 — A fonte é um clone fixo, fora do git

**Contexto.** O pipeline precisa dos 18 arquivos; o upstream muda toda semana.
**Decisão.** `make fonte` clona `openfootball/south-america` em `examples/futebol/south-america/`
e faz checkout do commit `119fa17`. O diretório entra no `.gitignore` e em `[fontes]
somente_leitura` do `projeto.toml` da raiz, para o hook bloquear edição.
**Alternativas descartadas.** Versionar 1,6 MB de texto de terceiros: cada atualização do
upstream vira um diff enorme e a fonte passa a parecer nossa. Submódulo git: exige
`--recurse-submodules` em todo clone e falha em silêncio quando esquecido.
**Consequências.** Atualizar a fonte é trocar um hash no `Makefile`, uma decisão explícita.
**Atende** REQ-005, REQ-010.3.

### ADR-003 — Cálculo em Python puro; Spark só lê e grava

**Contexto.** A steering manda a complexidade para o domínio. São 6.552 partidas.
**Decisão.** Parser, validação, deduplicação e classificação são funções puras. Os adaptadores
de tabela convertem modelo ↔ linha e usam `.collect()` para devolver modelos ao caso de uso.
**Alternativas descartadas.** Transformações Spark (`groupBy`, `join`) para silver e gold: a
regra de pontos e o nulo do aproveitamento ficariam testáveis só com JVM, e o host não tem Java.
**Consequências.** Tudo passa pela memória do driver. Revisitar se a fonte passar de 100 MB,
cerca de 60 vezes o volume atual; o limite é uma estimativa, não uma medição.
**Atende** REQ-001–008.

### ADR-004 — O código do pacote roda em Python 3.10, só com stdlib e PySpark *(mantida pela ADR-009: o Glue 4.0 também traz Python 3.10)*

**Contexto.** A imagem de job do minilake (`apache/spark:3.5.3-...-python3-ubuntu`) traz Python
3.10.12, sem `click` nem `pydantic`. O `tech.md` fixa 3.11.
**Decisão.** O desenvolvimento segue em 3.11 (o `uv` e o `.python-version` da raiz). O pacote
declara `ruff target-version = "py310"` e `mypy python_version = "3.10"`, para que nada exclusivo
do 3.11 entre (`StrEnum`, `datetime.UTC`, `tomllib`). `Status` é `class Status(str, Enum)`.
`click` fica restrito a `cli/main.py`, que roda só no host; `cli/job.py` usa `argparse`.
**Alternativas descartadas.** Imagem de job própria com 3.11: a imagem é configuração
compartilhada do minilake, não deste projeto. `pip install` dentro do job: exige rede no
container e torna a execução não reproduzível.
**Consequências.** Divergência documentada do `tech.md` da raiz, válida só para este exemplo. O
achado também vale para a raiz: o `tech.md` diz que o PySpark é o mesmo da imagem, mas não
alerta que o Python não é.
**Atende** todos os REQs (pré-condição de execução).

### ADR-005 — O pacote vai para o job como zip no volume *(substituída pela ADR-009)*

**Contexto.** `spark_python_task` executa um único `python_file`; as `libraries` do minilake só
aceitam coordenadas Maven, não wheel.
**Decisão.** `make publicar` gera `etl_futebol.zip` com `src/etl_futebol/`, envia para
`/data/dbfs/futebol/codigo/` e importa um `job.py` mínimo no Workspace. O `job.py` põe o zip no
`sys.path` e chama `etl_futebol.cli.job.main(argv)`.
**Alternativas descartadas.** Um script único com todo o código: perde a separação em camadas
que os testes exigem. `--py-files`: o minilake não expõe flags de `spark-submit` por tarefa.
**Consequências.** Todo módulo do pacote tem de ser importável de dentro de um zip, sem arquivo
de dados ao lado.
**Atende** REQ-009.

### ADR-008 — Publicar e executar pelo MCP do minilake *(revisão de 2026-10-13; substituída pela ADR-009)*

**Contexto.** Durante a implementação, o MCP do minilake foi ligado e o usuário pediu para usá-lo
em vez do comando `publicar`/`executar` da T-21. A ferramenta `upload_file` do MCP só aceita
texto, então o zip da ADR-005 não passa por ela.
**Decisão.** O código vai para `/data/dbfs/futebol/codigo/etl_futebol/` como arquivos `.py`
soltos, e o `job.py` põe `/data/dbfs/futebol/codigo` no `sys.path`. A fonte e o código sobem pela
Files API com `curl` (`make enviar`), o mesmo endpoint do `upload_file`. Catálogo, Job, execução
e conferência por SQL são feitos pelo MCP. O `ClienteMinilake` da T-19 continua, usado só pelo
`make e2e`, que precisa rodar sem o agente.
**Alternativas descartadas.** Mandar os 540 KB da fonte pelo `upload_file`: cada byte passaria
pelo contexto do agente, sem ganho nenhum. Manter a T-21: duplicaria o que o MCP já faz.
**Consequências.** Rodar o pipeline completo passa a exigir o Claude Code com o MCP ligado; o
`make e2e` é o caminho reproduzível sem agente. A checagem de tabela existente passa a olhar o
diretório `_delta_log` no volume, em vez de `DeltaTable.isDeltaTable`: o módulo Python `delta`
não está na imagem fora do `spark-submit`, e assim o pacote importa em qualquer Python 3.10.
**Atende** REQ-009.

### ADR-006 — Idempotência por substituição, nunca por MERGE *(princípio mantido; operações trocadas pela ADR-009)*

**Contexto.** Reprocessar é o caso normal (REQ-006).
**Decisão.** Bronze grava com `mode("overwrite")` e `replaceWhere` nas partições
`(competicao, temporada)` dos arquivos aprovados. Rejeitados de bronze, idem por `arquivo`.
Silver e gold sobrescrevem a tabela inteira, porque derivam integralmente da camada anterior.
**Alternativas descartadas.** `MERGE INTO`: proibido pela convenção do minilake e barrado pelo
guarda de dialeto. Append seguido de deduplicação: deixa a tabela errada entre as duas etapas.
**Consequências.** Um arquivo que falha na contagem mantém a versão anterior de sua partição,
em vez de apagá-la.
**Atende** REQ-005.2, REQ-006.

### ADR-007 — Um Job, três tarefas, silver roda mesmo se bronze falhar *(substituída pela ADR-009)*

**Contexto.** REQ-005.2 quer que um arquivo ruim não impeça os bons.
**Decisão.** Job `futebol-pipeline` com tarefas `bronze` → `silver` (`run_if: ALL_DONE`) →
`gold` (`run_if: ALL_SUCCESS`). A mesma `job.py` recebe a camada como parâmetro.
**Alternativas descartadas.** Três Jobs encadeados pelo host: a orquestração sairia do minilake.
`ALL_SUCCESS` em silver: um arquivo com contagem divergente congelaria silver e gold.
**Consequências.** O Job termina `FAILED` quando bronze falha, mesmo com silver e gold
atualizados. É o sinal de REQ-009.2.
**Atende** REQ-005.2, REQ-009.

### ADR-009 — Executar como job AWS Glue 4.0 no ministack, com tabelas Iceberg *(revisão de 2026-10-13)*

**Contexto.** O usuário trocou o alvo de execução: em vez do minilake (Databricks emulado), o
pipeline roda como job AWS Glue no ministack, com tabelas Iceberg. Antes de redesenhar, cinco jobs
de sonda no ministack confirmaram o que funciona; cada achado abaixo veio de uma execução.
**Decisão.**
- Um job Glue `futebol-pipeline` (`glueetl`, Glue 4.0) executa bronze, silver e gold em sequência,
  numa única subida de JVM. Silver roda mesmo se bronze reprovar algum arquivo (o objetivo da
  ADR-007 continua); gold roda depois de silver.
- O script `glue_job.py` fica no S3 (`ScriptLocation`) e o pacote vai como zip por
  `--extra-py-files` (volta a ideia da ADR-005, agora suportada). Argumentos por
  `getResolvedOptions`, **sem** `JOB_NAME`, que o ministack não passa.
- Tabelas Iceberg no catálogo Spark `iceberg`, do tipo `hadoop`, warehouse
  `s3a://futebol-lake/warehouse`, com os jars do Iceberg 1.0 da imagem **na frente** do
  `extraClassPath`. Depois de cada escrita, `RegistroCatalogoGlue` registra a tabela no Glue
  Data Catalog (`table_type=ICEBERG`, `metadata_location`).
- Idempotência: `overwritePartitions()` em `bronze.partidas`; `overwrite(arquivo IN (...))` em
  `bronze.rejeitados`; `overwrite(true)` em silver e gold.
- Resultado: o job registra `etl_futebol: codigo_saida=N` no log; `scripts/glue.sh` decide por ele.
- Conferência (REQ-005, REQ-006, REQ-008 no e2e) por um passo `verificacao` do próprio job, que lê
  as tabelas com Spark e registra os totais no log.
**Alternativas descartadas.**
- `GlueCatalog` do Iceberg: na versão 1.0 da imagem não existe `glue.endpoint`; o cliente fala
  com a AWS real e falha com `security token ... invalid`.
- Catálogo REST do Glue no ministack: cria a tabela, mas o commit não grava `snapshot-log`, e
  toda escrita do Spark quebra com `NoSuchElementException` em `updateSnapshotLog`. É bug do
  ministack; vale reportar.
- Parquet puro com sobrescrita dinâmica de partição: o Athena do ministack leria certo, mas o
  usuário pediu Iceberg, que é o formato de tabela que o Glue e o Athena da AWS tratam como de
  primeira classe.
- Conferir pelo Athena: o Athena do ministack não lê Iceberg (lê os arquivos crus como CSV).
- Confiar no `JobRunState`: a imagem do OpenArchFlow canaliza o `spark-submit` para o
  encaminhador de logs sem `pipefail`; um job com traceback termina `SUCCEEDED`.
- Três jobs Glue, um por camada: três subidas de JVM emulada (amd64 em Mac ARM) por execução.
**Consequências.** O código de `domain/` e `application/` não mudou. Saem `delta_spark.py`,
`sessao_spark.py`, `minilake_http.py` e `cli/job.py`; entram `iceberg.py`, `catalogo_glue.py`,
`sessao_glue.py`, `fonte_s3.py` e `cli/glue.py`. Na AWS real, o mesmo job rodaria trocando o
catálogo `hadoop` pelo `GlueCatalog` e o registro manual deixaria de ser necessário. Partição de
bronze com zero partidas não é limpa pelo `overwritePartitions()` (só troca partições presentes no
DataFrame); hoje nenhum arquivo do escopo tem zero partidas.
**Atende** REQ-005, REQ-006, REQ-009.

## Rastreabilidade

| REQ | Onde é atendido |
| --- | --- |
| REQ-001 | `domain/parser.py` |
| REQ-002 | `domain/resultado.py` |
| REQ-003 | `domain/resultado.py`, `domain/modelos.py` (`Status`) |
| REQ-004 | `domain/parser.py`, `application/casos_de_uso.py` (decodificação) |
| REQ-005 | `domain/contagem.py`, `IngerirBronze` |
| REQ-006 | portas de repositório, `infrastructure/iceberg.py`, ADR-006, ADR-009 |
| REQ-007 | `domain/invariantes.py`, `RefinarSilver` |
| REQ-008 | `domain/classificacao.py`, `CalcularGold` |
| REQ-009 | `application/relatorio.py`, `cli/glue.py`, `scripts/glue.sh`, ADR-009 |
| REQ-010 | `domain/escopo.py`, `FonteArquivosFs` (somente leitura), ADR-002 |

## Gate — 2026-10-13

Aprovado pelo usuário sem ajustes, incluindo as duas mudanças fora de `examples/` previstas nas
ADR-001 (opção `--glossario` na guarda) e ADR-002 (caminho da fonte em `[fontes]
somente_leitura` da raiz).

## Gate da revisão — 2026-10-13

A ADR-009 foi pedida pelo usuário ("ajuste tudo e execute", depois "use iceberg"), que pediu
execução direta. A troca de plataforma foi registrada aqui antes do código, como manda o
processo, e não passou por um gate intermediário a pedido dele.
