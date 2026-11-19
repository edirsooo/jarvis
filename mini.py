"""Esfera flutuante do Jarvis: janela sem moldura, sempre por cima, quieta no canto (só desvia do mouse no modo "livre").

- Chegar com o mouse perto: ela pula para o canto mais longe.
- Segurar SHIFT e chegar perto: ela fica parada; arrastar move, clicar abre o painel inteiro.
- Com missão rodando, a placa mostra quem está trabalhando e o que está fazendo agora, com dois botões
  (SHIFT + clique): PARAR interrompe as missões, ABRIR volta o painel.
"""
import ctypes, json, math, random, sys, threading, time, tkinter as tk, urllib.request

PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 4747
BASE = f"http://127.0.0.1:{PORTA}"
L, A = 300, 312
ESF = 236                  # largura da área da esfera (à esquerda); o mini mago fica em pé à direita, olhando para ela
KX, KY = 0.34, 0.3
CHAVE = "#010203"          # cor que vira transparente (Windows); no macOS o fundo é transparente de verdade
WIN, MAC = sys.platform == "win32", sys.platform == "darwin"
if not WIN and not MAC:
    CHAVE = "#0b0c10"      # Linux: o Tk não tem cor transparente; a esfera fica num quadro escuro
MONO = "Consolas" if WIN else "Menlo" if MAC else "DejaVu Sans Mono"
SANS = "Segoe UI" if WIN else "Helvetica Neue" if MAC else "DejaVu Sans"
E = {"estado": "dormindo", "mudo": False, "nivel": 0.0, "legenda": "", "ativas": 0, "total": 0, "acao": "", "quem": "", "pc": False, "canto": "dir-baixo", "fixo": False, "vivo": True, "mago_v": 0}
MAGO = {"v": None, "poses": None}       # poses desenhadas pela tela grande (mago.js), lidas de /api/visual?poses=1

PALETA = {
    "dormindo": ((70, 78, 100), (40, 44, 58)), "ouvindo": ((90, 215, 255), (230, 250, 255)),
    "pensando": ((255, 210, 63), (255, 107, 26)), "falando": ((255, 107, 26), (255, 190, 120)),
    "trabalhando": ((25, 195, 125), (255, 107, 26)), "mudo": ((120, 40, 50), (60, 30, 36)),
}
ALVO = {"dormindo": (.15, .03, .74), "ouvindo": (.4, .05, .92), "pensando": (1.7, .1, .82),
        "falando": (.55, .06, .95), "trabalhando": (.8, .05, .84), "mudo": (.05, .01, .68)}
NOMES = {"dormindo": "DORMINDO", "ouvindo": "OUVINDO", "pensando": "PENSANDO", "falando": "FALANDO",
         "trabalhando": "TRABALHANDO", "mudo": "MIC DESLIGADO"}


def paleta_da_cor(cor, e):
    """A cor escolhida para o Jarvis (menu Aparência), com o brilho de cada estado. Igual à paletaDaCor do app.js."""
    if not cor or len(str(cor)) != 7:
        return None
    try:
        n = int(str(cor)[1:], 16)
    except ValueError:
        return None
    c = [n >> 16, (n >> 8) & 255, n & 255]
    k = lambda f: [min(255, v * f) for v in c]
    claro = [v + (255 - v) * .55 for v in c]
    return {"dormindo": [k(.55), k(.3)], "ouvindo": [c, claro], "pensando": [claro, k(.75)], "falando": [c, claro],
            "trabalhando": [c, k(.7)], "mudo": [[120, 40, 50], [60, 30, 36]]}.get(e)


