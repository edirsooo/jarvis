---
nome: Corte para Reels
quando: tirar de um vídeo longo um corte vertical de até 60 s, pronto para postar.
gatilhos: corte, corta um trecho, faz um reels desse vídeo
agente: claude
nivel: pesado
tempo_max_min: 40
parametros: video (caminho ou nome do vídeo); trecho (minutagem ou assunto, se ele disse)
entregas: corte.mp4, capa.png
---
Objetivo: tirar de um vídeo longo um corte vertical de até 60 s, pronto para postar.

1. Ache o vídeo de origem pelo caminho ou nome dado. Se houver mais de um candidato, use o mais recente e diga qual foi.
2. Transcreva só o necessário para escolher o trecho (faster-whisper local; o ffmpeg decodifica o áudio). Escolha um trecho que se sustente sozinho: começa com gancho, termina com ideia fechada.
3. Padrão do corte: 1080x1920, conteúdo importante longe das bordas (deixe margem para os botões do aplicativo), legenda grande e legível com sombra ou contorno, áudio em −14 LUFS, nunca deformar a proporção.
4. Monte o corte em 1080x1920. Se o original for horizontal, enquadre a pessoa sem cortar o rosto, ou use moldura; nada de vídeo pequeno entre faixas pretas.
5. Render final com o ffmpeg, um render por vez (não dispare dois ao mesmo tempo).
6. Salve em `entregas\corte.mp4` e uma capa em `entregas\capa.png` (quadro montado, não quadro solto).
7. Confira duração, resolução e loudness do arquivo final e diga os números no resumo.
