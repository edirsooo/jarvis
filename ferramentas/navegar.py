"""Navegador do Jarvis para os agentes. Cada página aberta vira uma captura em <missão>\\telas, que o usuário vê ao vivo.

Uso:
  python navegar.py ajuda
  python navegar.py abrir <url> [--inteira] [--celular]
      Abre a página, salva a captura em telas\\ e imprime título, texto e links principais.
  python navegar.py maps "<busca>" [--max 20]
      Busca no Google Maps (ex.: "nutricionista em Florianópolis") e imprime JSON com
      nome, nota, avaliações, site, telefone e endereço de cada resultado.
  python navegar.py captura <url ou arquivo .html> --saida <arquivo.png> [--inteira] [--largura 1366] [--celular]
      Salva uma captura no caminho pedido (ex.: entregas\\antes.png) e também em telas\\.

A pasta da missão vem da variável JARVIS_MISSAO (ou a pasta atual).
"""
import json, os, re, sys, time, urllib.parse

MISSAO = os.environ.get("JARVIS_MISSAO") or os.getcwd()
TELAS = os.path.join(MISSAO, "telas")


def nome_tela(rotulo):
    os.makedirs(TELAS, exist_ok=True)
    n = len([a for a in os.listdir(TELAS) if a.endswith(".jpg")]) + 1
    s = re.sub(r"[^a-z0-9]+", "-", rotulo.lower()).strip("-")[:40] or "tela"
    return os.path.join(TELAS, f"{n:03d}_{s}.jpg")


def opcao(args, nome, padrao=None):
    if nome in args:
        i = args.index(nome)
        if i + 1 < len(args):
            return args[i + 1]
    return padrao


def navegador(p, celular=False, largura=1366):
    b = None
    escondido = os.environ.get("JARVIS_NAVEGADOR_VISIVEL") != "1"   # visível: o usuário vê a janela do navegador trabalhando
    for canal in ("msedge", "chrome", None):
        try:
            b = p.chromium.launch(channel=canal, headless=escondido) if canal else p.chromium.launch(headless=escondido)
            break
        except Exception:
            continue
    if b is None:
        sys.exit("Não achei Edge nem Chrome para abrir páginas.")
    if celular:
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                            locale="pt-BR", user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    else:
        ctx = b.new_context(viewport={"width": largura, "height": 850}, locale="pt-BR")
    return b, ctx.new_page()


def ir(pg, url):
    if os.path.exists(url):
        url = "file:///" + os.path.abspath(url).replace("\\", "/")
    elif not re.match(r"^[a-z]+://", url):
        url = "https://" + url
    try:
        pg.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            pg.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
    except Exception as e:
        print(f"ERRO ao abrir {url}: {type(e).__name__}: {str(e)[:200]}")
        return False
    return True


def abrir(args):
    from playwright.sync_api import sync_playwright
    url = args[0]
    with sync_playwright() as p:
        b, pg = navegador(p, "--celular" in args)
        if ir(pg, url):
            arq = nome_tela(urllib.parse.urlparse(pg.url).netloc or "pagina")
            pg.screenshot(path=arq, type="jpeg", quality=70, full_page="--inteira" in args)
            texto = pg.evaluate("document.body ? document.body.innerText : ''")
            links = pg.evaluate("[...document.querySelectorAll('a[href]')].slice(0,60).map(a=>[a.innerText.trim().slice(0,60),a.href])")
            print("TÍTULO:", pg.title())
            print("ENDEREÇO:", pg.url)
            print("CAPTURA:", arq)
            print("TEXTO:\n" + re.sub(r"\n{3,}", "\n\n", texto)[:6000])
            print("LINKS:")
            for t, h in links:
                if t:
                    print(f"- {t}: {h}")
        b.close()


def captura(args):
    from playwright.sync_api import sync_playwright
    saida = opcao(args, "--saida")
    if not saida:
        sys.exit("Faltou --saida <arquivo.png>")
    saida = saida if os.path.isabs(saida) else os.path.join(MISSAO, saida)
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with sync_playwright() as p:
        b, pg = navegador(p, "--celular" in args, int(opcao(args, "--largura", 1366)))
        if ir(pg, args[0]):
            pg.screenshot(path=saida, full_page="--inteira" in args)
            pg.screenshot(path=nome_tela(os.path.splitext(os.path.basename(saida))[0]), type="jpeg", quality=70)
            print("CAPTURA:", saida)
        b.close()


def maps(args):
    from playwright.sync_api import sync_playwright
    busca = args[0]
    maximo = int(opcao(args, "--max", 20))
    with sync_playwright() as p:
        b, pg = navegador(p)
        ok = ir(pg, "https://www.google.com/maps/search/" + urllib.parse.quote(busca) + "?hl=pt-BR")
        if not ok:
            b.close()
            return
        for txt in ("Aceitar tudo", "Rejeitar tudo"):
            try:
                pg.get_by_role("button", name=txt).first.click(timeout=1500)
                break
            except Exception:
                pass
        try:
            pg.wait_for_selector('div[role="feed"]', timeout=15000)
        except Exception:
            arq = nome_tela("maps-sem-lista")
            pg.screenshot(path=arq, type="jpeg", quality=70)
            print(json.dumps({"erro": "o Google Maps não mostrou a lista de resultados", "captura": arq, "endereco": pg.url}, ensure_ascii=False))
            b.close()
            return
        pg.screenshot(path=nome_tela("maps-" + busca), type="jpeg", quality=70)
        ant = -1
        for _ in range(14):
            qtd = pg.locator('div[role="feed"] a.hfpxzc').count()
            if qtd >= maximo or qtd == ant:
                break
            ant = qtd
            pg.evaluate("document.querySelector('div[role=\"feed\"]').scrollBy(0, 4000)")
            time.sleep(1.2)
        dados = pg.evaluate("""(max) => [...document.querySelectorAll('div[role="feed"] > div')].map(c => {
            const a = c.querySelector('a.hfpxzc'); if (!a) return null;
            const nota = c.querySelector('span.MW4etd'), av = c.querySelector('span.UY7F9');
            const site = [...c.querySelectorAll('a[href]')].find(x => x !== a && !x.href.includes('google.'));
            const linhas = [...c.querySelectorAll('.W4Efsd')].map(x => x.innerText).join(' · ');
            const tel = linhas.match(/\\(?\\d{2}\\)?\\s?9?\\d{4}[-\\s]?\\d{4}/);
            return { nome: a.getAttribute('aria-label'), nota: nota ? parseFloat(nota.innerText.replace(',', '.')) : null,
                     avaliacoes: av ? parseInt(av.innerText.replace(/\\D/g, '')) : null,
                     site: site ? site.href : null, telefone: tel ? tel[0] : null,
                     detalhes: linhas.slice(0, 160), maps: a.href };
        }).filter(Boolean).slice(0, max)""", maximo)
        pg.screenshot(path=nome_tela("maps-lista"), type="jpeg", quality=70)
        print(json.dumps({"busca": busca, "total": len(dados), "resultados": dados}, ensure_ascii=False, indent=1))
        b.close()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    a = sys.argv[1:]
    if not a or a[0] in ("ajuda", "-h", "--help"):
        print(__doc__)
    elif a[0] == "abrir" and len(a) > 1:
        abrir(a[1:])
    elif a[0] == "maps" and len(a) > 1:
        maps(a[1:])
    elif a[0] == "captura" and len(a) > 1:
        captura(a[1:])
    else:
        print(__doc__)
