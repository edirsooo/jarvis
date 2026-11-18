"""Mãos do Jarvis: mouse e teclado do computador do usuário, à vista dele.

O ciclo é sempre: VER a tela, AGIR, VER de novo.

  python pc.py ver [--tela N] [--grade]
      Tira uma captura da tela (a da janela ativa, ou a tela N) e salva em telas\\.
      Abra a imagem com a ferramenta de leitura para enxergar. Todas as coordenadas
      dos outros comandos são os pixels DESSA imagem (x da esquerda, y de cima).
      --grade desenha linhas numeradas a cada 100 px para medir melhor.
  python pc.py zoom X Y
      Recorte em tamanho real ao redor do ponto, para ler letra pequena.
  python pc.py clicar X Y [--direito] [--duplo]
  python pc.py mover X Y
  python pc.py arrastar X1 Y1 X2 Y2
  python pc.py rolar N [X Y]            N positivo desce, negativo sobe (em "cliques" da rodinha)
  python pc.py digitar "texto" [--enter]
  python pc.py tecla "ctrl+l"           enter, esc, tab, backspace, delete, espaco, setas (cima, baixo,
                                        esquerda, direita), home, end, pageup, pagedown, f1..f12,
                                        combinações com ctrl, shift, alt, win
  python pc.py abrir <endereço, caminho ou programa>
  python pc.py janelas                  lista as janelas abertas
  python pc.py focar "parte do título"  traz uma janela para a frente
  python pc.py telas                    lista os monitores
  python pc.py esperar S

Depois de cada ação sai uma captura nova sozinha (use --sem-ver para pular, --espera S para
dar mais tempo à tela). O mouse anda devagar de propósito: o usuário está olhando.

Travas:
- digitar e tecla só agem se a janela ativa for a mesma da última captura (se o usuário clicou em
  outra coisa, a ferramenta para e pede para ver de novo). Por isso não use --sem-ver antes de digitar.
- Enter em conversa ou e-mail (WhatsApp, Telegram, Discord, Gmail, Outlook...) é recusado: enviar é com o usuário.
- Parada de emergência: se o usuário levar o mouse ao canto de cima à esquerda da tela principal,
  os comandos param de agir.

A pasta da missão vem da variável JARVIS_MISSAO (ou a pasta atual).
"""
import ctypes, json, os, re, subprocess, sys, time
from ctypes import wintypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

MISSAO = os.environ.get("JARVIS_MISSAO") or os.getcwd()
TELAS = os.path.join(MISSAO, "telas")
TRAB = os.path.join(MISSAO, "trabalho")
ARQ_ESTADO = os.path.join(TRAB, "pc_estado.json")
ARQ_LOG = os.path.join(TRAB, "pc_acoes.log")
LARGURA_MAX = 1280

u32 = ctypes.windll.user32
ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


u32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
u32.GetForegroundWindow.restype = wintypes.HWND
u32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
u32.MonitorFromWindow.restype = wintypes.HANDLE
u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]


def sair(msg):
    print(msg)
    sys.exit(1)


