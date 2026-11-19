"""Mago: clicar em ponto livre = ir até lá. Confere chegada no chão do palco, pulo para um quadro, clique no orbe e seleção de texto."""
import os, sys, threading, time
from aiohttp import web
from playwright.sync_api import sync_playwright

J = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(__import__("tempfile").gettempdir(), "jarvis_testes")      # o que os testes criam fica fora da pasta do Jarvis
os.makedirs(SAIDA, exist_ok=True)
D = os.path.join(SAIDA, "clique_teste")
os.makedirs(D, exist_ok=True)
VIS = {"roupa": "torre", "tema": "classico", "tam": 1, "v": 1}


async def visual(req):
    return web.json_response(VIS)


async def nada(req):
    return web.json_response({})


def servidor():
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = web.Application()
    app.router.add_get("/api/visual", visual); app.router.add_post("/api/visual", visual)
    app.router.add_get("/api/{x:.*}", nada); app.router.add_post("/api/{x:.*}", nada)
    app.router.add_get("/", lambda r: web.FileResponse(os.path.join(J, "web", "index.html")))
    app.router.add_static("/", os.path.join(J, "web"))
    web.run_app(app, host="127.0.0.1", port=4797, print=None, handle_signals=False)


threading.Thread(target=servidor, daemon=True).start()
time.sleep(1.5)
MISSAO = """() => { const ag = Date.now() / 1000;
  S.missoes = [{ n: 14, agente: 'claude', titulo: 'Prospecção de academias', estado: 'trabalhando', etapa: 'Buscando', inicio: ag - 60, fim: null, entregas: [], telas: [], passos: [], log: [{t: ag, tipo: 'acao', txt: 'abrindo o Maps'}], motor: 'opus', modelo: '', resumo: '' }];
  S.estado = 'dormindo'; estado(); cartoes(); }"""
ok = True
def confere(nome, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print(("OK   " if cond else "FALHA"), nome, extra)

erros = []
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_cen = __import__("_cenario")
with sync_playwright() as p:
    b = _cen.abrir_navegador(p)
    pg = b.new_page(viewport={"width": 1900, "height": 1030})
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto("http://127.0.0.1:4797/"); pg.wait_for_timeout(900)
    pg.evaluate("() => { const e = document.getElementById('entrada'); if (e) e.hidden = true; }")
    pg.wait_for_timeout(2500)
    est = lambda: pg.evaluate("() => ({ x: MAGO.estado.x, y: MAGO.estado.y, modo: MAGO.estado.modo, ir: !!MAGO.estado.ir, dir: MAGO.estado.dir, surf: MAGO.estado.surf && MAGO.estado.surf.el ? (MAGO.estado.surf.el.id || MAGO.estado.surf.el.className) : 'chao' })")
    r = lambda sel: pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; }", sel)

    # 1. parado: clique no chão do palco, bem à direita
    pal = r("#palco"); a = est()
    alvo = pal["r"] - 160
    pg.mouse.click(alvo, pal["b"] - 40); pg.wait_for_timeout(300)
    meio = est(); pg.wait_for_timeout(5000); c = est()
    confere("parado: vai até o ponto no chão do palco", abs(c["x"] - alvo) < 30 and c["surf"] == "palco", f"de {a['x']:.0f} para {c['x']:.0f} (alvo {alvo:.0f})")
    confere("vira para o lado do destino", meio["dir"] == 1, f"dir {meio['dir']}")
    pg.screenshot(path=os.path.join(D, "1_palco_direita.png"))
    # 2. volta para a esquerda
    alvo = pal["l"] + 120
    pg.mouse.click(alvo, pal["b"] - 60); pg.wait_for_timeout(300); meio = est(); pg.wait_for_timeout(5500); c = est()
    confere("volta para a esquerda", abs(c["x"] - alvo) < 30, f"x {c['x']:.0f} (alvo {alvo:.0f})"); confere("vira para a esquerda", meio["dir"] == -1)
    # 3. clique num quadro da direita: pula para cima dele
    bl = r("#agora")
    pg.mouse.click((bl["l"] + bl["r"]) / 2, bl["t"] + 30); pg.wait_for_timeout(7000); c = est()
    confere("sobe no quadro clicado", c["surf"] in ("agora", "bloco") and abs(c["y"] - bl["t"]) < 6, f"superfície {c['surf']}, y {c['y']:.0f} (topo {bl['t']:.0f})")
    pg.screenshot(path=os.path.join(D, "2_em_cima_do_quadro.png"))
    # 4. clique no orbe: o mago não se mexe (congela o passeio sozinho antes de medir, para o teste não oscilar)
    pg.evaluate("() => { MAGO.estado.modo = 'parado'; MAGO.estado.ir = null; MAGO.estado.tm = 15; }")
    o = pg.evaluate("() => orbeTela()"); antes = est()
    pg.mouse.click(o["x"], o["y"]); pg.wait_for_timeout(600); c = est()
    confere("clique no orbe não manda o mago", not c["ir"] and abs(c["x"] - antes["x"]) < 3)
    # 5. arrastar por cima dos textos não seleciona nada
    pg.mouse.move(bl["l"] + 20, bl["t"] + 20); pg.mouse.down(); pg.mouse.move(bl["r"] - 20, bl["b"] + 200, steps=12); pg.mouse.up()
    sel = pg.evaluate("() => String(getSelection())")
    confere("arrastar não marca texto", sel == "", repr(sel[:40]))
    # 6. com missão: clique no cartão da missão (fora da telinha) e no chão da coluna
    pg.evaluate(MISSAO); pg.wait_for_timeout(1500)
    pal = r("#palco"); alvo = pal["r"] - 90
    pg.mouse.click(alvo, pal["b"] - 30); pg.wait_for_timeout(6500); c = est()
    confere("com missão: anda no chão da coluna do orbe", abs(c["x"] - alvo) < 30 and c["surf"] == "palco", f"x {c['x']:.0f} (alvo {alvo:.0f}), superfície {c['surf']}")
    tit = r("#grade .m-titulo")
    pg.mouse.click(tit["l"] + 400, tit["t"] + 10); pg.wait_for_timeout(6500); c = est()
    confere("com missão: sobe no cartão da missão", "missao" in c["surf"], f"superfície {c['surf']}")
    pg.screenshot(path=os.path.join(D, "3_no_cartao.png"))
    # 7. campo de escrever continua selecionável
    pg.fill("#campo", "teste de seleção"); pg.dblclick("#campo")
    confere("campo de escrever seleciona", pg.evaluate("() => { const c = document.getElementById('campo'); return c.selectionEnd - c.selectionStart; }") > 0)
    b.close()
print("erros na página:", erros or "nenhum")
print("TUDO CERTO" if ok and not erros else "TEM FALHA")
sys.exit(0 if ok and not erros else 1)
