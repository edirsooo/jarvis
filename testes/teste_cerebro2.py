"""A personalidade nova, com os cérebros de verdade: o Claude (Haiku) e o local (Gemma). Confere se cada pedido vira a ação certa."""
import asyncio, json, os, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(__import__("tempfile").gettempdir(), "jarvis_testes")      # o que os testes criam fica fora da pasta do Jarvis
os.makedirs(SAIDA, exist_ok=True)
PASTA = os.path.join(SAIDA, "jarvis_cerebro_" + time.strftime("%H%M%S"))
os.makedirs(PASTA, exist_ok=True)
os.environ["JARVIS_TESTE"] = PASTA
sys.path.insert(0, os.path.dirname(AQUI))
sys.stdout.reconfigure(encoding="utf-8")
import cerebro

CFG = __import__("configuracao").carregar()
BASE = ("[estado] hora 21:10 | missões: #13 claude \"Ir ao download do LoL\" concluida; #14 claude \"Prospecção de academias em Valinhos\" {e14} | painel aberto: nenhum"
        " | cotas das assinaturas: Claude semana 92% usado, Codex semana 60% usado"
        " | planilhas de leads: academias em valinhos sp (6 empresas, 4 na fila)"
        " | conversas do Claude Code: C3 \"CRM: funil\" (crm); C7 \"Painel de cotas novo\" (painel); C9 \"Loja: carrinho\" (loja)")
PRONTA = "concluida entregas: site.html, email.md, relatorio.md"
RODANDO = "trabalhando (Abrindo o site da Corpo e Mente)"
CASOS = [
    ("processo com parâmetros", PRONTA, "[dono] Faz a prospecção dos dentistas de Sorocaba, São Paulo.",
     lambda r, a: a and a[0].get("tipo") == "processo" and a[0].get("id") == "prospeccao" and "dentista" in json.dumps(a[0], ensure_ascii=False).lower() and "sorocaba" in json.dumps(a[0], ensure_ascii=False).lower()),
    ("ajuste na missão rodando", RODANDO, "[dono] Na 14, é Valinhos, não Campinas.",
     lambda r, a: a and a[0].get("tipo") == "continuar" and str(a[0].get("missao")) == "14" and "santa amélia" in a[0].get("instrucao", "").lower()),
    ("programar num projeto", PRONTA, "[dono] Na Loja, corrige o botão de vender que não está clicando.",
     lambda r, a: a and a[0].get("tipo") in ("processo", "delegar") and "loja" in str(a[0].get("projeto", "")).lower()),
    ("conversa numerada", PRONTA, "[dono] Na conversa 7, pede para continuar o desenvolvimento.",
     lambda r, a: a and a[0].get("tipo") == "conversa" and str(a[0].get("numero")) == "7"),
    ("abrir pelo assunto ou número", PRONTA, "[dono] Abre o site das academias.",
     lambda r, a: a and a[0].get("tipo") == "abrir" and (str(a[0].get("missao")) == "14" or "academ" in str(a[0].get("assunto", "")).lower())),
    ("próxima da prospecção", PRONTA, "[dono] Próxima empresa.",
     lambda r, a: a and a[0].get("tipo") == "processo" and a[0].get("id") == "prospeccao" and "prox" in json.dumps(a[0].get("parametros", {}), ensure_ascii=False).lower()),
    ("frase que não é para ele", PRONTA, "[dono] Amor, pega o controle ali pra mim, tá do lado da TV.",
     lambda r, a: not r["fala"].strip() and any(x.get("tipo") == "dormir" for x in a)),
    ("agendar", PRONTA, "[dono] Todo dia às oito da manhã faz o resumo do dia.",
     lambda r, a: a and a[0].get("tipo") == "agendar" and a[0].get("processo") == "resumo_do_dia" and str(a[0].get("hora", "")).lstrip("0").startswith("8:00")),
    ("só pelo nome", PRONTA, "[dono] Tem gente aqui na sala, fica só pelo nome.",
     lambda r, a: any(x.get("tipo") == "escuta" and x.get("modo") == "nome" for x in a)),
    ("conta de cabeça, sem missão", PRONTA, "[dono] Quanto é 17 vezes 23?",
     lambda r, a: "391" in r["fala"] and not a),
    ("fim de missão: resultado e próximo passo", PRONTA, "[sistema] A missão #14 \"Prospecção de academias em Valinhos\" terminou com estado concluida. Resumo do aprendiz (para você entender; não leia em voz alta): A planilha tem 6 academias, 4 sem site. O alvo foi a Corpo e Mente (nota 4,9): site novo e e-mail em rascunho prontos. Ainda há 4 na fila. Diga 'próxima' para eu seguir. | Entregas na tela: imagem, site, texto",
     lambda r, a: 0 < len(r["fala"]) < 170 and not a),
]


async def roda(nome, c):
    print(f"\n===== {nome} =====")
    certos = 0
    for rot, e14, frase, ok in CASOS:
        t0 = time.time(); cedo = {}
        r = await c.pensar(BASE.format(e14=e14) + "\n" + frase, ao_falar=lambda x: cedo.update(t=time.time() - t0))
        acoes = [x for x in r.get("acoes", []) if isinstance(x, dict)]
        try:
            bom = bool(ok(r, acoes))
        except Exception:
            bom = False
        certos += bom
        resumo = json.dumps([{k: (v[:46] if isinstance(v, str) else v) for k, v in x.items()} for x in acoes], ensure_ascii=False)
        print(f"{'OK   ' if bom else 'FALHA'} {rot} · fala em {cedo.get('t', time.time() - t0):.1f}s: {r['fala'][:110]!r}\n        {resumo[:230]}")
    print(f"--- {nome}: {certos} de {len(CASOS)}")
    return certos


async def main():
    qual = sys.argv[1] if len(sys.argv) > 1 else "os dois"
    cl = cerebro.Cerebro(CFG, lambda t: None)
    if qual in ("claude", "os dois"):
        await roda("Claude (Haiku)", cl)
        await cl.reiniciar()
    if qual in ("local", "os dois"):
        lo = cerebro.CerebroLocal(CFG, lambda t: print("   log:", t), cl._prompt)
        if await lo.disponivel():
            await lo.aquecer()
            await roda("Local (Gemma)", lo)

asyncio.run(main())
