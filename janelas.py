"""Janelas do Jarvis: a grande (painel) e a mini, que fica por cima de tudo, num canto (foge do mouse só no modo "livre").

No Windows o painel é achado, trazido para a frente e minimizado pela API de janelas (user32). No macOS e no Linux
o painel é a janela de aplicativo que o próprio Jarvis abriu (Chrome/Edge/Chromium com --app=): ele lembra desse
processo; trazer para a frente e minimizar usam o que o sistema oferece (AppleScript no macOS; wmctrl/xdotool no
Linux, se estiverem instalados) e, sem isso, apenas não acontecem (fica registrado no log uma vez).
"""
import os, subprocess, threading, time, webbrowser

import plataforma

T_GRANDE = "Jarvis · painel"
T_MINI = "Jarvis · mini"
MINI_L, MINI_A = 300, 340

if plataforma.WIN:
    import ctypes
    from ctypes import wintypes
    u32 = ctypes.windll.user32
    # sem isto o "-1" (sempre por cima) vira um identificador de janela inválido no Windows de 64 bits
    u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    u32.SetWindowPos.restype = wintypes.BOOL
    u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    u32.MonitorFromPoint.restype = wintypes.HANDLE
    u32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    POR_CIMA = wintypes.HWND(-1)
else:
    u32 = None
PORTA, DADOS, LOG = 4747, ".", print
_mini_vivo = False
_abrindo_ate = 0.0
_canto = "dir-baixo"
_foge = False        # a esfera só desvia do mouse se o usuário pedir "livre"
_fixo = False        # True quando o usuário escolheu um canto por voz
_painel = None       # macOS e Linux: o processo do navegador que abriu o painel
_avisado = set()
TESTE = bool(os.environ.get("JARVIS_TESTE"))   # em teste, nenhuma janela de verdade é aberta, movida ou escondida


def iniciar(porta, dados, log):
    global PORTA, DADOS, LOG
    PORTA, DADOS, LOG = porta, dados, log


def _avisar_uma_vez(chave, txt):
    if chave not in _avisado:
        _avisado.add(chave)
        LOG(txt)


def _navegador():
    return plataforma.navegador()


def achar(titulo):
    if not plataforma.WIN:
        return _achar_posix(titulo)
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


def _achar_posix(titulo):
    """Linux: id da janela pelo título (wmctrl). macOS: não há como listar janelas sem permissão; devolve None."""
    if plataforma.LINUX:
        saida = plataforma.rodar(["wmctrl", "-l"])
        for linha in (saida or "").splitlines():
            partes = linha.split(None, 3)
            if len(partes) == 4 and partes[3].strip() == titulo:
                return partes[0]
    return None


def _abrir(url, perfil, extra):
    global _painel
    exe = _navegador()
    if not exe:
        _avisar_uma_vez("sem-nav", "janelas: não achei Chrome, Edge nem Chromium; o painel abre no navegador padrão (sem janela própria)")
        webbrowser.open(url)
        return
    p = subprocess.Popen([exe, f"--app={url}", "--autoplay-policy=no-user-gesture-required",
                          f"--user-data-dir={os.path.join(DADOS, perfil)}", "--no-first-run"] + extra)
    if perfil == "janela":
        _painel = p


def abrir_site(url, cfg):
    """Abre um endereço no navegador e perfil que o usuário escolheu (config: sites_navegador, sites_perfil).
    Sem escolha, ou se o navegador não for achado, vai no padrão do sistema."""
    if TESTE:
        LOG(f"[teste] abriria o site {url}")
        return
    qual = str(cfg.get("sites_navegador") or "").lower()
    if qual in ("chrome", "edge", "chromium", "brave"):
        exe = plataforma.navegador(qual)
        if exe:
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


def _painel_vivo():
    return _painel is not None and _painel.poll() is None


