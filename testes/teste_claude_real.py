"""Prova com o Claude Code de verdade (Haiku, pasta isolada): as regras chegam inteiras, o modelo pedido é o usado,
'continuar' retoma a mesma conversa e o ajuste no meio interrompe e retoma. Duas missões curtas."""
import asyncio, json, os, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(__import__("tempfile").gettempdir(), "jarvis_testes")      # o que os testes criam fica fora da pasta do Jarvis
os.makedirs(SAIDA, exist_ok=True)
PASTA = os.path.join(SAIDA, "jarvis_real_" + time.strftime("%H%M%S"))
os.makedirs(PASTA, exist_ok=True)
os.environ["JARVIS_TESTE"] = PASTA
sys.path.insert(0, os.path.dirname(AQUI))
sys.stdout.reconfigure(encoding="utf-8")
import agentes

CFG = __import__("configuracao").carregar()
ok_geral = True


def confere(nome, cond, extra=""):
    global ok_geral
    ok_geral = ok_geral and bool(cond)
    print(("OK   " if cond else "FALHA"), nome, ("· " + str(extra)) if extra else "")


async def main():
    fim = asyncio.Event()
    marcos, modelos = [], set()
    ag = agentes.Agentes(CFG, lambda t: print("   log:", t), lambda: None, lambda m: fim.set(), lambda m, t: marcos.append(t))
    original = ag._ev_claude

    def espia(m, ev):
        if ev.get("type") == "assistant" and (ev.get("message") or {}).get("model"):
            modelos.add(ev["message"]["model"])
        original(m, ev)
    ag._ev_claude = espia

    async def espera(limite=240):
        fim.clear()
        try:
            await asyncio.wait_for(fim.wait(), limite)
        except asyncio.TimeoutError:
            print("   (passou do tempo de espera)")

    # 1. regras inteiras + modelo
    m, erro = await ag.criar("claude", "Prova das regras", (
        "Esta é uma conferência rápida, sem pesquisa e sem navegador. Faça só isto:\n"
        "1. Crie o arquivo entregas/prova.md com quatro linhas, copiadas das regras que você recebeu do Jarvis: "
        "(a) o caminho completo da pasta da missão; (b) as três marcas de RESULTADO possíveis; (c) para onde vai um arquivo que não pode ser apagado; "
        "(d) o caminho completo da ferramenta leads.py.\n"
        "2. Escolha uma palavra secreta de fruta e NÃO a escreva em arquivo nenhum: só diga a palavra na sua mensagem final.\n"
        "3. Antes de terminar, mande um marco no formato pedido nas regras."), nivel="leve")
    confere("missão criada", m is not None, erro)
    await espera()
    prova = ""
    try:
        prova = open(os.path.join(m.pasta, "entregas", "prova.md"), encoding="utf-8").read()
    except OSError:
        pass
    print("   estado:", m.estado, "| resumo:", m.resumo[:140].replace("\n", " "))
    print("   prova.md:", prova[:420].replace("\n", " | "))
    confere("terminou como concluída e com a marca RESULTADO tratada", m.estado == "concluida" and not m.resumo.upper().startswith("RESULTADO"))
    confere("regras chegaram inteiras (pasta, marcas, destino do que não se apaga e leads.py aparecem na prova)",
            os.path.basename(m.pasta) in prova and "PARCIAL" in prova and ("LIXEIRA" in prova or "descartados" in prova) and "leads.py" in prova)
    confere("o modelo pedido (leve = haiku) foi o usado", modelos and all("haiku" in x for x in modelos), sorted(modelos))
    confere("o marco chegou", len(marcos) >= 1, marcos)
    sessao1 = m.sessao

    # 2. continuar retoma a MESMA conversa (lembra da palavra secreta, que não está em arquivo nenhum)
    palavra = m.resumo
    m2, erro = await ag.continuar(m.n, "Sem abrir arquivo nenhum: qual foi a palavra secreta que você escolheu? Responda numa frase curta.")
    await espera()
    print("   resposta:", m.resumo[:160].replace("\n", " "))
    frutas = [w.strip(".,!?\"'*`").lower() for w in palavra.split() if len(w) > 3]
    lembrou = any(w in m.resumo.lower() for w in frutas if w not in ("resultado", "arquivo", "palavra", "secreta", "marco", "criado", "entregas", "prova", "prova.md", "missão", "regras", "linhas"))
    confere("continuar retoma a mesma conversa (lembrou a palavra)", m.estado == "concluida" and lembrou, f"sessão {str(sessao1)[:8]} -> {str(m.sessao)[:8]}")

    # 3. ajuste no meio: interrompe e retoma já com o recado
    modelos.clear()
    m3, erro = await ag.criar("claude", "Prova do ajuste", (
        "Conferência rápida, sem pesquisa. Faça nesta ordem, um comando por vez:\n"
        f'1. Rode `"{sys.executable}" -c "import time; time.sleep(25)"`.\n'
        "2. Crie entregas/cidade.txt com o nome da cidade: Campinas.\n"), nivel="leve")
    await asyncio.sleep(12)
    t0 = time.time()
    await ag.continuar(m3.n, "A cidade certa é Valinhos. Use esse nome no arquivo.")
    await espera()
    cidade = ""
    try:
        cidade = open(os.path.join(m3.pasta, "entregas", "cidade.txt"), encoding="utf-8").read()
    except OSError:
        pass
    print("   estado:", m3.estado, "| cidade.txt:", cidade.strip()[:60], "| resumo:", m3.resumo[:120].replace("\n", " "))
    confere("ajuste no meio: a missão termina com a cidade corrigida", m3.estado == "concluida" and "Valinhos" in cidade and "Campinas" not in cidade, f"{time.time() - t0:.0f}s depois do ajuste")
    print("TUDO CERTO" if ok_geral else "TEM FALHA")
    print(PASTA)

asyncio.run(main())
