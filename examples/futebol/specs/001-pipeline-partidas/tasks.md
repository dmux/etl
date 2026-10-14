# Tarefas — pipeline de partidas

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` concluída

Ordem de dentro para fora: fundação, domínio, aplicação, fakes, adaptadores reais, CLI, e2e.
Todo comando abaixo roda a partir de `examples/futebol/`, salvo indicação.

---

## Fundação

## T-01 — Criar o projeto do exemplo e baixar a fonte fixa
- [x] **Atende** REQ-010.3
- **Arquivos** `pyproject.toml`, `Makefile`, `src/etl_futebol/__init__.py`, `.gitignore` da raiz, `.claude/projeto.toml` da raiz
- **Descrição** Pacote `etl_futebol` com ruff `py310`, mypy `3.10` e cobertura ≥ 95% (ADR-001, ADR-004). Alvos `install`, `fonte`, `lint`, `test`, `cov`, `check`. `make fonte` clona o openfootball e faz checkout de `119fa17`. `examples/futebol/south-america/` vai para o `.gitignore` e para `[fontes] somente_leitura` (ADR-002).
- **Pronto quando** `make install fonte` termina; `git -C south-america rev-parse --short HEAD` imprime `119fa17`; o hook `proteger-dado-bruto.sh` sai com código 2 para um caminho em `examples/futebol/south-america/`.
- **Depende de** —

## T-02 — Dar à guarda de glossário a opção `--glossario`
- [x] **Atende** — (ADR-001: infraestrutura de qualidade, sem REQ de produto)
- **Arquivos** `tools/precommit/guardas_spark.py` (raiz), `Makefile` do exemplo
- **Descrição** `--glossario <caminho>` sobrescreve o padrão `.claude/glossario.toml`; sem a opção, nada muda. O `make guardas` do exemplo roda as 8 guardas com `--glossario glossario.toml`.
- **Pronto quando** a guarda barra `home_score` num arquivo de teste com `--glossario glossario.toml`; sem a opção, a partir da raiz, o resultado é o de antes; `make hooks` da raiz continua verde.
- **Depende de** T-01

---

## Domínio

## T-03 — Modelos de domínio
- [x] **Atende** REQ-001, REQ-003
- **Arquivos** `src/etl_futebol/domain/modelos.py`, `tests/unit/test_modelos.py`
- **Descrição** `Status(str, Enum)`, `Placar`, `Resultado`, `Partida`, `Rejeitado`, `ArquivoProcessado`, `LinhaClassificacao`, como no design. Frozen, slots, sem lógica além de propriedades derivadas triviais.
- **Pronto quando** os testes cobrem os seis valores de `Status` e a imutabilidade de `Partida`; `make check` verde.
- **Depende de** T-01

## T-04 — Interpretar cada forma de resultado
- [x] **Atende** REQ-002, REQ-003
- **Arquivos** `src/etl_futebol/domain/resultado.py`, `tests/unit/test_resultado.py`
- **Descrição** `interpretar_resultado(texto) -> Resultado | None`, testando as formas na ordem da skill `openfootball-format`, da mais específica para a mais genérica.
- **Pronto quando** há um teste para cada uma das 11 formas da skill (incluindo `pen. (N-N)` e `pen. N-N a.e.t. (N-N)`), para os quatro marcadores, para texto vazio (agendada) e para texto irreconhecível (`None`).
- **Depende de** T-03

## T-05 — Parser: cabeçalho, datas, horários e rodadas
- [x] **Atende** REQ-001
- **Arquivos** `src/etl_futebol/domain/parser.py`, `tests/unit/test_parser.py`
- **Descrição** `parsear_arquivo(arquivo, texto) -> ArquivoProcessado`, com o estado de leitura (data, hora e rodada vigentes, `ultima_data_completa`) num objeto imutável. Lê `# Matches N` para `declarado`.
- **Pronto quando** passam os casos: horário herdado por três partidas · data sem ano · virada de ano com data fora de ordem · primeira partida da data sem horário (`hora` nula) · rodada composta · rodada sem número · clube com sufixo de UF e acento · arquivo vazio.
- **Depende de** T-04

