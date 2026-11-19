"""1) Planilha de leads: juntar, não repetir, próxima, marcar, copiar. 2) Ouvido: filtro de voz (Silero) com fala curta, frase e ruído."""
import asyncio, json, os, subprocess, sys, time, wave
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(__import__("tempfile").gettempdir(), "jarvis_testes")      # o que os testes criam fica fora da pasta do Jarvis
os.makedirs(SAIDA, exist_ok=True)
J = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(SAIDA, "leads_teste_" + time.strftime("%H%M%S"))
os.makedirs(PASTA, exist_ok=True)
ok_geral = True


def confere(nome, cond, extra=""):
    global ok_geral
    ok_geral = ok_geral and bool(cond)
    print(("OK   " if cond else "FALHA"), nome, ("· " + str(extra)) if extra else "")


def leads(*a):
    amb = dict(os.environ, JARVIS_LEADS=os.path.join(PASTA, "leads"), PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(J, "ferramentas", "leads.py"), *a], capture_output=True, text=True, encoding="utf-8", env=amb)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"bruto": r.stdout + r.stderr}


# ---------- 1. leads ----------
maps = {"busca": "academias em Valinhos", "total": 4, "resultados": [
    {"nome": "Academia Corpo & Mente", "nota": 4.9, "avaliacoes": 48, "site": "https://www.instagram.com/corpoemente", "telefone": "(43) 99999-0000", "detalhes": "Rua A, 10", "maps": "https://maps/1"},
    {"nome": "Fit Center", "nota": 4.6, "avaliacoes": 120, "site": "https://fitcenter.com.br", "telefone": None, "detalhes": "Rua B", "maps": "https://maps/2"},
    {"nome": "Studio Movimento", "nota": 5.0, "avaliacoes": 12, "site": None, "telefone": "(43) 3333-1111", "detalhes": "Rua C", "maps": "https://maps/3"},
    {"nome": "Academia Velha", "nota": 3.9, "avaliacoes": 8, "site": "https://wa.me/5543999", "telefone": None, "detalhes": "Rua D", "maps": "https://maps/4"}]}
arq = os.path.join(PASTA, "maps.json")
with open(arq, "w", encoding="utf-8") as f:
    f.write("aviso qualquer antes do JSON\n" + json.dumps(maps, ensure_ascii=False))
r = leads("juntar", "academias", "Valinhos, SP", arq)
confere("juntar: 4 empresas entram como novas", r.get("entraram") == 4 and r.get("total") == 4, r)
r = leads("juntar", "Academias", "valinhos sp", arq)
confere("juntar de novo (mesmo nicho escrito diferente): ninguém entra duas vezes", r.get("entraram") == 0 and r.get("total") == 4, r)
r = leads("lista", "academias", "Valinhos, SP")
porn = {l["nome"]: l for l in r["leads"]}
confere("Instagram e WhatsApp não contam como site", porn["Academia Corpo & Mente"]["site"] == "" and "instagram.com" in porn["Academia Corpo & Mente"]["instagram"] and porn["Academia Velha"]["site"] == "")
r = leads("proximo", "academias", "Valinhos, SP", "--n", "2")
confere("próximo: melhor nota primeiro", [l["nome"] for l in r["proximos"]] == ["Studio Movimento", "Academia Corpo & Mente"], [l["nome"] for l in r["proximos"]])
leads("marcar", "academias", "Valinhos, SP", "Studio Movimento", "--situacao", "email_pronto", "--obs", "sem site; site novo feito", "--missao", "15")
leads("marcar", "academias", "Valinhos, SP", "academia velha", "--situacao", "descartado", "--obs", "nota 3,9")
r = leads("proximo", "academias", "Valinhos, SP", "--n", "5")
confere("quem já foi trabalhado sai da fila", [l["nome"] for l in r["proximos"]] == ["Academia Corpo & Mente", "Fit Center"] and r["restam"] == 2, [l["nome"] for l in r["proximos"]])
r = leads("marcar", "academias", "Valinhos, SP", "Fit Center", "--situacao", "inventada")
confere("situação desconhecida é recusada", "erro" in r)
saida = os.path.join(PASTA, "entregas", "leads.csv")
r = leads("copiar", "academias", "Valinhos, SP", "--saida", saida)
confere("copiar para a entrega", r.get("ok") and os.path.exists(saida) and open(saida, encoding="utf-8-sig").read().count("\n") == 5)
r = leads("planilhas")
confere("planilhas: resumo por situação", isinstance(r, list) and r and r[0]["total"] == 4 and r[0]["por_situacao"].get("email_pronto") == 1, r and r[0]["por_situacao"])

# ---------- 2. ouvido ----------
sys.path.insert(0, J)
import ouvido, voz

CFG = __import__("configuracao").carregar()
t = ouvido.Transcritor(CFG, lambda x: None)
t.carregar()
print("transcrição:", t.onde)


def audio_de(frase):
    v = voz.Voz(CFG, print)
    nome = asyncio.run(v.gerar(frase))
    wav = os.path.join(PASTA, nome + ".wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(voz.PASTA, nome), "-ac", "1", "-ar", "16000", wav], check=True)
    w = wave.open(wav)
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return np.concatenate([np.zeros(6400, np.float32), a, np.zeros(9600, np.float32)])     # com o silêncio que o gravador deixa em volta


def mede(a):
    t0 = time.time(); txt = t.transcrever(a)
    return txt, time.time() - t0


for frase, esperado in (("Jarvis.", "jarvis"), ("Sim.", "sim"), ("Abre o YouTube pra mim.", "youtube"), ("Faz a prospecção das academias de Valinhos, em São Paulo.", "valinhos")):
    txt, dt = mede(audio_de(frase))
    confere(f"filtro de voz ligado: ouve {frase!r}", esperado in txt.lower(), f"{txt!r} em {dt:.2f}s")
rng = np.random.default_rng(3)
ruido = (rng.standard_normal(16000 * 3) * 0.02).astype(np.float32)
teclado = np.zeros(16000 * 3, np.float32)
for i in range(0, len(teclado), 2600):
    teclado[i:i + 240] = (rng.standard_normal(240) * 0.35).astype(np.float32)[:len(teclado[i:i + 240])]
for nome, a in (("chiado", ruido), ("batidas de teclado", teclado)):
    txt, dt = mede(a)
    confere(f"filtro de voz ligado: {nome} não vira frase", txt == "", f"{txt!r} em {dt:.2f}s")
CFG2 = dict(CFG, filtro_de_voz=False); t.cfg = CFG2
for nome, a in (("chiado", ruido), ("batidas de teclado", teclado)):
    txt, dt = mede(a)
    print(f"      (sem o filtro, {nome} dava: {txt!r})")
print("TUDO CERTO" if ok_geral else "TEM FALHA")
sys.exit(0 if ok_geral else 1)
