# Glossário de dados

> **Este arquivo é um template.** É a linguagem ubíqua do projeto: todo nome de entidade,
> campo, coluna, variável, função e teste sai daqui. Enquanto estiver vazio, o agente deve
> avisar antes de nomear conceitos de domínio, e oferecer rodar `/sdd:steering glossario-dados`.
>
> A contraparte legível por máquina é `.claude/glossario.toml` — o guarda de pre-commit
> `glossario` lê a seção `[sinonimos]` de lá. **As duas precisam andar juntas:** conceito novo
> entra nos dois arquivos, na mesma rodada.

## A regra

Se um conceito não está aqui, ele não existe ainda. Acrescente — na spec que o introduziu —
antes de escrever a primeira linha que o usa.

Isso não é preciosismo. Sinônimo divergente é como duas partes do time passam a calcular a
mesma métrica de dois jeitos, e ninguém descobre até os números não baterem numa reunião.

## De onde vêm os nomes

Nesta ordem de precedência:

1. **O schema que já existe.** Se a tabela de destino já está no catálogo, os nomes de coluna
   dela mandam. O código se adapta ao schema, não o contrário. Confirme com
   `mcp__minilake__describe_table` antes de inventar nome.
2. **O vocabulário de quem usa o dado.** O termo que o consumidor usa na pergunta dele.
3. **Só então**, uma decisão sua — que vira ADR na spec.

O idioma dos identificadores está em `.claude/projeto.toml`, `[idioma] codigo`. A regra: siga o
idioma do schema que você já tem. Traduzir cria um dicionário a mais para manter errado.

---

## Entidades

> Uma seção por entidade. O grão é obrigatório: sem ele, ninguém sabe o que uma linha
> representa, e agregação errada vira métrica errada.

### `<Entidade>`

<Uma frase: o que é, no mundo real.>
**Grão:** uma linha por `<o quê>`.

| Coluna | Tipo | Definição | Domínio de valores |
|---|---|---|---|
| `<coluna>` | `<TIPO>` | <o que significa, não como é calculado> | <valores válidos, ou faixa, ou "—"> |

**Invariantes**
- <regra que sempre vale sobre esta entidade — vira teste e vira constraint>

---

## Métricas derivadas

> Toda métrica calculada mora aqui, **com a fórmula**. Métrica sem fórmula escrita é métrica
> que será recalculada diferente na próxima query.

| Métrica | Coluna | Fórmula | Caso de borda |
|---|---|---|---|
| `<nome>` | `<coluna>` | `<expressão explícita>` | <divisão por zero, conjunto vazio, nulo> |

O caso de borda não é opcional: a diferença entre uma métrica que devolve `0` e uma que devolve
`nulo` quando não há dado é a diferença entre uma média certa e uma errada.

---

## Convenções de nomenclatura

> Registre aqui as convenções que valem em todo o projeto, para não serem redecididas a cada
> arquivo. Exemplos do tipo de regra que pertence a esta seção:

- **Ordem fixa de pares.** Quando duas colunas formam um par (origem/destino, antes/depois),
  fixe a ordem e use sempre a mesma em nome, parâmetro, exibição e assert.
- **Sufixos com significado único.** Um sufixo (`_id`, `_dt`, `_pct`) significa uma coisa só,
  no projeto inteiro.
- **Sem abreviação inventada.** Escreva o termo por extenso.
- **Nulo tem significado declarado.** Para cada coluna anulável, diga o que o nulo quer dizer:
  "não se aplica", "desconhecido" ou "ainda não aconteceu" são coisas diferentes.

---

## Vocabulário de processo

Estes termos são do framework e valem em qualquer domínio:

| Termo | Definição |
|---|---|
| **bronze** | Espelho da origem, sem interpretação além do parsing |
| **silver** | Limpo, tipado, entidades resolvidas, sem duplicata |
| **gold** | Agregado pronto para consumo |
| **registro rejeitado** | Registro que o pipeline não entendeu. Preservado com o conteúdo original e o motivo — perda silenciosa é bug |
| **ingestão** | Ler a origem e materializar em bronze |
| **idempotência** | Reprocessar a mesma janela produz o mesmo resultado, sem duplicar |
| **grão** | O que uma linha da tabela representa |
| **chave de idempotência** | O conjunto de colunas que identifica o que será substituído no reprocessamento |

---

## Termos proibidos

> Sinônimos que aparecem naturalmente e criam divergência. Mantenha esta tabela em sincronia
> com `[sinonimos]` em `.claude/glossario.toml` — é a tabela que o pre-commit verifica.

| Não use | Use | Por quê |
|---|---|---|
| `<termo>` | `<canônico>` | <o conceito é o mesmo> |

Liste apenas sinônimo que causa dano real: dois nomes para o **mesmo** conceito. Palavra comum
do idioma sem conceito por trás só gera falso positivo, e guarda com falso positivo é guarda
que o time desativa.
