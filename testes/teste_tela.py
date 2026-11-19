"""Telas novas, no Jarvis de teste (porta 4792, Claude Code de mentira): etiquetas do topo, abas PROCESSOS, CONVERSAS e ENTREGAS
com busca, janela de rodar e de editar processo, cartão da missão com número e ajuste. Tira fotos e confere erros da página."""
import json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(__import__("tempfile").gettempdir(), "jarvis_testes")      # o que os testes criam fica fora da pasta do Jarvis
os.makedirs(SAIDA, exist_ok=True)
J = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(SAIDA, "jarvis_tela_" + time.strftime("%H%M%S"))
FOTOS = os.path.join(SAIDA, "telas_novas")
os.makedirs(os.path.join(PASTA, "dados"), exist_ok=True); os.makedirs(FOTOS, exist_ok=True)
BASE = "http://127.0.0.1:4792"
ok_geral = True


def confere(nome, cond, extra=""):
    global ok_geral
    ok_geral = ok_geral and bool(cond)
    print(("OK   " if cond else "FALHA"), nome, ("· " + str(extra)) if extra else "")


def get(caminho):
    with urllib.request.urlopen(BASE + caminho, timeout=5) as r:
        return json.load(r)


amb = dict(os.environ)
amb.update(JARVIS_TESTE=PASTA, JARVIS_PORTA="4792", JARVIS_CEREBRO="claude", PYTHONIOENCODING="utf-8", FALSO_DURA="14",
           JARVIS_LEADS=os.path.join(PASTA, "dados", "leads"), PYTHON=sys.executable)
