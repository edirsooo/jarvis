"""Cotas das assinaturas, lidas do próprio computador (arquivos que o Claude Code, o aplicativo do Claude e o Codex já gravam). Nada é enviado para fora."""
import asyncio, datetime, glob, json, os, shutil, time


def _janela(nome, usado, renova=None, fonte=""):
    return {"nome": nome, "usado": None if usado is None else round(float(usado)),
            "renova": renova, "fonte": fonte}


# ---------- Claude ----------
def _claude_statusline():
    """Arquivo que a linha de status do Claude Code grava, quando há um monitor de cotas instalado."""
    arq = os.path.join(os.environ.get("LOCALAPPDATA", ""), "AIUsageMonitor", "claude-limits.json")
    try:
        with open(arq, encoding="utf-8-sig") as f:
            d = json.load(f)
        quando = datetime.datetime.fromisoformat(d["captured_at"][:26].rstrip("Z") + "+00:00" if "+" not in d["captured_at"] else d["captured_at"][:19] + "+00:00").timestamp()
        lim = d.get("rate_limits") or {}
        out = {}
        for chave, k in (("five_hour", "5h"), ("seven_day", "semana")):
            w = lim.get(chave)
            if isinstance(w, dict) and w.get("used_percentage") is not None:
                out[k] = (w["used_percentage"], w.get("resets_at"))
        return quando, out
    except Exception:
        return 0, {}


def _claude_app():
    """Histórico de uso do aplicativo do Claude: amostras a cada 15 min (fh = 5 horas, sd = semana)."""
    base = os.environ.get("LOCALAPPDATA", "")
    arqs = glob.glob(os.path.join(base, "Claude-Data", "*", "plan-usage-history.json"))
    arqs.append(os.path.join(os.environ.get("APPDATA", ""), "Claude", "plan-usage-history.json"))
    arqs = [a for a in arqs if os.path.exists(a)]
    if not arqs:
        return 0, {}
    try:
        with open(max(arqs, key=os.path.getmtime), encoding="utf-8") as f:
            amostras = json.load(f).get("samples", [])
        if not amostras:
            return 0, {}
        ult = amostras[-1]
        u = ult.get("u", {})
        out = {}
        if u.get("fh") is not None:
            out["5h"] = (u["fh"], None)
        if u.get("sd") is not None:
            out["semana"] = (u["sd"], None)
        return ult["t"] / 1000, out
    except Exception:
        return 0, {}


_AO_VIVO = {"quando": 0, "dados": {}}
AO_VIVO = "Claude Code, na hora"      # fonte das janelas informadas pelo próprio Claude Code nesta abertura do Jarvis


def evento_claude(info):
    """Cota que o próprio Claude Code informa a cada resposta (cérebro e missões): é a leitura mais fresca que existe."""
    try:
        nomes = {"five_hour": "5h", "seven_day": "semana"}
        achou = False
        for chave, w in ((info or {}).get("unifiedWindows") or {}).items():
            if chave in nomes and isinstance(w, dict) and w.get("utilization") is not None:
                _AO_VIVO["dados"][nomes[chave]] = (float(w["utilization"]) * 100, w.get("resetsAt"))
                achou = True
        if achou:
            _AO_VIVO["quando"] = time.time()
    except Exception:
        pass


def _proxima_semanal(cfg):
    """Renovação semanal informada pelo usuário (padrão: sexta às 05h)."""
    dia, hora = cfg.get("claude_renova_dia", 4), cfg.get("claude_renova_hora", 5)   # 0 = segunda
    agora = datetime.datetime.now()
    alvo = agora.replace(hour=hora, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(dia - agora.weekday()) % 7)
    if alvo <= agora:
        alvo += datetime.timedelta(days=7)
    return alvo.timestamp()