## T-06 — Parser: linhas que viram rejeitados
- [x] **Atende** REQ-004.1, REQ-004.2, REQ-004.3
- **Arquivos** `src/etl_futebol/domain/parser.py`, `tests/unit/test_parser.py`
- **Descrição** Linha de partida com resultado irreconhecível ou truncada vira `Rejeitado` com arquivo, linha, texto e motivo; partida antes de qualquer data vira `Rejeitado` com motivo `partida sem data`. O parser segue nas linhas seguintes.
- **Pronto quando** os três casos têm teste, e um arquivo com uma linha ruim no meio produz as partidas de antes e de depois dela.
- **Depende de** T-05

## T-07 — Conferir a contagem declarada
- [x] **Atende** REQ-005
- **Arquivos** `src/etl_futebol/domain/contagem.py`, `tests/unit/test_contagem.py`
- **Descrição** `conferir_contagem(processado) -> str | None`: compara partidas + rejeitados com `declarado`.
- **Pronto quando** há testes para contagem certa, para mais, para menos e não declarada.
- **Depende de** T-03

## T-08 — Decidir o que está no escopo
- [x] **Atende** REQ-010.1, REQ-010.2
- **Arquivos** `src/etl_futebol/domain/escopo.py`, `tests/unit/test_escopo.py`
- **Descrição** `no_escopo(arquivo) -> bool` para `brazil/AAAA_br1.txt`, `_br2.txt` e `_brcup.txt`, com AAAA ≥ 2018.
- **Pronto quando** os 18 nomes do commit `119fa17` dão verdadeiro, e `brazil/2017_br1.txt`, `argentina/2024_ar1.txt` e `brazil/README.md` dão falso.
- **Depende de** —

## T-09 — Invariantes e deduplicação de silver
- [x] **Atende** REQ-007
- **Arquivos** `src/etl_futebol/domain/invariantes.py`, `tests/unit/test_invariantes.py`
- **Descrição** `validar(partidas)` separa válidas de `Rejeitado` com motivo; `deduplicar(partidas)` mantém a de menor `arquivo` e depois menor `linha`, e devolve as demais como rejeitadas.
- **Pronto quando** cada um dos quatro critérios do REQ-007 tem teste, e uma partida válida passa intacta.
- **Depende de** T-03

## T-10 — Calcular a classificação
- [x] **Atende** REQ-008
- **Arquivos** `src/etl_futebol/domain/classificacao.py`, `tests/unit/test_classificacao.py`
- **Descrição** `calcular_classificacao(partidas)`: uma linha por clube, temporada e competição, só Série A e Série B, contando apenas `realizada` e `atribuida`.
- **Pronto quando** há testes de pontos, saldo, aproveitamento com 4 casas, `jogos = 0` ⇒ `aproveitamento` nulo, clube só com partidas agendadas presente, Copa do Brasil ausente e W.O. contado.
- **Depende de** T-03

---

## Aplicação

## T-11 — Portas e adaptadores em memória
- [x] **Atende** REQ-006
- **Arquivos** `src/etl_futebol/application/portas.py`, `src/etl_futebol/infrastructure/memoria.py`, `tests/unit/test_memoria.py`
- **Descrição** As quatro portas do design e os quatro fakes. A semântica de substituição (`substituir_particoes`, `substituir_arquivos`, `substituir_tudo`) é implementada de verdade nos fakes.
- **Pronto quando** cada fake satisfaz `isinstance(..., Porta)`, e há teste mostrando que substituir uma partição preserva as outras.
- **Depende de** T-03

## T-12 — Relatório de execução
- [x] **Atende** REQ-009
- **Arquivos** `src/etl_futebol/application/relatorio.py`, `tests/unit/test_relatorio.py`
- **Descrição** `RelatorioExecucao` com uma entrada por arquivo (`declarado`, `gravadas`, `rejeitadas`, `situacao`, `motivo`), `codigo_saida` e uma forma de texto para o log.
- **Pronto quando** `codigo_saida` é 0 sem falhas e 1 com ao menos uma; `nao_carregado` não conta como falha.
- **Depende de** T-03

