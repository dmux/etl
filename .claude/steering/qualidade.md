# Qualidade

## O gate

`make check` precisa passar antes de qualquer commit ser considerado pronto:

```
ruff check      → zero violação
ruff format     → zero diferença
mypy --strict   → zero erro
pytest --cov    → cobertura ≥ 95%
```

Nenhum desses números é negociável no meio da tarefa. Se a cobertura caiu abaixo de 95%, ou
faltam testes ou sobra código não usado — nas duas hipóteses o problema é o código, não o gate.

## Como se chega a 95% num projeto Spark

A resposta é arquitetural, não de esforço: **a complexidade mora no domínio, que é Python
puro.** Parsing, regras de negócio, validação e derivações são funções puras, testadas em
milissegundos sem JVM. O adaptador Spark fica fino o bastante para ser coberto com
`unittest.mock` verificando as chamadas ao builder e ao writer.

Se para testar uma regra você precisou de uma `SparkSession`, a regra está na camada errada.

## Testes

- **TDD.** Teste vermelho primeiro, implementação depois, refatoração por último. O agente
  `spec-implementador` trabalha nessa ordem e mostra o teste falhando antes de implementar.
- Todo teste declara no docstring o requisito que cobre: `"""REQ-003: ..."""`.
- Nome do teste descreve o comportamento, não o método:
  `test_registro_sem_data_vira_rejeitado`, não `test_parse_1`.
- Um `assert` conceitual por teste. Se precisa de cinco asserts sem relação, são cinco testes.
- Fake em memória > mock, quando a porta permite. Mock só para o que é caro ou externo
  (SparkSession, chamada HTTP ao minilake).
- Casos de borda são obrigatórios, não bônus: entrada vazia, campo ausente, valor fora de
  domínio, arquivo malformado, encoding.

## Clean code

- Função faz uma coisa. Limite prático: **20 linhas**. Passou disso, extraia.
- Complexidade ciclomática **≤ 8** (o ruff falha acima disso via `C90`).
- No máximo **4 parâmetros**. Mais que isso, agrupe num objeto de domínio.
- Sem flag booleana de parâmetro que muda o comportamento da função — são duas funções.
- Nome revela intenção. Se precisou de comentário para explicar *o que* faz, renomeie.
  Comentário serve para explicar *por quê*, e aí é bem-vindo.
- Sem abreviação inventada: escreva o termo por extenso, como está no glossário.
- `if/else` aninhado além de dois níveis: inverta a condição e retorne cedo.
- Erro nunca é engolido. Ou trata, ou propaga com contexto. `except: pass` é proibido.
- Tipagem completa em toda função pública — `mypy --strict` cobra isso de qualquer forma.

## DRY, com juízo

Duplicação de **conhecimento** é dívida: uma regra de negócio escrita em dois lugares vai
divergir. Duplicação de **forma** — dois trechos que se parecem hoje por coincidência — não é.

A regra prática: extraia na terceira ocorrência, não na segunda. Abstração criada cedo demais
custa mais caro que a duplicação que ela evitou. E antes de escrever qualquer função nova,
procure: `grep` no `src/` pelo conceito. Reaproveitar o que existe vem antes de criar.

## O que nunca entra

- `print()` em `src/` — use `logging`. Em job Spark, stdout é canal de saída do job.
- `.collect()`, `.toPandas()` ou `.count()` fora de `infrastructure/` e testes — traz o dado
  todo para o driver e o OOM aparece só em produção.
- `select("*")` numa transformação — quebra o contrato de schema silenciosamente.
- `except Exception: pass`.
- `# type: ignore` sem código do erro e sem comentário justificando.
- Credencial, token ou caminho absoluto de máquina no código.
- Dependência nova sem ADR na spec.

Cada item dessa lista tem um hook de pre-commit correspondente. Eles existem porque cada um
desses erros já custou caro em algum pipeline.
