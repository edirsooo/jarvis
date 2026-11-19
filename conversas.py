"""Projetos e conversas, para se referir a eles por voz.

- Projetos: apelido falado -> pasta (dados\\projetos.json). "Na loja, corrige o botão" abre a missão dentro da pasta do projeto.
- Conversas: as sessões do Claude Code deste computador, cada uma com um número que nunca muda nem é reaproveitado
  (dados\\conversas.json). "Na conversa 7, pede para continuar" retoma uma cópia dela como missão do Jarvis.
  Daqui só saem título, pasta e data: o conteúdo das conversas não é lido nem mostrado.
"""
import glob, json, os, re, time, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.environ.get("JARVIS_TESTE") or AQUI
ARQ_PROJETOS = os.path.join(RAIZ, "dados", "projetos.json")
ARQ_CONVERSAS = os.path.join(RAIZ, "dados", "conversas.json")
SESSOES = os.environ.get("JARVIS_SESSOES") or os.path.join(os.path.expanduser("~"), ".claude", "projects")

PROJETOS_PADRAO = []       # os projetos são cadastrados por você, na aba CONVERSAS ou por voz ("cadastra o projeto...")


def chave(txt):
    t = unicodedata.normalize("NFKD", str(txt or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _ler(arq, padrao):
    try:
        with open(arq, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao


def _gravar(arq, dado):
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    tmp = arq + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dado, f, ensure_ascii=False, indent=1)
    os.replace(tmp, arq)


# ---------- projetos ----------
def projetos():
    ps = _ler(ARQ_PROJETOS, None)
    if ps is None:
        ps = [p for p in PROJETOS_PADRAO if os.path.isdir(p["pasta"])]
        try:
            _gravar(ARQ_PROJETOS, ps)
        except OSError:
            pass
    return [dict(p, existe=os.path.isdir(p.get("pasta", ""))) for p in ps]


def projeto(nome):
    """Acha o projeto pelo nome ou por um apelido falado. None se não achar ou a pasta não existir."""
    alvo = chave(nome)
    if not alvo:
        return None
    ps = projetos()
    for p in ps:
        if alvo == chave(p["nome"]) or alvo in [chave(a) for a in p.get("apelidos", [])]:
            return p if p["existe"] else None
    for p in ps:      # "o projeto da loja", "o site da loja"
        if any(chave(a) and chave(a) in alvo for a in [p["nome"]] + p.get("apelidos", [])):
            return p if p["existe"] else None
    return None


def salvar_projeto(nome, pasta, apelidos=None):
    nome, pasta = str(nome or "").strip(), str(pasta or "").strip().strip('"')
    if not nome or not os.path.isdir(pasta):
        return None, "preciso de um nome e de uma pasta que exista"
    ps = [p for p in _ler(ARQ_PROJETOS, None) or [q for q in PROJETOS_PADRAO if os.path.isdir(q["pasta"])] if chave(p["nome"]) != chave(nome)]
    ap = sorted({chave(a) for a in ([nome] + list(apelidos or [])) if chave(a)})
    ps.append({"nome": nome, "apelidos": ap, "pasta": pasta})
    _gravar(ARQ_PROJETOS, ps)
    return ps[-1], None


def projetos_para_o_cerebro():
    ps = [p for p in projetos() if p["existe"]]
    if not ps:
        return ""
    return ("# Projetos de {dono}\nQuando ele pedir para programar, corrigir ou mexer num destes, ponha o campo \"projeto\" na ação "
            "(a missão trabalha dentro da pasta do projeto): " + ", ".join(f"\"{p['nome']}\"" for p in ps) + ".")


# ---------- conversas do Claude Code ----------
FORA = ("jarvis-missoes", "jarvis-dados-cerebro", "scratch-workspaces", "appdata-local-temp", "jarvis-testes", "jarvis_testes", "-teste-")


_CABECAS = {}      # arquivo -> ((mtime, tamanho), (título, pasta, última pergunta)): só relê o que mudou


def _varrer_linhas(linhas, titulo="", pasta="", ultimo=""):
    for l in linhas:
        marcas = ('"custom-title"' in l, '"last-prompt"' in l, '"relocated"' in l)
        # quase toda linha tem "cwd": só vale abrir o JSON dela enquanto a pasta não apareceu (linhas de ferramenta chegam a MB)
        if not any(marcas) and (pasta or '"cwd"' not in l):
            continue
        try:
            d = json.loads(l)
        except Exception:
            continue
        t = d.get("type")
        if t == "custom-title" and d.get("customTitle"):
            titulo = str(d["customTitle"])
        elif t == "last-prompt" and d.get("lastPrompt"):
            ultimo = str(d["lastPrompt"])
        elif t == "relocated" and d.get("relocatedCwd"):
            pasta = str(d["relocatedCwd"])
        elif d.get("cwd") and not pasta:
            pasta = str(d["cwd"])
    return titulo, pasta, ultimo


def _cabeca(arq, limite=400):
    """Título, pasta e última pergunta de uma sessão, lendo só o começo e o fim do arquivo.
    Fica guardado por arquivo: sem mudança não relê; a conversa que está crescendo relê só o fim."""
    try:
        st = os.stat(arq)
    except OSError:
        return "", "", ""
    chave = (st.st_mtime_ns, st.st_size)
    guardado = _CABECAS.get(arq)
    if guardado and guardado[0] == chave:
        return guardado[1]
    titulo = pasta = ultimo = ""
    try:
        with open(arq, encoding="utf-8", errors="replace") as f:
            if guardado and guardado[1][1] and st.st_size >= guardado[0][1]:
                # já conhecida e só cresceu: o começo não mudou; lê só o que entrou no fim
                titulo, pasta, ultimo = guardado[1]
                f.seek(max(0, guardado[0][1] - 1, st.st_size - 200_000))
                f.readline()
                titulo, pasta, ultimo = _varrer_linhas(f.readlines()[-300:], titulo, pasta, ultimo)
            else:
                linhas = []
                for i, l in enumerate(f):
                    linhas.append(l)
                    if i >= limite:
                        break
                if st.st_size > 400_000:
                    f.seek(max(0, st.st_size - 200_000))
                    f.readline()
                    linhas += f.readlines()[-300:]
                titulo, pasta, ultimo = _varrer_linhas(linhas)
    except OSError:
        pass
    _CABECAS[arq] = (chave, (titulo, pasta, ultimo))
    return titulo, pasta, ultimo


def conversas(max_itens=24, dias=21):
    """As conversas recentes do Claude Code, da mais nova para a mais velha, cada uma com o seu número fixo."""
    mapa = _ler(ARQ_CONVERSAS, {"seq": 0, "numeros": {}})
    agora, achadas = time.time(), []
    try:
        arqs = glob.glob(os.path.join(SESSOES, "*", "*.jsonl"))
    except OSError:
        arqs = []
    arqs = [a for a in arqs if not any(x in os.path.basename(os.path.dirname(a)).lower() for x in FORA)]
    arqs.sort(key=lambda a: os.path.getmtime(a), reverse=True)
    mudou = False
    for a in arqs[:max_itens * 2]:
        mod = os.path.getmtime(a)
        if agora - mod > dias * 86400:
            break
        sid = os.path.basename(a)[:-6]
        titulo, pasta, ultimo = _cabeca(a)
        if not pasta or not os.path.isdir(pasta):
            continue
        if not titulo:
            titulo = re.sub(r"\s+", " ", ultimo).strip()[:60] or "Conversa sem título"
        if sid not in mapa["numeros"]:
            mapa["seq"] += 1
            mapa["numeros"][sid] = mapa["seq"]
            mudou = True
        achadas.append({"numero": mapa["numeros"][sid], "sessao": sid, "titulo": titulo[:90], "pasta": pasta,
                        "projeto": os.path.basename(pasta.rstrip("\\/")), "mod": int(mod)})
        if len(achadas) >= max_itens:
            break
    if mudou:
        try:
            _gravar(ARQ_CONVERSAS, mapa)
        except OSError:
            pass
    return achadas


def conversa(numero):
    try:
        numero = int(numero)
    except (TypeError, ValueError):
        return None
    return next((c for c in conversas(max_itens=60, dias=90) if c["numero"] == numero), None)


_PARA_CEREBRO = [0.0, ""]      # (quando, texto): o cérebro recebe isto a cada fala; a lista não muda de segundo em segundo


def conversas_para_o_cerebro(max_itens=8, validade_s=30):
    if time.time() - _PARA_CEREBRO[0] < validade_s:
        return _PARA_CEREBRO[1]
    _PARA_CEREBRO[1] = _conversas_para_o_cerebro(max_itens)
    _PARA_CEREBRO[0] = time.time()
    return _PARA_CEREBRO[1]


def _conversas_para_o_cerebro(max_itens=8):
    cs = conversas(max_itens=max_itens)
    if not cs:
        return ""
    return "conversas do Claude Code: " + "; ".join(f"C{c['numero']} \"{c['titulo'][:40]}\" ({c['projeto']})" for c in cs)
