# Produto

> **Este arquivo é um template.** Ele descreve *o que* o projeto entrega, e é a primeira coisa
> a preencher ao instanciar esta base. Enquanto estiver com os placeholders `<...>`, o agente
> deve avisar que o produto não foi definido e oferecer rodar `/sdd:steering produto`.

## O que é

<Uma a três frases: que dado entra, que dado sai, para que serve. Concreto, sem adjetivo.>

## Para quem

<Quem consome o resultado e que pergunta essa pessoa quer responder. Se não há consumidor
identificado, o pipeline não tem requisito — tem palpite.>

## Arquitetura de dados: medalhão

As camadas estão declaradas em `.claude/projeto.toml`, seção `[dados] camadas`. O papel de cada
uma é fixo, independente do domínio:

| Camada | Papel | Regra |
|---|---|---|
| **bronze** | espelho fiel da origem, sem interpretação além do parsing | nunca descarta registro; o que não parseia vira registro rejeitado com o motivo |
| **silver** | limpo, tipado, entidades resolvidas e deduplicadas | grão declarado e estável; sem duplicata |
| **gold** | agregados prontos para consumo | derivada apenas de silver, nunca de bronze |

Cada camada é um banco do Glue Data Catalog, `<[dados] prefixo>_<camada>`. Uma camada só lê da camada
imediatamente anterior — nunca pula, nunca lê de si mesma.

## Escopo

Dentro:

- <fonte, período, entidade que serão processados>

Fora, por decisão explícita:

- <o que a base de dados até permitiria, mas não será feito>
- <e por quê, em meia linha — é isso que impede o escopo de crescer sozinho>

## Princípios do produto

Estes valem para qualquer domínio e não são negociáveis:

- **O dado de origem é imutável.** Os diretórios listados em `[fontes] somente_leitura` são
  protegidos por hook. Toda correção acontece na transformação, nunca na fonte — senão o
  pipeline diverge da origem e a próxima sincronização apaga a mudança em silêncio.
- **Reprocessar é o caso normal, não a exceção.** Rodar de novo sobre a mesma janela de dados
  produz o mesmo resultado (idempotência), não duplica. Toda tabela declara sua chave de
  idempotência no `design.md`.
- **Perda de dado é bug.** Registro que o pipeline não entende não pode desaparecer em
  silêncio: vira registro rejeitado, com o conteúdo original e o motivo, visível e contável.
  Um pipeline que "funcionou" descartando 3% das linhas é um pipeline quebrado.
- **Contagem confere.** Sempre que a origem declara ou permite derivar um total, o pipeline
  compara e falha na divergência. É a asserção mais barata e a que mais pega erro real.
