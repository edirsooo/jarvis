"""Processos: roteiros prontos para tarefas que se repetem (pasta modelos\\, um .md por processo).

Cada arquivo tem um cabeçalho entre linhas `---` e, abaixo, o roteiro que o agente segue:

    ---
    nome: Prospecção
    quando: achar negócios bem avaliados com site fraco e preparar a abordagem
    gatilhos: prospecção, prospectar, achar clientes
    agente: claude
    nivel: pesado
    tempo_max_min: 30
    parametros: nicho (tipo de negócio); cidade; nota_minima = 4,5 (nota mínima no Google)
    entregas: relatorio.md, leads.csv, site.html, email.md
    ---
    Roteiro... pode usar {nicho}, {cidade} e os outros parâmetros.

O cérebro lê esta pasta sozinho (não precisa mexer no personalidade.md); a aba PROCESSOS da tela lista, edita, duplica e cria.

Os que vêm com o programa ficam em modelos\\. Os seus (criados ou editados na tela ou por voz) ficam em modelos\\meus\\,
que não vai para o repositório: um processo seu com o mesmo nome de um que veio pronto vale por cima dele.
No roteiro, {dono} vira o nome de quem usa e {pasta_jarvis} a pasta onde o Jarvis está instalado.
"""
import os, re, sys, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "modelos")
# em teste, o que for criado vai para a pasta do teste, não para a de verdade
MEUS = os.path.join(os.environ["JARVIS_TESTE"], "modelos_meus") if os.environ.get("JARVIS_TESTE") else os.path.join(PASTA, "meus")
DONO = "Usuário"      # o jarvis.py põe aqui o nome da configuração
CAMPOS = ("nome", "quando", "gatilhos", "agente", "nivel", "tempo_max_min", "parametros", "entregas")


def slug(txt):
    t = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")[:40]


def _parametros(linha):
    """'nicho (tipo de negócio); cidade; nota_minima = 4,5 (nota mínima)' -> lista de {nome, padrao, descricao}."""
    out = []
    for pedaco in re.split(r"\s*;\s*", linha or ""):
        pedaco = pedaco.strip()
        if not pedaco:
            continue
        m = re.match(r"([\wÀ-ÿ]+)\s*(?:=\s*([^()]+?))?\s*(?:\((.*)\))?\s*$", pedaco)
        if m:
            out.append({"nome": slug(m.group(1)), "padrao": (m.group(2) or "").strip(), "descricao": (m.group(3) or "").strip()})
    return out


def _abrir(arq):
    with open(arq, encoding="utf-8") as f:
        txt = f.read().replace("\r\n", "\n")
    cab, corpo = {}, txt
    m = re.match(r"\s*---\n(.*?)\n---\n?(.*)", txt, re.S)
    if m:
        corpo = m.group(2)
        for linha in m.group(1).split("\n"):
            if ":" in linha:
                k, v = linha.split(":", 1)
                cab[slug(k)] = v.strip()
    return cab, corpo.strip()


def ler(ident):
    ident = slug(ident)
    arq = _arquivo(ident)
    if not ident or not arq:
        return None
    cab, corpo = _abrir(arq)
    quando = cab.get("quando", "")
    if not quando:      # roteiro antigo, sem cabeçalho: a primeira linha ("Objetivo: ...") serve de descrição
        quando = re.sub(r"^objetivo:\s*", "", corpo.split("\n", 1)[0], flags=re.I)[:200]
    try:
        tempo = int(float(str(cab.get("tempo_max_min", "")).replace(",", ".") or 0))
    except ValueError:
        tempo = 0
    return {"id": ident, "nome": cab.get("nome") or ident.replace("_", " ").capitalize(), "quando": quando,
            "gatilhos": cab.get("gatilhos", ""), "agente": (cab.get("agente") or "").lower(), "nivel": (cab.get("nivel") or "").lower(),
            "tempo_max_min": tempo, "parametros": _parametros(cab.get("parametros", "")), "parametros_txt": cab.get("parametros", ""),
            "entregas": cab.get("entregas", ""), "corpo": corpo, "mod": int(os.path.getmtime(arq)),
            "meu": os.path.dirname(arq) == MEUS}


