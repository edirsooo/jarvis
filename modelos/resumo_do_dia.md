---
nome: Resumo do dia
quando: resumo do que está em andamento (o que as missões entregaram, o que ficou pendente nos projetos e o que vem primeiro hoje).
gatilhos: resumo do dia, resumo da manhã, o que ficou pendente, por onde eu começo
agente: claude
nivel: leve
tempo_max_min: 8
entregas: resumo.md
---
Objetivo: um resumo curto para {dono} começar o dia sabendo onde está cada coisa.

1. Leia `{pasta_jarvis}/dados/missoes.json` (missões das últimas 24 h: o que concluiu, o que deu erro, o que ficou parado).
2. Leia `{pasta_jarvis}/dados/projetos.json` (os projetos cadastrados). Em cada pasta que existir, veja o que mudou nos últimos 3 dias (histórico do git ou arquivos recentes) e se há anotação de pendência (LEIA-ME, TODO, notas).
3. Escreva `entregas/resumo.md`: "Ficou pronto", "Pendente" e "Primeiro hoje" (até 3 itens em cada). Sem inventar: o que não está registrado, não entra.
4. O resumo falado tem 2 frases: o que ficou pronto e a primeira coisa de hoje.