_cen = __import__("_cenario")
_cen.preparar(PASTA, amb)      # um projeto e duas conversas de mentira
FALSO = os.path.join(SAIDA, "falso")      # o Claude Code de mentira roda de uma pasta sem espaço nem "&" no caminho (o cmd não aceita)
__import__("shutil").copytree(os.path.join(AQUI, "falso"), FALSO, dirs_exist_ok=True)
if sys.platform != "win32":      # macOS e Linux: o falso é o script "claude" (sem extensão)
    os.chmod(os.path.join(FALSO, "claude"), 0o755)
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
    # uma planilha de leads de exemplo, para a aba CONVERSAS ter o que mostrar
    mp = os.path.join(PASTA, "maps.json")
    json.dump({"resultados": [{"nome": "Academia Corpo & Mente", "nota": 4.9, "avaliacoes": 48}, {"nome": "Fit Center", "nota": 4.6, "avaliacoes": 120, "site": "https://fit.com.br"}]}, open(mp, "w", encoding="utf-8"))
    subprocess.run([sys.executable, os.path.join(J, "ferramentas", "leads.py"), "juntar", "academias", "Valinhos, SP", mp], env=amb, capture_output=True)
    with sync_playwright() as p:
        b = _cen.abrir_navegador(p)
        pg = b.new_page(viewport={"width": 1900, "height": 1030})
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: erros.append("console: " + m.text) if m.type == "error" and "favicon" not in m.text else None)
        pg.goto(BASE + "/"); pg.wait_for_timeout(1200)
        pg.evaluate("() => { const e = document.getElementById('entrada'); if (e) e.hidden = true; }")
        pg.wait_for_timeout(2500)
        confere("etiquetas do topo mostram cérebro e escuta", "Claude" in pg.inner_text("#chCerebro") and "Conversa aberta" in pg.inner_text("#chEscuta"), pg.inner_text("#etiquetas").replace("\n", " | "))
        pg.screenshot(path=os.path.join(FOTOS, "1_parado_com_etiquetas.png"))
        pg.click("#chEscuta"); pg.wait_for_timeout(700)
        confere("clique na etiqueta troca para só pelo nome", "Só pelo nome" in pg.inner_text("#chEscuta") and get("/api/estado")["info"]["escuta"] == "nome")
        pg.click("#chEscuta"); pg.wait_for_timeout(500)

        # PROCESSOS
        pg.click("#vProcessos"); pg.wait_for_timeout(900)
        n = pg.locator("#procLista .proc").count()
        confere("aba PROCESSOS mostra os cartões", n >= 6, f"{n} processos")
        pg.screenshot(path=os.path.join(FOTOS, "2_processos.png"))
        pg.locator("#procLista .proc", has_text="Prospecção").first.locator(".editar").click(); pg.wait_for_timeout(500)
        confere("janela de editar abre com o roteiro", "Etapa 1" in pg.input_value("#procJanela textarea"))
        pg.screenshot(path=os.path.join(FOTOS, "3_editar_processo.png"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        # criar um processo novo pela tela
        pg.click("#procNovo"); pg.wait_for_timeout(400)
        pg.fill("#procJanela [name=nome]", "Orçamento de site"); pg.fill("#procJanela [name=quando]", "montar um orçamento de site para um cliente")
        pg.fill("#procJanela [name=parametros]", "cliente; paginas = 5"); pg.fill("#procJanela textarea", "Objetivo: orçamento de site para {cliente} com {paginas} páginas.\n\n1. Liste o escopo.\n2. Salve em entregas\\orcamento.md.")
        pg.click("#procJanela .forte"); pg.wait_for_timeout(1500)
        ps = get("/api/processos")["processos"]
        novo = next((x for x in ps if x["id"] == "orcamento_de_site"), None)
        confere("criar processo pela tela", bool(novo) and [x["nome"] for x in novo["parametros"]] == ["cliente", "paginas"] and novo["parametros"][1]["padrao"] == "5", novo and novo["id"])
        # rodar a prospecção pela tela
        pg.locator("#procLista .proc", has_text="Prospecção").first.locator(".rodar").click(); pg.wait_for_timeout(400)
        pg.fill("#procJanela [name=nicho]", "academias"); pg.fill("#procJanela [name=cidade]", "Valinhos, SP")
        pg.screenshot(path=os.path.join(FOTOS, "4_rodar_processo.png"))
        pg.click("#procJanela .forte"); pg.wait_for_timeout(4500)
        cart = pg.locator("#grade .missao")
        confere("missão aparece no painel com o número grande", cart.count() == 1 and pg.inner_text("#grade .m-num").strip() == "1", pg.inner_text("#grade .m-titulo"))
        confere("marco aparece no cartão", "Achei 9 academias" in pg.inner_text("#grade .m-passos"), pg.inner_text("#grade .m-passos").replace("\n", " | "))
        pg.screenshot(path=os.path.join(FOTOS, "5_missao_rodando.png"))
        # ajuste digitado no cartão; a barra de espaço dentro do campo não pode desligar o microfone
        pg.fill("#grade .m-recado input", "é Valinhos, não Campinas"); pg.keyboard.press("Enter"); pg.wait_for_timeout(3500)
        m = get("/api/estado")
        confere("digitar com espaço no campo não desliga o microfone", m["mudo"] is False)
        arq = os.path.join(m["missoes"][0]["pasta"], "trabalho", "args.txt")
        linhas = [json.loads(l) for l in open(arq, encoding="utf-8") if l.strip()]
        confere("ajuste digitado no cartão chega ao agente", len(linhas) >= 2 and "Valinhos, não Campinas" in linhas[-1]["pedido"] and "--resume" in linhas[-1]["args"])
        for _ in range(40):
            if get("/api/estado")["missoes"][0]["estado"] != "trabalhando":
                break
            time.sleep(0.5)
        pg.wait_for_timeout(2500)
        pg.screenshot(path=os.path.join(FOTOS, "6_entrega_aberta.png"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)

        # ENTREGAS com busca
        pg.click("#vEntregas"); pg.wait_for_timeout(700)
        confere("aba ENTREGAS lista a missão", pg.locator("#galLista .hist").count() == 1)
        pg.fill("#galBusca", "dentista"); pg.wait_for_timeout(300)
        vazio = pg.locator("#galLista .hist").count() == 0
        pg.fill("#galBusca", "academ"); pg.wait_for_timeout(300)
        confere("busca filtra pelo assunto (sem acento)", vazio and pg.locator("#galLista .hist").count() == 1)
        pg.screenshot(path=os.path.join(FOTOS, "7_entregas_busca.png"))

        # CONVERSAS
        pg.click("#vConversas"); pg.wait_for_timeout(2500)
        nc = pg.locator("#convLista .conv").count()
        confere("aba CONVERSAS: conversas numeradas, projetos e planilha de leads", nc > 0 and pg.locator("#projLista .linha-item").count() >= 1 and "academias" in pg.inner_text("#leadsLista"), f"{nc} conversas")
        pg.evaluate("() => document.querySelectorAll('.conv-txt b').forEach((b, i) => b.textContent = 'Conversa de exemplo ' + (i + 1))")   # a foto não leva os títulos de verdade
        pg.screenshot(path=os.path.join(FOTOS, "8_conversas.png"))

        # mago: campo e botão não mandam o mago andar; ponto livre manda
        pg.click("#vPainel"); pg.wait_for_timeout(600)
        antes = pg.evaluate("() => !!MAGO.estado.ir")
        pg.click("#campo"); pg.wait_for_timeout(200)
        confere("clicar no campo de escrever não manda o mago", not antes and not pg.evaluate("() => !!MAGO.estado.ir"))
        # Parar tudo: o primeiro clique só arma; o segundo, em até 3 s, para
        pg.click("#btParar"); pg.wait_for_timeout(300)
        armado = pg.inner_text("#btParar")
        confere("Parar tudo: primeiro clique só pede confirmação", armado == "Confirmar?", armado)
        pg.wait_for_timeout(3400)
        confere("Parar tudo: a confirmação expira sozinha", pg.inner_text("#btParar") == "Parar tudo")
        # clique no orbe com o microfone desligado: avisa em vez de ficar mudo
        pg.evaluate("() => { S.mudo = true; }")
        o = pg.evaluate("() => orbeTela()")
        pg.mouse.click(o["x"], o["y"]); pg.wait_for_timeout(400)
        confere("clique no orbe com microfone desligado avisa", "MICROFONE DESLIGADO" in pg.inner_text("#avisos"))
        pg.evaluate("() => { S.mudo = false; }")
        # sem ligação, o texto digitado fica no campo
        pg.evaluate("() => { S.conectado = false; }")
        pg.fill("#campo", "texto que não pode sumir"); pg.press("#campo", "Enter"); pg.wait_for_timeout(300)
        confere("sem ligação, o texto digitado não some", pg.input_value("#campo") == "texto que não pode sumir")
        pg.fill("#campo", ""); pg.evaluate("() => { S.conectado = true; }")
        pg.screenshot(path=os.path.join(FOTOS, "10_avisos.png"))
        # notebook: nada estoura
        pg.set_viewport_size({"width": 1366, "height": 740}); pg.wait_for_timeout(800)
        pg.click("#vProcessos"); pg.wait_for_timeout(700)
        larg = pg.evaluate("() => document.documentElement.scrollWidth")
        confere("notebook (1366): cabeçalho cabe, sem rolagem lateral", larg <= 1366, f"largura {larg}")
        pg.screenshot(path=os.path.join(FOTOS, "9_processos_notebook.png"))
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
# o processo de exemplo criado na tela fica na pasta do teste, nunca na pasta de processos de verdade
exemplo = os.path.join(J, "modelos", "orcamento_de_site.md")
if False:
    __import__("shutil").move(exemplo, os.path.join(PASTA, "orcamento_de_site.md"))
confere("o processo de exemplo ficou na pasta do teste", not os.path.exists(exemplo) and not os.path.exists(os.path.join(J, "modelos", "meus", "orcamento_de_site.md"))
        and os.path.exists(os.path.join(PASTA, "modelos_meus", "orcamento_de_site.md")))
confere("nenhum erro na página", not erros, erros[:3])
print("TUDO CERTO" if ok_geral else "TEM FALHA")
print(FOTOS)
sys.exit(0 if ok_geral else 1)