## T-13 — Caso de uso `IngerirBronze`
- [x] **Atende** REQ-001, REQ-004.4, REQ-005.2, REQ-006, REQ-009, REQ-010.2
- **Arquivos** `src/etl_futebol/application/casos_de_uso.py`, `tests/unit/test_casos_de_uso.py`
- **Descrição** Lista, filtra pelo escopo, decodifica UTF-8, parseia, confere a contagem; grava os aprovados por partição e por arquivo. Falha a execução inteira, antes de gravar, se dois arquivos caírem na mesma partição.
- **Pronto quando** testado com fakes: arquivo bom gravado; contagem divergente não grava e os demais sim; bytes não UTF-8 viram um rejeitado com `linha` nula; arquivo fora do escopo é ignorado; executar duas vezes dá o mesmo total; colisão de partição não grava nada.
- **Depende de** T-06, T-07, T-08, T-11, T-12

## T-14 — Caso de uso `RefinarSilver`
- [x] **Atende** REQ-006, REQ-007
- **Arquivos** `src/etl_futebol/application/casos_de_uso.py`, `tests/unit/test_casos_de_uso.py`
- **Descrição** Lê bronze, valida, deduplica, reescreve `silver.partidas` e `silver.rejeitados`.
- **Pronto quando** testado com fakes: partida inválida vai para rejeitados de silver; rodar duas vezes dá o mesmo resultado.
- **Depende de** T-09, T-11

## T-15 — Caso de uso `CalcularGold`
- [x] **Atende** REQ-006, REQ-008
- **Arquivos** `src/etl_futebol/application/casos_de_uso.py`, `tests/unit/test_casos_de_uso.py`
- **Descrição** Lê silver, calcula a classificação, reescreve `gold.classificacao`.
- **Pronto quando** testado com fakes, incluindo idempotência.
- **Depende de** T-10, T-11

---

## Infraestrutura

## T-16 — Fonte em sistema de arquivos
- [x] **Atende** REQ-004.4, REQ-010.3
- **Arquivos** `src/etl_futebol/infrastructure/fonte_fs.py`, `tests/unit/test_fonte_fs.py`
- **Descrição** `FonteArquivosFs(raiz)`: lista `.txt` recursivamente com caminho relativo e lê bytes, só em modo leitura.
- **Pronto quando** testado com `tmp_path`: lista em ordem estável, lê bytes crus, raiz inexistente dá erro com o caminho, e os arquivos não mudam de `mtime` após a leitura.
- **Depende de** T-11

## T-17 — Sessão Spark e conversão entre modelo e linha *(sessão substituída pela T-23; `esquemas.py` continua)*
- [x] **Atende** REQ-006
- **Arquivos** `src/etl_futebol/infrastructure/sessao_spark.py`, `src/etl_futebol/infrastructure/esquemas.py`, `tests/unit/test_sessao_spark.py`, `tests/unit/test_esquemas.py`
- **Descrição** `criar_sessao_spark()` com as duas configs Delta. `esquemas.py` declara os `StructType` das cinco tabelas e converte modelo ↔ tupla de valores.
- **Pronto quando** com mock do builder, as duas configs são passadas; a conversão ida e volta de uma `Partida` e de uma `LinhaClassificacao` devolve objetos iguais; a guarda `spark-delta-config` passa.
- **Depende de** T-03

## T-18 — Repositórios Delta *(substituída pela T-25 — ADR-009)*
- [x] **Atende** REQ-006
- **Arquivos** `src/etl_futebol/infrastructure/delta_spark.py`, `tests/unit/test_delta_spark.py`
- **Descrição** Os três repositórios Delta: escrita por path sob `/data/delta/futebol/`, `replaceWhere` nas partições ou arquivos, `overwrite` completo, leitura com `.collect()` convertida em modelos.
- **Pronto quando** com `SparkSession` mockada, os testes verificam caminho, `partitionBy`, a expressão de `replaceWhere` montada para duas partições, e que lista vazia não chama o writer.
- **Depende de** T-11, T-17

