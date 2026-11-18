"""Planilha de leads das prospecções do Jarvis: uma por nicho e cidade, guardada entre uma missão e outra.

Serve para a prospecção andar em etapas e nunca repetir empresa: quem já foi visto fica com a situação anotada.
Arquivo: E:\\.CODE & SAAS\\Jarvis\\dados\\leads\\<nicho>__<cidade>.csv (abre no Excel).

Uso:
  python leads.py ajuda
  python leads.py juntar "<nicho>" "<cidade>" <arquivo.json>
      Junta à planilha o resultado de `navegar.py maps` (salve a saída num .json antes). Empresa nova entra como "novo";
      empresa que já estava na planilha só ganha os dados que faltavam. Imprime quantas entraram.
  python leads.py lista "<nicho>" "<cidade>" [--situacao novo]
      Mostra a planilha (ou só uma situação), em JSON.
  python leads.py proximo "<nicho>" "<cidade>" [--n 1] [--situacao novo]
      As próximas empresas a trabalhar, da melhor nota para a pior (JSON). Vazio = não sobrou nenhuma.
  python leads.py marcar "<nicho>" "<cidade>" "<nome da empresa>" --situacao <situação> [--site URL] [--instagram URL]
                 [--telefone T] [--obs "uma linha"] [--missao N]
      Anota o que você descobriu. Situações: novo, sem_site, site_fraco, site_bom, site_feito, email_pronto, descartado.
  python leads.py copiar "<nicho>" "<cidade>" --saida entregas\\leads.csv
      Copia a planilha para a pasta de entregas da missão.
  python leads.py planilhas
      Lista as planilhas que existem, com a contagem por situação.
"""
import csv, datetime, json, os, re, shutil, sys, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(os.environ.get("JARVIS_LEADS") or os.path.join(os.path.dirname(AQUI), "dados", "leads"))
COLUNAS = ["nome", "situacao", "nota", "avaliacoes", "telefone", "site", "instagram", "endereco", "obs", "maps", "missao", "visto_em", "mudou_em"]
SITUACOES = ("novo", "sem_site", "site_fraco", "site_bom", "site_feito", "email_pronto", "descartado")
NAO_E_SITE = ("instagram.com", "facebook.com", "fb.com", "linktr.ee", "wa.me", "whatsapp.com", "api.whatsapp", "youtube.com", "tiktok.com", "ifood.com", "g.page")