def _arquivo(ident):
    """O arquivo do processo: o seu (modelos\\meus) vale antes do que veio com o programa."""
    for pasta in (MEUS, PASTA):
        arq = os.path.join(pasta, ident + ".md")
        if ident and os.path.isfile(arq):
            return arq
    return None


def todos():
    out = []
    nomes = set()
    for pasta in (PASTA, MEUS):
        try:
            nomes.update(n for n in os.listdir(pasta) if n.endswith(".md"))
        except OSError:
            pass
    nomes = sorted(nomes)
    for n in nomes:
        p = ler(n[:-3])
        if p:
            out.append(p)
    return out


def salvar(ident, campos, corpo):
    """Cria ou regrava um processo. Devolve (processo, erro)."""
    ident = slug(ident or campos.get("nome", ""))
    if not ident:
        return None, "o processo precisa de um nome"
    if not str(corpo or "").strip():
        return None, "o roteiro está vazio"
    os.makedirs(MEUS, exist_ok=True)
    linhas = ["---"]
    for k in CAMPOS:
        v = re.sub(r"\s+", " ", str(campos.get(k, "") or "")).strip()
        if v:
            linhas.append(f"{k}: {v}")
    linhas += ["---", str(corpo).replace("\r\n", "\n").strip(), ""]
    arq = os.path.join(MEUS, ident + ".md")
    tmp = arq + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(linhas))
    os.replace(tmp, arq)
    return ler(ident), None


def valores(p, dados):
    """Parâmetros do processo com o que veio no pedido; o que faltou fica com o padrão do cabeçalho."""
    dados = {slug(k): str(v).strip() for k, v in (dados or {}).items() if str(v).strip()}
    out = {}
    for par in p["parametros"]:
        v = dados.pop(par["nome"], "") or par["padrao"]
        if v:
            out[par["nome"]] = v
    out.update(dados)       # parâmetro que o roteiro não previu também segue junto
    return out


def montar(ident, dados=None):
    """O roteiro pronto para a missão, com os parâmetros no lugar. None se o processo não existe."""
    p = ler(ident)
    if not p:
        return None
    vals = valores(p, dados)
    py = sys.executable or ("python" if os.name == "nt" else "python3")
    corpo = p["corpo"].replace("{dono}", DONO).replace("{pasta_jarvis}", AQUI).replace("{python}", py)
    for k, v in vals.items():
        corpo = corpo.replace("{" + k + "}", v)
    cab = f"# Processo: {p['nome']}\n"
    if vals:
        cab += "Parâmetros desta vez: " + "; ".join(f"{k} = {v}" for k, v in vals.items()) + "\n"
    falta = [par["nome"] for par in p["parametros"] if par["nome"] not in vals]
    if falta:
        cab += "Não informado (decida pelo mais sensato a partir do pedido): " + ", ".join(falta) + "\n"
    if p["entregas"]:
        cab += f"Entregas esperadas em entregas{os.sep}: {p['entregas']}\n"
    return cab + "\n" + corpo


def para_o_cerebro():
    """Trecho do prompt do cérebro com os processos que existem agora."""
    ps = todos()
    if not ps:
        return ""
    linhas = ["# Processos prontos",
              "Roteiros salvos para tarefas que se repetem. Quando o pedido bater com um deles, use a ação \"processo\" "
              "(o roteiro inteiro vai junto sozinho; você só informa os parâmetros que ele disse):"]
    for p in ps:
        l = f"- \"{p['id']}\" ({p['nome']}): {p['quando']}"
        if p["gatilhos"]:
            l += f" Ele costuma dizer: {p['gatilhos']}."
        if p["parametros"]:
            l += " Parâmetros: " + ", ".join(par["nome"] + (f" (padrão {par['padrao']})" if par["padrao"] else "") for par in p["parametros"]) + "."
        if p["agente"] or p["nivel"]:
            l += f" Padrão: {p['agente'] or 'claude'}, nível {p['nivel'] or 'medio'}."
        linhas.append(l)
    return "\n".join(linhas)
