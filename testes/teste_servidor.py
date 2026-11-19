"""Teste de ponta a ponta do Jarvis numa cópia isolada: porta 4790, pasta de dados própria, Claude Code de mentira (sem cota).
Confere: processo com parâmetros, pedido literal na missão, marco, freio da fala, ajuste em missão rodando (interrompe e retoma),
missão dentro de projeto, abrir pelo assunto, conversa numerada, modo só pelo nome, agenda, salvar processo e as rotas das abas."""
import asyncio, json, os, subprocess, sys, time
import aiohttp

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(__import__("tempfile").gettempdir(), "jarvis_testes")      # o que os testes criam fica fora da pasta do Jarvis
os.makedirs(SAIDA, exist_ok=True)
J = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(SAIDA, "jarvis_teste_" + time.strftime("%H%M%S"))
os.makedirs(os.path.join(PASTA, "dados"), exist_ok=True)
BASE = "http://127.0.0.1:4790"
ok_geral = True


def confere(nome, cond, extra=""):
    global ok_geral
    ok_geral = ok_geral and bool(cond)
    print(("OK   " if cond else "FALHA"), nome, ("· " + str(extra)) if extra else "")


async def main():
    amb = dict(os.environ)
    amb.update(JARVIS_TESTE=PASTA, JARVIS_PORTA="4790", JARVIS_CEREBRO="claude", PYTHONIOENCODING="utf-8", FALSO_DURA="12",
               JARVIS_LEADS=os.path.join(PASTA, "dados", "leads"), PYTHON=sys.executable)
    __import__("_cenario").preparar(PASTA, amb)      # um projeto e duas conversas de mentira
    FALSO = os.path.join(SAIDA, "falso")      # o Claude Code de mentira roda de uma pasta sem espaço nem "&" no caminho (o cmd não aceita)
    __import__("shutil").copytree(os.path.join(AQUI, "falso"), FALSO, dirs_exist_ok=True)
    if sys.platform != "win32":      # macOS e Linux: o falso é o script "claude" (sem extensão)
        os.chmod(os.path.join(FALSO, "claude"), 0o755)
    amb["PATH"] = FALSO + os.pathsep + amb["PATH"]
    exe = os.path.join(PASTA, "programa.bat")      # se a ação rápida executasse, ele criaria rodou.txt
    with open(exe, "w") as f:
        f.write("@echo rodou > \"" + os.path.join(PASTA, "rodou.txt") + "\"\n")
    amb["FALSO_EXE"] = exe
    saida = open(os.path.join(PASTA, "servidor.log"), "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, os.path.join(J, "jarvis.py"), "--sem-ouvido"], env=amb, cwd=PASTA, stdout=saida, stderr=subprocess.STDOUT)
    try:
        async with aiohttp.ClientSession() as s:
            for _ in range(40):
                try:
                    async with s.get(BASE + "/saude") as r:
                        if r.status == 200:
                            break
                except Exception:
                    await asyncio.sleep(0.5)
            else:
                print("FALHA o servidor de teste não subiu"); return

            async def estado():
                async with s.get(BASE + "/api/estado") as r:
                    return await r.json()

            async def diz(txt, espera=2.5):
                async with s.post(BASE + "/api/texto", json={"texto": txt}) as r:
                    await r.json()
                await asyncio.sleep(espera)
                return await estado()

            async def ate(cond, limite=40, passo=0.5):
                t0 = time.time()
                while time.time() - t0 < limite:
                    e = await estado()
                    if cond(e):
                        return e
                    await asyncio.sleep(passo)
                return await estado()

            def missao(e, n):
                return next((m for m in e["missoes"] if m["n"] == n), None)

            def args_de(m):
                for _ in range(20):      # o agente de mentira grava os argumentos logo depois de subir
                    if os.path.exists(os.path.join(m["pasta"], "trabalho", "args.txt")):
                        break
                    time.sleep(0.3)
                with open(os.path.join(m["pasta"], "trabalho", "args.txt"), encoding="utf-8") as f:
                    return [json.loads(l) for l in f if l.strip()]

            # rotas das abas
            async with s.get(BASE + "/api/processos") as r:
                d = await r.json()
            confere("aba PROCESSOS lista os processos", len(d["processos"]) >= 6 and any(p["id"] == "prospeccao" for p in d["processos"]), f"{len(d['processos'])} processos, {len(d['projetos'])} projetos")
            async with s.get(BASE + "/api/conversas") as r:
                dc = await r.json()
            confere("aba CONVERSAS lista conversas numeradas e projetos", len(dc["conversas"]) > 0 and len(dc["projetos"]) >= 1 and all(c["sessao"] is None for c in dc["conversas"]),
                    f"{len(dc['conversas'])} conversas, números {[c['numero'] for c in dc['conversas'][:5]]}")

            # 1. processo por voz, com parâmetros, pedido literal, marco e freio na fala
            ws = await s.ws_connect(BASE + "/ws")
            recebidas = []

            async def ouvir():
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        recebidas.append(json.loads(msg.data))
            asyncio.ensure_future(ouvir())
            await diz("Faz a prospecção das academias de Valinhos, São Paulo.", 3)
            e = await ate(lambda e: any(m["estado"] == "trabalhando" for m in e["missoes"]), 15)
            m1 = e["missoes"][-1] if e["missoes"] else None
            confere("pedido vira missão pelo processo", bool(m1) and m1["processo"] == "prospeccao" and m1["estado"] == "trabalhando", m1 and m1["titulo"])
            falas = [c["txt"] for c in e["conversa"] if c["quem"] == "jarvis"]
            confere("freio: a fala longa do cérebro saiu só com a primeira frase", falas and falas[-1] == "Está a caminho.", falas[-1:] )
            await asyncio.sleep(2.5)
            a = args_de(m1)[0]
            confere("roteiro do processo foi junto, com os parâmetros no lugar", "prospectar academias em Campinas, SP" in a["pedido"] and "leads.py juntar" in a["pedido"])
            confere("pedido literal dele vai no fim da missão", "Pedido literal de " in a["pedido"] and "Valinhos, São Paulo" in a["pedido"])
            confere("regras falam de marcos e da planilha de leads", "MARCO:" in a["regras"] and "leads.py" in a["regras"])
            e = await ate(lambda e: bool(missao(e, m1["n"])["marcos"]), 10)
            confere("marco do agente chegou e aparece no cartão", missao(e, m1["n"])["marcos"] == ["Achei 9 academias, 5 sem site"], missao(e, m1["n"])["marcos"])
            confere("marco foi avisado à tela", any(x.get("t") == "marco" for x in recebidas))
            e = await ate(lambda e: any(c["txt"].startswith("Achei 9 academias") for c in e["conversa"] if c["quem"] == "jarvis"), 12)
            confere("marco foi falado quando o Jarvis ficou livre", any(c["txt"].startswith("Achei 9 academias") for c in e["conversa"] if c["quem"] == "jarvis"))

            # 2. ajuste com a missão rodando: interrompe e retoma a mesma conversa com o recado
            t0 = time.time()
            await diz(f"Na missão {m1['n']}, é Valinhos, não Campinas.", 2.5)
            e = await ate(lambda e: len(args_de(missao(e, m1["n"]))) >= 2, 12)
            ar = args_de(missao(e, m1["n"]))
            confere("ajuste na missão rodando: interrompida e retomada na hora", len(ar) >= 2 and "--resume" in ar[-1]["args"], f"{time.time() - t0:.1f}s")
            confere("o recado chegou ao agente", len(ar) >= 2 and "Valinhos, não Campinas" in ar[-1]["pedido"] and "interrompido" in ar[-1]["pedido"])
            e = await ate(lambda e: missao(e, m1["n"])["estado"] != "trabalhando", 25)
            mm = missao(e, m1["n"])
            confere("a missão termina como concluída depois do ajuste", mm["estado"] == "concluida", mm["estado"] + " · " + mm["resumo"][:50])
            await asyncio.sleep(2.5)
            e = await estado()
            falas = [c["txt"] for c in e["conversa"] if c["quem"] == "jarvis"]
            confere("fim da missão: resultado e próximo passo numa fala só", falas[-1] == "O site ficou pronto. Quer que eu escreva o e-mail?", falas[-1:])
            confere("painel abre a entrega sozinho", e["painel"] and e["painel"]["missao"] == m1["n"], e["painel"])

            # 3. abrir pelo assunto
            async with s.post(BASE + "/api/texto", json={"texto": "fecha"}) as r:
                pass
            await ws.send_str(json.dumps({"t": "fechar"})); await asyncio.sleep(0.5)
            await diz("Abre o site das academias.", 1)
            e = await ate(lambda e: bool(e["painel"]), 10)
            confere("abrir pelo assunto acha a missão certa", e["painel"] and e["painel"]["missao"] == m1["n"], str(e["painel"]))

            # 3b. ler uma entrega: o cérebro recebe o texto do site e responde sobre ele
            await diz("O que tem no site das academias?", 1)
            e = await ate(lambda e: any(c["txt"].startswith("Li a página") for c in e["conversa"] if c["quem"] == "jarvis"), 15)
            lidas = [c["txt"] for c in e["conversa"] if c["quem"] == "jarvis" and c["txt"].startswith("Li a página")]
            confere("ler: o texto da entrega chega ao cérebro", lidas and lidas[-1] == "Li a página: tem o texto", lidas[-1:])
            # 3c. "abrir" um programa não executa: só mostra a pasta
            await diz("Abre o programa.", 2)
            for _ in range(10):
                log_srv = open(os.path.join(PASTA, "dados", "jarvis.log"), encoding="utf-8").read()
                if "é executável" in log_srv:
                    break
                await asyncio.sleep(0.5)
            confere("abrir um .bat não executa (abre só a pasta)", "é executável, abri só a pasta" in log_srv and not os.path.exists(os.path.join(PASTA, "rodou.txt")))
            confere("o log registra as ações", "ações: ler entrega=site assunto=academias" in log_srv)

            # 4. recado pela tela (campo do cartão) e missão dentro de um projeto
            await diz("Na Loja, corrige o botão de vender.", 3)
            e = await ate(lambda e: e["missoes"][-1]["n"] != m1["n"] and e["missoes"][-1]["estado"] == "trabalhando", 12)
            m2 = e["missoes"][-1]
            await asyncio.sleep(2)
            a2 = args_de(m2)[0]
            confere("missão de projeto roda dentro da pasta do projeto", m2["projeto"] == "Loja" and a2["cwd"].lower().endswith("loja") and "--add-dir" in a2["args"], a2["cwd"])
            confere("regras avisam do projeto", "Projeto em que você vai trabalhar" in a2["regras"])
            await ws.send_str(json.dumps({"t": "recado", "missao": m2["n"], "txt": "Use o botão laranja."}))
            e = await ate(lambda e: len(args_de(missao(e, m2["n"]))) >= 2, 12)
            confere("recado pelo campo do cartão também retoma", len(args_de(missao(e, m2["n"]))) >= 2 and "botão laranja" in args_de(missao(e, m2["n"]))[-1]["pedido"])
            await ate(lambda e: missao(e, m2["n"])["estado"] != "trabalhando", 25)

            # 5. conversa numerada do Claude Code: continua numa cópia
            num = dc["conversas"][0]["numero"]
            await diz(f"Na conversa {num}, pede para continuar o desenvolvimento.", 3)
            e = await ate(lambda e: e["missoes"][-1]["conversa"] == num, 12)
            m3 = e["missoes"][-1]
            await asyncio.sleep(2)
            a3 = args_de(m3)[0] if m3["conversa"] == num else {"args": [], "cwd": ""}
            confere("conversa numerada vira missão numa cópia da sessão", m3["conversa"] == num and "--resume" in a3["args"] and "--fork-session" in a3["args"],
                    f"C{num} -> missão #{m3['n']}, pasta {os.path.basename(a3['cwd'])}")
            await ate(lambda e: missao(e, m3["n"])["estado"] != "trabalhando", 25)

            # 6. modo só pelo nome, agenda, salvar processo, ação rápida
            e = await diz("Fica só pelo nome.", 2.5)
            confere("modo só pelo nome liga e aparece na tela", e["info"]["escuta"] == "nome")
            async with s.post(BASE + "/api/ajuste", json={"escuta": "aberta"}) as r:
                await r.json()
            e = await estado()
            confere("etiqueta do topo volta para conversa aberta", e["info"]["escuta"] == "aberta")
            e = await diz("Todo dia às 8 faz o resumo do dia.", 2.5)
            confere("agendar por voz", len(e["agenda"]) == 1 and e["agenda"][0]["processo"] == "resumo_do_dia" and e["agenda"][0]["hora"] == "08:00", e["agenda"])
            e = await diz("Quanto é 17 vezes 23?", 2.5)
            falas = [c["txt"] for c in e["conversa"] if c["quem"] == "jarvis"]
            confere("pergunta dele libera até três frases (e corta a quarta)", falas[-1].count(".") == 3 and "método" not in falas[-1], falas[-1:])
            async with s.post(BASE + "/api/ajuste", json={"cerebro": "claude"}) as r:
                d = await r.json()
            e = await estado()
            confere("etiqueta do cérebro troca o modo", d["ok"] and e["info"]["cerebro_modo"] == "claude")

            # 7. aba PROCESSOS: rodar pela tela com parâmetros e criar um processo novo
            async with s.post(BASE + "/api/processos", json={"rodar": "pesquisa_mercado", "parametros": {"nicho": "dentistas", "cidade": "Sorocaba, SP"}}) as r:
                d = await r.json()
            e = await ate(lambda e: e["missoes"][-1]["processo"] == "pesquisa_mercado", 10)
            m4 = e["missoes"][-1]
            await asyncio.sleep(2)
            confere("rodar processo pela tela, com parâmetros", d["ok"] and "dentistas em Sorocaba, SP" in args_de(m4)[0]["pedido"], m4["titulo"])
            await ws.send_str(json.dumps({"t": "parar", "v": m4["n"]}))
            e = await ate(lambda e: missao(e, m4["n"])["estado"] == "parada", 10)
            confere("parar a missão pelo cartão", missao(e, m4["n"])["estado"] == "parada")
            await ws.close()
    finally:
        try:
            async with aiohttp.ClientSession() as s2:
                async with s2.post(BASE + "/api/sair", json={}) as r:
                    pass
        except Exception:
            pass
        await asyncio.sleep(1)
        if proc.poll() is None:
            proc.terminate()
        saida.close()
    print("\nlog do servidor (fim):")
    with open(os.path.join(PASTA, "servidor.log"), encoding="utf-8", errors="replace") as f:
        print("".join(f.readlines()[-22:]))
    print("TUDO CERTO" if ok_geral else "TEM FALHA")
    print(PASTA)
    sys.exit(0 if ok_geral else 1)

asyncio.run(main())
