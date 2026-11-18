"""Aparência, no Jarvis de teste (porta 4793, sem som, sem janela): fotografa cada cenário, cada forma do Jarvis, as classes
do mago no menu Aparência e o painel com uma missão. Confere que o cenário desenha, que a escolha fica guardada e que a
página não dá erro. As fotos ficam em %TEMP%\\jarvis_testes\\telas_visual."""
import json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(__import__("tempfile").gettempdir(), "jarvis_testes")
J = os.path.dirname(AQUI)
PASTA = os.path.join(SAIDA, "jarvis_visual_" + time.strftime("%H%M%S"))
FOTOS = os.path.join(SAIDA, "telas_visual")
os.makedirs(os.path.join(PASTA, "dados"), exist_ok=True); os.makedirs(FOTOS, exist_ok=True)
BASE = "http://127.0.0.1:4793"
ok_geral = True


def confere(nome, cond, extra=""):
    global ok_geral
    ok_geral = ok_geral and bool(cond)
    print(("OK   " if cond else "FALHA"), nome, ("· " + str(extra)) if extra else "")


def get(caminho):
    with urllib.request.urlopen(BASE + caminho, timeout=5) as r:
        return json.load(r)


amb = dict(os.environ)
amb.update(JARVIS_TESTE=PASTA, JARVIS_PORTA="4793", JARVIS_CEREBRO="claude", PYTHONIOENCODING="utf-8", FALSO_DURA="30")
__import__("_cenario").preparar(PASTA, amb)
FALSO = os.path.join(SAIDA, "falso")
__import__("shutil").copytree(os.path.join(AQUI, "falso"), FALSO, dirs_exist_ok=True)
amb["PATH"] = FALSO + os.pathsep + amb["PATH"]
saida = open(os.path.join(PASTA, "servidor.log"), "w", encoding="utf-8")
proc = subprocess.Popen([sys.executable, os.path.join(J, "jarvis.py"), "--sem-ouvido"], env=amb, cwd=PASTA, stdout=saida, stderr=subprocess.STDOUT)
erros = []
try:
    for _ in range(40):
        try:
            get("/saude"); break
        except Exception:
            time.sleep(0.5)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 1600, "height": 900})
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => { const e = document.getElementById('entrada'); if (e) e.hidden = true; }")
        confere("tema padrão é o Abismo", pg.evaluate("() => document.getElementById('app').dataset.tema") == "abismo")
        # cada cenário desenha alguma coisa (o canvas não fica vazio)
        for cen in pg.evaluate("() => CENARIOS.map(c => c[0])"):
            pg.evaluate(f"() => MAGO.aplica({{cenario: '{cen}'}})"); pg.wait_for_timeout(900)
            px = pg.evaluate("() => { const c = document.getElementById('cenario'), d = c.getContext('2d').getImageData(c.width/2|0, c.height*.3|0, 1, 1).data; return d[3]; }")
            if cen != "nenhum":
                confere(f"cenário {cen} desenha", px > 0, px)
            pg.screenshot(path=os.path.join(FOTOS, f"cenario_{cen}.png"))
        pg.evaluate("() => MAGO.aplica({cenario: 'ruinas'})")
        for fm in pg.evaluate("() => FORMAS.map(f => f[0])"):
            pg.evaluate(f"() => MAGO.aplica({{forma: '{fm}'}})"); pg.wait_for_timeout(700)
            confere(f"forma {fm} aplicada", pg.evaluate("() => document.getElementById('app').dataset.forma") == fm)
            pg.screenshot(path=os.path.join(FOTOS, f"forma_{fm}.png"))
        # a escolha fica guardada no servidor
        time.sleep(0.5)
        v = get("/api/visual")
        confere("forma e cenário guardados no servidor", v.get("forma") == "espirito" and v.get("cenario") == "ruinas", {k: v.get(k) for k in ("tema", "forma", "cenario")})
        pg.evaluate("() => MAGO.aplica({forma: 'orbe'})")
        pg.click("#btVisual"); pg.wait_for_timeout(600)
        confere("menu Aparência mostra forma, cenário e as 7 classes",
                pg.locator("#visual [data-forma]").count() == 5 and pg.locator("#visual [data-cenario]").count() >= 5 and pg.locator("#visual [data-roupa]").count() == 7)
        pg.screenshot(path=os.path.join(FOTOS, "menu_aparencia.png"))
        pg.click("#visual [data-roupa=cavaleiro]"); pg.wait_for_timeout(500); pg.keyboard.press("Escape"); pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(FOTOS, "classe_cavaleiro.png"))
        # outros temas continuam de pé
        for tm in ("cristal", "rpg", "grimorio"):
            pg.evaluate(f"() => MAGO.aplica({{tema: '{tm}'}})"); pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(FOTOS, f"tema_{tm}.png"))
        pg.evaluate("() => MAGO.aplica({tema: 'abismo', roupa: 'torre'})"); pg.wait_for_timeout(400)
        # com missão: palco vira coluna, cenário acompanha
        urllib.request.urlopen(urllib.request.Request(BASE + "/api/texto", data=json.dumps({"texto": "Faz a prospecção de academias em Valinhos."}).encode(), headers={"Content-Type": "application/json"}), timeout=5)
        pg.wait_for_timeout(5000)
        pg.screenshot(path=os.path.join(FOTOS, "missao_rodando.png"))
        pg.click("#vProcessos"); pg.wait_for_timeout(1200)
        pg.screenshot(path=os.path.join(FOTOS, "processos.png"))
        pg.click("#vPainel"); pg.wait_for_timeout(300)
        # desempenho: quantos quadros o cenário pede por segundo com a janela em foco
        fps = pg.evaluate("() => new Promise(r => { let n = 0; const c = document.getElementById('cenario'), ctx = c.getContext('2d'), o = ctx.drawImage.bind(ctx); ctx.drawImage = (...a) => { n++; return o(...a); }; setTimeout(() => r(n / 2 / 2), 2000); })")
        confere("cenário fica perto de 30 quadros por segundo (ou menos)", fps <= 34, f"{fps:.0f} q/s")
        b.close()
finally:
    try:
        urllib.request.urlopen(urllib.request.Request(BASE + "/api/sair", data=b"{}", method="POST"), timeout=3)
    except Exception:
        pass
    time.sleep(1)
    if proc.poll() is None:
        proc.terminate()
    saida.close()
confere("nenhum erro na página", not erros, erros[:3])
print("TUDO CERTO" if ok_geral else "TEM FALHA")
print(FOTOS)
