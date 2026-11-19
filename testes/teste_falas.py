"""Pedido falado em pedaços: confere a junção, o descarte da resposta pela metade, o 'não é contigo' e a missão redigida pelo Claude.
Roda o Jarvis de verdade por dentro, com cérebro, voz e ouvido de mentira (sem rede, sem som, sem cota)."""
import asyncio, os, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(__import__("tempfile").gettempdir(), "jarvis_testes")      # o que os testes criam fica fora da pasta do Jarvis
os.makedirs(SAIDA, exist_ok=True)
PASTA = os.path.join(SAIDA, "jarvis_falas_" + time.strftime("%H%M%S"))
os.makedirs(PASTA, exist_ok=True)
os.environ["JARVIS_TESTE"] = PASTA
os.environ["JARVIS_PORTA"] = "4791"
sys.argv = ["jarvis.py", "--sem-ouvido"]
sys.path.insert(0, os.path.dirname(AQUI))
sys.stdout.reconfigure(encoding="utf-8")
import jarvis

ok_geral = True


def confere(nome, cond, extra=""):
    global ok_geral
    ok_geral = ok_geral and bool(cond)
    print(("OK   " if cond else "FALHA"), nome, ("· " + str(extra)) if extra else "")


class OuvidoFalso:
    def __init__(self):
        self.ocup = False
        self.jarvis_falando = False
        self.mudo = False

    def ocupado(self):
        return self.ocup


