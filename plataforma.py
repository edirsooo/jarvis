"""O que muda entre Windows, macOS e Linux, num lugar só.

O resto do Jarvis pergunta aqui em vez de chamar o sistema direto. No Windows tudo continua como era;
no macOS e no Linux cada recurso usa o equivalente do sistema e, quando não há um equivalente simples,
é desligado com um aviso (nunca derruba o Jarvis).
"""
import os, shutil, subprocess, sys

WIN = sys.platform == "win32"
MAC = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
NOME = "Windows" if WIN else "macOS" if MAC else "Linux" if LINUX else sys.platform

SEM_JANELA = 0x08000000        # CREATE_NO_WINDOW: no Windows, programa de linha de comando abre sem janela preta

# extensões que nunca são executadas por um pedido de "abrir" (abre só a pasta com o arquivo marcado)
EXECUTAVEIS = {
    # Windows
    ".exe", ".bat", ".cmd", ".com", ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh", ".msi", ".msp",
    ".scr", ".lnk", ".url", ".reg", ".hta", ".cpl", ".jar", ".py", ".pyw",
    # macOS e Linux
    ".sh", ".bash", ".zsh", ".fish", ".command", ".tool", ".app", ".pkg", ".mpkg", ".dmg", ".scpt", ".applescript",
    ".workflow", ".action", ".desktop", ".run", ".bin", ".appimage", ".deb", ".rpm", ".snap", ".flatpakref",
    ".pl", ".rb", ".php", ".elf", ".out",
}


def sistema():
    """'windows', 'mac' ou 'linux'."""
    return "windows" if WIN else "mac" if MAC else "linux"


def sem_janela():
    """Opções de subprocess para um programa de linha de comando sem janela (só existe no Windows)."""
    return {"creationflags": SEM_JANELA} if WIN else {}


