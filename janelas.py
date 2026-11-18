"""Janelas do Jarvis no Windows: a grande (painel) e a mini, que fica por cima de tudo e foge do mouse."""
import ctypes, os, subprocess, threading, time, webbrowser
from ctypes import wintypes

T_GRANDE = "Jarvis · painel"
T_MINI = "Jarvis · mini"
MINI_L, MINI_A = 300, 340

u32 = ctypes.windll.user32
# sem isto o "-1" (sempre por cima) vira um identificador de janela inválido no Windows de 64 bits
u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
u32.SetWindowPos.restype = wintypes.BOOL
u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
u32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
u32.MonitorFromPoint.restype = wintypes.HANDLE
u32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
POR_CIMA = wintypes.HWND(-1)
PORTA, DADOS, LOG = 4747, ".", print
_mini_vivo = False
_abrindo_ate = 0.0
_canto = "dir-baixo"
_foge = False        # a esfera só desvia do mouse se o usuário pedir "livre"
_fixo = False        # True quando o usuário escolheu um canto por voz
TESTE = bool(os.environ.get("JARVIS_TESTE"))   # em teste, nenhuma janela de verdade é aberta, movida ou escondida


def iniciar(porta, dados, log):
    global PORTA, DADOS, LOG
    PORTA, DADOS, LOG = porta, dados, log


def _navegador():
    for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""), os.environ.get("LOCALAPPDATA", "")):
        for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
            exe = os.path.join(base, rel)
            if base and os.path.exists(exe):
                return exe
    return None


def achar(titulo):
    achado = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        if u32.IsWindowVisible(h):
            n = u32.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                u32.GetWindowTextW(h, b, n + 1)
                if b.value == titulo:
                    achado.append(h)
                    return False
        return True
    u32.EnumWindows(cb, 0)
    return achado[0] if achado else None


def _abrir(url, perfil, extra):
    exe = _navegador()
    if not exe:
        webbrowser.open(url)
        return
    subprocess.Popen([exe, f"--app={url}", "--autoplay-policy=no-user-gesture-required",
                      f"--user-data-dir={os.path.join(DADOS, perfil)}", "--no-first-run"] + extra)


def abrir_site(url, cfg):
    """Abre um endereço no navegador e perfil que o usuário escolheu (config: sites_navegador, sites_perfil).
    Sem escolha, ou se o navegador não for achado, vai no padrão do Windows."""
    if TESTE:
        LOG(f"[teste] abriria o site {url}")
        return
    qual = str(cfg.get("sites_navegador") or "").lower()
    rel = {"chrome": r"Google\Chrome\Application\chrome.exe", "edge": r"Microsoft\Edge\Application\msedge.exe"}.get(qual)
    if rel:
        for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""), os.environ.get("LOCALAPPDATA", "")):
            exe = os.path.join(base, rel)
            if base and os.path.exists(exe):
                args = [exe]
                if cfg.get("sites_perfil"):
                    args.append(f"--profile-directory={cfg['sites_perfil']}")
                subprocess.Popen(args + [url])
                return
    webbrowser.open(url)


def abrir_grande():
    _abrir(f"http://127.0.0.1:{PORTA}/", "janela", ["--window-size=1440,900"])


def _frente(h):
    try:
        if u32.IsIconic(h):
            u32.ShowWindow(h, 9)          # restaurar
        # o Windows só deixa trazer para a frente quem "tem a vez"; um Alt solto libera
        u32.keybd_event(0x12, 0, 0, 0)
        u32.keybd_event(0x12, 0, 2, 0)
        u32.SetForegroundWindow(h)
    except Exception:
        pass


def mostrar_grande():
    """Traz o painel para a frente (ou abre, se foi fechado)."""
    if TESTE:
        return
    def faz():
        global _abrindo_ate
        h = achar(T_GRANDE)
        if h:
            _frente(h)
        elif time.time() > _abrindo_ate:
            # a janela leva uns segundos para aparecer: clique duplo ou pedido repetido nesse meio tempo não abre outra
            _abrindo_ate = time.time() + 8
            abrir_grande()
    threading.Thread(target=faz, daemon=True).start()


def grande_na_frente():
    """True quando a janela em uso agora é o painel grande (a esfera flutuante some para não cobrir os botões dele)."""
    try:
        h = u32.GetForegroundWindow()
        n = u32.GetWindowTextLengthW(h)
        b = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(h, b, n + 1)
        return b.value == T_GRANDE
    except Exception:
        return False


def esconder_grande():
    if TESTE:
        return
    h = achar(T_GRANDE)
    if h:
        u32.ShowWindow(h, 6)              # minimizar


_proc = None


def mini_aberta():
    return _proc is not None and _proc.poll() is None


def _pythonw():
    """O Python sem janela de terminal: o mesmo que está rodando o Jarvis, quando dá para saber."""
    import sys
    exe = sys.executable or ""
    if os.path.basename(exe).lower().startswith("pythonw"):
        return exe
    irmao = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return irmao if os.path.exists(irmao) else "pythonw"


def abrir_mini(canto=None):
    """Esfera flutuante nativa (mini.py): sem moldura, sempre por cima, desvia do mouse."""
    global _proc, _canto, _fixo
    if canto:
        _canto, _fixo = canto, True
    if mini_aberta() or TESTE:
        return
    aqui = os.path.dirname(os.path.abspath(__file__))
    _proc = subprocess.Popen([_pythonw(), os.path.join(aqui, "mini.py"), str(PORTA)], cwd=aqui)


def fechar_mini():
    global _proc, _fixo
    _fixo = False
    if mini_aberta():
        try:
            _proc.terminate()
        except Exception:
            pass
    _proc = None


def canto(nome):
    """'esq-cima', 'dir-cima', 'esq-baixo', 'dir-baixo' ou 'livre' (volta a fugir do mouse)."""
    global _canto, _fixo, _foge
    if nome == "livre":
        _fixo, _foge = False, True
    elif nome in ("esq-cima", "dir-cima", "esq-baixo", "dir-baixo"):
        _canto, _fixo = nome, True


def estado_mini():
    return {"canto": _canto, "fixo": _fixo, "foge": _foge}


def grande_visivel():
    """True quando o painel grande está aberto na tela (não minimizado), mesmo sem estar em foco."""
    try:
        h = achar(T_GRANDE)
        return bool(h) and not u32.IsIconic(h)
    except Exception:
        return False