async def main():
    j = jarvis.Jarvis()
    j.laco = asyncio.get_running_loop()
    j.ouvido = OuvidoFalso()
    pensou, falou, agiu = [], [], []

    async def pensar(texto, ao_falar=None):
        pensou.append(texto)
        await asyncio.sleep(0.8)
        ult = texto.split("\n")[-1].lower()
        if "busca" in ult or "relatório" in ult:
            if ao_falar:
                ao_falar("Está a caminho.")
            return {"fala": "Está a caminho.", "acoes": [{"tipo": "delegar", "agente": "claude", "titulo": "Busca", "missao": ult}]}
        if ao_falar:
            ao_falar("Estou aqui.")
        return {"fala": "Estou aqui.", "acoes": []}

    async def falar(texto):
        falou.append(texto)

    async def acao(a):
        agiu.append(a)

    j.cerebro.pensar = pensar
    j.falar = falar
    j.acao = acao

    def zera():
        pensou.clear(); falou.clear(); agiu.clear(); j.conversa.clear()

    async def espera_fim():
        for _ in range(100):
            await asyncio.sleep(0.1)
            if not j._despachando and not j.vez.locked():
                return

    # 1. frase única: um pensamento, uma ação
    j._ouviu("Faz uma busca de academias em Valinhos.", False)
    await espera_fim()
    confere("frase única: uma resposta e uma ação", len(pensou) == 1 and len(agiu) == 1 and falou == ["Está a caminho."], f"{len(pensou)} pensamento(s), {len(agiu)} ação(ões)")
    confere("a ação leva o pedido literal", agiu and agiu[0].get("_literal") == "Faz uma busca de academias em Valinhos.")

    # 2. ele ainda está falando quando o primeiro pedaço vira texto: espera e manda junto
    zera()
    j.ouvido.ocup = True
    j._ouviu("Busca aqui de academias em Valinhos, São Paulo.", False)
    await asyncio.sleep(0.6)
    confere("com ele ainda falando, nada vai para o cérebro", len(pensou) == 0)
    j._ouviu("Que você faça um relatório, no caso.", False)
    await asyncio.sleep(0.3)
    j._ouviu("E eu quero ver também aquele comparativo.", False)
    j.ouvido.ocup = False
    await espera_fim()
    juntou = pensou[0].split("\n")[-1] if pensou else ""
    confere("três pedaços viram UM pedido", len(pensou) == 1 and len(agiu) == 1, juntou[:110])
    confere("na ordem em que foram ditos", "Valinhos, São Paulo. Que você faça um relatório, no caso. E eu quero ver também aquele comparativo." in juntou)

    # 3. ele volta a falar enquanto o cérebro pensa: a resposta pela metade é descartada e o pedido é refeito inteiro
    zera()
    j._ouviu("Busca aqui de academias em Valinhos.", False)
    await asyncio.sleep(0.3)
    j.ouvido.ocup = True            # recomeçou a falar com o cérebro pensando
    await asyncio.sleep(0.9)        # o cérebro termina de responder ao primeiro pedaço
    confere("resposta ao pedaço não vira ação enquanto ele fala", len(agiu) == 0 and len(falou) == 0, f"ações {len(agiu)}, falas {len(falou)}")
    j._ouviu("E faz um relatório com o comparativo.", False)
    j.ouvido.ocup = False
    await espera_fim()
    confere("pedido refeito com a frase inteira, uma ação só", len(pensou) == 2 and len(agiu) == 1, f"{len(pensou)} pensamentos, {len(agiu)} ação")
    confere("o cérebro é avisado de que a resposta anterior foi descartada", "foi cortada no meio" in pensou[1] and "Valinhos. E faz um relatório com o comparativo." in pensou[1])
    confere("a ação refeita leva a frase inteira", agiu and agiu[0].get("_literal") == "Busca aqui de academias em Valinhos. E faz um relatório com o comparativo.")
    confere("fala uma vez só", falou == ["Está a caminho."], falou)

    # 4. frase que não é para ele: dorme na hora, sem cérebro e sem fala
    zera()
    j.mudar_estado("ouvindo"); j.manter_acordado()
    j._ouviu("Não, eu tava falando com a minha esposa, não era pra ti não.", False)
    await asyncio.sleep(0.4)
    confere("'não era pra ti': dorme sem responder", len(pensou) == 0 and len(falou) == 0 and j.estado == "dormindo" and not j.acordado(), j.estado)
    for frase, esperado in (("Não é contigo.", True), ("Tô falando com a minha esposa.", True), ("Não é contigo que eu quero falar, é com o Claude", True),
                            ("Fala com a minha esposa que o vídeo ficou pronto", False), ("Isso não é comigo, é com o cliente", False)):
        confere(f"detector: {frase!r}", bool(jarvis.NAO_E_CONTIGO.search(frase)) == esperado)

    # 5. com o cérebro local em uso, a missão é redigida pelo Claude
    zera()
    redigiu = []

    async def redigir(linha, antes=()):
        redigiu.append(linha)
        return [{"tipo": "processo", "id": "prospeccao", "parametros": {"nicho": "academias", "cidade": "Valinhos, SP"}, "pedido": "redigida pelo Claude"}]
    j.cerebro.redigir = redigir
    j.cerebro.em_uso = "local"
    j._ouviu("Faz uma busca de academias em Valinhos.", False)
    await espera_fim()
    confere("cérebro local: a missão executada é a redigida pelo Claude", len(redigiu) == 1 and len(agiu) == 1 and agiu[0].get("pedido") == "redigida pelo Claude" and agiu[0].get("_literal"), agiu[:1])
    j.cerebro.em_uso = "claude"

    # 6. janela de conversa: curta, e desligada no modo só pelo nome
    j.so_nome = False; j.manter_acordado()
    janela = j.acordado_ate - time.time()
    confere("conversa aberta dura 12 s (era 25 a 40)", 11 <= janela <= 12.5, f"{janela:.1f}s")
    j.so_nome = True; j.acordado_ate = 0; j.manter_acordado()
    confere("só pelo nome: não fica acordado depois da resposta", j.acordado_ate <= time.time())
    j.manter_acordado(forcar=True)
    confere("só pelo nome: clique no orbe ainda abre a escuta", j.acordado_ate > time.time() + 5)

    # 7. limite de cota no Claude: não repete à toa e avisa direito (em vez de "Perdi o fio")
    import cerebro as cerebro_mod
    c = cerebro_mod.Cerebro(jarvis.CFG, lambda x: None)
    chamadas = []

    async def abrir_limite():
        chamadas.append(1)
        raise RuntimeError("You've hit your weekly limit · resets 5am")
    c._abrir = abrir_limite
    r_lim = await c.pensar("[dono] Oi")
    confere("cota estourada: avisa que acabou sem repetir à toa", len(chamadas) == 1 and "cota" in r_lim["fala"].lower() and r_lim.get("erro"), r_lim["fala"])
    print("TUDO CERTO" if ok_geral else "TEM FALHA")
    sys.exit(0 if ok_geral else 1)

asyncio.run(main())
