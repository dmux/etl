# Requisitos — pipeline de partidas

## Contexto

Os resultados do futebol brasileiro publicados pelo openfootball são texto pensado para leitura
humana: o significado de uma linha depende das anteriores, e o mesmo campo tem nove formas de
escrita. Esta feature transforma esses arquivos em partidas consultáveis e numa classificação por
temporada, sem perder nenhuma linha em silêncio.

Fonte analisada: `openfootball/south-america`, commit `119fa17` (2026-09-21), diretório `brazil/`.

## Fora de escopo

- Unificar o mesmo clube escrito de formas diferentes entre competições (`Grêmio FBPA` no
  Brasileirão, `Grêmio Porto Alegre` na Copa do Brasil). Exige uma tabela de-para curada; fica
  para uma spec própria.
- Arquivos fora de `brazil/` (Argentina, Colômbia, Equador, Paraguai, Libertadores,
  Sul-Americana).
- Classificação da Copa do Brasil: é mata-mata, não tem tabela de pontos.
- Escalações, gols por jogador, cartões, público: a origem não tem esses dados.
- Agendamento de execução. O pipeline roda quando alguém o chama.

---

## REQ-001 — Toda linha de partida vira uma partida

**User story**
Como analista, quero cada linha de partida dos arquivos como uma partida com competição,
temporada, rodada, data, hora, mandante e visitante, para consultar resultados sem ler texto.

**Critérios de aceitação**
1. QUANDO um arquivo for processado O SISTEMA DEVE produzir uma partida para cada linha que
   contenha o separador ` v ` entre dois nomes de clube.
2. O SISTEMA DEVE preencher `competicao` e `temporada` a partir da linha de cabeçalho `=`, e nunca
   a partir da data da partida.
3. QUANDO uma linha de partida não trouxer horário O SISTEMA DEVE atribuir a `hora` da última
   linha de partida que trouxe horário dentro da mesma data.
4. SE nenhuma partida anterior da mesma data trouxer horário ENTÃO O SISTEMA DEVE gravar `hora`
   nula, e nunca herdar o horário de outra data.
5. QUANDO uma linha de data não trouxer ano O SISTEMA DEVE usar o ano da última data completa do
   arquivo.
6. O SISTEMA DEVE atribuir a cada partida o rótulo `▪` vigente como `rodada`, e o número extraído
   do rótulo como `rodada_num`.
7. SE o rótulo da rodada não contiver número ENTÃO O SISTEMA DEVE gravar `rodada_num` nulo, e
   nunca zero.
8. O SISTEMA DEVE preservar o nome do clube exatamente como escrito no arquivo, incluindo acento e
   sufixo de UF.

**Notas**
Confirmado no dado: datas fora de ordem cronológica existem (`2020_br1.txt` lista `Thu Jan 28
2021` antes de `Wed Dec 2 2020`, por jogo adiado). Por isso o ano herdado é o da última data
completa, não inferido pelo mês. Também confirmado: 36 partidas (27 em `2025_br2.txt`, 9 em
`2026_br1.txt`) abrem uma data sem horário, por isso o critério 4.

---

## REQ-002 — Cada forma de resultado é interpretada sem ambiguidade

**User story**
Como analista, quero o placar do jogo separado do placar dos pênaltis e do primeiro tempo, para
que nenhuma disputa de pênaltis seja contada como gols.

**Critérios de aceitação**
1. QUANDO o resultado for `N-N (N-N)` O SISTEMA DEVE gravar o primeiro par em `gols_*` e o segundo
   em `gols_*_ht`.
2. QUANDO o resultado for `N-N` sem parênteses O SISTEMA DEVE gravar `gols_*` e deixar `gols_*_ht`
   nulos.
3. QUANDO o resultado contiver `pen.` seguido de dois placares entre parênteses O SISTEMA DEVE
   gravar o par antes de `pen.` em `penaltis`, o primeiro par dos parênteses em `gols_*` e o
   segundo em `gols_*_ht`.
4. QUANDO o resultado contiver `pen.` seguido de um único placar entre parênteses O SISTEMA DEVE
   gravar esse placar em `gols_*` e deixar `gols_*_ht` nulos.
5. O SISTEMA DEVE ignorar o placar marcado com `a.e.t.` para fins de `gols_*`, usando sempre o
   placar entre parênteses.
6. O SISTEMA DEVE manter `penaltis` nulo em toda partida cujo resultado não contenha `pen.`.

