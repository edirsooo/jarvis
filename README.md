# 🤖 Jarvis

Assistente de voz para Windows que conversa com você e põe o **Claude Code** e o **Codex** para trabalhar no seu computador.

Você fala "Jarvis, ...". Ele responde em voz alta, numa frase, abre uma missão para um dos agentes e mostra na tela, ao vivo, o que cada um está fazendo e o que ficou pronto.

![Painel do Jarvis com uma missão rodando](docs/missao-rodando.png)

- **Voz:** acorda pelo nome, transcreve no seu computador (Whisper) e fala com a voz do Edge.
- **Missões:** cada pedido vira uma missão do Claude Code ou do Codex, numa pasta própria, com as entregas (site, imagem, relatório, vídeo) abertas no painel.
- **Ajuste no meio:** "na 14, é Valinhos, não Campinas" corrige a missão enquanto ela roda.
- **Processos:** roteiros prontos para o que se repete (prospecção, site, pesquisa de mercado, programar num projeto). Dá para criar e editar os seus na tela ou por voz.
- **Projetos e conversas:** "na loja, corrige o botão" trabalha dentro da pasta do projeto; "na conversa 7, pede para continuar" retoma uma conversa do Claude Code.
- **Esfera flutuante:** com o painel minimizado, uma esfera pequena fica por cima das outras janelas mostrando o que ele está fazendo.
- **Cérebro local de reserva (opcional):** com o Ollama instalado, ele continua conversando quando a cota do Claude acaba.

![Aba de processos](docs/processos.png)

Ele usa as **suas** assinaturas (Claude e ChatGPT), pelos programas que já estão instalados e logados no seu computador. Não tem servidor nem conta do Jarvis.

## Do que precisa

