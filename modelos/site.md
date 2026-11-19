---
nome: Site
quando: criar ou refazer um site ou uma página.
gatilhos: cria um site, faz uma página, refaz o site
agente: claude
nivel: medio
tempo_max_min: 25
parametros: endereco_atual (se for refazer um site que já existe)
entregas: site.html, antes.png, depois.png
---
Objetivo: criar ou refazer um site ou página.

1. Se for refazer um site que já existe, salve antes a captura do atual: `navegar.py captura <url> --saida entregas/antes.png --inteira`, e leia o conteúdo com `navegar.py abrir <url>`.
2. Entregue em `entregas/site.html`: arquivo único (CSS e JS dentro), responsivo, que abre direto no navegador sem servidor.
3. Use só fatos dados na missão ou lidos na fonte. Não invente depoimentos, preços nem números.
4. Texto em português do Brasil, direto, sem frases de enfeite. Um objetivo por página e um botão principal.
5. Confira no computador e no celular: `navegar.py captura entregas/site.html --saida entregas/depois.png --inteira` e `navegar.py captura entregas/site.html --saida trabalho/celular.png --celular --inteira`. Olhe as capturas e corrija o que estiver quebrado.
