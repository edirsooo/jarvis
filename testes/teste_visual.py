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
amb.update(JARVIS_TESTE=PASTA, JARVIS_PORTA="4793", JARVIS_CEREBRO="claude", PYTHONIOENCODING="utf-8", FALSO_DURA="30", JARVIS_ATUALIZA_FALSO="2")
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
        confere("menu Aparência mostra forma, estilo do corpo, cenário e as 7 classes",
                pg.locator("#visual [data-forma]").count() == 5 and pg.locator("#visual [data-corpo]").count() == 5 and pg.locator("#visual [data-cenario]").count() >= 5 and pg.locator("#visual [data-roupa]").count() == 7)
        alturas = pg.evaluate("() => [...document.querySelectorAll('#visual [data-corj], #visual [data-forma]')].map(b => Math.round(b.getBoundingClientRect().height))")
        confere("cores do Jarvis do mesmo tamanho das formas", min(alturas) >= 36 and max(alturas) - min(alturas) <= 4, alturas)
        pg.locator("#visual").screenshot(path=os.path.join(FOTOS, "menu_aba_jarvis.png"))
        pg.click("#visual [data-aba=tela]"); pg.wait_for_timeout(300); pg.locator("#visual").screenshot(path=os.path.join(FOTOS, "menu_aba_tela.png"))
        pg.click("#visual [data-aba=mago]"); pg.wait_for_timeout(300); pg.locator("#visual").screenshot(path=os.path.join(FOTOS, "menu_aba_mago.png"))
        pg.click("#visual [data-roupa=cavaleiro]"); pg.wait_for_timeout(500); pg.keyboard.press("Escape"); pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(FOTOS, "classe_cavaleiro.png"))
        # outros temas continuam de pé
        for tm in ("cristal", "rpg", "grimorio"):
            pg.evaluate(f"() => MAGO.aplica({{tema: '{tm}'}})"); pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(FOTOS, f"tema_{tm}.png"))
        # as cores mudam de verdade: borda da caixa de diálogo, cenário e cor de destaque
        borda = lambda: pg.evaluate("() => getComputedStyle(document.getElementById('saudacao')).borderTopColor")
        pixel = lambda: pg.evaluate("() => { const c = document.getElementById('cenario'), d = c.getContext('2d').getImageData(c.width*.15|0, c.height*.15|0, 1, 1).data; return [d[0], d[1], d[2]]; }")
        pg.evaluate("() => MAGO.aplica({tema: 'abismo'})"); pg.wait_for_timeout(700); b1, p1 = borda(), pixel()
        pg.evaluate("() => MAGO.aplica({tema: 'cristal'})"); pg.wait_for_timeout(700); b2, p2 = borda(), pixel()
        confere("trocar o tema muda a caixa de diálogo", b1 != b2, f"{b1} -> {b2}")
        confere("trocar o tema muda o tom do cenário", p1 != p2, f"{p1} -> {p2}")
        pg.evaluate("() => MAGO.aplica({tema: 'abismo', cor: '#58c48d'})"); pg.wait_for_timeout(700)
        cor = pg.evaluate("() => getComputedStyle(document.getElementById('app')).getPropertyValue('--laranja').trim()")
        confere("cor de destaque vale por cima do tema", cor == "#58c48d", cor)
        pg.click("#btVisual"); pg.wait_for_timeout(400)
        confere("menu tem cor de destaque, cor do Jarvis e as cores livres (destaque, Jarvis e roupa)", pg.locator("#visual [data-cor]").count() >= 7 and pg.locator("#visual input[type=color]").count() == 3 and pg.locator("#visual [data-corj]").count() >= 8)
        pg.screenshot(path=os.path.join(FOTOS, "cor_esmeralda.png")); pg.keyboard.press("Escape")
        time.sleep(0.5)
        confere("cor guardada no servidor", get("/api/visual").get("cor") == "#58c48d")
        pg.evaluate("() => MAGO.aplica({cor: ''})"); pg.wait_for_timeout(300)
        # cor do próprio Jarvis: a bola fica rosa (no tom de dormindo) e a esfera flutuante recebe a mesma cor
        pg.evaluate("() => MAGO.aplica({cor_jarvis: '#ff7ac8'})"); pg.wait_for_timeout(2500)
        c1 = pg.evaluate("() => V.cor1.map(v => v | 0)")
        confere("cor do Jarvis pinta a bola", c1[0] > c1[1] + 20 and c1[2] > c1[1], c1)
        pg.screenshot(path=os.path.join(FOTOS, "cor_jarvis_rosa.png"))
        time.sleep(0.5)
        confere("esfera flutuante recebe a cor do Jarvis", get("/api/mini").get("cor_jarvis") == "#ff7ac8")
        pg.evaluate("() => MAGO.aplica({cor_jarvis: ''})"); pg.wait_for_timeout(300)
        # estilos do corpo e rosto: cada um desenha a esfera; fotos do fantasminha e da bola de fogo de perto
        caixa = pg.evaluate("() => { const r = document.getElementById('esfera').getBoundingClientRect(); return {x: r.x + r.width/2 - 190, y: r.y + r.height*.4 - 190, width: 380, height: 380}; }")
        for fm in ("fantasma", "chama"):
            for cp in pg.evaluate("() => CORPOS.map(c => c[0])"):
                pg.evaluate(f"() => MAGO.aplica({{forma: '{fm}', corpo: '{cp}'}})"); pg.wait_for_timeout(700)
                cheio = pg.evaluate("() => { const c = document.getElementById('esfera'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 64) if (d[i] > 20) n++; return n; }")
                confere(f"{fm} em {cp} desenha", cheio > 300, cheio)
                pg.screenshot(path=os.path.join(FOTOS, f"corpo_{fm}_{cp}.png"), clip=caixa)
        for est in ("ouvindo", "pensando", "falando"):      # rosto acordado (estado só na tela)
            pg.evaluate(f"() => {{ S.estado = '{est}'; }}"); pg.wait_for_timeout(900)
            pg.screenshot(path=os.path.join(FOTOS, f"rosto_{est}.png"), clip=caixa)
        pg.evaluate("() => { S.estado = 'dormindo'; }")
        pg.mouse.move(caixa["x"] + 190, caixa["y"] + 190); pg.wait_for_timeout(900)
        pg.screenshot(path=os.path.join(FOTOS, "fantasma_carinho.png"), clip=caixa)
        confere("estilo do corpo guardado", (time.sleep(0.4) or get("/api/visual")).get("corpo") == "liso")
        # personagem do mago: escolhas no menu viram o desenho e ficam guardadas
        pg.evaluate("() => MAGO.menu(true)"); pg.click("#visual [data-aba=mago]"); pg.wait_for_timeout(200)
        antes = pg.evaluate("() => document.querySelector('#visual [data-roupa=torre] canvas').toDataURL()")
        pg.click('#visual [data-pk=tipo][data-pv=h]'); pg.click('#visual [data-pk=barba][data-pv=cheia]'); pg.click('#visual [data-pk=pele][data-pv="#5e3a26"]'); pg.wait_for_timeout(300)
        depois = pg.evaluate("() => document.querySelector('#visual [data-roupa=torre] canvas').toDataURL()")
        ps = (time.sleep(0.4) or get("/api/visual")).get("pers") or {}
        confere("personagem do mago muda o desenho e fica guardado", antes != depois and ps.get("tipo") == "h" and ps.get("barba") == "cheia" and ps.get("pele") == "#5e3a26", str(ps))
        pg.evaluate("() => MAGO.menu(false)")
        pg.mouse.move(5, 880)
        pg.evaluate("() => MAGO.aplica({forma: 'orbe', corpo: 'cubos'})"); pg.wait_for_timeout(300)
        # aviso de atualização (o servidor finge 2 novidades): botão no topo, janela com a lista e atualizar
        confere("botão de atualização aparece", pg.is_visible("#btAtualiza"), pg.text_content("#btAtualiza"))
        pg.click("#btAtualiza"); pg.wait_for_timeout(400)
        confere("janela mostra as novidades", "Novidade de teste 1" in (pg.text_content("#atualiza") or ""))
        pg.screenshot(path=os.path.join(FOTOS, "atualizacao.png"))
        pg.click("#atualiza [data-acao=atualizar]"); pg.wait_for_timeout(800)
        confere("atualizar responde e some o botão", "Atualizado" in (pg.text_content("#atualiza .atu-msg") or "") and not pg.is_visible("#btAtualiza"), pg.text_content("#atualiza .atu-msg"))
        pg.click("#atualiza [data-acao=fechar]")
        with urllib.request.urlopen(BASE + "/estilo.css", timeout=5) as r:
            confere("arquivos da tela sem cache velho", r.headers.get("Cache-Control") == "no-cache", r.headers.get("Cache-Control"))
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
