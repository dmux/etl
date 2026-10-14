# A jornada do desenvolvedor — do dado bruto ao pipeline, por spec

Registro de como o pipeline de `examples/futebol/` foi construído com esta base, contado do
ponto de vista de quem desenvolve. Cada etapa responde a quatro perguntas: o que o
desenvolvedor pede, o que o agente faz, o que o desenvolvedor decide, e o que apareceu no
caminho que ninguém esperava.

O texto é escrito durante o trabalho, não depois: o que está aqui é o que aconteceu, inclusive
os erros.

## Mapa

| Etapa | O dev digita | Artefato | Gate | Estado |
| --- | --- | --- | --- | --- |
| 0. Preparação | "gere um pipeline em examples/" | clone da fonte | — | feito |
| 1. Requisitos | `/sdd:spec pipeline-partidas` | `requirements.md` | aprovação humana | aprovado em 2026-10-13 |
| 2. Design | `/sdd:design` | `design.md` | aprovação humana | aprovado em 2026-10-13 |
| 3. Tarefas | `/sdd:tasks` | `tasks.md` | aprovação humana | aprovado em 2026-10-13 |
| 4. Implementação | `/sdd:impl`, uma vez por tarefa | código + testes | revisão do diff | feito: 26 tarefas, 184 testes, 100% |
| 5. Troca de plataforma | `/sdd:steering` + `/sdd:design` | ADR-009, steering e skills | pedido do dev | feito: AWS Glue + Iceberg no ministack |
| 6. Execução | `make publicar executar` | tabelas Iceberg no Glue Data Catalog | contagem confere | feito: 6.552 partidas, e2e 5 de 5 |
| 7. Uso diário | `/glue:executar`, `/glue:verificar` | resumo por camada | veredito pelo marcador | feito |

```
 dev pede ──► agente escreve ──► dev aprova ──► próxima fase
                   ▲                  │
                   └── dev ajusta ◄───┘
```

O ritmo é sempre esse. O agente nunca passa de uma fase para a seguinte sozinho: o gate é o
ponto em que o desenvolvedor lê, discorda ou aprova.

---

## Etapa 0 — Preparação: olhar o dado antes de escrever qualquer coisa

**O dev pediu:** "preciso que gere um pipeline em examples/ e documente o processo e suas
etapas".

**O agente perguntou antes de começar** três coisas que só o dev podia decidir: parar em cada
gate ou fazer tudo de uma vez; de onde ler o dado; onde documentar. Escolhas: parar em cada
gate, clonar o openfootball, documentar em Markdown no repositório.

