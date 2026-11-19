"""Mãos do Jarvis no macOS e no Linux: o mesmo que o pc.py faz no Windows, com o que cada sistema oferece.

- Captura de tela: Pillow (ImageGrab). No macOS precisa da permissão "Gravação de Tela" para o Terminal/Python;
  no Linux funciona em X11 (Wayland puro não deixa capturar outros programas).
- Mouse e teclas: pyautogui (opcional: pip install pyautogui). No macOS precisa da permissão "Acessibilidade".
- Janela ativa (a trava que impede digitar no lugar errado): xdotool no Linux, AppleScript no macOS.
  Sem como saber a janela ativa, digitar e tecla são recusados (nada é digitado às cegas).
- Lista e foco de janelas: wmctrl no Linux; no macOS, a lista é de aplicativos abertos.
As coordenadas são as do mouse (pontos); a captura é reduzida para esse tamanho (tela Retina sai em pontos).
"""
import os, shutil, subprocess, sys, tempfile, time

MAC = sys.platform == "darwin"
FORA = 10 ** 6
LINUX = sys.platform.startswith("linux")


def sair(msg):
    print(msg)
    sys.exit(1)


def _rodar(args, tempo=3):
    if not shutil.which(args[0]):
        return None
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=tempo)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def _osa(script, tempo=4):
    return _rodar(["osascript", "-e", script], tempo) if MAC else None


def indisponivel():
    """Motivo de não dar para usar o computador por aqui, ou None se dá."""
    if LINUX:
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
            return ("Neste Linux a sessão é Wayland: o sistema não deixa um programa ver a tela nem mexer no mouse "
                    "e no teclado de outros. Entre numa sessão X11 (Xorg) para usar o computador pelo Jarvis.")
        if not os.environ.get("DISPLAY"):
            return "Não há área de trabalho gráfica (DISPLAY vazio): não dá para ver a tela nem mexer no mouse."
    elif not MAC:
        return f"O controle do computador não funciona neste sistema ({sys.platform})."
    return None


def _pag():
    try:
        import pyautogui
    except Exception:
        dica = " e dê permissão de Acessibilidade ao Terminal/Python (Ajustes do Sistema > Privacidade e Segurança)" if MAC else ""
        sair("Para mexer no mouse e no teclado, instale o pyautogui: python -m pip install pyautogui" + dica + ".")
    pyautogui.FAILSAFE = False       # o freio é o do pc.py (mouse no canto de cima à esquerda)
    pyautogui.PAUSE = 0
    return pyautogui


# ---------- monitores e janelas ----------
def _tamanho_pontos():
    try:
        import pyautogui
        w, h = pyautogui.size()
        return int(w), int(h)
    except Exception:
        pass
    if MAC:
        b = _osa('tell application "Finder" to get bounds of window of desktop')
        try:
            _, _, w, h = [int(x) for x in b.replace(" ", "").split(",")]
            return w, h
        except Exception:
            pass
    try:
        import mss
        with mss.mss() as m:
            d = m.monitors[1]
            return d["width"], d["height"]
    except Exception:
        pass
    try:
        from PIL import ImageGrab
        return ImageGrab.grab().size
    except Exception as e:
        sair(f"Não consegui medir a tela: {e}. Instale o pyautogui ou o mss (python -m pip install pyautogui mss).")


def monitores():
    """Lista de telas com o retângulo em coordenadas do mouse. Com o mss instalado, todas; sem ele, a principal."""
    try:
        import mss
        with mss.mss() as m:
            lista = [{"h": i, "ret": [d["left"], d["top"], d["left"] + d["width"], d["top"] + d["height"]]}
                     for i, d in enumerate(m.monitors[1:], 1)]
        if lista:
            lista.sort(key=lambda x: (x["ret"][:2] != [0, 0], x["ret"][0], x["ret"][1]))
            return lista
    except Exception:
        pass
    w, h = _tamanho_pontos()
    return [{"h": 1, "ret": [0, 0, w, h]}]


_OSA_JANELA = (
    'tell application "System Events"\n'
    '  tell (first application process whose frontmost is true)\n'
    '    set u to unix id as text\n'
    '    set n to name as text\n'
    '    set w to ""\n'
    '    try\n'
    '      set w to name of front window\n'
    '    end try\n'
    '    return u & "|" & n & "|" & w\n'
    '  end tell\n'
    'end tell'
)


def janela_id():
    """Identificador da janela ativa (texto), ou None quando o sistema não informa."""
    if LINUX:
        r = _rodar(["xdotool", "getactivewindow"])
        return r.strip() if r and r.strip() else None
    r = _osa(_OSA_JANELA)
    return r.strip() if r and r.strip() else None