## T-19 — Cliente HTTP do minilake *(substituída pela T-27 — ADR-009; código removido)*
- [x] **Atende** REQ-009
- **Arquivos** `src/etl_futebol/infrastructure/minilake_http.py`, `tests/unit/test_minilake_http.py`
- **Descrição** `ClienteMinilake(url)` via `urllib`: enviar arquivo, importar script no Workspace, criar ou atualizar o Job de três tarefas (ADR-007), disparar e aguardar, ler a saída, executar SQL.
- **Pronto quando** com `urlopen` mockado, cada método monta a requisição esperada; minilake fora do ar dá erro com a URL e a dica `make up`; execução `FAILED` devolve a saída da tarefa.
- **Depende de** T-12

---

## CLI e execução

## T-20 — Entrypoint do job *(substituída pela T-26 — ADR-009)*
- [x] **Atende** REQ-009
- **Arquivos** `src/etl_futebol/cli/job.py`, `job.py`
- **Descrição** `cli/job.py` (argparse) monta adaptadores reais e roda a camada pedida, registra o relatório em `logging` e devolve `codigo_saida`. `job.py` na raiz do exemplo põe o diretório do código no `sys.path` e chama `main` (ADR-008).
- **Pronto quando** o pacote importa no Python 3.10 da imagem do job (`docker run` com o PySpark da imagem no `PYTHONPATH`); as guardas passam.
- **Depende de** T-13, T-14, T-15, T-16, T-18

## T-21 — Publicar e executar pelo MCP *(substituída pela T-27 — ADR-009)*
- [ ] **Atende** REQ-009, REQ-010
- **Arquivos** `Makefile` (alvo `enviar`)
- **Descrição** `make enviar` sobe a fonte e o código pela Files API. Pelo MCP: catálogo `futebol` e schemas, `job.py` no Workspace, Job de três tarefas (`definir_job_pipeline`), execução, saída das tarefas e registro das cinco tabelas EXTERNAL.
- **Pronto quando** o Job termina `SUCCESS` e o relatório de bronze mostra 18 arquivos `ok`.
- **Depende de** T-19, T-20

## T-22 — Testes e2e contra o minilake *(substituída pela T-28 — ADR-009)*
- [ ] **Atende** REQ-005, REQ-006, REQ-008, REQ-009
- **Arquivos** `tests/e2e/test_pipeline_minilake.py`
- **Descrição** Roda o Job e confere por SQL: total de `bronze.partidas` = 6.552; nenhum arquivo com contagem divergente; 20 clubes com 38 jogos na Série A 2025; rodar de novo mantém os totais.
- **Pronto quando** `make e2e` passa com o minilake no ar.
- **Depende de** T-21

---

## Execução no AWS Glue (ADR-009)

## T-23 — Sessão pelo GlueContext
- [x] **Atende** REQ-009
- **Arquivos** `src/etl_futebol/infrastructure/sessao_glue.py`, `tests/unit/test_sessao_glue.py`
- **Descrição** `criar_sessao_glue()` devolve a `spark_session` de `GlueContext(SparkContext.getOrCreate())`, importando `awsglue` só dentro da função. Remove `sessao_spark.py`.
- **Pronto quando** o teste, com `awsglue` falso em `sys.modules`, mostra que a sessão é a do contexto; a guarda `glue-sessao` passa.
- **Depende de** —

## T-24 — Fonte no S3 lida pelo Spark
- [x] **Atende** REQ-004.4, REQ-010
- **Arquivos** `src/etl_futebol/infrastructure/fonte_s3.py`, `tests/unit/test_fonte_s3.py`
- **Descrição** `FonteS3Spark(spark, raiz)`: lê os `.txt` sob a raiz com `binaryFile` (recursivo), uma vez, e devolve caminhos relativos em ordem e bytes crus.
- **Pronto quando** com Spark mockado: caminho relativo correto, ordem estável, bytes intactos, uma única leitura para várias chamadas.
- **Depende de** T-11

