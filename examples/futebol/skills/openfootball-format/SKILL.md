---
name: openfootball-format
description: Gramática completa do formato de texto do openfootball em south-america/ e todos os casos de borda confirmados nos dados — horário herdado, data sem ano, pênaltis, prorrogação, placar ausente, marcadores [awarded]/[cancelled]/[postponed]/[abandoned], rótulos de rodada e sufixos de estado. Use ao escrever ou revisar qualquer parser dos arquivos .txt, ao especificar requisitos de ingestão, ou ao investigar linha que não parseou.
---

# O formato openfootball

Os arquivos em `south-america/` são texto pensado para leitura humana, não para máquina. A
consequência prática: o significado de uma linha **depende das linhas anteriores**. Um parser
que trata linha por linha isoladamente vai errar em pelo menos três lugares.

Os casos abaixo foram confirmados varrendo os arquivos reais, não deduzidos da documentação.

## Estrutura do arquivo

```
= Brasileiro Série A 2025                      ← cabeçalho: competição + temporada

# Date       Sat Mar 29 - Sun Dec 7 2025       ← metadados, começam com #
# Teams      20
# Matches    380

▪ Matchday 1                                   ← rodada
  Sat Mar 29 2025                              ← data completa
    18:30  São Paulo FC   v SC Recife    0-0   ← partida
           Cruzeiro EC    v Mirassol FC  2-1 (2-1)
  Thu Apr 3                                    ← data SEM ano
    21:30  Grêmio FBPA    v CA Mineiro   1-1 (0-1)
```

Cinco tipos de linha, distinguidos pelo primeiro caractere não-branco:

| Início | Tipo | Regra |
|---|---|---|
| `=` | cabeçalho | `= <competicao> <temporada>` — a temporada sai daqui, **nunca** da data da partida |
| `#` | metadado | comentário. `# Matches N` é útil para conferir a contagem final |
| `▪` | rodada | rótulo da fase |
| dígito ou letra | data ou partida | ver abaixo |
| vazio | separador | ignore |

## Os três casos de herança de contexto

Aqui mora quase todo bug de parser deste formato.

### 1. Horário implícito

Só a primeira partida de um mesmo horário traz o horário. As seguintes começam direto no nome
do mandante e **herdam o horário da linha anterior**:

```
    18:30  São Paulo FC   v SC Recife     0-0        ← 18:30
           Cruzeiro EC    v Mirassol FC   2-1 (2-1)  ← também 18:30
           Grêmio FBPA    v CA Mineiro    2-1 (2-0)  ← também 18:30
    21:30  Fortaleza EC   v Fluminense FC 2-0 (2-0)  ← 21:30
```

### 2. Data sem ano

A primeira data de um bloco traz o ano; as seguintes frequentemente não. O ano é herdado da
última data completa:

```
  Wed Jan 28 2026     ← ano explícito
    ...
  Thu Jan 29          ← herda 2026
```

Cuidado com a virada de ano: uma temporada pode cruzar dezembro/janeiro. O ano herdado é o da
última data completa, e ele muda quando aparece uma data completa nova — não infira por
proximidade de mês.

### 3. Rodada vigente

O rótulo `▪` vale para todas as partidas até o próximo `▪`. Formatos confirmados:

| Rótulo | `rodada_num` |
|---|---|
| `▪ Matchday 1` | 1 |
| `▪ Round 1` | 1 |
| `▪ 1° Semestre, Matchday 3` | 3 |
| `▪ Fase Campeón, Gruppe 2` | nulo |
| `▪ Copa Sud, Final` | nulo |

`rodada` guarda o rótulo inteiro como veio; `rodada_num` é o número extraído, quando houver.
Fase sem numeração ⇒ `rodada_num` nulo, nunca zero.

## Anatomia da linha de partida

```
    18:30  São Paulo FC            v SC Recife                0-0 (0-0)
    └─┬─┘  └────────┬─────────┘    │ └───────┬────────┘       └────┬───┘
    hora        mandante           v     visitante              resultado
   (opcional)                  separador
```

O separador é ` v ` isolado por espaços. Nomes de clube contêm espaços e acento
(`Águia de Marabá PA`, `SC Corinthians Paulista`), então **não faça split por espaço** —
localize o ` v ` e corte ali. Na Copa do Brasil o nome vem com sufixo de UF
(`Vasco da Gama RJ`); na Libertadores, com código de país entre parênteses
(`Club The Strongest (BOL)`).

