"""Simula o Jarvis no macOS e no Linux a partir de qualquer computador: cada sistema roda num Python separado com
sys.platform trocado ANTES dos imports, e confere que os módulos carregam e que os ramos de cada sistema respondem
sem erro (nada de windll, startfile, creationflags ou taskkill fora do Windows). Não abre janela, não sobe servidor,
não fala com nenhum Jarvis aberto. Também roda o ramo do sistema de verdade.
Limite: é simulação. Permissões do macOS, bandeja, áudio e janelas reais só se conferem numa máquina de verdade."""
import json, os, subprocess, sys, tempfile, time

sys.stdout.reconfigure(encoding="utf-8")
J = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(tempfile.gettempdir(), "jarvis_testes", "plataformas_" + time.strftime("%H%M%S"))
os.makedirs(SAIDA, exist_ok=True)

FILHO = r'''
import asyncio, json, os, sys
alvo, J, MISSAO = sys.argv[1], sys.argv[2], sys.argv[3]
# bibliotecas de fora que olham o sistema ao carregar (numpy chama os.uname no "Linux"): carregam antes da troca
import numpy, aiohttp, aiohttp.web, PIL.Image
sys.platform = alvo                       # a partir daqui todo o Jarvis acha que está nesse sistema
sys.path[:0] = [J, os.path.join(J, "ferramentas")]
res = {}
def conf(nome, cond, extra=""):
    res[nome] = [bool(cond), str(extra)[:160]]

import plataforma
conf("plataforma: sistema", plataforma.sistema() == {"darwin": "mac", "linux": "linux", "win32": "windows"}[alvo], plataforma.sistema())
conf("plataforma: sem creationflags fora do Windows", (plataforma.sem_janela() == {}) == (alvo != "win32"), plataforma.sem_janela())
conf("plataforma: processo solto", ("start_new_session" in plataforma.solto()) == (alvo != "win32"), plataforma.solto())
conf("plataforma: .sh e .command são executáveis", plataforma.executavel("x.sh") and plataforma.executavel("Y.command") and plataforma.executavel("App.app"))
# os.access(X_OK) só se confere num sistema de verdade (no Windows todo arquivo existente conta como executável)
conf("plataforma: .txt não é executável", (os.name == "nt" and alvo != "win32") or not plataforma.executavel(os.path.join(J, "LICENSE")))
conf("plataforma: navegador() não quebra", True, plataforma.navegador())
conf("plataforma: pastas de dados", bool(plataforma.pasta_dados_locais()) and bool(plataforma.pasta_config_apps()), plataforma.pasta_dados_locais())
conf("plataforma: python sem terminal", bool(plataforma.python_sem_terminal()), plataforma.python_sem_terminal())
plataforma.garantir_path()
conf("plataforma: garantir_path não quebra", bool(os.environ.get("PATH")))
conf("plataforma: tocar_audio_cmd não quebra", plataforma.tocar_audio_cmd("teste.mp3") in (None,) or isinstance(plataforma.tocar_audio_cmd("teste.mp3"), list))

import configuracao
async def prog():
    p = await configuracao.abrir_programa(sys.executable, ["-c", "import time; time.sleep(30)"],
                                          stdout=asyncio.subprocess.DEVNULL, creationflags=0x08000000)
    await asyncio.sleep(0.3)
    await configuracao.encerrar(p)
    try:
        await asyncio.wait_for(p.wait(), 8)
    except Exception:
        pass
    return p.returncode
rc = asyncio.run(prog())
conf("configuracao: abre e encerra programa", rc is not None, rc)

import janelas
conf("janelas: importa", True)
conf("janelas: grande_na_frente", janelas.grande_na_frente() in (True, False))
conf("janelas: grande_visivel", janelas.grande_visivel() in (True, False))
conf("janelas: achar", janelas.achar("titulo que nao existe 123") is None)
janelas.abrir_site("https://exemplo.invalid", {})          # JARVIS_TESTE: só registra
janelas.abrir_mini(); janelas.esconder_grande(); janelas.mostrar_grande()
conf("janelas: mini/esconder/mostrar em teste", not janelas.mini_aberta())

import cotas, voz, processos, conversas, agentes, cerebro
conf("cotas/voz/processos/conversas/agentes/cerebro: importam", True)
txt = agentes.regras(os.path.join(os.sep, "tmp", "m1"), None, {})
# os.sep é o do computador real (a simulação não o troca): confere que as regras usam o separador do sistema e sys.executable
conf("agentes: caminhos das regras com o separador do sistema", ("entregas" + os.sep) in txt and (os.sep == "\\" or "\\entregas" not in txt))
conf("agentes: regras usam o Python atual", sys.executable in txt)
proc_pc = processos.montar("computador") or ""
conf("processos: computador usa sys.executable e sem 'três monitores'", sys.executable in proc_pc and "três monitores" not in proc_pc)
conf("cotas: claude() responde", isinstance(cotas.claude({}), dict))

import ouvido
conf("ouvido: _dll_cuda não quebra", ouvido._dll_cuda() in (True, False))

sys.argv[:] = ["mini.py", "4791"]
import mini
conf("mini: importa", True, (mini.MONO, mini.SANS, mini.CHAVE))

os.environ["JARVIS_MISSAO"] = MISSAO
import pc
conf("pc: importa sem windll", True)
if alvo != "win32":
    os.environ.pop("DISPLAY", None); os.environ["WAYLAND_DISPLAY"] = "wayland-0"
    import pc_posix
    m_puro = pc_posix.indisponivel()
    conf("pc: Wayland puro desliga com aviso", (m_puro is not None) if alvo.startswith("linux") else (m_puro is None), m_puro)
    os.environ["DISPLAY"] = ":0"
    m_xwayland = pc_posix.indisponivel()
    conf("pc: Wayland com XWayland (DISPLAY + WAYLAND_DISPLAY) também avisa", (m_xwayland is not None and plataforma.wayland()) if alvo.startswith("linux") else (m_xwayland is None), m_xwayland)
    os.environ.pop("WAYLAND_DISPLAY", None); os.environ["XDG_SESSION_TYPE"] = "x11"
    conf("pc: X11 puro libera controle", pc_posix.indisponivel() is None and not plataforma.wayland())
    conf("pc: janela_id sem xdotool/osascript = None", pc.janela_id() in (None, 0) or isinstance(pc.janela_id(), str))
    if alvo == "darwin":
        conf("pc_posix: titulo macOS lê pid|app|janela", pc_posix.titulo("123|Google Chrome|YouTube") == "YouTube - Google Chrome")
        conf("pc_posix: AppleScript sem try dentro de expressão", "end try" in pc_posix._OSA_JANELA and "(try " not in pc_posix._OSA_JANELA)
        # win+q vira command+q no macOS e deve ser bloqueado
        bloqueou = False
        try:
            pc_posix.tecla("win+q", ["win", "q"])
        except SystemExit:
            bloqueou = True
        conf("pc_posix: bloqueia win+q (command+q) no macOS", bloqueou)

# instalador: plist do macOS com '&' no caminho gera XML válido e inclui PATH
import xml.etree.ElementTree as ET
import instalar
velho_aqui = instalar.AQUI
instalar.AQUI = "/Users/ana/Code & SaaS/Jarvis"
try:
    pl = instalar._plist()
    ET.fromstring(pl)
    conf("instalar: _plist escapa '&' e inclui PATH", "&amp;" in pl and "EnvironmentVariables" in pl and "<key>PATH</key>" in pl)
finally:
    instalar.AQUI = velho_aqui

# lançadores Unix sem CRLF e com resolução de symlink
for arq in ("Jarvis.command", "jarvis.sh", os.path.join("testes", "falso", "claude")):
    raw = open(os.path.join(J, arq), "rb").read()
    conf(f"lançador {arq}: só LF (sem CRLF)", b"\r\n" not in raw)
conf("Jarvis.command resolve symlink (atalho da área de trabalho)", "readlink" in open(os.path.join(J, "Jarvis.command"), encoding="utf-8").read())

sys.argv[:] = ["jarvis.py", "--sem-ouvido"]
import jarvis
conf("jarvis: importa", True)
conf("jarvis: executáveis protegidos", ".command" in jarvis.EXECUTAVEIS and ".exe" in jarvis.EXECUTAVEIS)
print("RESULTADO " + json.dumps(res, ensure_ascii=False))
'''

ok_geral = True
for alvo in ("darwin", "linux", "win32"):
    pasta = os.path.join(SAIDA, alvo)
    os.makedirs(os.path.join(pasta, "dados"), exist_ok=True)
    amb = dict(os.environ, JARVIS_TESTE=pasta, JARVIS_PORTA="4791", PYTHONIOENCODING="utf-8", JARVIS_SESSOES=os.path.join(pasta, "sessoes"))
    amb.pop("DISPLAY", None)
    r = subprocess.run([sys.executable, "-c", FILHO, alvo, J, os.path.join(pasta, "missao")], env=amb, cwd=pasta,
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    linha = next((l for l in r.stdout.splitlines() if l.startswith("RESULTADO ")), None)
    print(f"\n===== {alvo} =====")
    if not linha:
        ok_geral = False
        print("FALHA o Python simulado parou antes do fim:\n" + (r.stderr or r.stdout)[-1500:])
        continue
    for nome, (bom, extra) in json.loads(linha[10:]).items():
        ok_geral = ok_geral and bom
        print(("OK   " if bom else "FALHA"), nome, ("· " + extra) if extra and extra != "True" else "")

print("\nTUDO CERTO" if ok_geral else "\nTEM FALHA")
sys.exit(0 if ok_geral else 1)
