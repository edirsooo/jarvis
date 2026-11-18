---
nome: Pesquisa de mercado
quando: levantar como é um mercado local ou um nicho (quem são os concorrentes, preços públicos, presença online, o que falta) e entregar um relatório ou um comparativo.
gatilhos: pesquisa de mercado, comparativo, quem são os concorrentes, levanta o mercado
agente: claude
nivel: medio
tempo_max_min: 20
parametros: nicho; cidade; foco (o que ele quer comparar, se disse)
entregas: relatorio.md
---
Objetivo: entender o mercado de {nicho} em {cidade} e entregar um relatório que ajude {dono} a decidir o que oferecer.

1. Se já existe planilha de leads desse nicho e cidade (`leads.py lista "{nicho}" "{cidade}"`), comece por ela em vez de buscar tudo de novo. Senão, `navegar.py maps "{nicho} em {cidade}" --max 25`.
2. Para os 6 a 10 mais relevantes, levante só o que é público: nome, bairro, nota e número de avaliações, serviços, preços quando publicados, horários, site e Instagram. Abra os sites com `navegar.py abrir`.
3. Não invente número. O que não achou, escreva "não informado".
4. `entregas\relatorio.md`: resumo em 5 linhas no topo; tabela comparativa; o que os melhores fazem de diferente; lacunas (o que ninguém oferece ou comunica bem); 3 oportunidades concretas para {dono}.
5. Marco no meio: `MARCO: Levantei N concorrentes.`
