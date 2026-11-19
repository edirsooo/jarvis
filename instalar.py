"""Instala o Jarvis neste computador (Windows, macOS ou Linux).

    python instalar.py                       pergunta o seu nome e faz tudo
    python instalar.py --dono "Maria"        sem perguntas (bom para o Claude Code ou o Codex rodarem)
    python instalar.py --conferir            só confere o que falta, sem instalar nem mudar nada

Opções: --sem-pacotes (não roda o pip nem o gerenciador do sistema), --sem-atalho (não cria o atalho).
macOS e Linux: --ligar-com-o-sistema / --desligar-com-o-sistema (abrir sozinho ao entrar na conta;
no Windows é o arquivo "Ligar com o Windows.bat"). No macOS e no Linux use python3 no lugar de python.

O que ele faz: instala os pacotes do requirements.txt (e, no macOS/Linux, os do sistema que faltarem: PortAudio,
Tk, ffmpeg...), cria o seu config.json a partir do config.exemplo.json, grava o seu nome, confere Claude Code,
Codex, navegador e microfone, e cria o atalho "Jarvis" (área de trabalho no Windows e no macOS, menu de
aplicativos no Linux). Pode rodar de novo quando quiser: não apaga nem sobrescreve o que é seu.
"""
import html, json, os, shutil, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import plataforma
plataforma.garantir_path()

ARGS = sys.argv[1:]
SO_CONFERIR = "--conferir" in ARGS
falta_grave = []


def opcao(nome):
    if nome in ARGS and ARGS.index(nome) + 1 < len(ARGS):
        return ARGS[ARGS.index(nome) + 1]
    return None


def diz(marca, txt):
    print(f"[{marca}] {txt}", flush=True)


def interativo():
    return bool(sys.stdin and sys.stdin.isatty())


def _perguntar(txt):
    """Sim/não no terminal. Instalar programa do sistema é decisão de quem usa: sem resposta, é não."""
    try:
        return input(txt).strip().lower() in ("s", "sim", "y", "yes")
    except EOFError:
        return False


def passo_python():
    if not (plataforma.WIN or plataforma.MAC or plataforma.LINUX):
        diz("ERRO", f"Sistema não suportado: {sys.platform}. O Jarvis roda no Windows, no macOS e no Linux.")
        sys.exit(1)
    if sys.version_info < (3, 10):
        diz("ERRO", f"Python {sys.version.split()[0]} é antigo demais. Instale o Python 3.10 ou mais novo (python.org).")
        sys.exit(1)
    diz("OK", f"Python {sys.version.split()[0]} no {plataforma.NOME}")


# ---------- pacotes do sistema (macOS e Linux) ----------
def _gerenciador_linux():
    """(nome, comando de instalação, pacotes) do gerenciador de pacotes deste Linux, ou None."""
    if shutil.which("apt-get"):
        return "apt", ["sudo", "apt-get", "install", "-y"], {
            "portaudio": "libportaudio2", "tk": "python3-tk", "ffmpeg": "ffmpeg", "xdg": "xdg-utils",
            "wmctrl": "wmctrl", "xdotool": "xdotool", "venv": "python3-venv"}
    if shutil.which("dnf"):
        return "dnf", ["sudo", "dnf", "install", "-y"], {
            "portaudio": "portaudio", "tk": "python3-tkinter", "ffmpeg": "ffmpeg", "xdg": "xdg-utils",
            "wmctrl": "wmctrl", "xdotool": "xdotool"}
    if shutil.which("pacman"):
        return "pacman", ["sudo", "pacman", "-S", "--needed", "--noconfirm"], {
            "portaudio": "portaudio", "tk": "tk", "ffmpeg": "ffmpeg", "xdg": "xdg-utils",
            "wmctrl": "wmctrl", "xdotool": "xdotool"}
    if shutil.which("zypper"):
        return "zypper", ["sudo", "zypper", "install", "-y"], {
            "portaudio": "portaudio", "tk": "python3-tk", "ffmpeg": "ffmpeg", "xdg": "xdg-utils",
            "wmctrl": "wmctrl", "xdotool": "xdotool"}
    return None


def _portaudio_ok():
    try:
        import sounddevice  # noqa: F401  (sem a biblioteca PortAudio, o import falha com OSError)
        return True
    except OSError:
        return False
    except Exception:
        return True          # sounddevice ainda não instalado: o pip cuida; a PortAudio é conferida depois


