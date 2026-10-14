---
description: Mostra os totais das tabelas do pipeline no ministack, sem reprocessar nada
argument-hint: [diretório do projeto, ex.: examples/futebol]
allowed-tools: Bash(make:*), Bash(curl:*), Bash(grep:*), Read, Skill
---

# Verificar o pipeline no ministack — $ARGUMENTS

Lê as tabelas Iceberg com Spark, num job Glue, e mostra os totais. Não grava nada.

Por que um job e não o Athena: o Athena do ministack não lê Iceberg (lê os arquivos crus como
CSV). A leitura certa é a do Spark, com o leitor Iceberg.

## Passos

1. **Projeto e ministack:** como nos passos 1 e 2 de `/glue:executar`.

2. **Executar** (cerca de 1 minuto; avise em uma linha):

   ```bash
   make -C <projeto> verificar
   ```

3. **Apresentar:**
   - o veredito em uma frase;
   - a tabela da verificação, como o script imprimiu;
   - ao lado de cada total, o valor esperado quando a spec o declara. Procure em
     `<projeto>/specs/*/tasks.md` e `requirements.md` (por exemplo, o total de partidas na
     tarefa de e2e) e marque o que diverge;
   - falha com `Table or view not found` significa que o pipeline ainda não rodou nesse
     ministack (ou ele foi recriado sem `S3_PERSIST=1`): sugira `/glue:executar`.

4. **Se falhou:** como no passo 6 de `/glue:executar`.
