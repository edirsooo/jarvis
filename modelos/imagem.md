---
nome: Imagem
quando: gerar uma imagem (sempre pelo Codex, com a assinatura do ChatGPT).
gatilhos: gera uma imagem, cria uma arte, faz um desenho
agente: codex
nivel: medio
tempo_max_min: 10
parametros: formato = quadrada 1:1
entregas: imagem.png
---
Objetivo: gerar a imagem pedida com o gerador de imagem do próprio Codex (assinatura do ChatGPT, sem gastar crédito de outros serviços).

1. Escreva o prompt em inglês, com formato (quadrada 1:1, salvo pedido diferente), cena, roupa, luz e o texto que deve aparecer, se houver.
2. Se a imagem tiver uma pessoa real (por exemplo o próprio usuário), procure fotos de referência nos caminhos citados na missão. Sem referência, gere a cena sem rosto identificável e avise no resumo.
3. Gere a imagem e salve em `entregas/imagem.png`.
4. Abra o arquivo para conferir: proporção, texto escrito certo, mãos e rosto sem defeito. Se tiver defeito claro, gere de novo uma vez.
5. Não use serviço pago de geração de imagem.
