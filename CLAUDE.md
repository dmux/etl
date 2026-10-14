# Base para pipelines de dados guiados por spec

Template de projeto: Spec-Driven Development no estilo AWS Kiro, arquitetura hexagonal, jobs AWS
Glue 4.0 (PySpark + Iceberg) sobre ministack, gate de 95% de cobertura. **Agnóstico de domínio** — o que é específico
do projeto mora em `.claude/projeto.toml` e `.claude/glossario.toml`, e em nenhum outro lugar.

As regras abaixo são carregadas em toda sessão e valem para qualquer trabalho neste repositório.

@.claude/steering/sdd.md
@.claude/steering/produto.md
@.claude/steering/tech.md
@.claude/steering/estrutura.md
@.claude/steering/qualidade.md

## Configuração do projeto

| Arquivo | Contém |
| --- | --- |
| `.claude/projeto.toml` | nome do pacote, catálogo, camadas, particionamento, fontes somente-leitura, idioma |
| `.claude/glossario.toml` | sinônimos proibidos, verificados pelo pre-commit |

Ao instanciar esta base num projeto novo, edite esses dois arquivos e preencha os placeholders
`<...>` de `.claude/steering/produto.md` e `.claude/steering/glossario-dados.md`. Enquanto os
placeholders existirem, avise antes de nomear conceitos de domínio: o projeto ainda não definiu
sua linguagem ubíqua.

## Steering carregada sob demanda

Duas regras são grandes demais para ficar sempre em contexto e são carregadas pelas skills
correspondentes quando o assunto aparece:

| Arquivo | Skill que o carrega | Quando |
| --- | --- | --- |
| `.claude/steering/convencoes-spark.md` | `glue-ministack` | ao escrever qualquer PySpark, job Glue ou SQL |
| `.claude/steering/glossario-dados.md` | `glossario-dados` | ao nomear entidades, colunas ou tabelas |

Se você for escrever código Spark ou nomear um campo e essas skills não tiverem sido carregadas,
leia o arquivo diretamente antes de escrever.

## Exemplos

`examples/` guarda material de referência que **não** é carregado pelo agente: skills de domínio
já escritas, mostrando como esta base fica depois de instanciada. Use como modelo, não como
regra.