def _tk_ok():
    try:
        import tkinter  # noqa: F401
        return True
    except Exception:
        return False


def _faltas_do_sistema():
    """O que falta do sistema operacional (não do Python), por chave: portaudio, tk, ffmpeg, xdg, wmctrl, xdotool."""
    falta = []
    if not _portaudio_ok():
        falta.append("portaudio")
    if not _tk_ok():
        falta.append("tk")
    if not (shutil.which("ffmpeg") and shutil.which("ffplay")):
        falta.append("ffmpeg")
    if plataforma.LINUX:
        if not shutil.which("xdg-open"):
            falta.append("xdg")
        for prog in ("wmctrl", "xdotool"):
            if not shutil.which(prog):
                falta.append(prog)
    return falta


def passo_sistema():
    """macOS: Homebrew (portaudio, ffmpeg, python-tk). Linux: apt/dnf/pacman/zypper com sudo, perguntando antes."""
    if plataforma.WIN:
        return
    falta = _faltas_do_sistema()
    if not falta:
        diz("OK", "Programas do sistema: PortAudio, Tk e ffmpeg presentes" + (", xdg-open, wmctrl e xdotool" if plataforma.LINUX else ""))
        return
    if plataforma.MAC:
        brew = {"portaudio": "portaudio", "ffmpeg": "ffmpeg",
                "tk": f"python-tk@{sys.version_info.major}.{sys.version_info.minor}"}
        pacotes = [brew[f] for f in falta if f in brew]
        cmd = ["brew", "install"] + pacotes
        if not pacotes:
            return
        if "tk" in falta:
            diz("AVISO", "Sem o Tk do Python a esfera flutuante não abre. O Python de python.org já traz o Tk.")
        if SO_CONFERIR or "--sem-pacotes" in ARGS or not shutil.which("brew") or not interativo():
            onde = "" if shutil.which("brew") else " (instale o Homebrew antes: https://brew.sh)"
            diz("AVISO", "Faltam no macOS: " + ", ".join(pacotes) + f". Instale com: {' '.join(cmd)}{onde}")
            return
        if not _perguntar(f"Instalar agora pelo Homebrew? {' '.join(pacotes)} [s/N] "):
            diz("AVISO", f"Sem instalar. Quando quiser: {' '.join(cmd)}")
            return
        subprocess.run(cmd)
    else:
        g = _gerenciador_linux()
        if not g:
            diz("AVISO", "Não reconheci o gerenciador de pacotes deste Linux. Instale à mão: PortAudio, Tk do Python (python3-tk), "
                         "ffmpeg, xdg-utils, wmctrl e xdotool.")
            return
        nome, base, mapa = g
        pacotes = [mapa[f] for f in falta if f in mapa]
        cmd = base + pacotes
        if SO_CONFERIR or "--sem-pacotes" in ARGS or not interativo():
            diz("AVISO", "Faltam no Linux: " + ", ".join(pacotes) + f". Instale com: {' '.join(cmd)}")
            return
        if not _perguntar(f"Instalar agora com {nome} (pede a senha do sudo)? {' '.join(pacotes)} [s/N] "):
            diz("AVISO", f"Sem instalar. Quando quiser: {' '.join(cmd)}")
            return
        subprocess.run(cmd)
    resto = _faltas_do_sistema()
    if "portaudio" in resto:
        diz("AVISO", "A PortAudio ainda não carrega: sem ela o microfone não funciona (dá para usar escrevendo no painel).")


def passo_pacotes():
    if SO_CONFERIR or "--sem-pacotes" in ARGS:
        return
    diz("..", "Instalando os pacotes (pode levar alguns minutos na primeira vez)")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", os.path.join(AQUI, "requirements.txt")])
    if r.returncode != 0:
        dica = ""
        if not plataforma.WIN:
            dica = (" Se o erro falar em 'externally-managed-environment', crie um ambiente próprio e rode por ele: "
                    "python3 -m venv .venv && .venv/bin/python instalar.py (os lançadores já usam o .venv).")
        diz("ERRO", "O pip não conseguiu instalar tudo. Leia o erro acima, corrija e rode de novo." + dica)
        sys.exit(1)
    diz("OK", "Pacotes instalados")


