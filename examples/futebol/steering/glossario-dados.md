# Glossário de dados — exemplo instanciado (futebol)

> Exemplo de `.claude/steering/glossario-dados.md` preenchido. Compare com o template para ver
> o que cada seção vira num domínio real. A contraparte de máquina é
> `examples/futebol/glossario.toml`.

## De onde vêm os nomes

Do schema herdado de `futebol.brasileirao.partidas`, colunas em português. O
código se adapta ao schema, não o contrário.

---

## Entidades

### `Partida`

Um jogo entre dois clubes, em uma data, por uma competição.
**Grão:** uma linha por partida.

| Coluna | Tipo | Definição | Domínio de valores |
| --- | --- | --- | --- |
| `competicao` | STRING | Nome da competição como publicado no cabeçalho do arquivo | `Brasileiro Série A`, `Brasileiro Série B`, `Copa do Brasil` |
| `temporada` | INT | Ano da edição. Extraído do cabeçalho, **não** da data da partida | 2018–2026 |
| `rodada` | STRING | Rótulo da fase como publicado | `Matchday 1`, `Round 1`, `1° Semestre, Matchday 3` |
| `rodada_num` | INT | Número extraído de `rodada`, quando houver | ≥ 1; nulo em fase sem numeração, nunca zero |
| `data` | DATE | Data do jogo | — |
| `hora` | STRING | Horário de início, `HH:MM` local | nulo quando o arquivo não informa |
| `mandante` | STRING | Clube que joga em casa — o **primeiro** nome da linha | ver *Clube* |
| `visitante` | STRING | Clube visitante — o nome após o ` v ` | ver *Clube* |
| `gols_mandante` | INT | Gols do mandante no tempo normal, incluindo prorrogação | ≥ 0; nulo se sem placar |
| `gols_visitante` | INT | Idem, visitante | ≥ 0; nulo se sem placar |
| `gols_mandante_ht` | INT | Gols do mandante no primeiro tempo (`ht` = *half-time*) | ≥ 0; nulo quando não informado |
| `gols_visitante_ht` | INT | Idem, visitante | ≥ 0; nulo quando não informado |
| `penaltis` | STRING | Placar da disputa de pênaltis, formato `M-V` | `5-3`; nulo quando não houve |
| `status` | STRING | Situação da partida | ver *Status* |
| `arquivo` | STRING | Arquivo de origem, relativo à raiz da fonte | `brazil/2025_br1.txt` |
| `linha` | INT | Número da linha da partida no arquivo, a partir de 1. Serve para auditoria e desempate | ≥ 1 |

**Invariantes**

- `gols_*` preenchido ⟺ `status` ∈ (`realizada`, `atribuida`).
- `gols_*_ht` ≤ `gols_*` correspondente, quando ambos preenchidos.
- `mandante ≠ visitante`.

### `Status`

Os seis valores saem dos marcadores que a origem realmente usa — confirmados varrendo os
arquivos, não presumidos da documentação:

| Valor | Origem no arquivo | Placar | Conta como jogo? |
| --- | --- | --- | --- |
| `realizada` | linha com placar | preenchido | sim |
| `agendada` | linha sem placar nem marcador | nulo | não |
| `atribuida` | `[awarded]` — resultado dado por tribunal (W.O.) | preenchido | sim |
| `adiada` | `[postponed]` | nulo | não |
| `cancelada` | `[cancelled]` | nulo | não |
| `abandonada` | `[abandoned]` | nulo | não |

### `Clube`

Uma agremiação. A origem escreve o nome de forma inconsistente entre competições: o mesmo clube
aparece como `Grêmio FBPA` no Brasileirão e `Grêmio Porto Alegre` na Copa do Brasil, e na Copa
do Brasil vem com sufixo de estado (`Vasco da Gama RJ`). Resolver essa identidade é trabalho da
camada **silver**, nunca da bronze.

| Termo | Definição |
| --- | --- |
| `clube` | Entidade canônica, com nome normalizado |
| `nome_bruto` | Nome exatamente como veio do arquivo, preservado para auditoria |
| `uf` | Sigla do estado, quando o arquivo traz |

### `Rejeitado`

Uma linha, partida ou arquivo que o pipeline não aceitou, guardado com o motivo para que nada
desapareça em silêncio. Existe uma tabela por camada: em bronze, o que não parseou; em silver, o
que violou invariante ou era duplicata.

| Coluna | Tipo | Definição |
| --- | --- | --- |
| `arquivo` | STRING | Arquivo de origem |
| `linha` | INT | Linha no arquivo; nula quando o arquivo inteiro foi rejeitado |
| `texto` | STRING | Conteúdo original, sem alteração |
| `motivo` | STRING | Por que foi rejeitado, em uma frase |

---

## Métricas derivadas

Camada **gold**. Grão da classificação: uma linha por clube por temporada por competição.

| Métrica | Coluna | Fórmula | Caso de borda |
| --- | --- | --- | --- |
| Vitórias | `vitorias` | partidas contadas em `jogos` em que o clube marcou mais gols | — |
| Empates | `empates` | partidas contadas em `jogos` com gols iguais | — |
| Derrotas | `derrotas` | partidas contadas em `jogos` em que o clube marcou menos gols | — |
| Pontos | `pontos` | `3 × vitorias + empates` | — |
| Jogos | `jogos` | contagem de partidas com `status` ∈ (`realizada`, `atribuida`) | — |
| Gols pró | `gols_pro` | gols marcados, somando mando e visita | — |
| Gols contra | `gols_contra` | gols sofridos | — |
| Saldo de gols | `saldo_gols` | `gols_pro − gols_contra` | pode ser negativo |
| Aproveitamento | `aproveitamento` | `pontos / (jogos × 3)`, 4 casas decimais | **`jogos = 0` ⇒ nulo, nunca zero** |

O caso de borda do aproveitamento é a diferença entre uma média certa e uma errada: um clube com
zero jogos disputados não tem 0% de aproveitamento, tem aproveitamento indefinido.

---

## Convenções de nomenclatura

- **Mandante sempre antes de visitante** — em nome de coluna, ordem de parâmetro, ordem de
  exibição e ordem de assert. `gols_mandante, gols_visitante`, nunca o inverso.
- **`_ht` significa primeiro tempo** (*half-time*). Não use `_1t`, `_primeiro_tempo`,
  `_halftime`.
- **`gols_*` é tempo normal mais prorrogação.** Pênaltis nunca entram na contagem de gols —
  moram só em `penaltis`.
- **Nulo em `gols_*` significa "não aconteceu"**, não "zero a zero". `0-0` é um placar válido e
  registrado.

---

## Termos proibidos

Em sincronia com `[sinonimos]` de `examples/futebol/glossario.toml`:

| Não use | Use | Por quê |
| --- | --- | --- |
| `home`/`away`, `casa`/`fora` | `mandante` / `visitante` | mesmo conceito, três grafias |
| `time`, `equipe`, `team` | `clube` | mesmo conceito |
| `ano`, `year`, `season` | `temporada` | `ano` confunde com o ano da `data` |
| `jogo`, `match`, `game` | `partida` | mesmo conceito |
| `placar_casa`, `score_home`, `gols_casa` | `gols_mandante` | mesmo conceito |
| `campeonato`, `torneio` | `competicao` | mesmo conceito |
| `round`, `fase` | `rodada` | mesmo conceito |
| `pens`, `penais` | `penaltis` | mesmo conceito |

`jogos` no plural é exceção legítima: é o nome da coluna de contagem na classificação.
