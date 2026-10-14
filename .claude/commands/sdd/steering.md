---
description: Revisa e atualiza as Steering Rules do projeto
argument-hint: [arquivo específico, ex: glossario-dados]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Steering Rules — $ARGUMENTS

Revisa as regras que governam todo o desenvolvimento deste repositório.

## As regras

| Arquivo | Papel | Carga |
|---|---|---|
| `.claude/steering/sdd.md` | o processo e os gates | sempre |
| `.claude/steering/produto.md` | o que é, para quem, camadas, escopo | sempre |
| `.claude/steering/tech.md` | stack fechada e comandos | sempre |
| `.claude/steering/estrutura.md` | layout hexagonal e regra de dependência | sempre |
| `.claude/steering/qualidade.md` | gate, clean code, DRY, proibições | sempre |
| `.claude/steering/convencoes-spark.md` | Glue 4.0, ministack, Iceberg | skill `glue-ministack` |
| `.claude/steering/glossario-dados.md` | linguagem ubíqua e nomes de coluna | skill `glossario-dados` |

As cinco primeiras são importadas pelo `CLAUDE.md` e ficam sempre em contexto — por isso
precisam ser enxutas. As duas últimas são grandes e carregam sob demanda.

## Passos

1. Sem argumento, mostre a tabela acima com a data da última modificação de cada arquivo e
   pergunte qual revisar.

2. Leia o arquivo escolhido inteiro antes de propor qualquer mudança.

3. **Verifique a regra contra a realidade.** Steering desatualizada é pior que ausente, porque
   é obedecida. Conferências úteis:
   - `tech.md`: as versões batem com `pyproject.toml`?
   - `glossario-dados.md`: os nomes de coluna batem com o schema real das tabelas
     (`aws glue get-table` no ministack)? Os domínios de valor batem com o dado real? A tabela
     de termos proibidos está em sincronia com `[sinonimos]` de `.claude/glossario.toml`?
   - `convencoes-spark.md`: bate com o que um job de sonda no ministack confirma?
   - `estrutura.md`: o layout descrito bate com `src/`?
   - `produto.md` e `glossario-dados.md`: ainda têm placeholders `<...>` do template?

4. Proponha as mudanças, uma a uma, com o motivo. Mudança em steering afeta todo o
   desenvolvimento futuro — não é edição de rotina.

5. Se a mudança for no glossário e um termo já estiver em uso no código, aponte os arquivos
   afetados:

   ```bash
   rg -n '<termo antigo>' src tests specs
   ```

   Renomear o glossário sem renomear o código cria exatamente a divergência que o glossário
   existe para evitar.

## Ao acrescentar uma regra nova

- Ela pertence a qual arquivo? Regra em dois lugares diverge.
- É "sempre" ou "sob demanda"? Sempre custa contexto em toda sessão — só entra se valer para
  praticamente todo trabalho.
- Dá para verificar automaticamente? Se sim, ela merece também um hook de pre-commit em
  `tools/precommit/`. Regra que só existe no texto é regra que será esquecida.