def titulo(h):
    if not h:
        return ""
    if LINUX:
        return (_rodar(["xdotool", "getwindowname", str(h)]) or "").strip()
    partes = str(h).split("|", 2)
    if len(partes) == 3:
        _, app_nome, win_nome = partes
        return " - ".join(x for x in (win_nome, app_nome) if x)
    nome = _osa('tell application "System Events" to return name of (first application process whose frontmost is true)')
    janela = partes[1] if len(partes) > 1 else ""
    return " - ".join(x for x in (janela, (nome or "").strip()) if x)


def janela_ativa():
    return titulo(janela_id()), 1


def listar_janelas():
    if LINUX:
        saida = _rodar(["wmctrl", "-l"])
        if saida is None:
            sair("Para listar e focar janelas no Linux, instale o wmctrl (sudo apt install wmctrl).")
        achadas = []
        for linha in saida.splitlines():
            p = linha.split(None, 3)
            if len(p) == 4 and p[3].strip() and not p[3].startswith("Jarvis · esfera"):
                achadas.append((p[0], p[3].strip()))
        return achadas
    saida = _osa('tell application "System Events" to get name of every application process whose visible is true')
    if saida is None:
        sair("O macOS não deixou listar os aplicativos: dê permissão de Automação/Acessibilidade ao Terminal/Python.")
    return [(n.strip(), n.strip()) for n in saida.split(",") if n.strip() and n.strip() != "Python"]


def focar(parte):
    p = parte.lower()
    for h, t in listar_janelas():
        if p in t.lower():
            if LINUX:
                _rodar(["wmctrl", "-i", "-a", h])
            else:
                nome = t.replace("\\", "\\\\").replace('"', '\\"')
                _osa(f'tell application "System Events" to set frontmost of process "{nome}" to true')
            time.sleep(0.35)
            return t
    return None


# ---------- ver ----------
def cursor():
    try:
        import pyautogui
        x, y = pyautogui.position()
        return int(x), int(y)
    except Exception:       # sem pyautogui não dá para ler o mouse: um ponto longe da tela (não aciona o freio)
        return FORA, FORA


def _capturar_mac(bbox):
    """macOS: screencapture -R usa coordenadas lógicas (pontos) direto, inclusive em tela Retina e vários monitores."""
    if not MAC or not shutil.which("screencapture"):
        return None
    try:
        from PIL import Image
        l, t, r, b = bbox
        tmp = os.path.join(tempfile.gettempdir(), "jarvis_pc_cap.png")
        res = subprocess.run(["screencapture", "-x", f"-R{int(l)},{int(t)},{int(r - l)},{int(b - t)}", tmp],
                             capture_output=True, timeout=6)
        if res.returncode != 0 or not os.path.exists(tmp):
            return None
        with Image.open(tmp) as im:
            return im.convert("RGB")
    except Exception:
        return None


def capturar(bbox):
    """Captura o retângulo (coordenadas do mouse) e devolve a imagem no tamanho desse retângulo."""
    from PIL import ImageGrab
    l, t, r, b = bbox
    img = None
    if MAC:
        img = _capturar_mac(bbox) or _capturar_mss(bbox)
    if img is None:
        try:
            img = ImageGrab.grab(bbox=(l, t, r, b))
        except Exception:
            img = _capturar_mss(bbox)
    if img is None:
        dica = " (macOS: dê a permissão Gravação de Tela ao Terminal/Python em Ajustes do Sistema > Privacidade e Segurança)" if MAC else ""
        sair(f"Não consegui capturar a tela (Pillow e mss falharam){dica}. No Linux, a captura precisa de X11 e do Pillow com XCB, ou do mss (python -m pip install mss).")
    img = img.convert("RGB")
    if img.size != (r - l, b - t):         # Retina: a captura vem com o dobro de pixels
        img = img.resize((r - l, b - t))
    return img


def _capturar_mss(bbox):
    try:
        import mss
        from PIL import Image
        l, t, r, b = bbox
        with mss.mss() as m:
            c = m.grab({"left": l, "top": t, "width": r - l, "height": b - t})
            return Image.frombytes("RGB", c.size, c.bgra, "raw", "BGRX")
    except Exception:
        return None


# ---------- agir ----------
def andar(x, y, dur=0.32):
    pag = _pag()
    x0, y0 = cursor()
    passos = 20
    for i in range(1, passos + 1):
        f = i / passos
        f = f * f * (3 - 2 * f)
        pag.moveTo(round(x0 + (x - x0) * f), round(y0 + (y - y0) * f))
        time.sleep(dur / passos)
    pag.moveTo(x, y)
    time.sleep(0.06)


def clicar(x, y, direito=False, duplo=False):
    pag = _pag()
    andar(x, y)
    for _ in range(2 if duplo else 1):
        pag.click(button="right" if direito else "left")
        time.sleep(0.09)


