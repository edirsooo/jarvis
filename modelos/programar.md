---
nome: Programar
quando: programar, corrigir, revisar ou continuar o desenvolvimento dentro de um projeto cadastrado (a missão trabalha na pasta do projeto).
gatilhos: corrige, implementa, continua o desenvolvimento, revisa aquela funcionalidade, arruma o bug
agente: claude
nivel: medio
tempo_max_min: 40
parametros: projeto (nome do projeto); tarefa (o que fazer)
entregas: resumo.md (o que mudou e como conferir)
---
Objetivo: fazer no projeto exatamente a tarefa pedida, do jeito que o projeto já trabalha.

1. Antes de mexer, leia o CLAUDE.md, o AGENTS.md e o LEIA-ME do projeto, se existirem.
2. Ache onde a tarefa mora no código antes de escrever. Siga o estilo, os nomes e a estrutura que já existem; não troque biblioteca nem reorganize pasta sem a tarefa pedir.
3. Faça a mudança menor que resolve. Se a tarefa for vaga ("revisa aquela funcionalidade"), use o pedido literal e as falas anteriores para descobrir qual é; se continuar ambíguo, faça só a revisão (lista do que achou) e não altere nada.
4. Rode o que o projeto tem para conferir (testes, compilação, abrir a tela). Diga o que rodou e o resultado; se não deu para conferir, diga isso.
5. Não faça commit, push, deploy nem publicação, a não ser que a tarefa peça com todas as letras.
6. Escreva `entregas\resumo.md`: o que mudou (arquivos e por quê), como conferir e o que ficou pendente. Se mexeu em tela, salve uma captura em `entregas\depois.png`.