# a esfera do canto segue a forma escolhida na tela grande (orbe, fantasma, chama, elétrica, espírito), em cubinhos de luz
PALETA_FORMA = {
    "fantasma": {"dormindo": [[120, 140, 170], [70, 80, 100]], "ouvindo": [[170, 240, 255], [240, 255, 255]], "pensando": [[220, 230, 255], [170, 180, 255]], "falando": [[200, 255, 240], [255, 255, 255]], "trabalhando": [[150, 255, 200], [220, 255, 240]], "mudo": [[110, 70, 80], [60, 40, 50]]},
    "chama": {"dormindo": [[150, 50, 20], [90, 30, 14]], "ouvindo": [[255, 170, 60], [255, 240, 180]], "pensando": [[255, 120, 30], [255, 220, 90]], "falando": [[255, 140, 40], [255, 230, 150]], "trabalhando": [[255, 130, 40], [255, 200, 80]], "mudo": [[90, 40, 36], [50, 30, 28]]},
    "eletrica": {"dormindo": [[60, 70, 140], [40, 40, 90]], "ouvindo": [[120, 220, 255], [240, 250, 255]], "pensando": [[180, 120, 255], [120, 220, 255]], "falando": [[140, 200, 255], [255, 255, 255]], "trabalhando": [[100, 160, 255], [200, 140, 255]], "mudo": [[70, 40, 70], [40, 30, 45]]},
    "espirito": {"dormindo": [[150, 120, 60], [90, 70, 40]], "ouvindo": [[255, 220, 140], [255, 250, 220]], "pensando": [[255, 200, 90], [255, 160, 60]], "falando": [[255, 210, 120], [255, 245, 200]], "trabalhando": [[230, 200, 110], [140, 220, 160]], "mudo": [[90, 60, 50], [50, 40, 36]]},
}
VOX = {}


def _dentro(fm):
    def fant(x, y, z):
        r = math.hypot(x, z)
        if y < -.05:
            return r * r + (y + .05) ** 2 / .9 <= .74
        return r <= .86 and y <= .92 - .16 * (.5 + .5 * math.sin(math.atan2(z, x) * 4))

    def chama(x, y, z):
        r = math.hypot(x, z)
        if y >= .25:
            return r * r + (y - .25) ** 2 <= .6
        k = (y + 1.25) / 1.5
        return k > 0 and r <= .77 * k ** 1.25

    def esp(x, y, z):
        if x * x + (y + .3) ** 2 + z * z <= .34:
            return True
        for i in range(1, 8):
            u = i / 7
            px_, py_, rr = .38 * math.sin(u * 2.8), .1 + u * .95, .44 * (1 - u * .78)
            if (x - px_) ** 2 + (y - py_) ** 2 + z * z <= rr * rr:
                return True
        return False
    return {"fantasma": fant, "chama": chama, "espirito": esp,
            "eletrica": lambda x, y, z: x * x + y * y + z * z <= .6}.get(fm, lambda x, y, z: x * x + y * y + z * z <= .92)


def vox_forma(fm):
    """casca de cubinhos da forma (grade 13x13x13, mais leve que a da tela grande) + enfeites: espinhos, órbitas, brasas"""
    if fm in VOX:
        return VOX[fm]
    n, d = 13, _dentro(fm)
    cel = 2.6 / n
    P = lambda i: -1.3 + (i + .5) * cel
    em = lambda i, j, k: 0 <= i < n and 0 <= j < n and 0 <= k < n and d(P(i), P(j), P(k))
    L = []
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if em(i, j, k) and not all(em(*q) for q in ((i + 1, j, k), (i - 1, j, k), (i, j + 1, k), (i, j - 1, k), (i, j, k + 1), (i, j, k - 1))):
                    L.append((P(i), P(j), P(k), random.random() * 6.28, .82 + random.random() * .3, "corpo", 0))
    if fm == "eletrica":
        for a in range(10):
            yy = 1 - (a + .5) / 5
            rr = math.sqrt(max(0, 1 - yy * yy))
            th = a * 2.39996
            r = .82
            while r < 1.36:
                L.append((math.cos(th) * rr * r, yy * r, math.sin(th) * rr * r, random.random() * 6.28, 1.15, "raio", a))
                r += cel
    if fm == "espirito":
        L += [(0, 0, 0, a / 6 * 6.28, 1.2, "orbita", 0) for a in range(6)]
    if fm == "chama":
        for _ in range(10):
            th, r = random.random() * 6.28, random.random() * .45
            L.append((math.cos(th) * r, 0, math.sin(th) * r, random.random() * 6.28, 1.2, "brasa", 0))
    VOX[fm] = (L, cel)
    return VOX[fm]