def passo_modulos():
    faltam = []
    dica_tk = {"windows": "tkinter (vem com o Python de python.org)",
               "mac": "tkinter (vem com o Python de python.org; no Homebrew: brew install python-tk)",
               "linux": "tkinter (pacote python3-tk do sistema)"}[plataforma.sistema()]
    mods = [("aiohttp", "aiohttp"), ("numpy", "numpy"), ("sounddevice", "sounddevice"), ("faster_whisper", "faster-whisper"),
            ("openwakeword", "openwakeword"), ("edge_tts", "edge-tts"), ("pystray", "pystray"), ("PIL", "pillow"),
            ("playwright", "playwright"), ("tkinter", dica_tk)]
    for mod, pacote in mods:
        try:
            __import__(mod)
        except Exception:
            faltam.append(pacote)
    if faltam:
        diz("FALTA", "Pacotes: " + ", ".join(faltam))
        falta_grave.append("pacotes do Python")
    else:
        diz("OK", "Todos os pacotes do Python estão instalados")
    if not plataforma.WIN:
        try:
            __import__("pyautogui")
            diz("OK", "pyautogui encontrado (missões que mexem no mouse e no teclado)")
        except Exception:
            diz("AVISO", "pyautogui não instalado: opcional. Sem ele as missões não mexem no mouse nem no teclado (só veem a tela).")
        try:
            __import__("mss")
            diz("OK", "mss encontrado (captura de tela e vários monitores)")
        except Exception:
            diz("AVISO", "mss não instalado: opcional. Ajuda a capturar a tela e reconhecer vários monitores.")


