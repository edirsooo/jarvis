"""Configuração do Jarvis.

- `config.exemplo.json` vem com o programa e traz todos os padrões.
- `config.json` é o seu (fica fora do repositório): o que estiver nele vale por cima do padrão.
  Na primeira vez ele é criado como cópia do exemplo; o `instalar.py` já grava nele o seu nome.
"""
import getpass, json, os, shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
EXEMPLO = os.path.join(AQUI, "config.exemplo.json")
MEU = os.path.join(AQUI, "config.json")


def _junta(base, extra):
    out = dict(base)
    for k, v in (extra or {}).items():
        out[k] = _junta(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def carregar():
    try:
        with open(EXEMPLO, encoding="utf-8") as f:
            padrao = json.load(f)
    except Exception:
        padrao = {"porta": 4747, "nome": "Jarvis"}
    if not os.path.exists(MEU):
        try:
            shutil.copyfile(EXEMPLO, MEU)
        except OSError:
            pass
    try:
        with open(MEU, encoding="utf-8-sig") as f:
            meu = json.load(f)
    except FileNotFoundError:
        meu = {}
    return _junta(padrao, meu)


def dono(cfg):
    """Nome de quem usa o Jarvis (config "dono"). Sem nome gravado, vale o usuário do Windows."""
    nome = str(cfg.get("dono") or "").strip()
    if nome:
        return nome
    try:
        return getpass.getuser().split(".")[0].capitalize() or "Usuário"
    except Exception:
        return "Usuário"


_ESPECIAIS = set(' \t&|<>^()"')


def _aspas(a):
    """Um argumento para a linha do cmd.exe: entre aspas sempre que tiver espaço ou símbolo que o cmd interpreta."""
    import subprocess
    q = subprocess.list2cmdline([a])
    if q.startswith('"') or '"' in a or not (set(a) & _ESPECIAIS):
        return q
    barras = len(a) - len(a.rstrip("\\"))      # barra no fim dobra, senão escaparia a aspa que fecha
    return '"' + a + "\\" * barras + '"'


async def abrir_programa(exe, args, **kw):
    """Abre o Claude Code ou o Codex. No Windows eles são .cmd, que só rodam pelo cmd.exe: a linha vai inteira entre
    aspas (cmd /c "...") e cada argumento com espaço, & ou parênteses vai entre aspas, para que um caminho como
    E:\\P&D\\loja não vire dois comandos."""
    import asyncio
    if exe.lower().endswith((".cmd", ".bat")):
        linha = " ".join(_aspas(x) for x in [exe] + list(args))
        return await asyncio.create_subprocess_shell(linha, **kw)
    return await asyncio.create_subprocess_exec(exe, *args, **kw)


async def encerrar(proc):
    """Encerra um processo e todos os filhos dele. Claude Code e Codex são .cmd: o proc é o cmd.exe, e um kill()
    simples deixa o node e o agente vivos (em 18/11/2026, 77 'codex app-server' órfãos somavam 29 GB)."""
    import asyncio
    if not proc or proc.returncode is not None:
        return
    try:
        if proc.stdin and not proc.stdin.is_closing():
            proc.stdin.close()
    except Exception:
        pass
    try:
        k = await asyncio.create_subprocess_exec(
            "taskkill", "/PID", str(proc.pid), "/T", "/F", creationflags=0x08000000,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(k.wait(), 10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
