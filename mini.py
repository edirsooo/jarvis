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
CHAVE = "#010203"          # cor que vira transparente
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
    u32 = ctypes.windll.user32
    raiz = tk.Tk()
    global L, A
    esc = max(1.0, raiz.winfo_fpixels("1i") / 96)      # tela em 150% → tudo 1,5x
    px = lambda n: int(n * esc)
    L, A = px(L), px(A)
    LE = px(ESF)
    raiz.title("Jarvis · esfera")
    raiz.overrideredirect(True)
    raiz.attributes("-topmost", True)
    raiz.configure(bg=CHAVE)
    raiz.attributes("-transparentcolor", CHAVE)
    tela = tk.Canvas(raiz, width=L, height=A, bg=CHAVE, highlightthickness=0)
    tela.pack()

    N = 120
    pts = []
    for i in range(N):
        y = 1 - (i / (N - 1)) * 2
        r = math.sqrt(max(0, 1 - y * y))
        th = i * math.pi * (3 - math.sqrt(5))
        pts.append((math.cos(th) * r, y, math.sin(th) * r, random.random() * 6.28, .6 + random.random() * .8))
    itens = [(tela.create_rectangle(0, 0, 1, 1, width=0), tela.create_rectangle(0, 0, 1, 1, width=0)) for _ in range(N)]
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
    rot = tela.create_text(L / 2, A - PLACA + px(13), text="", fill="#8a90a0", font=("Consolas", 8, "bold"))
    leg = tela.create_text(L / 2, A - PLACA + px(42), text="", fill="#f2f3f5", font=("Segoe UI", 8), width=L - px(28), justify="center")
    # botões (só com missão rodando): [x0, y0, x1, y1]
    B_PARAR = (px(14), A - px(36), L / 2 - px(3), A - px(12))
    B_ABRIR = (L / 2 + px(3), A - px(36), L - px(14), A - px(12))
    bp = tela.create_rectangle(*B_PARAR, fill="#ff6b1a", outline="#ff6b1a")
    bpt = tela.create_text((B_PARAR[0] + B_PARAR[2]) / 2, (B_PARAR[1] + B_PARAR[3]) / 2, text="■ PARAR", fill="#000000", font=("Consolas", 8, "bold"))
    ba = tela.create_rectangle(*B_ABRIR, fill="#14161d", outline="#8a90a0")
    bat = tela.create_text((B_ABRIR[0] + B_ABRIR[2]) / 2, (B_ABRIR[1] + B_ABRIR[3]) / 2, text="▣ ABRIR", fill="#f2f3f5", font=("Consolas", 8, "bold"))
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
    raiz.geometry(f"{L}x{A}+{x0}+{y0}")

    def pressionar(ev):
        arr.update(x=ev.x_root - raiz.winfo_x(), y=ev.y_root - raiz.winfo_y(), moveu=False, ativo=True)

    def arrastar(ev):
        arr["moveu"] = True
        raiz.geometry(f"+{ev.x_root - arr['x']}+{ev.y_root - arr['y']}")

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
        pal = PALETA.get(e, PALETA["dormindo"])
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
        cx, cy, R = LE / 2 + px(4), (A - PLACA) / 2 + px(2), (A - PLACA) * .37 * v["raio"]
        cs, sn, ci, si = math.cos(v["rot"]), math.sin(v["rot"]), math.cos(.35), math.sin(.35)
        lista = []
        for idx, (qx, qy, qz, f, s) in enumerate(pts):
            d = 1 + v["amp"] * math.sin(agora * 1.3 * s + f)
            if e == "falando":
                d += v["nivel"] * .32 * (.5 + .5 * math.sin(qy * 7 - agora * 9))
            elif e == "ouvindo":
                d += v["nivel"] * .5 * s * (.4 + .6 * abs(math.sin(f * 3 + agora * 5)))
            elif e == "pensando":
                d += .09 * math.sin(qy * 9 + agora * 7)
            elif e == "trabalhando":
                d += .05 * math.sin(math.atan2(qz, qx) * 4 + agora * 3)
            x, z = qx * cs - qz * sn, qx * sn + qz * cs
            y2, z2 = qy * ci - z * si, qy * si + z * ci
            lista.append((z2 * d, x * d, y2 * d, f, s))
        lista.sort()
        base = max(3.0, R * .085)
        n_q = estado_local["n_quadro"] = estado_local.get("n_quadro", 0) + 1
        # a ordem de desenho dos quadradinhos é fixa (o de trás primeiro): cada ponto, já ordenado pela profundidade,
        # entra no lugar certo da fila. Assim nunca é preciso reordenar o desenho, que era o que mais pesava
        for (z, x, y, f, s), (frente, topo) in zip(lista, itens):
            prof = (z + 1.4) / 2.8
            l = base * (.55 + prof * .75)
            X, Y = cx + x * R, cy + y * R
            mix = .5 + .5 * math.sin(f + agora * .6)
            luz = .35 + prof * .75
            c = [min(255, (int((v["cor1"][i] * (1 - mix) + v["cor2"][i] * mix) * luz) // 6) * 6) for i in range(3)]
            c2 = [min(255, int(q * 1.4)) for q in c]
            tela.coords(frente, X - l / 2, Y - l / 2, X + l / 2, Y + l / 2)
            tela.coords(topo, X - l / 2, Y - l / 2 - l * .28, X + l / 2, Y - l / 2)
            # cada quadradinho recebe um ponto diferente a cada quadro: a cor vai junto, só quando muda
            cf = "#%02x%02x%02x" % tuple(max(q, 4) for q in c)
            ct = "#%02x%02x%02x" % tuple(max(q, 4) for q in c2)
            if cores.get(frente) != cf:
                cores[frente] = cf
                tela.itemconfig(frente, fill=cf)
            if cores.get(topo) != ct:
                cores[topo] = ct
                tela.itemconfig(topo, fill=ct)
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
            shift = bool(u32.GetAsyncKeyState(0x10) & 0x8000)
            botao = bool(u32.GetAsyncKeyState(0x01) & 0x8000)
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
                raiz.geometry(f"+{int(nx)}+{int(ny)}")
        except Exception:
            pass
        raiz.after(45 if e in ("dormindo", "mudo") else 33, quadro)

    threading.Thread(target=buscar, daemon=True).start()
    raiz.after(50, quadro)
    raiz.mainloop()


if __name__ == "__main__":
    main()