def passo_config():
    meu = os.path.join(AQUI, "config.json")
    if not os.path.exists(meu):
        if SO_CONFERIR:
            diz("FALTA", "config.json ainda não existe (o instalador cria)")
            return
        shutil.copyfile(os.path.join(AQUI, "config.exemplo.json"), meu)
        diz("OK", "config.json criado a partir do exemplo")
    with open(meu, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    nome = opcao("--dono")
    if not nome and not str(cfg.get("dono") or "").strip() and not SO_CONFERIR and interativo():
        try:
            nome = input("Como o Jarvis deve chamar você? (seu primeiro nome) ").strip()
        except EOFError:
            nome = ""
    if nome and not SO_CONFERIR and nome != cfg.get("dono"):
        cfg["dono"] = nome
        with open(meu, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
    dono = str(cfg.get("dono") or "").strip()
    if dono:
        diz("OK", f"Nome de quem usa: {dono}")
    else:
        diz("AVISO", 'Sem nome gravado: o Jarvis vai usar o nome do usuário do sistema. Para trocar: python instalar.py --dono "Seu Nome"')


def _playwright_chromium():
    """Baixa o Chromium do Playwright (navegador das missões) quando não há Chrome nem Edge."""
    if SO_CONFERIR or "--sem-pacotes" in ARGS:
        return False
    diz("..", "Baixando o Chromium do Playwright (navegador das missões)")
    return subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"]).returncode == 0


def passo_programas():
    if shutil.which("claude"):
        diz("OK", "Claude Code encontrado (o Jarvis pensa e trabalha por ele; se ainda não entrou na sua conta, rode `claude` uma vez)")
    else:
        diz("FALTA", "Claude Code não encontrado. Instale (https://claude.com/claude-code), entre na sua conta e rode o instalador de novo.")
        falta_grave.append("Claude Code")
    if shutil.which("codex"):
        diz("OK", 'Codex encontrado (missões de imagem e as que você pedir com "Codex, ...")')
    else:
        diz("AVISO", "Codex não encontrado: opcional. Sem ele, peça tudo ao Claude.")
    if plataforma.navegador():
        diz("OK", "Navegador da família Chrome encontrado (janela do painel e navegador das missões)")
    elif plataforma.WIN:
        diz("FALTA", "Não achei o Edge nem o Chrome.")
        falta_grave.append("Edge ou Chrome")
    else:
        diz("AVISO", "Não achei Chrome, Edge nem Chromium: o painel abre no navegador padrão, sem janela própria. "
                     "Para a janela própria, instale o Google Chrome ou o Chromium.")
        if _playwright_chromium():
            diz("OK", "Chromium do Playwright instalado (missões que navegam na web)")
    if shutil.which("ollama"):
        diz("OK", "Ollama encontrado (cérebro local de reserva)")
    else:
        diz("AVISO", "Ollama não encontrado: opcional. É o cérebro local de reserva, para quando a cota do Claude acaba.")
    if shutil.which("ffplay"):
        diz("OK", "ffmpeg encontrado")
    elif plataforma.MAC and shutil.which("afplay"):
        diz("AVISO", "ffmpeg não encontrado: opcional no macOS (o Jarvis já fala sem a janela pelo afplay; o ffmpeg só faz falta no processo de corte de vídeo).")
    else:
        diz("AVISO", "ffmpeg não encontrado: opcional. Sem ele o Jarvis só fala com a janela do painel aberta, e o processo de corte de vídeo não roda.")
    try:
        import sounddevice as sd
        diz("OK", f"Microfone: {sd.query_devices(kind='input')['name']}")
    except Exception as e:
        dica = " No macOS, permita o microfone para o Terminal/Python em Ajustes do Sistema > Privacidade e Segurança." if plataforma.MAC else ""
        diz("AVISO", f"Não consegui ver o microfone ({type(e).__name__}). Sem microfone dá para usar escrevendo no painel.{dica}")
    if plataforma.wayland():
        diz("AVISO", "Sessão Wayland: o painel, a voz e as missões funcionam; ver a tela e mexer no mouse/teclado (missões de computador) "
                     "ficam desligados. Para isso, entre numa sessão X11 (Xorg).")
    elif plataforma.LINUX and not plataforma.tem_tela():
        diz("AVISO", "Sem área de trabalho gráfica: o Jarvis roda como servidor; abra http://127.0.0.1:4747 num navegador.")


# ---------- atalho e início automático ----------
def _python_dos_lancadores():
    venv = os.path.join(AQUI, ".venv", "bin", "python")
    return venv if os.path.exists(venv) else (sys.executable or "python3")


def _executavel(arq):
    try:
        os.chmod(arq, os.stat(arq).st_mode | 0o111)
    except OSError:
        pass


def _desktop_linux():
    return ("[Desktop Entry]\nType=Application\nName=Jarvis\nComment=Assistente de voz\n"
            f'Exec="{os.path.join(AQUI, "jarvis.sh")}"\nPath={AQUI}\nIcon={os.path.join(AQUI, "web", "icone.png")}\n'
            "Terminal=false\nCategories=Utility;\n")


def _launch_agent():
    return os.path.expanduser("~/Library/LaunchAgents/com.jarvis.assistente.plist")


def _plist():
    e = lambda s: html.escape(str(s), quote=False)
    path_atual = os.environ.get("PATH") or "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.jarvis.assistente</string>
  <key>ProgramArguments</key>
  <array><string>{e(_python_dos_lancadores())}</string><string>{e(os.path.join(AQUI, "jarvis.py"))}</string><string>--janela</string></array>
  <key>WorkingDirectory</key><string>{e(AQUI)}</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>{e(path_atual)}</string></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{e(os.path.join(AQUI, "dados", "jarvis-terminal.log"))}</string>
  <key>StandardErrorPath</key><string>{e(os.path.join(AQUI, "dados", "jarvis-terminal.log"))}</string>
</dict>
</plist>
"""


def passo_atalho():
    if SO_CONFERIR or "--sem-atalho" in ARGS:
        return
    if plataforma.WIN:
        ps = ("$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Jarvis.lnk')); "
              "$s.TargetPath='wscript.exe'; $s.Arguments=[char]34 + $env:JARVIS_VBS + [char]34; $s.WorkingDirectory=$env:JARVIS_PASTA; "
              "$s.IconLocation=$env:JARVIS_ICO; $s.Save()")
        amb = dict(os.environ, JARVIS_VBS=os.path.join(AQUI, "Jarvis.vbs"), JARVIS_PASTA=AQUI, JARVIS_ICO=os.path.join(AQUI, "Jarvis.ico"))
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=amb, capture_output=True, text=True)
        if r.returncode == 0:
            diz("OK", 'Atalho "Jarvis" criado na área de trabalho')
        else:
            diz("AVISO", "Não consegui criar o atalho. Para abrir, dê dois cliques em Jarvis.vbs.")
        return
    for arq in ("Jarvis.command", "jarvis.sh"):
        _executavel(os.path.join(AQUI, arq))
    if plataforma.MAC:
        atalho = os.path.expanduser("~/Desktop/Jarvis.command")
        try:
            if not os.path.lexists(atalho):
                os.symlink(os.path.join(AQUI, "Jarvis.command"), atalho)
            diz("OK", 'Atalho "Jarvis.command" na área de trabalho (dois cliques abrem o Jarvis)')
        except OSError as e:
            diz("AVISO", f"Não consegui criar o atalho ({e}). Para abrir, dê dois cliques em Jarvis.command, na pasta do Jarvis.")
        return
    try:
        pasta = os.path.expanduser("~/.local/share/applications")
        os.makedirs(pasta, exist_ok=True)
        arq = os.path.join(pasta, "jarvis.desktop")
        with open(arq, "w", encoding="utf-8", newline="\n") as f:
            f.write(_desktop_linux())
        _executavel(arq)
        diz("OK", 'Atalho "Jarvis" no menu de aplicativos (ou rode ./jarvis.sh)')
    except OSError as e:
        diz("AVISO", f"Não consegui criar o atalho ({e}). Para abrir, rode ./jarvis.sh na pasta do Jarvis.")


def passo_inicio_automatico():
    """--ligar-com-o-sistema / --desligar-com-o-sistema (macOS: LaunchAgent; Linux: ~/.config/autostart)."""
    ligar, desligar = "--ligar-com-o-sistema" in ARGS, "--desligar-com-o-sistema" in ARGS
    if not (ligar or desligar) or SO_CONFERIR:
        return
    if plataforma.WIN:
        diz("AVISO", 'No Windows, use o arquivo "Ligar com o Windows.bat" (dois cliques liga, outros dois desligam).')
        return
    arq = _launch_agent() if plataforma.MAC else os.path.expanduser("~/.config/autostart/jarvis.desktop")
    if desligar:
        if os.path.exists(arq):
            if plataforma.MAC:
                subprocess.run(["launchctl", "unload", arq], capture_output=True)
            destino = os.path.join(tempfile.gettempdir(), "Jarvis-inicio-desligado" + os.path.splitext(arq)[1])
            shutil.move(arq, destino)      # guardado, não apagado (como no Windows)
            diz("OK", f"O Jarvis não abre mais sozinho. (O arquivo foi guardado em {destino}.)")
        else:
            diz("OK", "O Jarvis já não abria sozinho.")
        return
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    os.makedirs(os.path.join(AQUI, "dados"), exist_ok=True)
    with open(arq, "w", encoding="utf-8", newline="\n") as f:
        f.write(_plist() if plataforma.MAC else _desktop_linux())
    diz("OK", "Pronto: o Jarvis vai abrir sozinho quando você entrar na sua conta. Para desligar: "
              "python3 instalar.py --desligar-com-o-sistema")


def mensagem_final():
    if plataforma.WIN:
        diz("PRONTO", 'Abra pelo atalho "Jarvis" da área de trabalho (ou Jarvis.vbs) e diga "Jarvis".')
    elif plataforma.MAC:
        diz("PRONTO", 'Abra com dois cliques em Jarvis.command (área de trabalho ou pasta do Jarvis) e diga "Jarvis".')
        print("         Na primeira vez o macOS pede permissão de Microfone (e, para missões de computador, Gravação de Tela e Acessibilidade).")
    else:
        diz("PRONTO", 'Abra pelo menu de aplicativos ("Jarvis") ou com ./jarvis.sh e diga "Jarvis".')
    print("         Na primeira vez ele baixa o modelo de transcrição de voz: pode levar alguns minutos até começar a ouvir.")


if __name__ == "__main__":
    if "-h" in ARGS or "--help" in ARGS:
        print(__doc__)
        sys.exit(0)
    passo_python()
    passo_sistema()
    passo_pacotes()
    passo_modulos()
    passo_config()
    passo_programas()
    passo_atalho()
    passo_inicio_automatico()
    print()
    if falta_grave:
        diz("FALTA", "Ainda falta: " + ", ".join(falta_grave) + ". Resolva e rode de novo.")
        sys.exit(2)
    if SO_CONFERIR:
        diz("PRONTO", "Nada grave faltando.")
    else:
        mensagem_final()