def solto():
    """Opções para um processo que continua vivo depois que o Jarvis fecha (reinício)."""
    if WIN:
        return {"creationflags": getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {"start_new_session": True}


def wayland():
    """Linux numa sessão Wayland (mesmo com XWayland definindo DISPLAY): captura de tela, mouse e teclado de
    outros programas nativos não são permitidos pelo sistema."""
    return LINUX and (os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY")))


def tem_tela():
    """Há uma área de trabalho gráfica? (Linux sem DISPLAY nem WAYLAND_DISPLAY = servidor/terminal)."""
    if not LINUX:
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def garantir_path():
    """macOS e Linux: quando o Jarvis abre pelo atalho gráfico (Finder, LaunchAgent, menu .desktop), o PATH costuma
    vir sem Homebrew, ~/.local/bin ou Node/nvm, e o Jarvis não acha o claude, o codex nem o ffmpeg.
    Acrescenta no FIM do PATH os diretórios comuns que existirem (sem passar na frente do que já está no PATH)."""
    if WIN:
        return
    import glob
    home = os.path.expanduser("~")
    candidatos = [
        "/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin",
        os.path.join(home, ".local", "bin"),
        os.path.join(home, ".npm-global", "bin"),
        os.path.join(home, ".volta", "bin"),
        os.path.join(home, ".fnm", "current", "bin"),
        os.path.join(home, ".cargo", "bin"),
    ]
    if LINUX:
        candidatos.append("/snap/bin")
    nvm = sorted(glob.glob(os.path.join(home, ".nvm", "versions", "node", "*", "bin")), reverse=True)
    if nvm:
        candidatos.append(nvm[0])
    atual = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    vistos = set(atual)
    extras = [d for d in candidatos if d not in vistos and os.path.isdir(d)]
    if extras:
        os.environ["PATH"] = os.pathsep.join(atual + extras)


def tocar_audio_cmd(caminho):
    """Comando para tocar um áudio quando não há janela do painel aberta, ou None se não houver reprodutor."""
    if MAC:
        if shutil.which("afplay"):            # vem instalado em todo macOS, sem precisar do ffmpeg
            return ["afplay", caminho]
        if shutil.which("ffplay"):
            return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", caminho]
        return None
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", caminho]
    if LINUX:
        if shutil.which("mpv"):
            return ["mpv", "--no-video", "--really-quiet", caminho]
        if shutil.which("mpg123"):
            return ["mpg123", "-q", caminho]
    return None


def executavel(caminho):
    """True quando abrir o arquivo poderia rodar um programa: extensão de programa/script, pacote .app ou arquivo
    marcado como executável (macOS e Linux)."""
    ext = os.path.splitext(str(caminho).rstrip("/\\"))[1].lower()
    if ext in EXECUTAVEIS:
        return True
    if not WIN and os.path.isfile(caminho) and os.access(caminho, os.X_OK):
        return True
    return False


def _popen(args, **kw):
    return subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)


def abrir(alvo):
    """Abre um arquivo, pasta ou endereço com o programa padrão do sistema."""
    if WIN:
        os.startfile(alvo)
    elif MAC:
        _popen(["open", alvo], start_new_session=True)
    else:
        if not shutil.which("xdg-open"):
            raise RuntimeError("xdg-open não encontrado (instale o pacote xdg-utils)")
        _popen(["xdg-open", alvo], start_new_session=True)


def revelar(caminho):
    """Abre a pasta com o arquivo marcado (sem abrir o arquivo)."""
    caminho = os.path.normpath(caminho)
    if WIN:
        subprocess.Popen(["explorer", "/select,", caminho])
    elif MAC:
        _popen(["open", "-R", caminho], start_new_session=True)
    else:
        # o Linux não tem um "marcar o arquivo" que funcione em todos os gerenciadores: abre a pasta dele
        abrir(os.path.dirname(caminho) or ".")


# ---------- navegador (Chrome/Edge/Chromium) ----------
_NAV_WIN = {"edge": r"Microsoft\Edge\Application\msedge.exe", "chrome": r"Google\Chrome\Application\chrome.exe"}
_NAV_MAC = {"chrome": "Google Chrome.app/Contents/MacOS/Google Chrome",
            "edge": "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "chromium": "Chromium.app/Contents/MacOS/Chromium",
            "brave": "Brave Browser.app/Contents/MacOS/Brave Browser"}
_NAV_LINUX = {"chrome": ("google-chrome", "google-chrome-stable"),
              "edge": ("microsoft-edge", "microsoft-edge-stable"),
              "chromium": ("chromium", "chromium-browser"),
              "brave": ("brave-browser", "brave")}


def navegador(qual=None):
    """Caminho de um navegador da família Chrome (o painel abre como janela de aplicativo, --app=).
    qual = 'edge', 'chrome', 'chromium' ou 'brave'; sem qual, o primeiro que achar (no Windows, Edge antes do Chrome)."""
    if WIN:
        ordem = [qual] if qual else ["edge", "chrome"]
        if qual:
            bases = ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")
        else:
            bases = ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")
        for base in (os.environ.get(b, "") for b in bases):
            for q in ordem:
                rel = _NAV_WIN.get(q)
                exe = os.path.join(base, rel) if base and rel else ""
                if exe and os.path.exists(exe):
                    return exe
        return None
    if MAC:
        ordem = [qual] if qual else ["chrome", "edge", "chromium", "brave"]
        for raiz in ("/Applications", os.path.expanduser("~/Applications")):
            for q in ordem:
                rel = _NAV_MAC.get(q)
                exe = os.path.join(raiz, rel) if rel else ""
                if exe and os.path.exists(exe):
                    return exe
        return None
    ordem = [qual] if qual else ["chrome", "chromium", "edge", "brave"]
    for q in ordem:
        for nome in _NAV_LINUX.get(q, ()):
            exe = shutil.which(nome)
            if exe:
                return exe
    return None


def python_sem_terminal():
    """O Python que abre sem janela de terminal. No Windows é o pythonw; nos outros, o próprio python."""
    exe = sys.executable or ""
    if not WIN:
        return exe or "python3"
    if os.path.basename(exe).lower().startswith("pythonw"):
        return exe
    irmao = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return irmao if os.path.exists(irmao) else "pythonw"


def acender_tela():
    """Acende a tela se ela estiver apagada (quando o Jarvis acorda por palmas). Devolve True se tentou."""
    try:
        if WIN:
            import ctypes
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            ctypes.windll.user32.mouse_event(0x0001, 0, -1, 0, 0)
            ctypes.windll.kernel32.SetThreadExecutionState(0x00000002)
            return True
        if MAC and shutil.which("caffeinate"):
            _popen(["caffeinate", "-u", "-t", "2"])       # "usuário ativo": acende a tela por 2 s
            return True
        if LINUX and os.environ.get("DISPLAY") and shutil.which("xset"):
            _popen(["xset", "dpms", "force", "on"])
            return True
    except Exception:
        pass
    return False


# ---------- pastas onde outros programas gravam dados ----------
def pasta_dados_locais():
    """Windows: %LOCALAPPDATA%. macOS: ~/Library/Application Support. Linux: ~/.local/share."""
    if WIN:
        return os.environ.get("LOCALAPPDATA", "")
    if MAC:
        return os.path.expanduser("~/Library/Application Support")
    return os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")


def pasta_config_apps():
    """Windows: %APPDATA%. macOS: ~/Library/Application Support. Linux: ~/.config."""
    if WIN:
        return os.environ.get("APPDATA", "")
    if MAC:
        return os.path.expanduser("~/Library/Application Support")
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


# ---------- ferramentas de janela do Linux (opcionais) ----------
def rodar(args, tempo=3):
    """Roda um comando curto e devolve a saída (texto) ou None se falhar / não existir."""
    if not shutil.which(args[0]):
        return None
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=tempo, **sem_janela())
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def osascript(script, tempo=3):
    """macOS: roda um AppleScript e devolve a saída, ou None (sem permissão, por exemplo)."""
    if not MAC:
        return None
    return rodar(["osascript", "-e", script], tempo)