def arrastar(x1, y1, x2, y2):
    pag = _pag()
    andar(x1, y1)
    pag.mouseDown()
    time.sleep(0.12)
    andar(x2, y2, 0.55)
    time.sleep(0.1)
    pag.mouseUp()


def rolar(n):
    """n positivo desce, negativo sobe."""
    pag = _pag()
    for _ in range(abs(n)):
        pag.scroll(-3 if n > 0 else 3)
        time.sleep(0.04)


NOMES = {"enter": "enter", "esc": "esc", "escape": "esc", "tab": "tab", "backspace": "backspace", "delete": "delete",
         "del": "delete", "espaco": "space", "espaço": "space", "space": "space", "cima": "up", "baixo": "down",
         "esquerda": "left", "direita": "right", "up": "up", "down": "down", "left": "left", "right": "right",
         "home": "home", "end": "end", "pageup": "pageup", "pagedown": "pagedown", "insert": "insert",
         "ctrl": "ctrl", "control": "ctrl", "shift": "shift", "alt": "option" if MAC else "alt",
         "win": "command" if MAC else "winleft", "cmd": "command" if MAC else "winleft", "command": "command" if MAC else "winleft",
         "option": "option" if MAC else "alt", "printscreen": "printscreen", "+": "+", "mais": "+", "-": "-", "menos": "-"}
NOMES.update({f"f{i}": f"f{i}" for i in range(1, 13)})
PROIBIDAS_POSIX = ({"ctrl", "command", "q"}, {"command", "q"}, {"ctrl", "alt", "backspace"}, {"winleft", "l"})


def tecla(combo, nomes):
    teclas = []
    for n in nomes:
        k = n.strip().lower()
        if k in NOMES:
            teclas.append(NOMES[k])
        elif len(k) == 1:
            teclas.append(k)
        else:
            sair(f"Não conheço a tecla '{n}'. Veja a lista em: python pc.py ajuda")
    if set(teclas) in PROIBIDAS_POSIX:
        sair("Essa combinação não é permitida.")
    pag = _pag()
    pag.hotkey(*teclas, interval=0.03)


def _escrever(trecho):
    if not trecho:
        return
    if LINUX:
        if shutil.which("xdotool"):
            subprocess.run(["xdotool", "type", "--delay", "30", "--clearmodifiers", "--", trecho])
            return
        if any(ord(c) > 127 for c in trecho):
            sair("Para digitar acentos no Linux, instale o xdotool (sudo apt install xdotool). Nada com acento foi digitado.")
        _pag().write(trecho, interval=0.03)
        return
    # macOS: keystroke direto só é confiável para ASCII; com acentos (ç, ã, é...), cola via pbcopy preservando a área de transferência
    if any(ord(c) > 127 for c in trecho) and shutil.which("pbcopy"):
        ant = None
        if shutil.which("pbpaste"):
            try:
                r = subprocess.run(["pbpaste"], capture_output=True, timeout=2)
                if r.returncode == 0:
                    ant = r.stdout
            except Exception:
                pass
        try:
            subprocess.run(["pbcopy"], input=trecho.encode("utf-8"), timeout=3, check=True)
            if _osa('tell application "System Events" to keystroke "v" using command down', tempo=10) is None:
                sair("O macOS não deixou digitar: dê permissão de Acessibilidade ao Terminal/Python.")
            time.sleep(0.12)
        finally:
            if ant is not None:
                try:
                    subprocess.run(["pbcopy"], input=ant, timeout=3)
                except Exception:
                    pass
        return
    seguro = trecho.replace("\\", "\\\\").replace('"', '\\"')
    if _osa(f'tell application "System Events" to keystroke "{seguro}"', tempo=60) is None:
        sair("O macOS não deixou digitar: dê permissão de Acessibilidade ao Terminal/Python.")


def digitar(texto, alvo):
    """Digita linha por linha; antes de cada pedaço confere se a janela ativa ainda é a mesma."""
    trecho = ""
    for n, ch in enumerate(texto + "\0"):
        if ch in "\n\t\0":
            if janela_id() != alvo:
                sair(f"PAREI no caractere {n} de {len(texto)}: a janela ativa mudou no meio da digitação. Rode ver e confira antes de continuar.")
            _escrever(trecho)
            trecho = ""
            if ch == "\n":
                tecla("enter", ["enter"])
            elif ch == "\t":
                tecla("tab", ["tab"])
        elif ch != "\r":
            trecho += ch
        time.sleep(0)


def abrir_programa(alvo):
    if MAC:
        subprocess.Popen(["open", "-a", alvo])
    else:
        exe = shutil.which(alvo)
        if not exe:
            sair(f"Não achei o programa '{alvo}'.")
        subprocess.Popen([exe], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
