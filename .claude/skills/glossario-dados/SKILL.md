---
name: glossario-dados
description: Como manter e aplicar o glossário de dados do projeto — linguagem ubíqua, nomes canônicos de coluna, grão de tabela, fórmulas de métrica e sinônimos proibidos verificados no pre-commit. Use ao nomear qualquer entidade, campo, coluna, variável, tabela ou teste, ao introduzir um conceito novo, ou ao revisar código em busca de sinônimo divergente.
---

# O glossário do projeto

O glossário deste projeto está em **dois arquivos que precisam andar juntos**:

| Arquivo | Para quem | Conteúdo |
|---|---|---|
| `.claude/steering/glossario-dados.md` | humanos e agente | entidades, grão, definições, fórmulas, convenções |
| `.claude/glossario.toml` | máquina | seção `[sinonimos]`, lida pelo guarda de pre-commit `glossario` |

**Leia o `.md` antes de nomear qualquer coisa.** Se ele ainda estiver com os placeholders do
template, avise: o projeto não definiu sua linguagem ubíqua, e nomear agora é criar dívida.

## A regra

Se um conceito não está no glossário, ele não existe ainda. Acrescente — na spec que o
introduziu, nos dois arquivos, na mesma rodada — antes de escrever a primeira linha que o usa.

Sinônimo divergente é como duas partes do time passam a calcular a mesma métrica de dois
jeitos, e ninguém descobre até os números não baterem numa reunião.

## De onde vêm os nomes

Nesta ordem de precedência:

1. **O schema que já existe.** Se a tabela de destino já está no catálogo, as colunas dela
   mandam — o código se adapta ao schema, não o contrário. Confirme antes de inventar:
   `mcp__minilake__describe_table` com o nome de três partes.
2. **O vocabulário de quem consome o dado.** O termo que a pessoa usa na pergunta dela.
3. **Só então** uma decisão sua — e ela vira ADR no `design.md` da spec.

## Ao introduzir um conceito

Um conceito só está completo quando tem as quatro coisas:

- **definição** de uma frase, dizendo o que é no mundo real (não como é calculado);
- **grão**, se for entidade — o que uma linha representa;
- **domínio de valores**, se for coluna — faixa, enumeração, ou "—";
- **significado do nulo**, se for anulável — "não se aplica", "desconhecido" e "ainda não
  aconteceu" são coisas diferentes e viram queries diferentes.

Métrica derivada precisa da **fórmula explícita e do caso de borda**. A diferença entre
devolver `0` e devolver `nulo` quando não há dado é a diferença entre uma média certa e uma
errada.

## Ao acrescentar um sinônimo proibido

Vai em `[sinonimos]` de `.claude/glossario.toml`, como `"proibido" = "canonico"`, e na tabela
de termos proibidos do `.md`. O guarda quebra identificadores por `_` e por mudança de caixa,
então `score_home` e `scoreHome` batem os dois em `score` e `home`.

Critério para entrar na lista: **dois nomes para o mesmo conceito, com dano real.** Palavra
comum do idioma sem conceito por trás só gera falso positivo — e guarda com falso positivo é
guarda que o time desativa.

## Ao revisar código

```bash
# os sinônimos configurados, aplicados ao código
python tools/precommit/guardas_spark.py --guarda glossario $(git ls-files 'src/**/*.py' 'tests/**/*.py')
```

Achou? É renomeação, não é preferência de estilo.

## Ao renomear um termo do glossário

Renomear no glossário sem renomear no código cria exatamente a divergência que o glossário
existe para evitar. Antes de mudar, levante o impacto:

```bash
rg -n '<termo antigo>' src tests specs .claude
```

E mude os três: glossário narrativo, `glossario.toml` e o código.
