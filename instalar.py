"""Instala o Jarvis neste computador (Windows).

    python instalar.py                       pergunta o seu nome e faz tudo
    python instalar.py --dono "Maria"        sem perguntas (bom para o Claude Code ou o Codex rodarem)
    python instalar.py --conferir            só confere o que falta, sem instalar nem mudar nada

Opções: --sem-pacotes (não roda o pip), --sem-atalho (não cria o atalho na área de trabalho).

O que ele faz: instala os pacotes do requirements.txt, cria o seu config.json a partir do config.exemplo.json,
grava o seu nome, confere Claude Code, Codex, navegador e microfone, e cria o atalho "Jarvis" na área de trabalho.
Pode rodar de novo quando quiser: não apaga nem sobrescreve o que é seu.
"""
import json, os, shutil, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[1:]
SO_CONFERIR = "--conferir" in ARGS
falta_grave = []


def opcao(nome):
    if nome in ARGS and ARGS.index(nome) + 1 < len(ARGS):
        return ARGS[ARGS.index(nome) + 1]
    return None


def diz(marca, txt):
    print(f"[{marca}] {txt}", flush=True)


def passo_python():
    if os.name != "nt":
        diz("ERRO", "O Jarvis só funciona no Windows (10 ou 11).")
        sys.exit(1)
    if sys.version_info < (3, 10):
        diz("ERRO", f"Python {sys.version.split()[0]} é antigo demais. Instale o Python 3.10 ou mais novo (python.org).")
        sys.exit(1)
    diz("OK", f"Python {sys.version.split()[0]}")


def passo_pacotes():
    if SO_CONFERIR or "--sem-pacotes" in ARGS:
        return
    diz("..", "Instalando os pacotes (pode levar alguns minutos na primeira vez)")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", os.path.join(AQUI, "requirements.txt")])
    if r.returncode != 0:
        diz("ERRO", "O pip não conseguiu instalar tudo. Leia o erro acima, corrija e rode de novo.")
        sys.exit(1)
    diz("OK", "Pacotes instalados")


def passo_modulos():
    faltam = []
    for mod, pacote in (("aiohttp", "aiohttp"), ("numpy", "numpy"), ("sounddevice", "sounddevice"), ("faster_whisper", "faster-whisper"),
                        ("openwakeword", "openwakeword"), ("edge_tts", "edge-tts"), ("pystray", "pystray"), ("PIL", "pillow"),
                        ("playwright", "playwright"), ("tkinter", "tkinter (vem com o Python de python.org)")):
        try:
            __import__(mod)
        except Exception:
            faltam.append(pacote)
    if faltam:
        diz("FALTA", "Pacotes: " + ", ".join(faltam))
        falta_grave.append("pacotes do Python")
    else:
        diz("OK", "Todos os pacotes do Python estão instalados")


def passo_config():
    meu = os.path.join(AQUI, "config.json")
    if not os.path.exists(meu):
        if SO_CONFERIR:
            diz("FALTA", "config.json ainda não existe (o instalador cria)")
            return
        shutil.copyfile(os.path.join(AQUI, "config.exemplo.json"), meu)
        diz("OK", "config.json criado a partir do exemplo")
    with open(meu, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    nome = opcao("--dono")
    if not nome and not str(cfg.get("dono") or "").strip() and not SO_CONFERIR and sys.stdin and sys.stdin.isatty():
        try:
            nome = input("Como o Jarvis deve chamar você? (seu primeiro nome) ").strip()
        except EOFError:
            nome = ""
    if nome and not SO_CONFERIR and nome != cfg.get("dono"):
        cfg["dono"] = nome
        with open(meu, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
    dono = str(cfg.get("dono") or "").strip()
    if dono:
        diz("OK", f"Nome de quem usa: {dono}")
    else:
        diz("AVISO", 'Sem nome gravado: o Jarvis vai usar o nome do usuário do Windows. Para trocar: python instalar.py --dono "Seu Nome"')


def passo_programas():
    if shutil.which("claude"):
        diz("OK", "Claude Code encontrado (o Jarvis pensa e trabalha por ele; se ainda não entrou na sua conta, rode `claude` uma vez)")
    else:
        diz("FALTA", "Claude Code não encontrado. Instale (https://claude.com/claude-code), entre na sua conta e rode o instalador de novo.")
        falta_grave.append("Claude Code")
    if shutil.which("codex"):
        diz("OK", 'Codex encontrado (missões de imagem e as que você pedir com "Codex, ...")')
    else:
        diz("AVISO", "Codex não encontrado: opcional. Sem ele, peça tudo ao Claude.")
    bases = [os.environ.get(v, "") for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    nav = [os.path.join(b, rel) for b in bases if b for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe")]
    if any(os.path.exists(n) for n in nav):
        diz("OK", "Edge ou Chrome encontrado (janela do painel e navegador das missões)")
    else:
        diz("FALTA", "Não achei o Edge nem o Chrome.")
        falta_grave.append("Edge ou Chrome")
    if shutil.which("ollama"):
        diz("OK", "Ollama encontrado (cérebro local de reserva)")
    else:
        diz("AVISO", "Ollama não encontrado: opcional. É o cérebro local de reserva, para quando a cota do Claude acaba.")
    if shutil.which("ffplay"):
        diz("OK", "ffmpeg encontrado")
    else:
        diz("AVISO", "ffmpeg não encontrado: opcional. Sem ele o Jarvis só fala com a janela do painel aberta, e o processo de corte de vídeo não roda.")
    try:
        import sounddevice as sd
        diz("OK", f"Microfone: {sd.query_devices(kind='input')['name']}")
    except Exception as e:
        diz("AVISO", f"Não consegui ver o microfone ({type(e).__name__}). Sem microfone dá para usar escrevendo no painel.")


def passo_atalho():
    if SO_CONFERIR or "--sem-atalho" in ARGS:
        return
    ps = ("$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Jarvis.lnk')); "
          "$s.TargetPath='wscript.exe'; $s.Arguments=[char]34 + $env:JARVIS_VBS + [char]34; $s.WorkingDirectory=$env:JARVIS_PASTA; "
          "$s.IconLocation=$env:JARVIS_ICO; $s.Save()")
    amb = dict(os.environ, JARVIS_VBS=os.path.join(AQUI, "Jarvis.vbs"), JARVIS_PASTA=AQUI, JARVIS_ICO=os.path.join(AQUI, "Jarvis.ico"))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=amb, capture_output=True, text=True)
    if r.returncode == 0:
        diz("OK", 'Atalho "Jarvis" criado na área de trabalho')
    else:
        diz("AVISO", "Não consegui criar o atalho. Para abrir, dê dois cliques em Jarvis.vbs.")


if __name__ == "__main__":
    if "-h" in ARGS or "--help" in ARGS:
        print(__doc__)
        sys.exit(0)
    passo_python()
    passo_pacotes()
    passo_modulos()
    passo_config()
    passo_programas()
    passo_atalho()
    print()
    if falta_grave:
        diz("FALTA", "Ainda falta: " + ", ".join(falta_grave) + ". Resolva e rode de novo.")
        sys.exit(2)
    if SO_CONFERIR:
        diz("PRONTO", "Nada grave faltando.")
    else:
        diz("PRONTO", 'Abra pelo atalho "Jarvis" da área de trabalho (ou Jarvis.vbs) e diga "Jarvis".')
        print("         Na primeira vez ele baixa o modelo de transcrição de voz: pode levar alguns minutos até começar a ouvir.")
