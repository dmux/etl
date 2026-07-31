# examples/

Material de referência. **Nada aqui é carregado pelo agente** — não são skills ativas, não são
steering rules. Servem para mostrar como esta base fica *depois* de instanciada num domínio real.

Copie, adapte, ou ignore.

## `futebol/`

Instância baseada nos dados do [openfootball](https://github.com/openfootball/south-america) —
resultados de futebol sul-americano em arquivos de texto — carregados para o catálogo `futebol`
do minilake.

```
futebol/
├── projeto.toml                      → .claude/projeto.toml
├── glossario.toml                    → .claude/glossario.toml
├── steering/produto.md               → .claude/steering/produto.md
├── steering/glossario-dados.md       → .claude/steering/glossario-dados.md
└── skills/openfootball-format/       → .claude/skills/
```

Os quatro primeiros são exatamente os arquivos que você precisa preencher ao instanciar o
template. Lidos lado a lado com os templates vazios, mostram o nível de detalhe esperado.

### O que cada um demonstra

**`projeto.toml`** — as decisões de configuração com o *porquê* junto: por que
`temporada`/`competicao` particionam bem e `data` não; por que o idioma dos identificadores é
português (o schema existente já é).

**`glossario.toml`** — sinônimos reais, e uma nota sobre o que deliberadamente **não** entrou na
lista. Palavra comum sem um segundo nome concorrente só gera falso positivo, e guarda com falso
positivo é guarda que o time desativa.

**`steering/produto.md`** — escopo com o "fora de escopo" preenchido de verdade, e princípios
que viram asserção testável (`# Matches N` do cabeçalho contra o total ingerido).

**`steering/glossario-dados.md`** — entidades com grão declarado, invariantes, domínio de
valores, e métricas com fórmula **e caso de borda**. O `aproveitamento` mostra por que isso
importa: `jogos = 0` resulta em nulo, não zero — é a diferença entre uma média certa e uma
errada.

**`skills/openfootball-format/`** — uma **skill de domínio**: a gramática completa de um formato
de origem, com todos os casos de borda confirmados varrendo os dados reais (horário implícito
herdado da linha anterior, data sem ano, pênaltis, prorrogação, placar ausente, marcadores
`[awarded]`, `[cancelled]`, `[postponed]`, `[abandoned]`).

É o tipo de artefato que vale a pena escrever para o **seu** formato de origem. O padrão que ela
demonstra:

- **grave o que você confirmou no dado, não o que a documentação promete** — os quatro
  marcadores acima não estavam documentados em lugar nenhum, apareceram varrendo os arquivos;
- **nomeie os casos de herança de contexto** — onde o significado de uma linha depende das
  anteriores é onde todo parser erra;
- **fixe a ordem de reconhecimento** — testar formas da mais genérica para a mais específica faz
  o parser casar errado e produzir dado inválido *sem erro nenhum*;
- **aponte a asserção que fecha o parser** — aqui, o total declarado no cabeçalho;
- **termine com a lista de casos de teste obrigatórios**, para o implementador não precisar
  redescobri-los.
