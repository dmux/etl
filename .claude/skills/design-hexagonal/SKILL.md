---
name: design-hexagonal
description: Como derivar portas, adaptadores e ADRs a partir dos requisitos, mantendo o domínio livre de framework. Use ao escrever ou revisar design.md, ao decidir em que camada um comportamento mora, ao criar uma porta nova, ou quando estiver tentado a importar pyspark fora de infrastructure.
---

# Design hexagonal

O objetivo prático da hexagonal aqui é um só: **conseguir testar a lógica que importa sem subir
uma JVM**. Toda decisão de camada se resolve com essa pergunta — "para testar isto, preciso de
Spark?" Se a resposta é sim e não deveria ser, a lógica está na camada errada.

## Em que camada isto mora?

| A operação... | Camada | Testada com |
|---|---|---|
| interpreta texto, calcula, valida, decide | `domain/` | nada além de pytest |
| orquestra domínio + portas, sem saber quem implementa | `application/` | fakes em memória |
| fala com Spark, Iceberg, S3, Glue, filesystem, HTTP | `infrastructure/` | mock ou ministack real |
| lê argumento de linha de comando e monta o wiring | `cli/` | e2e |

Regra de bolso: se o código menciona um nome de tecnologia, é infraestrutura. Se menciona um
nome do glossário, é domínio.

## Portas

Uma porta é um `Protocol` em `application/portas.py`, tipado **em termos do domínio**:

```python
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from <pacote>.domain.modelos import Registro


@runtime_checkable
class EscritorTabelaPort(Protocol):
    """Persiste registros num destino. Não sabe se é Iceberg, parquet ou memória."""

    def escrever(self, registros: Sequence[Registro], destino: str) -> int:
        """Retorna quantos registros foram gravados."""
        ...
```

O que uma porta nunca faz:

- Aparecer `DataFrame`, `SparkSession`, `Row` ou qualquer tipo de framework na assinatura. Se
  aparece, o domínio passou a depender do Spark por via indireta.
- Vazar detalhe do adaptador no nome — `EscritorTabelaPort`, não `EscritorIcebergPort`.
- Existir com um único adaptador. Toda porta tem o real e o fake de teste. Se você só consegue
  imaginar um adaptador, provavelmente é uma função de domínio, não uma porta.

## Estrutura de design.md

```markdown
# Design — <nome da feature>

## Visão geral
<como a feature funciona, em 5-10 linhas>

## Fluxo de dados
<diagrama em texto: origem → domínio → porta → adaptador → destino>

## Modelos de domínio
<dataclasses frozen, com campos e invariantes>

## Portas
| Porta | Método | Contrato | Adaptadores |
|---|---|---|---|

## Adaptadores
<um bloco por adaptador: responsabilidade, dependências, o que pode falhar>

## Schema das tabelas
<colunas, tipos, particionamento, tabela no catálogo, chave de idempotência>

## Tratamento de erro
<o que é fatal, o que vira registro rejeitado, o que é log e segue>
<para cada REQ do tipo SE/ENTÃO, onde ele é tratado>

## Decisões (ADR)
### ADR-001 — <título>
**Contexto** · **Decisão** · **Alternativas descartadas** · **Consequências** · **Atende** REQ-###

## Rastreabilidade
| REQ | Onde é atendido |
|---|---|
```

## ADRs

Registre decisão que alguém questionaria em seis meses. Sempre com as alternativas descartadas
e o motivo — sem isso a ADR não impede a discussão de voltar.

Merece ADR: escolha de particionamento, estratégia de idempotência, o que fazer com linha
inválida, dependência nova, decisão que afeta o schema público.

Não merece: nome de variável, ordem de parâmetro, qualquer coisa já decidida na steering.

## Erros comuns

| Sintoma | Diagnóstico |
|---|---|
| a porta recebe ou devolve `DataFrame` | o domínio acabou de virar refém do Spark |
| o caso de uso instancia `EscritorIcebergSpark` direto | falta injeção; o wiring é do `cli/` |
| há regra de negócio dentro do adaptador | mova para o domínio; adaptador só traduz |
| o domínio tem `if config.modo == "spark"` | infraestrutura vazou; é escolha de adaptador |
| uma porta com um adaptador só | provavelmente era uma função |

## Antes de fechar a fase

- Todo `REQ-###` aparece na tabela de rastreabilidade?
- Todo requisito `SE ... ENTÃO` tem tratamento explícito na seção de erro?
- Toda porta tem ao menos dois adaptadores previstos, um deles fake?
- Alguma assinatura de porta menciona tipo de framework?
- O schema declara particionamento e chave de idempotência?
- Alguma decisão discutível ficou sem ADR?