def vox_pos(fm, c, t):
    x, y, z, f, tom_, k, g = c
    if k == "orbita":
        a = f + t * .8
        return math.cos(a) * 1.3, -.15 + .25 * math.sin(a * 2 + f), math.sin(a) * 1.3, 1.25
    if k == "brasa":
        u = (t * .45 + f / 6.28) % 1
        return x * (1 - u * .6) + .12 * math.sin(t * 3 + f), -.55 - u * 1.05, z * (1 - u * .6), .9 * (1 - u)
    if k == "raio":
        if math.sin(t * 9 + g * 2.3) < -.25:
            return None
        return x + (random.random() - .5) * .04, y + (random.random() - .5) * .04, z, 1
    if fm == "fantasma" and y > .35:
        q = (y - .35) * 1.6
        x += .06 * q * math.sin(t * 3 + y * 5)
        y += .06 * q * math.sin(math.atan2(z, x) * 4 + t * 4)
    elif fm == "chama":
        up = max(0, .3 - y)
        x += .09 * up * math.sin(t * 8 + y * 6)
        z += .05 * up * math.cos(t * 6.5 + y * 5)
    elif fm == "espirito" and y > .1:
        x += .13 * (y - .1) * math.sin(t * 2.2 - y * 3)
    return x, y, z, 1


def buscar():
    falhas = 0
    while E["vivo"]:
        try:
            with urllib.request.urlopen(BASE + "/api/mini", timeout=2) as r:
                E.update(json.load(r))
            falhas = 0
            if E.get("mago_v") and E["mago_v"] != MAGO["v"]:
                with urllib.request.urlopen(BASE + "/api/visual?poses=1", timeout=3) as r:
                    p = json.load(r).get("poses")
                MAGO["v"] = E["mago_v"]
                if p:
                    MAGO["poses"] = p
        except Exception:
            falhas += 1
            if falhas > 12:        # o Jarvis fechou: a esfera some junto
                E["vivo"] = False
        time.sleep(0.5 if E.get("painel_frente") else 0.25)


