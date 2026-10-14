# Pipeline de partidas do futebol brasileiro

Exemplo instanciado da base: um pipeline real, construído do zero com o processo da raiz do
repositório e executado como **job AWS Glue 4.0** no ministack.

## Propósito

O [openfootball](https://github.com/openfootball/south-america) publica os resultados do futebol
sul-americano em arquivos de texto pensados para leitura humana. Neles, o significado de uma
linha depende das anteriores: o horário vale para as linhas seguintes até aparecer outro, datas
vêm sem ano e o placar dos pênaltis vem antes do placar do jogo. Responder a "qual foi o
aproveitamento do Flamengo em 2025?" exige parsear texto à mão.

Este pipeline transforma esses arquivos em tabelas consultáveis, sem perder nenhuma linha em
silêncio. Ele serve a dois públicos:

- **quem quer os dados:** analistas que querem consultar partidas e classificação por SQL;
- **quem quer a base:** desenvolvedores que querem ver como ela fica num domínio real, com spec,
  testes, guardas e execução de verdade.

## O que ele produz

| Camada | Tabela | Conteúdo |
| --- | --- | --- |
| bronze | `futebol_bronze.partidas` | uma linha por partida, como o arquivo diz: 6.552 partidas da Série A (2018–2026), da Série B (2018–2025) e da Copa do Brasil 2025 |
| bronze | `futebol_bronze.rejeitados` | toda linha que o parser não entendeu, com o texto original e o motivo |
| silver | `futebol_silver.partidas` | as partidas que respeitam as regras do glossário, sem duplicata |
| silver | `futebol_silver.rejeitados` | as partidas barradas, com o motivo |
| gold | `futebol_gold.classificacao` | pontos, vitórias, saldo e aproveitamento por clube, temporada e competição |

As tabelas são Iceberg, no S3 do ministack, registradas no Glue Data Catalog. As garantias vêm de
[`specs/001-pipeline-partidas/requirements.md`](specs/001-pipeline-partidas/requirements.md):

- **nenhuma linha some:** o que não é entendido vira registro rejeitado;
- **a contagem confere:** o total de cada arquivo bate com o `# Matches N` que ele declara;
- **reprocessar não duplica:** cada arquivo substitui só a sua partição.

## Como executar

Com o ministack de pé (`make up` na raiz do repositório):

```bash
make install fonte     # dependências e clone fixo do openfootball (commit 119fa17)
make check             # lint, tipos, 8 guardas e cobertura de 95% — sem Spark, sem rede
make executar          # publica se algo mudou, roda o job e mostra o resumo por camada
make verificar         # só os totais lidos das tabelas
make e2e               # duas execuções completas e as asserções dos requisitos
```

No Claude Code, o mesmo pelos comandos `/glue:executar examples/futebol` e
`/glue:verificar examples/futebol`.

## Onde está cada coisa

| Caminho | Conteúdo |
| --- | --- |
| [`PROCESSO.md`](PROCESSO.md) | a jornada do desenvolvedor: como o pipeline foi construído, etapa por etapa, com as decisões e os erros encontrados |
| [`specs/001-pipeline-partidas/`](specs/001-pipeline-partidas/) | requisitos, design (ADRs) e tarefas |
| `src/etl_futebol/domain/` | parser, regras e classificação, em Python puro |
| `src/etl_futebol/application/` | portas e casos de uso |
| `src/etl_futebol/infrastructure/` | Spark, Iceberg, S3, Glue Data Catalog |
| `glue_job.py`, `scripts/glue.sh` | o script do job e a publicação e execução no ministack |
| `projeto.toml`, `glossario.toml`, `steering/`, `skills/` | a configuração de domínio que a base pede ao ser instanciada |