**O agente fez:** clonou [`openfootball/south-america`](https://github.com/openfootball/south-america)
(commit `119fa17`, 2026-09-21, 60 arquivos, 1,6 MB) e varreu os 18 arquivos de `brazil/` com
`grep`, antes de escrever uma linha de requisito.

**O que apareceu.** A skill `openfootball-format` descrevia o formato, mas fora escrita sobre
uma versão anterior dos dados. A varredura achou três casos que ela não cobria:

| Achado | Onde | Virou |
| --- | --- | --- |
| `5-3 pen. (0-0)`, um placar só entre parênteses | 6 linhas, `2025_brcup.txt` | dúvida de gate; a regra da skill estava errada para este caso |
| `4-3 pen. 4-3 a.e.t. (0-0)`, placar `a.e.t.` que não é empate | 4 linhas, `2025_brcup.txt` | dúvida de gate; provável erro da origem |
| data cuja primeira partida não tem horário | 36 linhas, `2025_br2.txt` e `2026_br1.txt` | critério REQ-001.4: `hora` nula, nunca herdada de outra data |

O terceiro achado é o tipo de bug que passaria por todos os testes escritos a partir da
documentação: um parser que herda o horário "da linha anterior" daria a essas 36 partidas o
horário do último jogo do dia anterior, sem erro nenhum.

**Lição para quem usa a base:** olhar o dado é parte da fase de requisitos, não da
implementação. Os comandos usados, para repetir:

```bash
cd south-america/brazil
grep -c ' v ' *.txt                                   # linhas de partida por arquivo
grep -h '# Matches' *.txt                             # contagem declarada
grep -ho '\[[a-z]*\]' *.txt | sort | uniq -c          # marcadores de status
grep -h ' pen\. ' *.txt | sed -E 's/.* v +[^0-9\[]+//; s/[0-9]+/N/g' | sort | uniq -c
```

---

## Etapa 1 — Requisitos: o quê, e como se prova

**O dev digita:** `/sdd:spec pipeline-partidas`. O comando cria
`specs/001-pipeline-partidas/` e aciona o `spec-analista`, que carrega as skills `spec-ears` e
`glossario-dados` e a skill do formato da fonte.

**Entrada:** o produto (`steering/produto.md`), o glossário (`steering/glossario-dados.md`), a
skill do formato e a varredura da etapa 0.

**Saída:** [`requirements.md`](specs/001-pipeline-partidas/requirements.md), com 10 requisitos
em EARS.

| Id | Requisito | Camada |
| --- | --- | --- |
| REQ-001 | Toda linha de partida vira uma partida | bronze |
| REQ-002 | Cada forma de resultado é interpretada sem ambiguidade | bronze |
| REQ-003 | Status da partida vem dos marcadores da origem | bronze |
| REQ-004 | Linha não reconhecida vira registro rejeitado | bronze |
| REQ-005 | Contagem de cada arquivo confere com o cabeçalho | bronze |
| REQ-006 | Reprocessar não duplica | todas |
| REQ-007 | Partida que viola invariante não chega à camada consumível | silver |
| REQ-008 | Classificação por temporada nos campeonatos de pontos corridos | gold |
| REQ-009 | Cada execução presta contas do que fez | execução |
| REQ-010 | Só os arquivos do escopo são carregados | execução |

**O que a fase cuidou de não fazer.** Nenhum requisito fala em Spark, Delta, partição ou
tabela: isso é design. Todo requisito tem ao menos um critério `SE ... ENTÃO` para o caminho
triste. O que não cabe nesta spec, como unificar o mesmo clube escrito de dois jeitos, ficou em
"Fora de escopo" para não crescer sozinho.

**O gate.** O agente apresentou a lista e quatro dúvidas com uma proposta para cada uma. O dev
respondeu "siga", aprovando as quatro propostas. O agente então:

- registrou as decisões no fim do `requirements.md`, com a data;
- corrigiu a skill `openfootball-format` na mesma rodada, porque a decisão 1 contradizia a
  regra dela. Uma skill errada ensinaria o erro à próxima spec.

---

## Etapa 2 — Design: como, e por que assim

**O dev digita:** `/sdd:design`. O `spec-arquiteto` lê o `requirements.md` aprovado e carrega
`design-hexagonal`, `minilake-spark` e `glossario-dados`.

**O agente investigou o alvo antes de desenhar.** O design depende de como o minilake executa
um job, então o agente leu a documentação e o código do minilake e testou contra a instância
rodando:

| Pergunta | Como respondeu | Resposta |
| --- | --- | --- |
| Como o código chega ao job? | `docs/spark-and-delta.md`, `services/jobs.py` | `spark_python_task` roda **um** arquivo; `libraries` só aceita Maven |
| Onde caem os arquivos enviados? | upload de teste pela Files API | `PUT /api/2.0/fs/files/X` → `/data/dbfs/X` no volume |
| Que Python roda o job? | `docker run apache/spark:3.5.3-... python3 --version` | **3.10.12**, sem `click` nem `pydantic` |
| Por que o MCP do minilake dá 404? | `docker-compose.yml` do minilake | `MINILAKE_MCP` está comentado: desligado por padrão |

O terceiro achado mudou o design. O `tech.md` da raiz fixa Python 3.11, e com
`target-version = "py311"` o ruff reescreveria `timezone.utc` como `datetime.UTC`, que não
existe no 3.10. O código passaria em todos os testes locais e quebraria no container.

**Saída:** [`design.md`](specs/001-pipeline-partidas/design.md).

| Parte | Conteúdo |
| --- | --- |
| Domínio | 6 módulos puros: `resultado`, `parser`, `contagem`, `invariantes`, `classificacao`, `escopo` |
| Portas | `FontePort`, `RepositorioPartidasPort`, `RepositorioRejeitadosPort`, `RepositorioClassificacaoPort`, cada uma com adaptador real e fake |
| Casos de uso | `IngerirBronze`, `RefinarSilver`, `CalcularGold` |
| Tabelas | `bronze.partidas`, `bronze.rejeitados`, `silver.partidas`, `silver.rejeitados`, `gold.classificacao`, no catálogo `futebol` |

| ADR | Decisão em uma frase |
| --- | --- |
| 001 | O exemplo é um projeto autocontido em `examples/futebol/`; a guarda `glossario` ganha `--glossario <caminho>` |
| 002 | A fonte é um clone no commit `119fa17`, fora do git e protegida pelo hook de somente-leitura |
| 003 | Cálculo em Python puro; Spark só lê e grava |
| 004 | O pacote mira Python 3.10 e só usa stdlib e PySpark no código que roda no job |
| 005 | O pacote vai para o job como zip no volume, carregado por um `job.py` mínimo |
| 006 | Idempotência por `replaceWhere` em bronze e sobrescrita completa em silver e gold, nunca `MERGE` |
| 007 | Um Job com três tarefas; silver roda mesmo se bronze falhar (`run_if: ALL_DONE`) |

**Um efeito colateral das guardas.** O glossário proíbe `ano` (sinônimo de `temporada`) e
`fora` (sinônimo de `visitante`). Isso apareceu no design, não no commit: o estado do parser
guarda `ultima_data_completa` em vez de `ano_vigente`, e a situação "fora de escopo" do
relatório se chama `nao_carregado`. A guarda molda os nomes antes da primeira linha de código.

**Também atualizado nesta fase:** o glossário ganhou `linha`, a entidade `Rejeitado` e as
métricas `vitorias`, `empates` e `derrotas`, que o design usa e o glossário não tinha.

**O gate.** O agente destacou as escolhas entre alternativas equivalentes: a mudança na guarda
da raiz (ADR-001), o cálculo fora do Spark (ADR-003) e o desvio do Python 3.11 (ADR-004). O dev
respondeu "sim". A aprovação ficou registrada no fim do `design.md`, incluindo as duas mudanças
fora de `examples/`, para que ninguém as encontre depois sem saber de onde vieram.

Um detalhe de processo: no meio desta etapa o minilake parou. O agente não o religou por conta
própria, porque o container roda fora do compose deste projeto e podia ter sido parado de
propósito. Seguiu lendo o código-fonte do minilake e, quando o dev avisou que ele estava de
volta, confirmou o caminho de upload contra a instância real. Durante essa espera o agente
também achou um erro próprio: tinha escrito 6.858 partidas no design; a soma real é 6.552.

---

## Etapa 3 — Tarefas: em que ordem, e como se sabe que acabou

**O dev digita:** `/sdd:tasks`. O `spec-planejador` lê os dois artefatos aprovados.

**Saída:** [`tasks.md`](specs/001-pipeline-partidas/tasks.md), com 22 tarefas em ordem de dentro
para fora:

| Bloco | Tarefas | Precisa de Spark? |
| --- | --- | --- |
| Fundação | T-01 projeto e fonte · T-02 opção `--glossario` | não |
| Domínio | T-03 a T-10: modelos, resultado, parser (2), contagem, escopo, invariantes, classificação | não |
| Aplicação | T-11 portas e fakes · T-12 relatório · T-13 a T-15 casos de uso | não |
| Infraestrutura | T-16 fonte · T-17 sessão e esquemas · T-18 repositórios Delta · T-19 cliente HTTP | só como mock |
| Execução | T-20 entrypoint do job · T-21 publicar e executar · T-22 e2e | sim, no minilake |

As 15 primeiras tarefas rodam sem JVM. É a hexagonal pagando a conta: quando o primeiro
container Spark subir, toda a lógica já terá testes.

**Três regras que a fase seguiu:**

- **Cada tarefa traz o próprio teste.** Não existe "escrever os testes" no fim.
- **"Pronto quando" é um comando ou um teste, nunca um adjetivo.** Por exemplo, T-04 só termina
  com um teste para cada uma das 11 formas de resultado da skill.
- **Toda tarefa aponta um REQ.** A exceção, T-02, diz isso por extenso: é infraestrutura de
  qualidade, motivada pela ADR-001, não por um requisito de produto.

Os números esperados no e2e (6.552 partidas, 20 clubes com 38 jogos na Série A 2025) foram
conferidos contra a fonte antes de entrar na tarefa.

**O gate.** O dev respondeu "sim todas e implemente": aprovou as tarefas e pediu a
implementação inteira de uma vez, em vez de parar a cada tarefa.

---

## Etapa 4 — Implementação: teste vermelho, código, teste verde

**O dev digita:** `/sdd:impl`, uma vez por tarefa. Aqui o dev pediu tudo em sequência; o agente
seguiu as tarefas na ordem do `tasks.md`, uma de cada vez, sempre mostrando o teste falhando
antes de escrever o código.

**Onde chegou:**

| Bloco | Tarefas | Testes | Observação |
| --- | --- | --- | --- |
| Fundação | T-01, T-02 | — | `make fonte` trava a fonte em `119fa17`; o hook bloqueia edição nela |
| Domínio | T-03 a T-10 | 97 | 100% de cobertura sem nenhuma JVM |
| Aplicação | T-11 a T-15 | 35 | casos de uso fechados só com fakes em memória |
| Infraestrutura | T-16 a T-19 | 55 | Spark e HTTP cobertos por mock e por fake |
| Execução | T-20 | — | o pacote importa no Python 3.10 da imagem do job |

Gate ao fim da T-20: `make check` verde, 187 testes, 99,65% de cobertura, 8 de 8 guardas.

**O que o TDD e o gate pegaram no caminho.** Cada linha abaixo é um erro que chegaria à
execução se a etapa tivesse sido pulada:

| Onde | O que apareceu | Quem pegou |
| --- | --- | --- |
| T-05 | 425 partidas agendadas, não 102: a Série B 2025 tem 323 jogos sem placar, porque a origem parou de atualizar o arquivo. A nota do requisito estava errada | rodar o parser sobre os 18 arquivos reais |
| T-06 | linha sem mandante (`18:30  v SC Recife`) levantava `ValueError` fora do controle do parser e derrubaria o arquivo inteiro | um teste de caso de borda escrito antes do código |
| T-10 | a Série A 2025 calculada dá Flamengo campeão com 79 pontos, como no campeonato real | conferência do domínio contra o dado real |
| T-18 | 21 identificadores barrados pela guarda de glossário: `_COM_JOGO`, `ano_explicito`, `test_..._fora_da_raiz`, `ROUND_HALF_UP` | `make guardas` |
| T-19 | `urlopen(requisicao, 60.0)` passava o tempo limite como **corpo** da requisição; o fake do teste aceitava, o código real quebraria | `mypy --strict` |

Sobre as guardas: parte dos 21 nomes era erro de verdade (`_COM_JOGO` falava de "jogo" onde o
glossário diz `partida`). Outra parte era falso positivo: `fora` no sentido de "do lado de fora",
`ano` como ano de calendário, `round` dentro de `ROUND_HALF_UP`. O agente renomeou o código e não
mexeu no glossário, porque mudar a lista de sinônimos é decisão de spec. Fica a sugestão para o
próximo gate: `fora` e `ano` geram falso positivo demais, que é exatamente o risco que o
`examples/README.md` descreve.

**Uma mudança de rumo no meio da etapa.** Depois da T-19, o dev perguntou se não dava para
"somente usar o MCP do minilake e enviar o job e executar". O MCP estava desligado no minilake,
e o dev o ligou. Como isso alterava o design aprovado, o agente registrou a ADR-008 antes de
seguir:

- o código vai para o volume como arquivos `.py`, porque o `upload_file` do MCP só aceita texto
  e o zip da ADR-005 não passa por ele;
- a fonte (540 KB) e o código sobem com `make enviar`, por `curl` na mesma Files API, para que
  os bytes não passem pelo contexto do agente;
- catálogo, Job, execução e conferência por SQL são feitos pelo MCP;
- a T-21 foi reescrita, e o cliente HTTP da T-19 fica só para o `make e2e`, que precisa rodar
  sem o agente.

**Onde parou.** Com o MCP o agente criou o catálogo `futebol`, os schemas `bronze`, `silver` e
`gold`, o `job.py` no Workspace e o Job `futebol-pipeline`. A primeira execução não saiu do
lugar. O minilake recriado para ligar o MCP sobe **sem o socket do Docker e sem o volume
`minilake_data`**, e sem o socket ele não consegue criar o container Spark que executa cada
tarefa: `DockerException: Error while fetching server API version`. A execução ficou presa em
`RUNNING` em vez de terminar `FAILED`, o que parece um bug do próprio minilake, e foi cancelada.

---

## Etapa 5 — Troca de plataforma: de Databricks emulado para AWS Glue

**O dev pediu:** "mude as skills e claude para não usar o minilake e sim o ministack (...)
preciso que essa pipeline execute no ministack como um aws glue". Logo depois: "use iceberg".

Essa é a mudança que mais testa a base, porque troca o alvo inteiro de execução. O que ela
mostrou, primeiro:

| Camada | Mudou? |
| --- | --- |
| `requirements.md` | não: nenhum requisito falava de tecnologia |
| `domain/` e `application/` | não: nenhuma linha |
| portas | não |
| adaptadores, entrypoint, publicação | sim: tudo |

É a promessa da arquitetura hexagonal cumprida na prática. O desenvolvedor troca de Databricks
para AWS sem reabrir um requisito nem reescrever uma regra de negócio.

**Antes de escrever, sondar.** A primeira coisa que o agente fez não foi editar arquivo. Ele
leu o código do ministack e rodou seis jobs Glue de sonda, cada um respondendo a uma pergunta.
Cada resposta errada teria virado um bug descoberto só no fim:

| Sonda | Pergunta | O que o ministack respondeu |
| --- | --- | --- |
| 1 | o job roda? | rodou, falhou com `GlueArgumentError: --JOB_NAME`, e mesmo assim terminou `SUCCEEDED` |
| 2 | sem `JOB_NAME`, o Iceberg funciona? | o `spark_catalog` da imagem tentou falar com a AWS real |
| 3 | e com um catálogo `GlueCatalog` próprio? | `NoSuchMethodError`: dois AWS SDK v2 no classpath |
| 4 | e com os jars do Iceberg na frente? | o `GlueCatalog` do Iceberg 1.0 não aceita endpoint: AWS real de novo |
| 5 | e pelo REST do Iceberg que o ministack implementa? | cria a tabela, mas o commit quebra: o ministack não grava `snapshot-log` |
| 6 | e com catálogo `hadoop` no S3 + registro no Glue via boto3? | funcionou: `overwritePartitions()` correto e tabela `ICEBERG` no Glue Data Catalog |

Uma sétima consulta testou o Athena: ele não lê Iceberg no ministack (lê os arquivos crus como
CSV). Por isso a conferência dos resultados virou um passo do próprio job.

**Problemas encontrados fora deste repositório**, que valem reporte:

- **Imagem Glue do OpenArchFlow:** o `entrypoint.sh` canaliza o `spark-submit` sem `pipefail`.
  Job com traceback termina `SUCCEEDED`. A correção é uma linha.
- **ministack, Iceberg REST do Glue:** o `add-snapshot` não acrescenta a entrada em
  `snapshot-log`, e todo commit do Spark falha.
- **ministack, Glue:** o script não recebe `--JOB_NAME`, que a AWS sempre passa.
- **PySpark 3.3 (o do Glue 4.0):** `DataFrameWriterV2.overwrite(condition)` repassa a `Column`
  do Python ao JVM sem converter. O adaptador entrega `coluna._jc`.

**O que mudou no template**, para o próximo projeto já nascer certo:

| Arquivo | Mudança |
| --- | --- |
| `.claude/steering/tech.md` | runtime Glue 4.0 (Spark 3.3, Python 3.10, Iceberg 1.0); infraestrutura ministack |
| `.claude/steering/convencoes-spark.md` | reescrito: a configuração do Iceberg que funciona e o porquê de cada peça |
| `.claude/skills/minilake-spark` → `glue-ministack` | ciclo completo de um job e tabela de diagnóstico com os erros reais das sondas |
| agentes, comandos e demais skills | referências trocadas de minilake/Delta para ministack/Iceberg |
| `.claude/projeto.toml` | `[dados]` com `prefixo`, `bucket` e `warehouse` no lugar de catálogo e `/data/` |
| guardas de pre-commit | `spark-delta-config` → `glue-sessao`; `minilake-sql-dialect` → `athena-sql-dialect`; `hexagonal-imports` agora barra `awsglue` e `boto3` |
| `Makefile`, `pyproject.toml`, `.mcp.json` | `make up` sobe o ministack; PySpark 3.3.0; sem o MCP do minilake |

**Na spec**, a troca virou a ADR-009 no `design.md`, com as alternativas descartadas e o motivo
de cada uma: o resultado das sondas. As ADR-005, 007 e 008 ficaram marcadas como substituídas, e
as tarefas T-18 a T-22 também, sem renumerar nada. Seis tarefas novas (T-23 a T-28) entraram no
fim, cada uma em TDD como as outras. A T-25 pegou mais um caso: o PySpark 3.3 exige uma JVM até
para construir uma `AnalysisException`. A checagem de "tabela existe" passou a consultar o
catálogo, em vez de capturar a exceção.

---

## Etapa 6 — Execução: o pipeline rodando como job AWS Glue

**O dev digita:**

```bash
make up                 # na raiz: ministack com o executor de jobs Glue
cd examples/futebol
make fonte              # clone fixo do openfootball (commit 119fa17)
make publicar           # fonte, zip do pacote e script no S3; job futebol-pipeline no Glue
make executar           # bronze, silver e gold; resultado pelo marcador do log
make verificar          # totais lidos das tabelas Iceberg
make e2e                # duas execuções completas e as asserções dos requisitos
```

**A primeira execução falhou**, e o desenho previsto para isso funcionou. O ministack disse
`SUCCEEDED`, mas o script viu que faltava a linha `codigo_saida=` e acusou falha. O log mostrou o
bug do PySpark 3.3 descrito acima. Teste vermelho, correção, teste verde, nova execução.

**A segunda execução**, em 64 segundos de job:

| Camada | Resultado |
| --- | --- |
| bronze | 18 arquivos `ok`, 6.552 partidas, 0 rejeitados; 42 arquivos fora do escopo reportados como `nao_carregado` |
| silver | 6.552 partidas, 0 rejeitadas |
| gold | 340 linhas (17 temporadas × 20 clubes); Série A 2025 com 20 clubes e 38 jogos cada |

No Glue Data Catalog ficaram os bancos `futebol_bronze`, `futebol_silver` e `futebol_gold`, com
as cinco tabelas registradas como `ICEBERG`.

**O e2e** (`make e2e`, 2min27s) executa o job duas vezes e confere cada requisito mensurável:
contagem (REQ-005), escopo (REQ-010), classificação (REQ-008), relatório sem falha (REQ-009) e
os mesmos totais na segunda execução (REQ-006). 5 de 5.

---

## Etapa 7 — Uso diário: um comando para executar e ver o resultado

**O dev perguntou:** "eu consigo usando algum slash command executar o job no ministack e exibir
o resultado da pipeline?" Não havia. Depois de "sim crie todos, execute e documente tudo", o
agente criou dois comandos no template, para servirem a qualquer projeto instanciado:

| Comando | O dev vê |
| --- | --- |
| `/glue:executar examples/futebol` | o veredito, se houve publicação, uma tabela por camada (ok, falhou, fora do escopo, gravadas, rejeitadas), os totais da verificação e, em caso de falha, o traceback com a causa tirada da tabela de diagnóstico da skill `glue-ministack` |
| `/glue:verificar examples/futebol` | só os totais lidos das tabelas Iceberg, cada um ao lado do valor que a spec declara |

**A parte determinística ficou no script, não no comando.** O comando orquestra e apresenta; o
`scripts/glue.sh` faz o resto:

- `garantir` publica só quando muda a impressão digital (código, script, definição do job e
  commit da fonte). A impressão fica no S3 do próprio ministack, então um ministack recriado
  força a publicação sozinho;
- `executar` grava o log filtrado em `dist/ultima-execucao.log` e imprime só o resumo em
  markdown. O log de uma execução tem centenas de linhas de Spark; o resumo tem doze.

**Testar o roteiro antes de usar achou dois defeitos no próprio comando:**

| Defeito | Correção |
| --- | --- |
| a busca do projeto usava `*/Makefile`; no zsh, um glob sem correspondência aborta o comando inteiro, e a busca não achava nada | `find ... -exec grep -l '^executar:'` |
| a checagem do socket do Docker usava `docker ps --format {{.Mounts}}`, que trunca os caminhos | `docker inspect` com a lista de destinos das montagens |

**As duas execuções:**

| Comando | Publicou? | Tempo do job | Resultado |
| --- | --- | --- | --- |
| `/glue:executar` | sim: ainda não havia impressão digital gravada | 75 s | sucesso; 18 arquivos `ok`, 6.552 partidas em bronze e silver, 340 linhas em gold |
| `/glue:verificar` | não: "publicação em dia" | 43 s | sucesso; os oito totais batem com a T-28 |

Um detalhe do Claude Code: comando recém-criado demora a entrar na lista. Nesta sessão, a
primeira chamada falhou com `Unknown skill`; o comando apareceu instantes depois, mas carregado
na versão anterior à correção dos dois defeitos. Os passos corrigidos tinham sido conferidos à
mão logo antes, e a versão nova vale a partir da próxima sessão.

---

## O que a jornada mostra

1. **O tempo gasto antes do código foi o que mais economizou.** Olhar o dado (etapa 0) achou três
   casos que a documentação não tinha. Sondar a plataforma (etapa 5) achou cinco comportamentos
   que nenhuma documentação descrevia. Cada um teria custado uma rodada de depuração no fim.
2. **Os gates não atrasaram; eles registraram decisões.** Cada "siga" ou "sim" do desenvolvedor
   está datado na spec, com o que foi aprovado. Quem chegar daqui a seis meses sabe por que o
   Iceberg usa catálogo `hadoop`.
3. **A arquitetura pagou a troca de plataforma.** Mudar de Databricks para AWS Glue não tocou em
   uma linha de regra de negócio, e os 132 testes de domínio e aplicação seguiram valendo sem
   alteração.
4. **As guardas acham mais do que deveriam, e isso também é informação.** O glossário barrou 21
   nomes, parte com razão, parte falso positivo. Os falsos positivos são o insumo para revisar o
   glossário no próximo gate.
