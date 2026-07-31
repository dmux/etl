---
description: Implementa UMA tarefa da spec em TDD
argument-hint: [T-NN, REQ-NNN ou vazio para a próxima pendente]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# Implementação — $ARGUMENTS

Executa **uma** tarefa do `tasks.md`, em TDD, e para.

## Pré-condição

`tasks.md` precisa existir e estar aprovado. Se não existir, **pare** e indique a fase que
falta. Este comando não improvisa implementação sem plano.

## Passos

1. Identifique a spec ativa — a que tem tarefas em aberto:

   ```bash
   rg -l '^\s*- \[ \]' specs/*/tasks.md 2>/dev/null
   ```

2. Escolha a tarefa:
   - `$ARGUMENTS` é um `T-NN` → essa tarefa;
   - é um `REQ-NNN` → a primeira tarefa pendente que atende esse requisito;
   - vazio → a primeira tarefa pendente cujas dependências estejam todas concluídas.

3. Verifique as dependências declaradas. Se alguma estiver aberta, **pare** e diga qual — não
   implemente fora de ordem.

4. Confirme com o usuário qual tarefa vai ser implementada, em uma linha. Só isso; não peça
   confirmação de detalhe de implementação.

5. Delegue ao subagente `spec-implementador`, passando o id da tarefa e o caminho da spec.

6. Quando ele voltar, apresente o relatório: requisitos atendidos, arquivos tocados, resultado
   do gate.

7. **Pare.** Não emende a próxima tarefa. Diga qual é a próxima e quantas faltam.

## Se o gate falhar

Não marque a tarefa como concluída. Mostre a saída do erro e pergunte se deve corrigir ou se o
usuário prefere olhar. Nunca reporte tarefa concluída com o gate vermelho, e nunca baixe o
`fail_under` para fechar.
