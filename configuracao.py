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