**Notas**
Ocorrências no dado: 12 `N-N pen. (N-N, N-N)`, 6 `N-N pen. (N-N)`, 2 `N-N pen. N-N a.e.t.
(N-N, N-N)` e 2 `N-N pen. N-N a.e.t. (N-N)`, todas em `2025_brcup.txt`. Os critérios 4 e 5 são
decisões tomadas no gate de 2026-10-13.

---

## REQ-003 — Status da partida vem dos marcadores da origem

**User story**
Como analista, quero saber se uma partida foi realizada, está agendada ou foi adiada, para não
confundir jogo que não aconteceu com 0 a 0.

**Critérios de aceitação**
1. QUANDO a linha tiver placar e nenhum marcador O SISTEMA DEVE gravar `status = 'realizada'`.
2. QUANDO a linha não tiver placar nem marcador O SISTEMA DEVE gravar `status = 'agendada'` com
   `gols_*` nulos.
3. QUANDO a linha tiver placar seguido de `[awarded]` O SISTEMA DEVE gravar `status = 'atribuida'`
   com o placar informado.
4. QUANDO a linha tiver `[postponed]`, `[cancelled]` ou `[abandoned]` O SISTEMA DEVE gravar
   `status` como `adiada`, `cancelada` ou `abandonada`, respectivamente, com `gols_*` nulos.

**Notas**
No dado atual: 1 `[awarded]`, 1 `[postponed]` e 425 partidas agendadas: 102 em `2026_br1.txt`
(temporada em andamento) e 323 em `2025_br2.txt`, temporada já encerrada que a origem deixou de
atualizar. A classificação da Série B 2025 sai, portanto, parcial. *Nota corrigida na
implementação (T-05): a versão aprovada dizia só 102, porque a varredura inicial olhou um
arquivo só.* `[cancelled]` e `[abandoned]` não aparecem em `brazil/`, mas estão na skill do
formato e entram nos testes.

---

## REQ-004 — Linha não reconhecida vira registro rejeitado

**User story**
Como responsável pelo pipeline, quero ver toda linha que o sistema não entendeu, para que
nenhuma partida desapareça em silêncio.

**Critérios de aceitação**
1. SE uma linha de partida não casar com nenhuma forma de resultado conhecida ENTÃO O SISTEMA DEVE
   gravá-la como registro rejeitado com o arquivo, o número da linha, o texto original e o motivo.
2. SE uma linha for rejeitada ENTÃO O SISTEMA DEVE continuar processando as linhas seguintes do
   mesmo arquivo.
3. SE uma linha de partida aparecer antes de qualquer linha de data ENTÃO O SISTEMA DEVE
   rejeitá-la com o motivo `partida sem data`.
4. SE o arquivo não puder ser lido como UTF-8 ENTÃO O SISTEMA DEVE rejeitar o arquivo inteiro com o
   motivo, e seguir para o próximo arquivo.

**Notas**
nenhuma

---

## REQ-005 — Contagem de cada arquivo confere com o cabeçalho

**User story**
Como responsável pelo pipeline, quero que o total lido de cada arquivo seja comparado com o total
que o próprio arquivo declara, para detectar linha perdida.

**Critérios de aceitação**
1. QUANDO um arquivo terminar de ser processado O SISTEMA DEVE comparar partidas mais rejeitados
   com o `N` de `# Matches N` do cabeçalho.
2. SE a soma divergir de `N` ENTÃO O SISTEMA DEVE falhar a execução daquele arquivo, sem gravar
   nenhuma partida dele.
3. SE o arquivo não declarar `# Matches` ENTÃO O SISTEMA DEVE falhar a execução daquele arquivo com
   o motivo `contagem não declarada`.

**Notas**
No commit analisado, as 18 contagens conferem com o número de linhas ` v ` (380 por arquivo de
Série A ou B, 92 na Copa do Brasil 2025).

---

## REQ-006 — Reprocessar não duplica

**User story**
Como responsável pelo pipeline, quero rodar de novo sobre os mesmos arquivos sem gerar
duplicatas, porque a origem muda toda semana e reprocessar é o caso normal.

**Critérios de aceitação**
1. QUANDO o mesmo arquivo for processado duas vezes O SISTEMA DEVE terminar com o mesmo número de
   partidas que após a primeira execução.
2. QUANDO um arquivo for reprocessado após mudar na origem O SISTEMA DEVE substituir todas as
   partidas anteriores daquele arquivo pelas novas.
3. O SISTEMA DEVE manter intactas as partidas de arquivos que não foram reprocessados.