def chave(txt):
    t = unicodedata.normalize("NFKD", str(txt or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def arquivo(nicho, cidade):
    os.makedirs(PASTA, exist_ok=True)
    return os.path.join(PASTA, f"{chave(nicho).replace(' ', '-')}__{chave(cidade).replace(' ', '-')}.csv")


def ler(arq):
    if not os.path.exists(arq):
        return []
    with open(arq, encoding="utf-8-sig", newline="") as f:
        return [{c: (l.get(c) or "") for c in COLUNAS} for l in csv.DictReader(f, delimiter=";")]


def gravar(arq, linhas):
    tmp = arq + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, COLUNAS, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)
    os.replace(tmp, arq)


def opcao(args, nome, padrao=None):
    if nome in args:
        i = args.index(nome)
        if i + 1 < len(args):
            return args[i + 1]
    return padrao


def hoje():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def nota_de(l):
    try:
        return float(str(l.get("nota") or 0).replace(",", "."))
    except ValueError:
        return 0.0


def juntar(nicho, cidade, origem):
    with open(origem, encoding="utf-8-sig") as f:
        bruto = f.read()
    i = bruto.find("{")           # a saída do navegar.py pode ter linhas de aviso antes do JSON
    j = bruto.find("[")
    ini = min(x for x in (i, j) if x >= 0) if max(i, j) >= 0 else 0
    dados = json.loads(bruto[ini:])
    itens = dados.get("resultados", []) if isinstance(dados, dict) else dados
    arq = arquivo(nicho, cidade)
    linhas = ler(arq)
    por_nome = {chave(l["nome"]): l for l in linhas}
    novos = 0
    for it in itens:
        nome = str(it.get("nome") or "").strip()
        if not nome:
            continue
        site = str(it.get("site") or "")
        insta = site if "instagram.com" in site else str(it.get("instagram") or "")
        if any(x in site for x in NAO_E_SITE):
            site = ""             # perfil de rede social, WhatsApp ou agregador não é site próprio
        l = por_nome.get(chave(nome))
        if l is None:
            l = {c: "" for c in COLUNAS}
            l.update(nome=nome, situacao="novo", visto_em=hoje())
            linhas.append(l)
            por_nome[chave(nome)] = l
            novos += 1
        for campo, valor in (("nota", it.get("nota")), ("avaliacoes", it.get("avaliacoes")), ("telefone", it.get("telefone")),
                             ("site", site), ("instagram", insta), ("endereco", it.get("endereco") or it.get("detalhes")), ("maps", it.get("maps"))):
            if valor not in (None, "") and not l.get(campo):
                l[campo] = str(valor).replace("\n", " ")[:300]
    gravar(arq, linhas)
    cont = {}
    for l in linhas:
        cont[l["situacao"] or "novo"] = cont.get(l["situacao"] or "novo", 0) + 1
    print(json.dumps({"planilha": arq, "entraram": novos, "ja_estavam": len(itens) - novos, "total": len(linhas), "por_situacao": cont}, ensure_ascii=False))


def lista(nicho, cidade, situacao=None):
    linhas = ler(arquivo(nicho, cidade))
    if situacao:
        linhas = [l for l in linhas if (l["situacao"] or "novo") == situacao]
    print(json.dumps({"planilha": arquivo(nicho, cidade), "total": len(linhas), "leads": linhas}, ensure_ascii=False, indent=1))


def proximo(nicho, cidade, n=1, situacao="novo"):
    linhas = [l for l in ler(arquivo(nicho, cidade)) if (l["situacao"] or "novo") == situacao]
    linhas.sort(key=lambda l: (-nota_de(l), -int(re.sub(r"\D", "", l.get("avaliacoes") or "") or 0)))
    print(json.dumps({"restam": len(linhas), "proximos": linhas[:n]}, ensure_ascii=False, indent=1))


def marcar(nicho, cidade, nome, args):
    arq = arquivo(nicho, cidade)
    linhas = ler(arq)
    alvo = chave(nome)
    l = next((x for x in linhas if chave(x["nome"]) == alvo), None) or next((x for x in linhas if alvo and alvo in chave(x["nome"])), None)
    if l is None:
        l = {c: "" for c in COLUNAS}
        l.update(nome=nome, situacao="novo", visto_em=hoje())
        linhas.append(l)
    sit = opcao(args, "--situacao")
    if sit:
        if sit not in SITUACOES:
            print(json.dumps({"erro": f"situação desconhecida: {sit}", "use": SITUACOES}, ensure_ascii=False))
            return
        l["situacao"] = sit
    for campo in ("site", "instagram", "telefone", "obs", "missao", "endereco"):
        v = opcao(args, "--" + campo)
        if v is not None:
            l[campo] = v.replace("\n", " ")[:300]
    l["mudou_em"] = hoje()
    gravar(arq, linhas)
    print(json.dumps({"ok": True, "lead": l}, ensure_ascii=False))


def copiar(nicho, cidade, saida):
    arq = arquivo(nicho, cidade)
    if not os.path.exists(arq):
        print(json.dumps({"erro": "essa planilha ainda não existe"}, ensure_ascii=False))
        return
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    shutil.copyfile(arq, saida)
    print(json.dumps({"ok": True, "copiada_para": os.path.abspath(saida), "total": len(ler(arq))}, ensure_ascii=False))


def planilhas():
    out = []
    if os.path.isdir(PASTA):
        for n in sorted(os.listdir(PASTA)):
            if n.endswith(".csv"):
                linhas = ler(os.path.join(PASTA, n))
                cont = {}
                for l in linhas:
                    cont[l["situacao"] or "novo"] = cont.get(l["situacao"] or "novo", 0) + 1
                nicho, _, cidade = n[:-4].partition("__")
                out.append({"nicho": nicho.replace("-", " "), "cidade": cidade.replace("-", " "), "total": len(linhas), "por_situacao": cont,
                            "arquivo": os.path.join(PASTA, n), "mod": int(os.path.getmtime(os.path.join(PASTA, n)))})
    return out


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    a = sys.argv[1:]
    try:
        if not a or a[0] in ("ajuda", "-h", "--help"):
            print(__doc__)
        elif a[0] == "juntar" and len(a) >= 4:
            juntar(a[1], a[2], a[3])
        elif a[0] == "lista" and len(a) >= 3:
            lista(a[1], a[2], opcao(a, "--situacao"))
        elif a[0] == "proximo" and len(a) >= 3:
            proximo(a[1], a[2], int(opcao(a, "--n", 1)), opcao(a, "--situacao", "novo"))
        elif a[0] == "marcar" and len(a) >= 4:
            marcar(a[1], a[2], a[3], a[4:])
        elif a[0] == "copiar" and len(a) >= 3 and opcao(a, "--saida"):
            copiar(a[1], a[2], opcao(a, "--saida"))
        elif a[0] == "planilhas":
            print(json.dumps(planilhas(), ensure_ascii=False, indent=1))
        else:
            print(__doc__)
    except Exception as e:
        print(json.dumps({"erro": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        sys.exit(1)