def registrar(txt):
    try:
        os.makedirs(TRAB, exist_ok=True)
        with open(ARQ_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {txt}\n")
    except Exception:
        pass


def ler_estado():
    try:
        with open(ARQ_ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def gravar_estado(e):
    os.makedirs(TRAB, exist_ok=True)
    with open(ARQ_ESTADO, "w", encoding="utf-8") as f:
        json.dump(e, f)


# ---------- monitores e janelas ----------
def monitores():
    lista = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    def cb(h, _dc, r, _l):
        lista.append({"h": h, "ret": [r.contents.left, r.contents.top, r.contents.right, r.contents.bottom]})
        return True
    u32.EnumDisplayMonitors(None, None, cb, 0)
    lista.sort(key=lambda m: (m["ret"][:2] != [0, 0], m["ret"][0], m["ret"][1]))   # a principal é a 1
    return lista


def titulo(h):
    n = u32.GetWindowTextLengthW(h)
    b = ctypes.create_unicode_buffer(n + 1)
    u32.GetWindowTextW(h, b, n + 1)
    return b.value


def janela_ativa():
    h = u32.GetForegroundWindow()
    if not h:
        return "", 1
    hm = u32.MonitorFromWindow(h, 2)
    num = 1
    for i, m in enumerate(monitores(), 1):
        if m["h"] == hm:
            num = i
    return titulo(h), num


def listar_janelas():
    achadas = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        if u32.IsWindowVisible(h) and u32.GetWindowTextLengthW(h):
            t = titulo(h)
            r = wintypes.RECT()
            u32.GetWindowRect(h, ctypes.byref(r))
            if t not in ("Program Manager",) and r.right - r.left > 60 and not t.startswith("Jarvis · esfera"):
                achadas.append((h, t))
        return True
    u32.EnumWindows(cb, 0)
    return achadas


def focar(parte):
    p = parte.lower()
    for h, t in listar_janelas():
        if p in t.lower():
            if u32.IsIconic(h):
                u32.ShowWindow(h, 9)
            # o Windows só deixa trazer para a frente quem acabou de mandar uma tecla; usa uma tecla
            # sem função (o Alt abriria o menu do programa e a digitação seguinte viraria atalho)
            u32.keybd_event(0xE8, 0, 0, 0)
            u32.keybd_event(0xE8, 0, 2, 0)
            u32.SetForegroundWindow(h)
            time.sleep(0.35)
            return t
    return None


# ---------- ver ----------
def cursor():
    p = wintypes.POINT()
    u32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def nome_tela(rotulo):
    os.makedirs(TELAS, exist_ok=True)
    n = len([a for a in os.listdir(TELAS) if a.endswith(".jpg")]) + 1
    s = re.sub(r"[^a-z0-9]+", "-", rotulo.lower()).strip("-")[:40] or "tela"
    return os.path.join(TELAS, f"{n:03d}_{s}.jpg")


def ver(num=None, grade=False, rotulo="pc"):
    from PIL import ImageGrab, ImageDraw
    mons = monitores()
    tit, ativa = janela_ativa()
    est = ler_estado()
    if num is None:
        num = ativa
    num = max(1, min(len(mons), int(num)))
    l, t, r, b = mons[num - 1]["ret"]
    img = ImageGrab.grab(bbox=(l, t, r, b), all_screens=True).convert("RGB")
    escala = max(1.0, img.width / LARGURA_MAX)
    if escala > 1:
        img = img.resize((round(img.width / escala), round(img.height / escala)))
    d = ImageDraw.Draw(img)
    if grade:
        for x in range(100, img.width, 100):
            d.line([(x, 0), (x, img.height)], fill=(255, 107, 26), width=1)
            d.text((x + 3, 3), str(x), fill=(255, 107, 26))
        for y in range(100, img.height, 100):
            d.line([(0, y), (img.width, y)], fill=(255, 107, 26), width=1)
            d.text((3, y + 3), str(y), fill=(255, 107, 26))
    cx, cy = cursor()
    mx, my = (cx - l) / escala, (cy - t) / escala
    if 0 <= mx < img.width and 0 <= my < img.height:      # a captura não traz o ponteiro: marca onde ele está
        d.line([(mx - 9, my), (mx + 9, my)], fill=(255, 40, 40), width=2)
        d.line([(mx, my - 9), (mx, my + 9)], fill=(255, 40, 40), width=2)
    arq = nome_tela(rotulo)
    img.save(arq, "JPEG", quality=72)
    gravar_estado({"ret": [l, t, r, b], "escala": escala, "tela": num, "tam": [img.width, img.height],
                   "cursor": [cx, cy], "janela": u32.GetForegroundWindow() or 0})
    print(f'JANELA ATIVA: "{tit[:90]}" (na tela {ativa})')
    print(f"CAPTURA: {arq}")
    print(f"  imagem {img.width}x{img.height} da tela {num} de {len(mons)}; a cruz vermelha é o ponteiro do mouse"
          + (f" em ({round(mx)},{round(my)})" if 0 <= mx < img.width and 0 <= my < img.height else " (fora desta tela)"))
    if est and est.get("tela") != num:
        print(f"  ATENÇÃO: mudou da tela {est.get('tela')} para a tela {num}; as coordenadas agora são desta imagem.")
    print("  Leia essa imagem para enxergar a tela antes de agir.")


def zoom(x, y):
    from PIL import ImageGrab
    e = precisa_estado()
    rx, ry = real(x, y, e)
    l, t, r, b = e["ret"]
    L, A = 640, 360
    x0 = max(l, min(r - L, rx - L // 2))
    y0 = max(t, min(b - A, ry - A // 2))
    img = ImageGrab.grab(bbox=(x0, y0, x0 + L, y0 + A), all_screens=True).convert("RGB")
    arq = nome_tela("pc-zoom")
    img.save(arq, "JPEG", quality=85)
    print(f"ZOOM: {arq}")
    print(f"  recorte em tamanho real; o canto de cima à esquerda dele é o ponto ({round((x0 - l) / e['escala'])},{round((y0 - t) / e['escala'])}) da captura")


# ---------- agir ----------
def precisa_estado():
    e = ler_estado()
    if not e:
        sair("Rode primeiro: python pc.py ver   (as coordenadas são da captura)")
    return e


def real(x, y, e):
    L, A = e["tam"]
    if not (0 <= x <= L and 0 <= y <= A):
        sair(f"Ponto ({x},{y}) fora da captura ({L}x{A}). Rode ver de novo e confira as coordenadas.")
    l, t, _, _ = e["ret"]
    return round(l + x * e["escala"]), round(t + y * e["escala"])


def freio():
    x, y = cursor()
    if x <= 3 and y <= 3:
        sair("PARADO: o usuário levou o mouse ao canto da tela para interromper. Não aja mais; encerre e avise.")


CONVERSAS = re.compile(r"whatsapp|telegram|discord|messenger|instagram|outlook|gmail|e-mail|email|slack|teams", re.I)


def mesma_janela():
    """Teclado só vai para a janela que estava ativa na última captura: se o usuário trocou de janela
    no meio, o texto cairia no lugar errado (numa conversa, por exemplo)."""
    e = precisa_estado()
    agora = u32.GetForegroundWindow() or 0
    if e.get("janela") and agora != e["janela"]:
        sair(f'PAREI: a janela ativa mudou para "{titulo(agora)[:70]}" desde a última captura (o usuário pode ter clicado em outra coisa). '
             "Nada foi digitado. Rode ver, confira onde está o foco e só então continue.")
    return agora


def sem_enviar(combo):
    """Enter numa conversa ou e-mail envia a mensagem: essa parte é sempre do usuário."""
    t = titulo(u32.GetForegroundWindow() or 0)
    if "enter" in combo.lower() and CONVERSAS.search(t):
        sair(f'NÃO FIZ: Enter na janela "{t[:60]}" pode enviar uma mensagem. Enviar é sempre o usuário quem faz; deixe o texto pronto e avise.')


def mandar(*entradas):
    v = (INPUT * len(entradas))(*entradas)
    u32.SendInput(len(entradas), v, ctypes.sizeof(INPUT))


def rato(flags, dado=0):
    return INPUT(type=0, u=_U(mi=MOUSEINPUT(0, 0, dado & 0xFFFFFFFF, flags, 0, 0)))


def andar(x, y, dur=0.32):
    x0, y0 = cursor()
    passos = 20
    for i in range(1, passos + 1):
        f = i / passos
        f = f * f * (3 - 2 * f)
        u32.SetCursorPos(round(x0 + (x - x0) * f), round(y0 + (y - y0) * f))
        time.sleep(dur / passos)
    u32.SetCursorPos(x, y)
    time.sleep(0.06)


def clicar(x, y, direito=False, duplo=False):
    andar(x, y)
    baixo, cima = (0x0008, 0x0010) if direito else (0x0002, 0x0004)
    for _ in range(2 if duplo else 1):
        mandar(rato(baixo))
        time.sleep(0.05)
        mandar(rato(cima))
        time.sleep(0.09)


def arrastar(x1, y1, x2, y2):
    andar(x1, y1)
    mandar(rato(0x0002))
    time.sleep(0.12)
    andar(x2, y2, 0.55)
    time.sleep(0.1)
    mandar(rato(0x0004))


VK = {"enter": 0x0D, "esc": 0x1B, "escape": 0x1B, "tab": 0x09, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
      "espaco": 0x20, "espaço": 0x20, "space": 0x20, "cima": 0x26, "baixo": 0x28, "esquerda": 0x25, "direita": 0x27,
      "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27, "home": 0x24, "end": 0x23, "pageup": 0x21,
      "pagedown": 0x22, "insert": 0x2D, "ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
      "printscreen": 0x2C, "+": 0xBB, "mais": 0xBB, "-": 0xBD, "menos": 0xBD}
VK.update({f"f{i}": 0x6F + i for i in range(1, 13)})
ESTENDIDAS = {0x26, 0x28, 0x25, 0x27, 0x24, 0x23, 0x21, 0x22, 0x2D, 0x2E, 0x5B}
PROIBIDAS = ({"win", "l"}, {"ctrl", "alt", "delete"}, {"ctrl", "alt", "del"})


def tecla_vk(nome):
    n = nome.strip().lower()
    if n in VK:
        return VK[n]
    if len(n) == 1:
        v = u32.VkKeyScanW(ord(n)) & 0xFF
        if v != 0xFF:
            return v
    sair(f"Não conheço a tecla '{nome}'. Veja a lista em: python pc.py ajuda")


def tecla(combo):
    nomes = [p for p in re.split(r"\s*\+\s*", combo.strip()) if p] if combo.strip() not in ("+",) else ["+"]
    if {n.lower() for n in nomes} in PROIBIDAS:
        sair("Essa combinação não é permitida.")
    vks = [tecla_vk(n) for n in nomes]
    for v in vks:
        mandar(INPUT(type=1, u=_U(ki=KEYBDINPUT(v, 0, 0x0001 if v in ESTENDIDAS else 0, 0, 0))))
        time.sleep(0.03)
    for v in reversed(vks):
        mandar(INPUT(type=1, u=_U(ki=KEYBDINPUT(v, 0, 0x0002 | (0x0001 if v in ESTENDIDAS else 0), 0, 0))))
        time.sleep(0.03)


def digitar(texto):
    alvo = u32.GetForegroundWindow()
    for n, ch in enumerate(texto):
        if u32.GetForegroundWindow() != alvo:
            sair(f"PAREI no caractere {n} de {len(texto)}: a janela ativa mudou no meio da digitação. Rode ver e confira antes de continuar.")
        if ch in "\r":
            continue
        if ch == "\n":
            tecla("enter")
            continue
        if ch == "\t":
            tecla("tab")
            continue
        dado = ch.encode("utf-16-le")
        for i in range(0, len(dado), 2):
            cod = int.from_bytes(dado[i:i + 2], "little")
            mandar(INPUT(type=1, u=_U(ki=KEYBDINPUT(0, cod, 0x0004, 0, 0))))
            time.sleep(0.012)
            mandar(INPUT(type=1, u=_U(ki=KEYBDINPUT(0, cod, 0x0004 | 0x0002, 0, 0))))
        time.sleep(0.03)      # rápido demais e alguns programas embaralham as letras


def abrir_site(url):
    """Sites abrem no navegador e perfil escolhidos pelo usuário (config.json do Jarvis)."""
    try:
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, raiz)
        import janelas
        with open(os.path.join(raiz, "config.json"), encoding="utf-8") as f:
            janelas.abrir_site(url, json.load(f))
    except Exception:
        os.startfile(url)


def abrir(alvo):
    if re.match(r"^https?://", alvo):
        abrir_site(alvo)
    elif re.match(r"^[a-z]+://", alvo) or os.path.exists(alvo):
        os.startfile(alvo)
    elif re.match(r"^[\w.-]+\.[a-z]{2,}(/.*)?$", alvo):
        abrir_site("https://" + alvo)
    else:
        subprocess.Popen(f'start "" "{alvo}"', shell=True)


def opcao(args, nome, padrao=None):
    if nome in args:
        i = args.index(nome)
        if i + 1 < len(args):
            return args[i + 1]
    return padrao


def numeros(args, qtd):
    try:
        return [int(float(v)) for v in args[:qtd]]
    except Exception:
        sair("Faltaram as coordenadas (números). Veja: python pc.py ajuda")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    a = sys.argv[1:]
    if not a or a[0] in ("ajuda", "-h", "--help"):
        print(__doc__)
        return
    cmd, r = a[0], a[1:]
    livres = [x for x in r if not x.startswith("--")]
    for chave in ("--tela", "--espera"):          # o valor dessas opções não é argumento do comando
        v = opcao(r, chave)
        if v in livres:
            livres.remove(v)

    if cmd == "ver":
        ver(opcao(r, "--tela"), "--grade" in r)
        return
    if cmd == "telas":
        _, ativa = janela_ativa()
        for i, m in enumerate(monitores(), 1):
            l, t, rr, b = m["ret"]
            print(f"tela {i}: {rr - l}x{b - t}" + (" (principal)" if (l, t) == (0, 0) else "") + (" ← janela ativa" if i == ativa else ""))
        return
    if cmd == "janelas":
        for _, t in listar_janelas():
            print("-", t[:110])
        return
    if cmd == "esperar":
        time.sleep(min(30, float(livres[0]) if livres else 1))
        ver(ler_estado() and ler_estado().get("tela"))
        return
    if cmd == "zoom":
        x, y = numeros(livres, 2)
        zoom(x, y)
        return

    freio()
    feito = ""
    if cmd == "clicar":
        e = precisa_estado()
        x, y = numeros(livres, 2)
        rx, ry = real(x, y, e)
        clicar(rx, ry, "--direito" in r, "--duplo" in r)
        feito = f"clique{' direito' if '--direito' in r else ''}{' duplo' if '--duplo' in r else ''} em ({x},{y})"
    elif cmd == "mover":
        e = precisa_estado()
        x, y = numeros(livres, 2)
        andar(*real(x, y, e))
        feito = f"mouse em ({x},{y})"
    elif cmd == "arrastar":
        e = precisa_estado()
        x1, y1, x2, y2 = numeros(livres, 4)
        arrastar(*real(x1, y1, e), *real(x2, y2, e))
        feito = f"arrastei de ({x1},{y1}) até ({x2},{y2})"
    elif cmd == "rolar":
        n = numeros(livres, 1)[0]
        if len(livres) >= 3:
            andar(*real(*numeros(livres[1:], 2), precisa_estado()))
        for _ in range(abs(n)):
            mandar(rato(0x0800, -120 if n > 0 else 120))
            time.sleep(0.04)
        feito = f"rolei {abs(n)} para {'baixo' if n > 0 else 'cima'}"
    elif cmd == "digitar":
        if not livres:
            sair('Faltou o texto: python pc.py digitar "texto"')
        mesma_janela()
        if "--enter" in r or "\n" in livres[0]:
            sem_enviar("enter")
        digitar(livres[0])
        if "--enter" in r:
            time.sleep(0.15)
            tecla("enter")
        feito = f"digitei {len(livres[0])} caracteres" + (" e dei enter" if "--enter" in r else "")
    elif cmd == "tecla":
        if not livres:
            sair('Faltou a tecla: python pc.py tecla "ctrl+l"')
        mesma_janela()
        sem_enviar(livres[0])
        tecla(livres[0])
        feito = f"tecla {livres[0]}"
    elif cmd == "abrir":
        if not livres:
            sair("Faltou o que abrir.")
        abrir(livres[0])
        feito = f"abri {livres[0]}"
        time.sleep(1.6)
    elif cmd == "focar":
        t = focar(livres[0]) if livres else None
        if not t:
            sair("Não achei janela com esse título. Veja: python pc.py janelas")
        feito = f'janela "{t[:70]}" na frente'
    else:
        print(__doc__)
        return

    registrar(f"{cmd} {' '.join(r)[:200]}")
    print("FEITO:", feito)
    if "--sem-ver" not in r:
        time.sleep(float(opcao(r, "--espera", 0.9)))
        ver(None, rotulo="pc-" + cmd)      # a captura segue a janela ativa, em qualquer monitor


if __name__ == "__main__":
    main()
