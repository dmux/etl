# Produto — exemplo instanciado (futebol)

> Exemplo de `.claude/steering/produto.md` preenchido. Compare com o template para ver o que
> cada placeholder vira num domínio real.

## O que é

Um pipeline que transforma os resultados de futebol sul-americano publicados pelo projeto
[openfootball](https://github.com/openfootball/south-america) — arquivos de texto pensados para
leitura humana — em tabelas Iceberg, escritas por um job AWS Glue e registradas no Glue Data
Catalog.

## Para quem

Analistas e curiosos que querem responder perguntas sobre futebol brasileiro sem parsear texto:
aproveitamento como mandante, evolução de um clube entre temporadas, frequência de decisões por
pênaltis na Copa do Brasil.

## Arquitetura de dados: medalhão

| Camada | Papel neste projeto |
|---|---|
| **bronze** | uma linha por partida, exatamente como o arquivo diz; o que não parseia vira registro rejeitado |
| **silver** | clubes deduplicados (`Grêmio FBPA` e `Grêmio Porto Alegre` viram o mesmo), datas completas, tipos corretos |
| **gold** | classificação por temporada, desempenho como mandante, séries históricas |

Um banco do Glue Data Catalog por camada: `futebol_bronze`, `futebol_silver`, `futebol_gold`.

## Escopo

Dentro:

- Brasileirão Série A e B (2018 em diante) e Copa do Brasil.
- Ingestão incremental por arquivo de temporada.
- Tabelas de partidas e classificação.

Fora, por decisão explícita:

- Demais países do repositório upstream (Argentina, Colômbia, Equador, Paraguai) e
  Libertadores/Sudamericana — o parser lida com eles, mas não são carregados. Ampliar é mudar
  uma lista de arquivos, não o código.
- Escalações, gols por jogador, cartões, arbitragem, público — a origem não tem esses dados.
- Previsão, modelo estatístico, qualquer ML.
- Interface de usuário. O consumo é por SQL.

## Princípios do produto

- **O dado de origem é imutável.** `south-america/` é um clone upstream, atualizado
  semanalmente. Toda correção acontece na transformação — editar a fonte seria apagado pelo
  próximo `git pull`.
- **Reprocessar é o caso normal.** O upstream muda toda semana; rodar de novo sobre a mesma
  temporada produz o mesmo resultado, não duplica.
- **Perda de dado é bug.** Partida que o parser não entende vira registro rejeitado, visível e
  contável — nunca desaparece em silêncio.
- **Contagem confere.** Cada arquivo declara `# Matches N` no cabeçalho. O total ingerido tem
  que bater com esse número. É a asserção mais barata deste domínio e a que mais pega erro real.
