# Instruções para a IA que vai instalar ou mexer no Jarvis

(O nome é INSTALAR.md, e não AGENTS.md ou CLAUDE.md, de propósito: um arquivo com esses nomes na raiz seria lido por todas as missões que o Jarvis abre.)

Este arquivo é para o Claude Code, o Codex ou outro agente de programação. Se uma pessoa pediu para você instalar o Jarvis, siga a parte 1. Se pediu para alterar o código, leia a parte 2.

## 1. Instalar no computador da pessoa

O Jarvis funciona no **Windows** (10 e 11), no **macOS** (12 ou mais novo) e no **Linux** com área de trabalho. Trabalhe em português do Brasil e fale com a pessoa de forma simples: ela pode não ser programadora. Nos passos abaixo, `python` é `python3` no macOS e no Linux, e as barras de caminho são `/` (no Windows, `\`).

1. **Onde:** clone numa pasta chamada `Jarvis`, num lugar que a pessoa escolher (se ela não disser, use a pasta atual). Se você já está dentro do repositório clonado, não clone de novo.
   `git clone https://github.com/edirsooo/jarvis.git Jarvis`
2. **Python:** confira com `python --version` (`python3 --version`). Precisa ser 3.10 ou mais novo. Se não houver Python, diga à pessoa como instalar e pare até ela confirmar: instalar programa é decisão dela.
   - Windows: python.org, marcando "Add python.exe to PATH".
   - macOS: python.org (já traz o Tk, que a esfera flutuante usa) ou `brew install python python-tk`.
   - Linux: o Python do sistema serve; se o pip recusar com "externally-managed-environment", crie um ambiente na pasta: `python3 -m venv .venv` e rode tudo com `.venv/bin/python` (os lançadores `jarvis.sh` e `Jarvis.command` já usam o `.venv` se ele existir).
3. **Nome:** pergunte como o Jarvis deve chamá-la, se ela ainda não disse.
4. **Instalar:** dentro da pasta, rode `python instalar.py --dono "<nome>"`. Ele instala os pacotes do `requirements.txt` com o pip, cria o `config.json`, confere o que falta e cria o atalho. A primeira instalação baixa algumas centenas de megabytes de pacotes: avise antes.
   - **macOS:** se faltar PortAudio, ffmpeg ou o Tk, ele mostra o comando do Homebrew (`brew install ...`) e, num terminal, pergunta antes de rodar; rodando sem terminal interativo (o seu caso, IA), só mostra: passe para a pessoa. O atalho é um `Jarvis.command` na área de trabalho.
   - **Linux:** ele confere PortAudio, `python3-tk`, ffmpeg, xdg-utils, wmctrl e xdotool e, se faltar algum, mostra o comando do apt/dnf/pacman/zypper e pergunta antes de rodar com `sudo`. Rodando sem terminal interativo (o seu caso, IA), ele só mostra o comando: passe para a pessoa rodar, porque pede a senha dela. O atalho entra no menu de aplicativos (`~/.local/share/applications/jarvis.desktop`; há um modelo em `jarvis.desktop.exemplo`).
5. **Leia a saída.** Cada linha começa com `[OK]`, `[AVISO]` (opcional, só informe) ou `[FALTA]` (precisa resolver):
   - **Claude Code faltando:** é obrigatório. Passe o link https://claude.com/claude-code, peça para a pessoa instalar e entrar na conta dela, e rode o instalador de novo. Você não entra em conta nem digita senha por ela.
   - **Codex, Ollama, ffmpeg faltando:** são opcionais. Explique em uma linha o que cada um acrescenta e siga.
   - **Navegador:** no Windows, Edge ou Chrome é obrigatório. No macOS e no Linux, sem Chrome/Edge/Chromium o painel abre no navegador padrão (sem janela própria) e o instalador baixa o Chromium do Playwright para as missões.
   - **Wayland (Linux):** é só um aviso. Painel, voz e missões funcionam; as missões que veem a tela e mexem no mouse ficam desligadas. Para elas, a pessoa entra numa sessão X11 (Xorg).
6. **Conferir sem gastar cota:** rode `python testes/teste_servidor.py` (no Windows, `python testes\teste_servidor.py`). Tem de terminar com `TUDO CERTO`. Ele usa um Claude Code de mentira numa pasta temporária e não abre janela nem toca som. `python testes/teste_plataformas.py` confere em segundos que os caminhos do sistema carregam.
7. **Entregar:** diga para a pessoa abrir e falar "Jarvis":
   - Windows: atalho **Jarvis** da área de trabalho (ou `Jarvis.vbs`).
   - macOS: dois cliques em `Jarvis.command`. Na primeira vez o macOS pede o **Microfone**; para missões que mexem no computador, ela precisa liberar **Gravação de Tela** e **Acessibilidade** para o Terminal (ou o Python) em Ajustes do Sistema > Privacidade e Segurança. Se o macOS bloquear o `.command` por ser baixado da internet, botão direito > Abrir.
   - Linux: "Jarvis" no menu de aplicativos, ou `./jarvis.sh` na pasta.
   Avise que na primeira abertura ele baixa o modelo de transcrição de voz e pode levar alguns minutos para começar a ouvir. Não abra o Jarvis você mesmo sem ela pedir: ele liga o microfone e fala em voz alta.
8. **Avise sobre a segurança**, em poucas linhas, com o que está na seção "Segurança e privacidade" do `README.md`: as missões agem no computador sem pedir confirmação a cada passo e gastam a cota das assinaturas dela.

Opcionais que você pode oferecer depois, um por vez e só se ela quiser:
- `memoria/sobre_mim.md`: algumas linhas sobre quem ela é e como trabalha (modelo em `memoria/sobre_mim.exemplo.md`).
- Transcrição na placa NVIDIA (Windows e Linux): `pip install torch --index-url https://download.pytorch.org/whl/cu128` (download grande). No macOS não há CUDA: fica no processador.
- Cérebro local de reserva: instalar o Ollama e baixar o modelo indicado em `cerebro_reserva.modelo` do `config.exemplo.json`.
- Abrir junto com o sistema: no Windows, `Ligar com o Windows.bat`; no macOS e no Linux, `python3 instalar.py --ligar-com-o-sistema` (desliga com `--desligar-com-o-sistema`).

Não faça por conta própria: mudar `claude_permissao`, instalar programas fora do pip (no Linux, o comando do `sudo` é a pessoa quem roda), mexer em arquivos fora da pasta do Jarvis.

### O que muda em cada sistema

| Recurso | Windows | macOS | Linux |
|---|---|---|---|
| Voz, missões, painel, processos, atualização | sim | sim | sim |
| Janela própria do painel | Edge/Chrome | Chrome/Edge/Chromium (senão, navegador padrão) | Chrome/Chromium/Edge (senão, navegador padrão) |
| Trazer o painel para a frente / minimizar | sim | com permissão de Automação | com `wmctrl` ou `xdotool` |
| Esfera flutuante | transparente | transparente | em quadrado escuro; sem tela gráfica, desligada |
| Ícone de bandeja | ao lado do relógio | barra de menus | área de notificação (GNOME: extensão AppIndicator) |
| Missões que mexem no computador | sim | `pyautogui` + `mss` + Gravação de Tela + Acessibilidade | X11 com `pyautogui`, `mss`, `xdotool`, `wmctrl`; Wayland: desligadas com aviso |
| Acender a tela nas palmas | sim | `caffeinate` | `xset` (X11) |
| Transcrição na placa | NVIDIA | não (processador) | NVIDIA com CUDA |

## 2. Mexer no código

- Tudo em português do Brasil: nomes, comentários, mensagens.
- **O que é da pessoa fica fora do repositório:** `config.json`, `dados/`, `missoes/`, `memoria/`, `modelos/meus/`. Não escreva nome de pessoa, caminho de pasta pessoal nem chave no código: o nome vem de `configuracao.dono(cfg)`, as regras pessoais de `regras_extras` e os padrões novos entram no `config.exemplo.json`.
- Nos textos que vão para as IAs, `{dono}` e `{tratamento}` (em `personalidade.md`) e `{dono}` e `{pasta_jarvis}` (nos roteiros de `modelos/`) são trocados na hora.
- **Três sistemas:** o que muda entre Windows, macOS e Linux fica em `plataforma.py` (abrir arquivo, revelar na pasta, navegador, opções de processo, pastas de dados, acender a tela). Não chame `os.startfile`, `ctypes.windll`, `creationflags`, `taskkill` ou `explorer` direto em código novo: use `plataforma` ou ponha o ramo do Windows atrás de `plataforma.WIN`/`sys.platform == "win32"`. Recurso sem equivalente simples num sistema é desligado com aviso no log, nunca derruba o Jarvis. Programas externos abrem por `configuracao.abrir_programa` e fecham por `configuracao.encerrar` (no Windows, `taskkill /T`; nos outros, o grupo de processos inteiro).
- **Nunca passe texto com quebra de linha como opção de linha de comando** para o `claude` ou o `codex`: no Windows eles são arquivos `.cmd` e a linha é cortada na primeira quebra. Regras e prompts vão em arquivo (`--append-system-prompt-file`) ou pela entrada padrão.
- Os agentes das missões nunca usam comando de apagar; mantenha isso nas regras de `agentes.py`.
- O servidor só atende em `127.0.0.1` e recusa pedidos com `Origin` de outro site (`so_local` em `jarvis.py`). Não afrouxe isso.
- **Teste antes de entregar:** `python testes/teste_falas.py`, `python testes/teste_servidor.py`, `python testes/teste_tela.py`, `python testes/teste_clique.py` e `python testes/teste_plataformas.py` (simula macOS e Linux). Rodam numa cópia isolada (`JARVIS_TESTE`, `JARVIS_PORTA`) e não mexem no Jarvis aberto. Detalhes em `testes/LEIA-ME.md`.
- Depois de mudar o Python, o Jarvis aberto precisa ser reiniciado para valer (fechar pelo ícone da bandeja e abrir de novo). Não reinicie com missão trabalhando.