| | |
|---|---|
| Windows 10 ou 11 | obrigatório |
| Python 3.10 ou mais novo ([python.org](https://www.python.org/downloads/), marcando "Add python.exe to PATH") | obrigatório |
| [Claude Code](https://claude.com/claude-code) instalado e com a sua conta | obrigatório: é quem pensa e quem faz a maior parte das missões |
| Codex (da OpenAI) instalado e com a sua conta | opcional: missões de imagem e as que você pedir com "Codex, ..." |
| Microfone | opcional: sem ele, dá para escrever os pedidos no painel |
| Placa NVIDIA | opcional: a transcrição fica mais rápida e mais precisa (ver "Transcrição na placa") |
| [Ollama](https://ollama.com) | opcional: cérebro local de reserva |
| ffmpeg | opcional: fala sem a janela aberta e processo de corte de vídeo |

## Instalar

### Pelo Claude Code ou pelo Codex (mais fácil)

Abra o Claude Code ou o Codex numa pasta onde você guarda programas e cole:

```
Instale o Jarvis deste repositório: https://github.com/edirsooo/jarvis
Clone numa pasta chamada Jarvis, leia o INSTALAR.md e siga o passo a passo de instalação. Meu nome é <seu nome>.
```

A IA clona, instala os pacotes, grava o seu nome, confere o que falta e cria o atalho na área de trabalho.

### Na mão

```
git clone https://github.com/edirsooo/jarvis.git Jarvis
```

```
cd Jarvis
```

```
python instalar.py
```

O instalador pergunta o seu nome, instala os pacotes, confere Claude Code, Codex, navegador e microfone e cria o atalho **Jarvis** na área de trabalho. Pode rodar de novo quando quiser; `python instalar.py --conferir` só mostra o que falta.

## Usar

- Abra pelo atalho **Jarvis** (ou `Jarvis.vbs`). Aparece a janela do painel e um ícone ao lado do relógio.
- Na primeira vez ele baixa o modelo de transcrição: pode levar alguns minutos até começar a ouvir. O painel mostra o microfone e o modelo de transcrição quando estiver pronto.
- Diga **"Jarvis"** e faça o pedido. Depois de cada resposta ele fica alguns segundos ouvindo sem precisar repetir o nome.
- **"Claude, ..."** manda para o Claude Code; **"Codex, ..."** manda para o Codex. Sem dizer o nome, ele escolhe.
- **"Para tudo"** interrompe as missões. **ESPAÇO** desliga e liga o microfone.
- **"Fica só pelo nome"** quando tiver mais gente na sala. **"Não é contigo"** faz ele dormir na hora.
- Também dá para escrever no campo de baixo do painel.
- Para ver erros na tela: `Abrir Jarvis (com erros na tela).bat`. Para abrir junto com o Windows: `Ligar com o Windows.bat`.
- Fechar de verdade: botão direito no ícone ao lado do relógio, "Fechar o Jarvis".

Exemplos de pedido:
- "Jarvis, faz a prospecção de academias em Londrina."
- "Cria um site de uma página para uma clínica de fisioterapia."
- "Codex, gera uma imagem de um dragão de cubos."
- "Abre o YouTube."
- "Na 3, troca o título para azul."
- "Todo dia às 8 faz o resumo do dia."

## Deixar do seu jeito

Tudo o que é seu fica em arquivos que não vão para o repositório (atualizar com `git pull` não mexe neles):

| Arquivo | Para quê |
|---|---|
| `config.json` | seu nome (`dono`), como ele chama você (`tratamento`), voz, microfone, modelos, tempo de conversa aberta. Os padrões e todas as opções estão em `config.exemplo.json` |
| `memoria\sobre_mim.md` | quem é você e como trabalha, em poucas linhas (modelo em `memoria\sobre_mim.exemplo.md`) |
| `memoria\caderno.md` | o que ele anota quando você diz "anota isso" |
| `modelos\meus\` | os seus processos (criados na aba PROCESSOS ou com "salva isso como processo"). Um seu com o mesmo nome de um que veio pronto vale por cima |
| `dados\`, `missoes\` | histórico, projetos cadastrados, planilhas de leads e as pastas das missões |

Opções úteis do `config.json`:
- `lixeira`: pasta para onde os agentes movem o que não pode ser apagado (eles nunca usam comando de apagar). Sem isso, vai para uma pasta dentro da própria missão.
- `regras_extras`: lista de regras suas que toda missão recebe.
- `pessoas_por_perto`: nomes de quem costuma estar na sala ("tô falando com a Ana" faz ele dormir).
- `whisper_dica`: nomes próprios que você fala muito, para a transcrição acertar.
- `claude_niveis` e `codex_niveis`: qual modelo ou esforço usar em missão leve, média e pesada.

A personalidade (um espírito de poucas palavras que vive no orbe) está em `personalidade.md`.

### Transcrição na placa

Sem placa NVIDIA, a transcrição usa o processador com o modelo `small`. Com placa, instale o PyTorch com CUDA (ele traz as bibliotecas que a transcrição precisa) e o Jarvis passa a usar o `large-v3-turbo` sozinho:

```
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

## Segurança e privacidade

Leia antes de usar:

- **Os agentes agem no seu computador sem pedir confirmação a cada passo.** As missões do Claude Code rodam com `--permission-mode bypassPermissions` (opção `claude_permissao` do `config.json`) e as do Codex com `workspace-write`. Eles podem criar e alterar arquivos e rodar comandos. Use numa máquina e com contas em que você aceita isso.
- As regras de toda missão proíbem apagar arquivo, enviar e-mail ou mensagem, publicar, comprar e instalar programas, e o Jarvis pede confirmação por voz antes de delegar algo assim. Isso é instrução para a IA, não uma trava técnica.
- O processo "computador" mexe no mouse e no teclado à sua vista. Levar o mouse ao canto de cima à esquerda da tela para na hora.
- O servidor só atende no próprio computador (`127.0.0.1`) e recusa pedidos vindos de outros sites abertos no navegador.
- **O que sai do computador:** o texto dos seus pedidos vai para a Anthropic e a OpenAI pelos programas deles (Claude Code e Codex), e o texto que ele fala vai para o serviço de voz do Edge (Microsoft). O áudio do microfone é transcrito no seu computador e não é enviado.
- Cada missão gasta a cota das suas assinaturas. Processo agendado também.

## Testes

A pasta `testes\` roda o Jarvis numa cópia isolada (outra porta, pasta temporária, sem som nem janela) com um Claude Code de mentira, sem gastar cota. Detalhes em `testes\LEIA-ME.md`.

```
python testes\teste_servidor.py
```

## Como é por dentro

| Arquivo | Papel |
|---|---|
| `jarvis.py` | servidor local (aiohttp) que junta tudo e serve o painel |
| `ouvido.py` | microfone, palavra de ativação e transcrição (faster-whisper) |
| `cerebro.py` | quem decide o que falar e o que delegar: Claude Code (Haiku) ou o modelo local do Ollama |
| `agentes.py` | missões: abre e acompanha o Claude Code e o Codex |
| `processos.py`, `modelos\` | roteiros prontos |
| `conversas.py` | projetos cadastrados e conversas numeradas do Claude Code |
| `voz.py` | fala (Edge TTS) |
| `janelas.py`, `mini.py` | janela do painel e esfera flutuante |
| `ferramentas\` | navegador com capturas, planilha de leads, mouse e teclado |
| `web\` | o painel (HTML, CSS e JavaScript puros) |

## Licença

MIT. Feito por [Prestes Design](https://github.com/edirsooo). "Jarvis" aqui é só o nome que o assistente atende; o projeto não tem ligação com a Marvel.
