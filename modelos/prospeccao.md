---
nome: Prospecção
quando: achar negócios de um nicho numa cidade, conferir quem tem site, Instagram e outros canais, escolher o melhor alvo, refazer o site e deixar o e-mail de abordagem em rascunho. Também serve para "continua a prospecção" e "próxima empresa" (segue de onde parou, sem repetir empresa).
gatilhos: prospecção, prospectar, achar clientes, negócios sem site, próxima empresa, continua a prospecção
agente: claude
nivel: pesado
tempo_max_min: 30
parametros: nicho (tipo de negócio, ex.: academias); cidade (com o estado, ex.: Valinhos, SP); nota_minima = 4,5 (nota mínima no Google); quantos_alvos = 1 (quantas empresas ganham site e e-mail nesta rodada); etapa = tudo (tudo, levantar ou proxima)
entregas: relatorio.md, leads.csv, antes.png, site.html, depois.png, email.md
---
Objetivo: prospectar {nicho} em {cidade}. A planilha de leads guarda tudo entre uma missão e outra, então nenhuma empresa é vista duas vezes.

Ferramentas (caminho completo nas regras acima): `navegar.py` (Google Maps, abrir site, capturas) e `leads.py` (a planilha). Leia `leads.py ajuda` antes de começar.

Etapa 1 — Levantar (se etapa = proxima e a planilha já tiver empresas, pule para a Etapa 3)
1. `navegar.py maps "{nicho} em {cidade}" --max 25 > trabalho\maps.json`
2. `leads.py juntar "{nicho}" "{cidade}" trabalho\maps.json` (empresa que já estava na planilha não entra de novo).
3. Marco: `MARCO: Achei N {nicho} em {cidade}.`
Se etapa = levantar, pare aqui: vá para a Etapa 4.

Etapa 2 — Analisar as empresas novas
4. `leads.py proximo "{nicho}" "{cidade}" --n 12`. Para cada uma, confira os canais e anote com `leads.py marcar ... --situacao ...`:
   - nota abaixo de {nota_minima}, fechada ou fora do nicho: `descartado`, com o motivo em `--obs`.
   - sem site próprio (só Instagram, Facebook, Linktree, WhatsApp ou nada): `sem_site`. Anote o Instagram em `--instagram` quando achar.
   - com site: abra com `navegar.py abrir <url>` (no máximo 8 sites por rodada; cada um vira uma captura na tela) e avalie em uma linha (`--obs`): visual, leitura no celular, clareza da oferta, botão de contato. Site fraco: `site_fraco`. Site bom: `site_bom`.
5. Marco: `MARCO: X sem site e Y com site fraco.`

Etapa 3 — Escolher e produzir ({quantos_alvos} empresa(s) nesta rodada)
6. Escolha entre as `sem_site` e `site_fraco` que ainda não viraram `site_feito`: melhor nota, mais avaliações, mais chance de fechar. Explique a escolha em duas frases no relatório.
7. Se ela tem site, salve o atual: `navegar.py captura <url> --saida entregas\antes.png --inteira`.
8. Faça o site novo em `entregas\site.html`: arquivo único, responsivo, com os dados reais do negócio (nome, serviços, endereço, telefone, horário e avaliações que você leu). Não invente depoimentos, preços, registros profissionais nem números. Fotos do original só por endereço (sem baixar), ou blocos de cor no lugar.
9. `navegar.py captura entregas\site.html --saida entregas\depois.png --inteira`.
10. `entregas\email.md`: assunto e corpo curtos, tom de quem quer ajudar, sem pressão de venda, convidando a ver a prévia. É rascunho: não envie nada.
11. `leads.py marcar "{nicho}" "{cidade}" "<empresa>" --situacao email_pronto --missao <número desta missão, se souber>`.
12. Com mais de um alvo, o primeiro fica na raiz de `entregas\` e os outros em `entregas\<nome-curto>\` (site.html, depois.png, email.md).
13. Marco: `MARCO: Site e e-mail prontos para <empresa>.`

Etapa 4 — Fechar
14. `leads.py copiar "{nicho}" "{cidade}" --saida entregas\leads.csv`.
15. `entregas\relatorio.md`: tabela das empresas vistas (nome, nota, avaliações, site, Instagram, situação, observação em uma linha), o alvo escolhido e por quê, e a fila das próximas.
16. No resumo final diga: quantas empresas a planilha tem, qual foi o alvo e quantas ainda estão na fila. Se sobrou fila, termine com: "Diga 'próxima' para eu seguir."