**Notas**
nenhuma

---

## REQ-007 — Partida que viola invariante não chega à camada consumível

**User story**
Como analista, quero que as partidas que eu consulto respeitem as regras do glossário, para
confiar em qualquer soma que eu fizer.

**Critérios de aceitação**
1. SE `mandante` for igual a `visitante` ENTÃO O SISTEMA DEVE rejeitar a partida com o motivo.
2. SE `gols_mandante_ht` for maior que `gols_mandante`, ou `gols_visitante_ht` maior que
   `gols_visitante`, ENTÃO O SISTEMA DEVE rejeitar a partida com o motivo.
3. SE `gols_*` estiver preenchido e `status` não for `realizada` nem `atribuida` ENTÃO O SISTEMA
   DEVE rejeitar a partida com o motivo.
4. SE a mesma partida (competição, temporada, mandante, visitante e data) aparecer mais de uma vez
   ENTÃO O SISTEMA DEVE manter uma única ocorrência e registrar as demais como rejeitadas.

**Notas**
Na camada bronze nada é descartado: estas regras valem na passagem para a camada consumível.

---

## REQ-008 — Classificação por temporada nos campeonatos de pontos corridos

**User story**
Como analista, quero a classificação de cada clube por temporada da Série A e da Série B, para
comparar desempenho sem recalcular pontos à mão.

**Critérios de aceitação**
1. O SISTEMA DEVE produzir uma linha por clube, temporada e competição para `Brasileiro Série A` e
   `Brasileiro Série B`.
2. O SISTEMA DEVE contar em `jogos` apenas partidas com `status` `realizada` ou `atribuida`.
3. O SISTEMA DEVE calcular `pontos` como `3 × vitorias + empates`.
4. O SISTEMA DEVE calcular `saldo_gols` como `gols_pro − gols_contra`.
5. O SISTEMA DEVE calcular `aproveitamento` como `pontos / (jogos × 3)`, com 4 casas decimais.
6. SE um clube tiver `jogos = 0` na temporada ENTÃO O SISTEMA DEVE gravar `aproveitamento` nulo,
   e nunca zero.
7. O SISTEMA DEVE incluir na classificação todo clube que aparece em ao menos uma partida da
   temporada, inclusive os que só têm partidas agendadas.

**Notas**
Temporada em andamento (2026) produz classificação parcial. Ordem e critérios de desempate não
fazem parte deste requisito: a tabela entrega as métricas e quem consulta ordena.

---

## REQ-009 — Cada execução presta contas do que fez

**User story**
Como responsável pelo pipeline, quero um resumo ao final de cada execução, para saber sem
consultar tabelas se algo foi perdido.

**Critérios de aceitação**
1. QUANDO uma execução terminar O SISTEMA DEVE reportar, por arquivo, o total declarado, o total de
   partidas gravadas e o total de rejeitados.
2. SE algum arquivo tiver falhado ENTÃO O SISTEMA DEVE terminar a execução com código de saída
   diferente de zero.

**Notas**
nenhuma

---

## REQ-010 — Só os arquivos do escopo são carregados

**User story**
Como responsável pelo pipeline, quero que só os arquivos combinados sejam carregados, para que
ampliar o escopo seja uma decisão e não um acidente.

**Critérios de aceitação**
1. O SISTEMA DEVE carregar os arquivos de `brazil/` de Série A, Série B e Copa do Brasil a partir
   da temporada 2018.
2. SE um arquivo fora dessa lista for passado ao pipeline ENTÃO O SISTEMA DEVE ignorá-lo e
   reportá-lo como fora de escopo.
3. O SISTEMA DEVE ler a origem sem nunca alterar seus arquivos.

**Notas**
São 18 arquivos no commit analisado: Série A 2018–2026, Série B 2018–2025, Copa do Brasil 2025.

---

## Decisões do gate — 2026-10-13

Aprovado pelo usuário, com as quatro propostas abaixo aceitas como estavam:

1. **`pen. (N-N)` com um placar só:** o placar entre parênteses é o do jogo; `gols_*_ht` fica
   nulo (REQ-002.4). A skill `openfootball-format` foi corrigida na mesma rodada.
2. **`a.e.t.` com o placar dos pênaltis:** ignorado; vale o placar entre parênteses (REQ-002.5).
3. **Unificação de clubes:** fora desta spec, confirmado.
4. **Contagem divergente:** falha só o arquivo; os demais são gravados e a execução termina com
   erro (REQ-005.2, REQ-009.2).
