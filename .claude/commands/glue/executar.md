---
description: Executa o pipeline como job AWS Glue no ministack e mostra o resultado de cada camada
argument-hint: [diretório do projeto, ex.: examples/futebol]
allowed-tools: Bash(make:*), Bash(docker ps:*), Bash(docker inspect:*), Bash(curl:*), Bash(find:*), Read, Skill
---

# Executar o pipeline no ministack — $ARGUMENTS

Publica o job se algo mudou, executa todas as camadas e mostra o resultado. Não muda código.

## Passos

1. **Projeto.** Se `$ARGUMENTS` tiver um diretório, use-o. Senão, procure quem implementa o
   contrato (alvos `executar` e `verificar` no Makefile, mais `scripts/glue.sh`):

   ```bash
   find . -maxdepth 3 -name Makefile -not -path '*/.venv/*' -exec grep -l '^executar:' {} +
   ```

   (`find`, não um glob como `*/Makefile`: no zsh, um glob sem correspondência aborta o comando.)

   Um só candidato: use-o e diga qual. Vários: pergunte qual. Nenhum: explique que o projeto
   ainda não tem job Glue e que ele nasce de uma spec (`/sdd:spec`); pare.

2. **ministack de pé?** Em paralelo:

   ```bash
   curl -sf http://localhost:4566/_ministack/health >/dev/null && echo ok
   docker ps -q --filter ancestor=ministackorg/ministack:full \
     | xargs docker inspect --format '{{.Name}}: {{range .Mounts}}{{.Destination}} {{end}}'
   ```

   (`docker inspect`, não `docker ps --format {{.Mounts}}`, que trunca os caminhos.)

   Fora do ar: diga para rodar `make up` na raiz e pare. De pé sem `/var/run/docker.sock`
   montado: avise que nenhum job vai rodar de verdade (o ministack marca a execução como
   concluída sem subir o container) e pare.

3. **Fonte.** Se `<projeto>/south-america/.git` (ou o diretório de `[fontes]` do projeto) não
   existir, rode `make -C <projeto> fonte` antes.

4. **Executar.** Um job leva de 1 a 3 minutos (imagem amd64 emulada em Mac ARM); avise antes,
   em uma linha, e rode com timeout de 15 minutos:

   ```bash
   make -C <projeto> executar
   ```

   O alvo publica só se código, script, fonte ou definição do job mudaram, executa bronze, silver,
   gold e a verificação, e imprime um resumo. O log filtrado fica em
   `<projeto>/dist/ultima-execucao.log`.

5. **Apresentar o resultado.** Mostre, nesta ordem:
   - uma frase com o veredito (`RESULTADO:` do fim da saída) e o tempo do job;
   - se houve publicação, em meia linha;
   - a tabela de camadas e a tabela da verificação, como o script imprimiu;
   - as linhas `falhou:`, se houver, com o motivo de cada uma.

   Não cole o log inteiro. O resumo é a resposta; o log é para diagnóstico.

6. **Se falhou:**
   - leia o traceback impresso; se precisar de mais contexto, leia
     `<projeto>/dist/ultima-execucao.log` com `Read`, não com `cat`;
   - carregue a skill `glue-ministack` e ache na tabela de diagnóstico a linha que bate com o
     erro; diga a causa e a correção que ela aponta;
   - arquivo `falhou` por contagem divergente não é erro de infraestrutura: é dado. Mostre o
     motivo e sugira olhar o arquivo na fonte;
   - não corrija código por conta própria. Mudança de comportamento passa pelo `/sdd:impl`.

## Lembrete

O `JobRunState` do ministack é informativo: a imagem Glue pode marcar `SUCCEEDED` um job que
falhou. O veredito vem sempre da linha `codigo_saida=` do log, que o script já interpreta.
