# Testes do Jarvis

Rodam numa cópia isolada do Jarvis: outra porta, outra pasta de dados (na pasta temporária do sistema, `jarvis_testes`), sem abrir janela e sem som. Não mexem no Jarvis que está aberto.

| Teste | O que confere | Gasta cota? |
|---|---|---|
| `teste_falas.py` | pedido dito em pedaços, "não é contigo", janela de conversa, missão redigida pelo Claude | não |
| `teste_servidor.py` | processos, pedido literal, marco, ajuste com a missão rodando, projeto, conversa numerada, agenda, etiquetas, ler entrega, abrir programa sem executar, log das ações | não (usa `falso\`, um Claude Code de mentira) |
| `teste_tela.py` | abas PROCESSOS, CONVERSAS e ENTREGAS, cartão da missão, etiquetas, Parar tudo com confirmação, clique no orbe mudo, texto sem ligação; tira fotos | não |
| `teste_visual.py` | cada cenário desenha, cada forma do Jarvis, menu Aparência com as 7 classes, escolha guardada, temas antigos, ritmo do cenário (~30 quadros/s); tira fotos | não |
| `teste_clique.py` | o mago indo aonde se clica, sem marcar texto | não |
| `teste_leads_ouvido.py` | planilha de leads e filtro de voz da transcrição | não (usa a voz do Edge para gerar as frases) |
| `teste_claude_real.py` | regras chegando inteiras, modelo certo, retomada e ajuste no meio, com o Claude Code de verdade | um pouco (Haiku) |
| `teste_plataformas.py` | simula macOS e Linux (troca `sys.platform` antes dos imports): tudo carrega, nada de `windll`/`startfile`/`creationflags` fora do Windows, Wayland desliga o controle do computador com aviso; roda também o ramo do sistema de verdade | não |
| `teste_cerebro2.py` | a personalidade com o Haiku e com o Gemma de verdade (`claude`, `local` ou os dois) | um pouco (Haiku) |

Rodar, da pasta do Jarvis: `python testes\teste_servidor.py` (macOS e Linux: `python3 testes/teste_servidor.py`; lá o Claude Code de mentira é o `falso/claude`, no Windows o `falso\claude.cmd`). Cada um termina com TUDO CERTO ou TEM FALHA.

Os testes usam um projeto e duas conversas de mentira (`_cenario.py`) e a sua `config.json`. O que eles criam (missões, planilhas, o processo de exemplo do `teste_tela.py`) fica na pasta temporária, nunca na pasta do Jarvis. `teste_leads_ouvido.py` precisa do ffmpeg e da internet (voz do Edge).
