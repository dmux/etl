---
name: spec-ears
description: Como escrever requisitos em EARS (Easy Approach to Requirements Syntax) com user stories e critérios de aceitação testáveis. Use ao escrever ou revisar requirements.md, ao transformar um pedido vago em requisito verificável, ou quando um critério de aceitação estiver ambíguo demais para virar teste.
---

# Requisitos em EARS

EARS existe para eliminar ambiguidade: cada requisito vira uma frase com gatilho e resposta,
diretamente traduzível em teste. Um critério que não vira teste não é critério — é desejo.

## Os cinco padrões

| Padrão | Forma | Quando usar |
|---|---|---|
| **Ubíquo** | O SISTEMA DEVE `<comportamento>` | vale sempre, sem gatilho |
| **Dirigido a evento** | QUANDO `<gatilho>` O SISTEMA DEVE `<resposta>` | reação a um acontecimento |
| **Dirigido a estado** | ENQUANTO `<estado>` O SISTEMA DEVE `<resposta>` | vale durante uma condição |
| **Opcional** | ONDE `<funcionalidade presente>` O SISTEMA DEVE `<resposta>` | comportamento condicionado a configuração |
| **Indesejado** | SE `<condição indesejada>` ENTÃO O SISTEMA DEVE `<resposta>` | erro, exceção, entrada inválida |

O padrão **SE/ENTÃO é o mais esquecido e o mais importante** num pipeline de dados: arquivo
malformado, encoding inesperado, campo ausente, registro duplicado, origem indisponível.
Requisito que só descreve o caminho feliz produz pipeline que quebra na primeira semana.

## Estrutura de requirements.md

```markdown
# Requisitos — <nome da feature>

## Contexto
<2-4 linhas: por que esta feature existe, que problema resolve>

## Fora de escopo
- <o que explicitamente NÃO será feito, para conter interpretação>

---

## REQ-001 — <título curto e afirmativo>

**User story**
Como <papel>, quero <capacidade>, para que <valor>.

**Critérios de aceitação**
1. QUANDO <gatilho> O SISTEMA DEVE <resposta observável>
2. SE <condição indesejada> ENTÃO O SISTEMA DEVE <resposta>
3. O SISTEMA DEVE <invariante>

**Notas**
<ambiguidade resolvida, decisão de escopo, ou "nenhuma">
```

## O que faz um critério ser bom

Todo critério precisa passar nestes cinco testes:

1. **Observável.** Descreve algo que se pode medir de fora. "O sistema deve ser robusto" não é
   critério. "SE o arquivo tiver linha inválida ENTÃO o sistema deve registrá-la como rejeitada
   com o motivo e continuar processando as demais" é.
2. **Um comportamento.** Um critério, uma asserção. Se tem "e" ligando duas respostas
   independentes, são dois critérios.
3. **Sem solução técnica.** Nada de Iceberg, Spark, Glue, partição. Isso é `design.md`.
   O requisito diz *o que*, o design diz *como*.
4. **Números concretos.** "Rápido" não é critério; "menos de 5 minutos para uma carga diária" é.
   Se você não sabe o número, essa é uma pergunta para o gate, não um "TBD" escondido.
5. **Falseável.** Você consegue descrever a entrada que faz esse critério falhar? Se não
   consegue, o critério é vago.

## Vocabulário

Use os termos do `.claude/steering/glossario-dados.md`. Requisito escrito com sinônimo cria
código com sinônimo. Se o conceito ainda não está no glossário, acrescente lá primeiro.

## Exemplos

Bom:

> **REQ-004 — Registro sem data utilizável é rejeitado, não descartado**
>
> 1. QUANDO um registro da origem não tiver data reconhecível O SISTEMA DEVE gravá-lo na
>    tabela de registros rejeitados, com o conteúdo original e o motivo, e seguir processando
>    os demais registros do arquivo.
> 2. SE mais de 5% dos registros de um arquivo forem rejeitados ENTÃO O SISTEMA DEVE falhar a
>    execução, sem gravar nada em bronze.
> 3. O SISTEMA DEVE reportar, ao final de cada execução, o total lido, o total gravado e o
>    total rejeitado.

Ruim, e por quê:

| Escrito | Problema |
|---|---|
| "O parser deve ser tolerante a falhas" | não observável, não falseável |
| "O sistema deve gravar em Iceberg particionado por data" | é design |
| "Deve processar rápido" | sem número |
| "Deve tratar duplicata, campo ausente e encoding inválido" | três critérios num |

## Antes de fechar a fase

- Todo requisito tem pelo menos um critério `SE ... ENTÃO` cobrindo o caminho triste?
- Todo critério consegue virar o nome de um teste?
- A seção "Fora de escopo" está preenchida? Ela é o que impede escopo de crescer sozinho.
- Sobrou algum "TBD"? Vire pergunta explícita no gate — não deixe passar disfarçado.