## Formas do resultado

Todas confirmadas nos dados:

| Forma | Significado | Campos |
|---|---|---|
| `2-1 (2-0)` | placar final e do primeiro tempo | `gols_*` = 2,1 · `gols_*_ht` = 2,0 |
| `0-0` | placar final, sem primeiro tempo informado | `gols_*` = 0,0 · `gols_*_ht` nulos |
| *(ausente)* | partida ainda não realizada | todos nulos · `status = 'agendada'` |
| `5-3 pen. (1-1, 0-1)` | decidida nos pênaltis | `penaltis` = `5-3` · `gols_*` = 1,1 · `gols_*_ht` = 0,1 |
| `1-4 pen. 1-4 a.e.t. (1-1, 0-0)` | prorrogação e pênaltis | `penaltis` = `1-4` · `gols_*` = 1,1 · `gols_*_ht` = 0,0 |
| `3-0 [awarded]` | resultado atribuído (W.O.) | `gols_*` = 3,0 · `status = 'atribuida'` |
| `[postponed]` | adiada | placares nulos · `status = 'adiada'` |
| `[cancelled]` | cancelada | placares nulos · `status = 'cancelada'` |
| `[abandoned]` | abandonada | placares nulos · `status = 'abandonada'` |

Duas armadilhas nessa tabela:

1. **Com pênaltis, o primeiro placar da linha é o dos pênaltis, não o do jogo.** Em
   `5-3 pen. (1-1, 0-1)`, o jogo terminou 1-1; `5-3` é a disputa. Ler `5-3` como gols é o erro
   mais caro possível aqui.
2. **Quando há parênteses com dois placares separados por vírgula, o primeiro é o tempo normal
   e o segundo é o primeiro tempo** — nessa ordem. Com um placar só entre parênteses, ele é o
   primeiro tempo.

O sufixo `a.e.t.` (*after extra time*) indica prorrogação. Os `gols_*` já incluem a prorrogação;
não existe campo separado para ela.

## Ordem de reconhecimento

Testar as formas na ordem errada faz `5-3 pen. (1-1, 0-1)` casar com o padrão simples e produzir
dado errado sem erro nenhum. A ordem correta é da mais específica para a mais genérica:

1. marcador `[...]` isolado → status especial, sem placar
2. `N-N pen. N-N a.e.t. (N-N, N-N)` → pênaltis com prorrogação
3. `N-N pen. (...)` → pênaltis
4. `N-N [awarded]` → resultado atribuído
5. `N-N (N-N)` → final e primeiro tempo
6. `N-N` → só final
7. nada → agendada

## Contagem: a verificação que fecha o parser

O cabeçalho declara `# Matches N`. Ao final da ingestão, o total de partidas parseadas do
arquivo tem que bater com esse N. Não bateu ⇒ há linha silenciosamente perdida. Essa é a
melhor asserção de teste disponível para este formato, e vale para cada arquivo.

## Regras de parsing

- **Nunca descarte linha em silêncio.** O que não casar com nenhuma forma vira registro
  rejeitado, com o texto original e o motivo. Perda silenciosa é bug.
- Encoding é **UTF-8**; os nomes têm acento e caractere especial (`▪`, `°`).
- Preserve o nome do clube exatamente como veio, em `nome_bruto`. Normalização de identidade é
  trabalho da camada silver, nunca da bronze.
- O parser é função **pura**, em `domain/parser.py`: texto entra, `list[Partida]` sai. Sem
  Spark, sem I/O — é o que sustenta a meta de 95% de cobertura.
- Nomes de campo vêm do glossário do projeto.

## Casos de teste obrigatórios

Todo parser deste formato precisa cobrir, no mínimo: horário herdado por três partidas
seguidas · data sem ano · virada de ano dentro da temporada · `0-0` sem primeiro tempo ·
partida sem placar · pênaltis sem prorrogação · pênaltis com `a.e.t.` · cada um dos quatro
marcadores `[...]` · `▪ Fase, Matchday N` composto · rodada sem número · clube com sufixo de UF ·
clube com acento · arquivo vazio · linha truncada no meio · conferência do `# Matches N`.