## T-25 — Repositórios Iceberg e registro no Glue Data Catalog
- [x] **Atende** REQ-006
- **Arquivos** `src/etl_futebol/infrastructure/iceberg.py`, `src/etl_futebol/infrastructure/catalogo_glue.py`, `tests/unit/test_iceberg.py`, `tests/unit/test_catalogo_glue.py`
- **Descrição** Os três repositórios: DDL `CREATE TABLE IF NOT EXISTS ... USING iceberg PARTITIONED BY`, `overwritePartitions()`, `overwrite(arquivo IN ...)`, `overwrite(true)`, leitura de volta; registro no Glue depois de cada escrita. Remove `delta_spark.py`.
- **Pronto quando** com Spark e boto3 falsos: nome qualificado `iceberg.futebol_<camada>.<tabela>`, operação certa por caso, lista vazia sem escrita, tabela inexistente lida como vazia, registro cria e depois atualiza.
- **Depende de** T-17, T-23

## T-26 — Entrypoint do job Glue
- [x] **Atende** REQ-009
- **Arquivos** `src/etl_futebol/cli/glue.py`, `glue_job.py`
- **Descrição** `getResolvedOptions` sem `JOB_NAME`; executa as camadas pedidas na ordem (silver mesmo com falha em bronze, gold depois de silver); passo `verificacao` com os totais; registra `etl_futebol: codigo_saida=N`. Remove `cli/job.py`, `job.py` e `minilake_http.py`.
- **Pronto quando** o pacote importa no Python 3.10 da imagem Glue; as guardas passam.
- **Depende de** T-13, T-14, T-15, T-24, T-25

## T-27 — Publicar e executar no ministack
- [x] **Atende** REQ-009, REQ-010
- **Arquivos** `scripts/glue.sh`, `Makefile`
- **Descrição** `make publicar` (bucket, fonte, zip, script, job com o `--conf` do Iceberg), `make executar` (executa, espera, decide pelo marcador), `make verificar`.
- **Pronto quando** `make publicar executar` termina com `codigo_saida=0` e 18 arquivos `ok` no relatório de bronze.
- **Depende de** T-26

## T-28 — Testes e2e contra o ministack
- [x] **Atende** REQ-005, REQ-006, REQ-008, REQ-009
- **Arquivos** `tests/e2e/test_pipeline_glue.py`
- **Descrição** Executa o job e o passo `verificacao`, e confere pelos totais do log: 6.552 partidas em bronze; 18 arquivos `ok`; 20 clubes com 38 jogos na Série A 2025; rodar de novo mantém os totais.
- **Pronto quando** `make e2e` passa com o ministack de pé.
- **Depende de** T-27

## T-29 — Comandos `/glue:executar` e `/glue:verificar`
- [x] **Atende** REQ-009
- **Arquivos** `.claude/commands/glue/executar.md`, `.claude/commands/glue/verificar.md` (raiz), `scripts/glue.sh`, `Makefile`
- **Descrição** Publicação só quando algo muda (`garantir`), resumo em markdown por camada e da verificação, log filtrado em `dist/ultima-execucao.log`; comandos que conferem o ministack, executam e apresentam o resultado, com diagnóstico pela skill `glue-ministack` em caso de falha.
- **Pronto quando** `/glue:executar examples/futebol` mostra as tabelas e `RESULTADO: sucesso`; `/glue:verificar` roda sem republicar.
- **Depende de** T-27

---

## Matriz de cobertura

| REQ | Tarefas |
| --- | --- |
| REQ-001 | T-03, T-05, T-13 |
| REQ-002 | T-04 |
| REQ-003 | T-03, T-04 |
| REQ-004 | T-06, T-13, T-16, T-24 |
| REQ-005 | T-07, T-13, T-28 |
| REQ-006 | T-11, T-13, T-14, T-15, T-17, T-25, T-28 |
| REQ-007 | T-09, T-14 |
| REQ-008 | T-10, T-15, T-28 |
| REQ-009 | T-12, T-13, T-23, T-26, T-27, T-28, T-29 |
| REQ-010 | T-01, T-08, T-13, T-16, T-24, T-27 |