def _frente_posix():
    """Traz o painel para a frente no macOS/Linux. Devolve True se o painel está aberto (mesmo sem conseguir focar)."""
    if plataforma.LINUX:
        h = _achar_posix(T_GRANDE)
        if h:
            plataforma.rodar(["wmctrl", "-i", "-a", h])
            return True
        if _painel_vivo():
            if plataforma.rodar(["xdotool", "search", "--name", T_GRANDE, "windowactivate"]) is None:
                _avisar_uma_vez("frente", "janelas: para trazer o painel para a frente no Linux, instale wmctrl ou xdotool")
            return True
        return False
    if _painel_vivo():
        ok = plataforma.osascript(
            f'tell application "System Events" to set frontmost of (first process whose unix id is {_painel.pid}) to true')
        if ok is None:
            _avisar_uma_vez("frente", "janelas: o macOS não deixou trazer o painel para a frente (Ajustes > Privacidade > Automação)")
        return True
    return False


def mostrar_grande():
    """Traz o painel para a frente (ou abre, se foi fechado)."""
    if TESTE:
        return
    def faz():
        global _abrindo_ate
        if plataforma.WIN:
            h = achar(T_GRANDE)
            if h:
                _frente(h)
                return
        elif _frente_posix():
            return
        if time.time() > _abrindo_ate:
            # a janela leva uns segundos para aparecer: clique duplo ou pedido repetido nesse meio tempo não abre outra
            _abrindo_ate = time.time() + 8
            abrir_grande()
    threading.Thread(target=faz, daemon=True).start()


def grande_na_frente():
    """True quando a janela em uso agora é o painel grande (a esfera flutuante some para não cobrir os botões dele).
    macOS: não dá para saber sem permissão de acessibilidade; responde False (a esfera continua visível)."""
    try:
        if plataforma.WIN:
            h = u32.GetForegroundWindow()
            n = u32.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(h, b, n + 1)
            return b.value == T_GRANDE
        if plataforma.LINUX and not plataforma.wayland():
            nome = plataforma.rodar(["xdotool", "getactivewindow", "getwindowname"], 1)
            return bool(nome) and nome.strip() == T_GRANDE
    except Exception:
        pass
    return False


def esconder_grande():
    if TESTE:
        return
    if plataforma.WIN:
        h = achar(T_GRANDE)
        if h:
            u32.ShowWindow(h, 6)              # minimizar
        return
    if not _painel_vivo() and not (plataforma.LINUX and _achar_posix(T_GRANDE)):
        return
    if plataforma.LINUX:
        if plataforma.rodar(["xdotool", "search", "--name", T_GRANDE, "windowminimize"]) is None:
            _avisar_uma_vez("min", "janelas: para minimizar o painel no Linux, instale xdotool")
    elif plataforma.MAC:
        if plataforma.osascript(f'tell application "System Events" to set visible of (first process whose unix id is {_painel.pid}) to false') is None:
            _avisar_uma_vez("min", "janelas: o macOS não deixou esconder o painel (Ajustes > Privacidade > Automação)")


_proc = None


def mini_aberta():
    return _proc is not None and _proc.poll() is None


def _pythonw():
    """O Python sem janela de terminal: o mesmo que está rodando o Jarvis, quando dá para saber."""
    return plataforma.python_sem_terminal()


def abrir_mini(canto=None):
    """Esfera flutuante nativa (mini.py): sem moldura, sempre por cima, num canto."""
    global _proc, _canto, _fixo
    if canto:
        _canto, _fixo = canto, True
    if mini_aberta() or TESTE:
        return
    if not plataforma.tem_tela():
        _avisar_uma_vez("mini", "janelas: sem área de trabalho gráfica (DISPLAY); a esfera flutuante fica desligada")
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
    """True quando o painel grande está aberto na tela (não minimizado), mesmo sem estar em foco.
    Fora do Windows não há como saber se está minimizado: responde False e a esfera continua visível."""
    try:
        if plataforma.WIN:
            h = achar(T_GRANDE)
            return bool(h) and not u32.IsIconic(h)
    except Exception:
        pass
    return False