def claude(cfg):
    t1, a = _claude_statusline()
    t2, b = _claude_app()
    quando, dados, fonte = (t1, a, "linha de status do Claude Code") if t1 >= t2 and a else (t2, b, "aplicativo do Claude")
    fontes = {k: fonte for k in dados}
    if _AO_VIVO["quando"] > quando:
        # O que o Claude Code acabou de informar vale mais que os arquivos, que atrasam e não veem um reset
        # (em 17/11/2026 o arquivo do aplicativo dizia 92% da semana horas depois de um reset; ao vivo eram 8%).
        # Cada janela guarda a própria fonte: a que só existe no arquivo continua aparecendo, marcada como arquivo.
        dados = {**dados, **_AO_VIVO["dados"]}
        fontes.update({k: AO_VIVO for k in _AO_VIVO["dados"]})
        quando = _AO_VIVO["quando"]
    if not dados:
        return {"nome": "Claude", "erro": "sem leitura", "janelas": [], "lido": None}
    janelas = []
    agora = time.time()
    if "5h" in dados:
        usado, renova = dados["5h"]
        if renova and renova < agora:
            usado, renova = 0, None      # a janela de 5 horas já virou
        janelas.append(_janela("5 horas", usado, renova, fontes["5h"]))
    if "semana" in dados:
        usado, renova = dados["semana"]
        estimada = not renova
        renova = renova or _proxima_semanal(cfg)
        j = _janela("Semana", usado, renova, fontes["semana"])
        j["renova_estimada"] = estimada
        janelas.append(j)
    return {"nome": "Claude", "janelas": janelas, "lido": quando}


# ---------- Codex ----------
async def codex():
    exe = shutil.which("codex")
    if not exe:
        return {"nome": "Codex", "erro": "Codex não encontrado", "janelas": [], "lido": None}
    args = ["app-server", "--stdio"]
    if exe.lower().endswith((".cmd", ".bat")):
        args = ["/c", exe] + args
        exe = os.environ.get("COMSPEC", "cmd.exe")
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            exe, *args, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, creationflags=0x08000000, limit=8 * 1024 * 1024)

        async def manda(o):
            proc.stdin.write((json.dumps(o) + "\n").encode())
            await proc.stdin.drain()

        async def resposta(n):
            while True:
                l = await asyncio.wait_for(proc.stdout.readline(), timeout=20)
                if not l:
                    raise IOError("o Codex fechou")
                try:
                    m = json.loads(l)
                except Exception:
                    continue
                if isinstance(m, dict) and m.get("id") == n:
                    if "error" in m:
                        raise RuntimeError(str(m["error"])[:120])
                    return m.get("result", {})

        await manda({"method": "initialize", "id": 1, "params": {"clientInfo": {"name": "jarvis", "title": "Jarvis", "version": "1.0"}}})
        await resposta(1)
        await manda({"method": "initialized"})
        await manda({"method": "account/rateLimits/read", "id": 2})
        r = await resposta(2)
        baldes = r.get("rateLimitsByLimitId") or {}
        b = baldes.get("codex") or (next(iter(baldes.values())) if baldes else None) or r.get("rateLimits") or {}
        janelas = []
        for chave in ("primary", "secondary"):
            w = b.get(chave)
            if not isinstance(w, dict):
                continue
            usado = w.get("usedPercent", w.get("used_percent"))
            mins = w.get("windowDurationMins", w.get("window_minutes")) or 0
            renova = w.get("resetsAt", w.get("resets_at"))
            if isinstance(renova, str):
                try:
                    renova = datetime.datetime.fromisoformat(renova.replace("Z", "+00:00")).timestamp()
                except Exception:
                    renova = None
            nome = "5 horas" if 0 < mins <= 400 else "Semana" if mins >= 9000 else f"{round(mins / 60)} h" if mins else chave
            janelas.append(_janela(nome, usado, renova, "codex app-server"))
        plano = r.get("planType") or b.get("planType")
        return {"nome": "Codex", "janelas": janelas, "lido": time.time(), "plano": plano,
                "erro": None if janelas else "sem janela de cota"}
    except Exception as e:
        return {"nome": "Codex", "erro": f"não consegui ler ({type(e).__name__})", "janelas": [], "lido": None}
    finally:
        if proc and proc.returncode is None:
            try:
                proc.kill()
            except Exception:
                pass


async def ler(cfg):
    return [claude(cfg), await codex()]


def frase(cotas):
    """Uma linha para o cérebro saber das cotas."""
    partes = []
    for c in cotas or []:
        js = ", ".join(f"{j['nome'].lower()} {j['usado']}% usado" for j in c.get("janelas", []) if j.get("usado") is not None)
        partes.append(f"{c['nome']}: {js or c.get('erro') or 'sem leitura'}")
    return " | ".join(partes)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(ler({})), ensure_ascii=False, indent=1))
