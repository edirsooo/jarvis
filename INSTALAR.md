# Instruções para a IA que vai instalar ou mexer no Jarvis

(O nome é INSTALAR.md, e não AGENTS.md ou CLAUDE.md, de propósito: um arquivo com esses nomes na raiz seria lido por todas as missões que o Jarvis abre.)

Este arquivo é para o Claude Code, o Codex ou outro agente de programação. Se uma pessoa pediu para você instalar o Jarvis, siga a parte 1. Se pediu para alterar o código, leia a parte 2.

## 1. Instalar no computador da pessoa

O Jarvis só funciona no **Windows**. Trabalhe em português do Brasil e fale com a pessoa de forma simples: ela pode não ser programadora.

1. **Onde:** clone numa pasta chamada `Jarvis`, num lugar que a pessoa escolher (se ela não disser, use a pasta atual). Se você já está dentro do repositório clonado, não clone de novo.
   `git clone https://github.com/edirsooo/jarvis.git Jarvis`
2. **Python:** confira com `python --version`. Precisa ser 3.10 ou mais novo. Se não houver Python, diga à pessoa para instalar pelo python.org marcando "Add python.exe to PATH" e pare até ela confirmar: instalar programa é decisão dela.
3. **Nome:** pergunte como o Jarvis deve chamá-la, se ela ainda não disse.
4. **Instalar:** dentro da pasta, rode `python instalar.py --dono "<nome>"`. Ele instala os pacotes do `requirements.txt` com o pip, cria o `config.json`, confere o que falta e cria o atalho na área de trabalho. A primeira instalação baixa algumas centenas de megabytes de pacotes: avise antes.
5. **Leia a saída.** Cada linha começa com `[OK]`, `[AVISO]` (opcional, só informe) ou `[FALTA]` (precisa resolver):
   - **Claude Code faltando:** é obrigatório. Passe o link https://claude.com/claude-code, peça para a pessoa instalar e entrar na conta dela, e rode o instalador de novo. Você não entra em conta nem digita senha por ela.
   - **Codex, Ollama, ffmpeg faltando:** são opcionais. Explique em uma linha o que cada um acrescenta e siga.
6. **Conferir sem gastar cota:** rode `python testes\teste_servidor.py`. Tem de terminar com `TUDO CERTO`. Ele usa um Claude Code de mentira numa pasta temporária e não abre janela nem toca som.
7. **Entregar:** diga para a pessoa abrir pelo atalho **Jarvis** da área de trabalho e falar "Jarvis". Avise que na primeira abertura ele baixa o modelo de transcrição de voz e pode levar alguns minutos para começar a ouvir. Não abra o Jarvis você mesmo sem ela pedir: ele liga o microfone e fala em voz alta.
8. **Avise sobre a segurança**, em poucas linhas, com o que está na seção "Segurança e privacidade" do `README.md`: as missões agem no computador sem pedir confirmação a cada passo e gastam a cota das assinaturas dela.

Opcionais que você pode oferecer depois, um por vez e só se ela quiser:
- `memoria\sobre_mim.md`: algumas linhas sobre quem ela é e como trabalha (modelo em `memoria\sobre_mim.exemplo.md`).
- Transcrição na placa NVIDIA: `pip install torch --index-url https://download.pytorch.org/whl/cu128` (download grande).
- Cérebro local de reserva: instalar o Ollama e baixar o modelo indicado em `cerebro_reserva.modelo` do `config.exemplo.json`.
- Abrir com o Windows: `Ligar com o Windows.bat`.

Não faça por conta própria: mudar `claude_permissao`, instalar programas fora do pip, mexer em arquivos fora da pasta do Jarvis.

## 2. Mexer no código

- Tudo em português do Brasil: nomes, comentários, mensagens.
- **O que é da pessoa fica fora do repositório:** `config.json`, `dados\`, `missoes\`, `memoria\`, `modelos\meus\`. Não escreva nome de pessoa, caminho de pasta pessoal nem chave no código: o nome vem de `configuracao.dono(cfg)`, as regras pessoais de `regras_extras` e os padrões novos entram no `config.exemplo.json`.
- Nos textos que vão para as IAs, `{dono}` e `{tratamento}` (em `personalidade.md`) e `{dono}` e `{pasta_jarvis}` (nos roteiros de `modelos\`) são trocados na hora.
- **Nunca passe texto com quebra de linha como opção de linha de comando** para o `claude` ou o `codex`: no Windows eles são arquivos `.cmd` e a linha é cortada na primeira quebra. Regras e prompts vão em arquivo (`--append-system-prompt-file`) ou pela entrada padrão.
- Os agentes das missões nunca usam comando de apagar; mantenha isso nas regras de `agentes.py`.
- O servidor só atende em `127.0.0.1` e recusa pedidos com `Origin` de outro site (`so_local` em `jarvis.py`). Não afrouxe isso.
- **Teste antes de entregar:** `python testes\teste_falas.py`, `python testes\teste_servidor.py`, `python testes\teste_tela.py` e `python testes\teste_clique.py`. Rodam numa cópia isolada (`JARVIS_TESTE`, `JARVIS_PORTA`) e não mexem no Jarvis aberto. Detalhes em `testes\LEIA-ME.md`.
- Depois de mudar o Python, o Jarvis aberto precisa ser reiniciado para valer (fechar pelo ícone ao lado do relógio e abrir de novo). Não reinicie com missão trabalhando.