def chamar(caminho):
    def f():
        try:
            urllib.request.urlopen(urllib.request.Request(BASE + caminho, data=b"{}", method="POST"), timeout=3)
        except Exception:
            pass
    threading.Thread(target=f, daemon=True).start()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    u32 = ctypes.windll.user32 if WIN else None
    raiz = tk.Tk()
    global L, A
    esc = max(1.0, raiz.winfo_fpixels("1i") / 96)      # tela em 150% → tudo 1,5x
    px = lambda n: int(n * esc)
    L, A = px(L), px(A)
    LE = px(ESF)
    raiz.title("Jarvis · esfera")
    raiz.overrideredirect(True)
    raiz.attributes("-topmost", True)
    fundo = CHAVE
    try:
        if WIN:
            raiz.configure(bg=CHAVE)
            raiz.attributes("-transparentcolor", CHAVE)
        elif MAC:
            fundo = "systemTransparent"
            raiz.attributes("-transparent", True)
            raiz.configure(bg=fundo)
        else:
            raiz.configure(bg=CHAVE)
    except tk.TclError:          # Tk antigo sem transparência: fica com o quadro escuro
        fundo = "#0b0c10"
        raiz.configure(bg=fundo)
    try:
        tela = tk.Canvas(raiz, width=L, height=A, bg=fundo, highlightthickness=0)
    except tk.TclError:
        fundo = "#0b0c10"
        raiz.configure(bg=fundo)
        tela = tk.Canvas(raiz, width=L, height=A, bg=fundo, highlightthickness=0)
    tela.pack()

    N = 260                    # cubinhos reaproveitados: a forma escolhida usa só os que precisa, o resto fica escondido
    itens = [(tela.create_rectangle(0, 0, 1, 1, width=0), tela.create_rectangle(0, 0, 1, 1, width=0), tela.create_polygon(0, 0, 0, 0, 0, 0, width=0)) for _ in range(N)]
    # olhos do fantasminha e da bola de fogo (na frente da forma)
    olhos = [tela.create_rectangle(0, 0, 1, 1, width=0, fill="#0e101e", state="hidden") for _ in range(2)]
    brilhos = [tela.create_rectangle(0, 0, 1, 1, width=0, fill="#ffffff", state="hidden") for _ in range(2)]
    PLACA = px(104)            # altura da placa de baixo: estado, duas linhas de texto e os botões
    # mini mago: um conjunto de polígonos reaproveitados (3 faces por caixa), redesenhado só quando troca o quadro da pose
    sombra = tela.create_oval(0, 0, 1, 1, fill="#05060a", width=0, state="hidden", tags="mago")
    poli = [tela.create_polygon(0, 0, 0, 0, 0, 0, width=0, state="hidden", tags="mago") for _ in range(3 * 140)]
    mg = {"chave": None}

    def tom(hexa, k):
        n = int(hexa[1:], 16)
        return "#%02x%02x%02x" % tuple(max(4, min(255, int(((n >> s) & 255) * k))) for s in (16, 8, 0))

    def mago(agora, e):
        ps = MAGO["poses"]
        if not ps:
            return False
        pose = {"falando": "conjura", "trabalhando": "conjura", "ouvindo": "ouve", "pensando": "pensa"}.get(e, "parado")
        fps = {"conjura": 6, "pensa": 7, "ouve": 1.2, "parado": 0.8}[pose]
        lista = ps.get(pose) or ps.get("parado") or []
        if not lista:
            return False
        i = int(agora * fps) % len(lista)
        if mg["chave"] == (pose, i, MAGO["v"]):
            return False
        mg["chave"] = (pose, i, MAGO["v"])
        q = lista[i]
        u = px(112) / max(18.0, ps.get("topo", 22) + 2)        # o mago tem ~112 px de altura na tela
        ox = LE + (L - LE) / 2 - 3.5 * KX * u - px(4)
        oy = A - PLACA - px(10) + q["ap"] * u
        tela.coords(sombra, ox - px(26), A - PLACA - px(14), ox + px(40), A - PLACA - px(6))
        tela.itemconfig(sombra, state="normal")
        k = 0
        for x, y, z, w, h, d, cor, _ in q["cx"]:
            X = lambda a, c: ox + (a + c * KX) * u
            Y = lambda a, c: oy - (a + c * KY) * u
            faces = (
                ((X(x, z), Y(y + h, z), X(x + w, z), Y(y + h, z), X(x + w, z + d), Y(y + h, z + d), X(x, z + d), Y(y + h, z + d)), tom(cor, 1.2)),
                ((X(x + w, z), Y(y, z), X(x + w, z), Y(y + h, z), X(x + w, z + d), Y(y + h, z + d), X(x + w, z + d), Y(y, z + d)), tom(cor, .7)),
                ((X(x, z), Y(y, z), X(x + w, z), Y(y, z), X(x + w, z), Y(y + h, z), X(x, z), Y(y + h, z)), tom(cor, 1)),
            )
            for pts_, c in faces:
                if k >= len(poli):
                    break
                tela.coords(poli[k], *pts_)
                tela.itemconfig(poli[k], fill=c, outline=c, width=1, state="normal")
                k += 1
        for j in range(k, len(poli)):
            tela.itemconfig(poli[j], state="hidden")
        return True
    placa = tela.create_rectangle(px(8), A - PLACA, L - px(8), A - px(6), fill="#0b0c10", outline="#ff6b1a", width=2)
    rot = tela.create_text(L / 2, A - PLACA + px(13), text="", fill="#8a90a0", font=(MONO, 8, "bold"))
    leg = tela.create_text(L / 2, A - PLACA + px(42), text="", fill="#f2f3f5", font=(SANS, 8), width=L - px(28), justify="center")
    # botões (só com missão rodando): [x0, y0, x1, y1]
    B_PARAR = (px(14), A - px(36), L / 2 - px(3), A - px(12))
    B_ABRIR = (L / 2 + px(3), A - px(36), L - px(14), A - px(12))
    bp = tela.create_rectangle(*B_PARAR, fill="#ff6b1a", outline="#ff6b1a")
    bpt = tela.create_text((B_PARAR[0] + B_PARAR[2]) / 2, (B_PARAR[1] + B_PARAR[3]) / 2, text="■ PARAR", fill="#000000", font=(MONO, 8, "bold"))
    ba = tela.create_rectangle(*B_ABRIR, fill="#14161d", outline="#8a90a0")
    bat = tela.create_text((B_ABRIR[0] + B_ABRIR[2]) / 2, (B_ABRIR[1] + B_ABRIR[3]) / 2, text="▣ ABRIR", fill="#f2f3f5", font=(MONO, 8, "bold"))
    BOTOES = (bp, bpt, ba, bat)
    dentro = lambda r, ev: r[0] <= ev.x <= r[2] and r[1] <= ev.y <= r[3]

    cores = {}                  # última cor de cada quadradinho (só manda trocar quando muda)
    v = {"cor1": [70, 78, 100], "cor2": [40, 44, 58], "vel": .15, "amp": .03, "raio": .74, "nivel": 0.0, "rot": 0.0, "t": time.time()}
    arr = {"x": 0, "y": 0, "moveu": False, "ativo": False}

    class MI(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("m", ctypes.c_long * 4), ("w", ctypes.c_long * 4), ("f", ctypes.c_ulong)]

    class PT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    def area():
        if not WIN:
            # macOS e Linux: a tela principal inteira, com folga para a barra de menus/painel e o Dock
            mx, my = raiz.winfo_pointerxy()
            sw, sh = raiz.winfo_screenwidth(), raiz.winfo_screenheight()
            cima, baixo = (px(28), px(80)) if MAC else (px(32), px(8))
            return (0, cima, sw, sh - baixo), (mx, my)
        p = PT()
        u32.GetCursorPos(ctypes.byref(p))
        u32.MonitorFromPoint.restype = ctypes.c_void_p
        mon = u32.MonitorFromPoint(p, 2)
        mi = MI()
        mi.cb = ctypes.sizeof(MI)
        u32.GetMonitorInfoW(ctypes.c_void_p(mon), ctypes.byref(mi))
        return tuple(mi.w), (p.x, p.y)

    def pos(canto, ar):
        e, t, d, b = ar
        m = px(14)
        return (e + m if canto.startswith("esq") else d - L - m, t + m if canto.endswith("cima") else b - A - m)

    estado_local = {"canto": E["canto"], "alvo": None, "ult_fuga": 0.0}
    ar, _ = area()
    x0, y0 = pos(estado_local["canto"], ar)
    raiz.geometry(f"{L}x{A}{int(x0):+d}{int(y0):+d}")

    def pressionar(ev):
        arr.update(x=ev.x_root - raiz.winfo_x(), y=ev.y_root - raiz.winfo_y(), moveu=False, ativo=True)

    def arrastar(ev):
        arr["moveu"] = True
        raiz.geometry(f"{int(ev.x_root - arr['x']):+d}{int(ev.y_root - arr['y']):+d}")

    def soltar(ev):
        arr["ativo"] = False
        if not arr["moveu"]:
            if E["ativas"] and dentro(B_PARAR, ev):
                chamar("/api/parar")
            else:
                chamar("/api/janela/grande")
        else:
            estado_local["alvo"] = None
            estado_local["solta_em"] = time.time()
    tela.bind("<ButtonPress-1>", pressionar)
    tela.bind("<B1-Motion>", arrastar)
    tela.bind("<ButtonRelease-1>", soltar)
    tela.bind("<Button-3>", lambda ev: chamar("/api/mudo"))
    if MAC:      # no macOS o botão direito do mouse é o Button-2 do Tk
        tela.bind("<Button-2>", lambda ev: chamar("/api/mudo"))

    def quadro():
        if not E["vivo"]:
            raiz.destroy()
            return
        # com o painel grande em uso, a esfera sai da frente (não cobre botão nem aviso); volta quando ele muda de janela
        some = bool(E.get("painel_frente")) and not arr["ativo"]
        if some != estado_local.get("escondida", False):
            estado_local["escondida"] = some
            try:
                if some:
                    raiz.withdraw()
                else:
                    raiz.deiconify()
                    raiz.attributes("-topmost", True)
            except Exception:
                pass
        if some:
            raiz.after(120, quadro)
            return
        agora = time.time()
        dt = min(.06, agora - v["t"])
        v["t"] = agora
        e = "mudo" if E["mudo"] else E["estado"]
        if e == "dormindo" and E["ativas"]:
            e = "trabalhando"
        vel, amp, raio = ALVO.get(e, ALVO["dormindo"])
        fm = E.get("forma") or "orbe"
        pal = paleta_da_cor(E.get("cor_jarvis"), e) or (PALETA_FORMA.get(fm) or PALETA).get(e, PALETA["dormindo"])
        k = 1 - 0.02 ** dt
        v["vel"] += (vel - v["vel"]) * k
        v["amp"] += (amp - v["amp"]) * k
        v["raio"] += (raio - v["raio"]) * k
        for i in range(3):
            v["cor1"][i] += (pal[0][i] - v["cor1"][i]) * k
            v["cor2"][i] += (pal[1][i] - v["cor2"][i]) * k
        if e == "falando":      # sem acesso ao som daqui: pulsa num ritmo de fala
            nv = .35 + .3 * abs(math.sin(agora * 9)) * (.5 + .5 * math.sin(agora * 2.3)) + .15 * random.random()
        elif e == "ouvindo":
            nv = E["nivel"]
        else:
            nv = E["nivel"] * .2
        v["nivel"] += (nv - v["nivel"]) * (.5 if nv > v["nivel"] else .15)
        v["rot"] += dt * v["vel"]
        cx, cy, R = LE / 2 + px(4), (A - PLACA) / 2 + px(2), (A - PLACA) * .34 * v["raio"]
        cy += R * {"fantasma": -.08, "chama": .1}.get(fm, 0)
        cs, sn, ci, si = math.cos(v["rot"]), math.sin(v["rot"]), math.cos(.35), math.sin(.35)
        vox, cel = vox_forma(fm)
        lista = []
        for c in vox:
            q = vox_pos(fm, c, agora)
            if not q:
                continue
            qx, qy, qz, sz = q
            f, s = c[3], c[4]
            d = 1 + v["amp"] * .6 * math.sin(agora * 1.3 + f)
            if e == "falando":
                d += v["nivel"] * .14 * (.5 + .5 * math.sin(qy * 7 - agora * 9))
            elif e == "ouvindo":
                d += v["nivel"] * .18 * (.4 + .6 * abs(math.sin(f * 3 + agora * 5)))
            elif e == "pensando":
                d += .06 * math.sin(qy * 9 + agora * 7)
            x, z = qx * cs - qz * sn, qx * sn + qz * cs
            y2, z2 = qy * ci - z * si, qy * si + z * ci
            lista.append((z2 * d, x * d, y2 * d, f, s * sz))
        lista.sort()
        lado0 = R * cel * .93
        usados = min(len(lista), N)
        if estado_local.get("usados") != usados:      # esconde só os que sobraram (troca rara: muda a forma)
            for i, par in enumerate(itens):
                st = "normal" if i < usados else "hidden"
                for it in par:
                    tela.itemconfig(it, state=st)
            estado_local["usados"] = usados
        n_q = estado_local["n_quadro"] = estado_local.get("n_quadro", 0) + 1
        # a ordem de desenho dos quadradinhos é fixa (o de trás primeiro): cada ponto, já ordenado pela profundidade,
        # entra no lugar certo da fila. Assim nunca é preciso reordenar o desenho, que era o que mais pesava
        for (z, x, y, f, s), (frente, topo, lado) in zip(lista, itens):
            prof = max(0, min(1, (z + 1.4) / 2.8))
            l = lado0 * (.82 + prof * .32) * (s if s < 1 else 1)
            X, Y = cx + x * R, cy + y * R
            mix = .5 + .5 * math.sin(f + agora * .6)
            luz = (.62 + prof * .55) * min(1.2, s)
            c = [min(255, (int((v["cor1"][i] * (1 - mix) + v["cor2"][i] * mix) * luz + 34 * prof) // 6) * 6) for i in range(3)]
            c2 = [min(255, int(q * 1.25 + 30)) for q in c]
            o = l * .28
            tela.coords(frente, X - l / 2, Y - l / 2, X + l / 2, Y + l / 2)
            tela.coords(topo, X - l / 2, Y - l / 2 - o, X + l / 2, Y - l / 2)
            tela.coords(lado, X + l / 2, Y - l / 2, X + l / 2 + o, Y - l / 2 - o, X + l / 2 + o, Y + l / 2 - o, X + l / 2, Y + l / 2)
            cl = "#%02x%02x%02x" % tuple(max(int(q * .62), 4) for q in c)
            if cores.get(lado) != cl:
                cores[lado] = cl
                tela.itemconfig(lado, fill=cl)
            # cada quadradinho recebe um ponto diferente a cada quadro: a cor vai junto, só quando muda
            cf = "#%02x%02x%02x" % tuple(max(q, 4) for q in c)
            ct = "#%02x%02x%02x" % tuple(max(q, 4) for q in c2)
            if cores.get(frente) != cf:
                cores[frente] = cf
                tela.itemconfig(frente, fill=cf)
            if cores.get(topo) != ct:
                cores[topo] = ct
                tela.itemconfig(topo, fill=ct)
        # olhos: fantasma e bola de fogo têm rosto, que pisca de vez em quando
        tem_rosto = fm in ("fantasma", "chama")
        st = "normal" if tem_rosto else "hidden"
        if estado_local.get("rosto") != st:
            estado_local["rosto"] = st
            for it in olhos + brilhos:
                tela.itemconfig(it, state=st)
        if tem_rosto:
            Rf = R * (.82 if fm == "chama" else 1)
            ey = cy + (R * .12 if fm == "chama" else -R * .02) - Rf * .06
            w = Rf * .19
            h = Rf * (.05 if (agora % 3.7) < .13 or e in ("dormindo", "mudo") else .28)
            for s_, ol, br in ((-1, olhos[0], brilhos[0]), (1, olhos[1], brilhos[1])):
                ox = cx + s_ * Rf * .3
                tela.coords(ol, ox - w / 2, ey - h / 2, ox + w / 2, ey + h / 2)
                b_ = w * .36 if h > Rf * .1 else 0
                tela.coords(br, ox - w * .14 - b_ / 2, ey - h * .2 - b_ / 2, ox - w * .14 + b_ / 2, ey - h * .2 + b_ / 2)
            for it in olhos + brilhos:
                tela.tag_raise(it)
        mago(agora, e)          # o mago, a placa e os botões foram criados depois da esfera: já ficam na frente
        for it in BOTOES:
            est = "normal" if E["ativas"] else "hidden"
            if estado_local.get("bot") != est:
                tela.itemconfig(it, state=est)
        estado_local["bot"] = "normal" if E["ativas"] else "hidden"
        cor = {"ouvindo": "#5ad7ff", "pensando": "#ffd23f", "falando": "#ff6b1a", "trabalhando": "#19c37d", "mudo": "#ff4d5e"}.get(e, "#8a90a0")
        txt_rot = "NO COMPUTADOR" if E.get("pc") and e == "trabalhando" else NOMES.get(e, e.upper())
        if estado_local.get("placa") != (txt_rot, cor):
            estado_local["placa"] = (txt_rot, cor)
            tela.itemconfig(rot, text=txt_rot, fill=cor)
            tela.itemconfig(placa, outline=cor)
        if e == "falando" and E["legenda"]:
            linha = E["legenda"]
        elif E["ativas"]:       # quem está trabalhando e o que está fazendo agora
            linha = f"{E.get('quem', '')}: {E.get('acao', '')}" + (f"  (+{E['ativas'] - 1})" if E["ativas"] > 1 else "")
        else:
            linha = 'Diga "Jarvis"' if e == "dormindo" else ""
        linha = linha[:74] + ("…" if len(linha) > 74 else "")
        if estado_local.get("leg") != linha:
            estado_local["leg"] = linha
            tela.itemconfig(leg, text=linha)

        # posição: canto pedido, ou foge do mouse
        try:
            ar, (mx, my) = area()
            wx, wy = raiz.winfo_x(), raiz.winfo_y()
            if WIN:
                shift = bool(u32.GetAsyncKeyState(0x10) & 0x8000)
                botao = bool(u32.GetAsyncKeyState(0x01) & 0x8000)
            else:      # fora do Windows não dá para ler o teclado de outra janela: SHIFT não segura a esfera
                shift, botao = False, arr["ativo"]
            if E["canto"] != estado_local.get("pedido"):
                estado_local["pedido"] = E["canto"]
                estado_local["canto"] = E["canto"]
                estado_local["alvo"] = pos(E["canto"], ar)
            perto = wx - px(20) < mx < wx + L + px(20) and wy - px(20) < my < wy + A + px(20)
            # só foge do mouse quando o usuário pediu "livre"; por padrão a esfera fica quieta no canto
            if E.get("foge") and perto and not shift and not botao and not arr["ativo"] and not E["fixo"] and agora - estado_local["ult_fuga"] > .6 \
                    and agora - estado_local.get("solta_em", 0) > 1.5:
                cantos = ["dir-baixo", "esq-baixo", "dir-cima", "esq-cima"]
                melhor = max(cantos, key=lambda c: (pos(c, ar)[0] + L / 2 - mx) ** 2 + (pos(c, ar)[1] + A / 2 - my) ** 2)
                estado_local["canto"], estado_local["alvo"], estado_local["ult_fuga"] = melhor, pos(melhor, ar), agora
            al = estado_local["alvo"]
            if al and not arr["ativo"]:
                nx, ny = wx + (al[0] - wx) * .45, wy + (al[1] - wy) * .45
                if abs(al[0] - wx) < 3 and abs(al[1] - wy) < 3:
                    nx, ny = al
                    estado_local["alvo"] = None
                raiz.geometry(f"{int(nx):+d}{int(ny):+d}")
        except Exception:
            pass
        raiz.after(45 if e in ("dormindo", "mudo") else 33, quadro)

    threading.Thread(target=buscar, daemon=True).start()
    raiz.after(50, quadro)
    raiz.mainloop()


if __name__ == "__main__":
    main()
