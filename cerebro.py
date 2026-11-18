"""Cérebro do Jarvis: um Claude Code rápido, sem ferramentas, que fica aberto e responde em JSON."""
import asyncio, datetime, json, os, re, shutil

import configuracao

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.environ.get("JARVIS_TESTE") or AQUI
PASTA = os.path.join(RAIZ, "dados", "cerebro")
os.makedirs(PASTA, exist_ok=True)
CADERNO = os.path.join(RAIZ, "memoria", "caderno.md")
SOBRE_MIM = os.path.join(AQUI, "memoria", "sobre_mim.md")      # quem é o usuário, escrito por ele (fora do repositório)


def _ler(caminho, limite=4000):
    try:
        with open(caminho, encoding="utf-8") as f:
            t = f.read()
        return t[-limite:]
    except Exception:
        return ""


def anotar(texto):
    os.makedirs(os.path.dirname(CADERNO), exist_ok=True)
    with open(CADERNO, "a", encoding="utf-8") as f:
        f.write(f"- {datetime.date.today().isoformat()}: {texto.strip()}\n")


def extrair_json(txt):
    txt = txt.strip()
    txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.M).strip()
    i, j = txt.find("{"), txt.rfind("}")
    if i >= 0 and j > i:
        try:
            d = json.loads(txt[i:j + 1])
            if isinstance(d, dict):
                d.setdefault("fala", "")
                d.setdefault("acoes", [])
                if not isinstance(d["acoes"], list):
                    d["acoes"] = []
                return d
        except Exception:
            pass
    return {"fala": txt[:400], "acoes": []}


def fala_parcial(txt):
    """A fala, assim que a string dela fecha no JSON que ainda está chegando (None enquanto não fechou)."""
    m = re.search(r'"fala"\s*:\s*"((?:[^"\\]|\\.)*)"', txt)
    if not m:
        return None
    try:
        return json.loads('"' + m.group(1) + '"')
    except Exception:
        return None


class Cerebro:
    def __init__(self, cfg, log):
        self.cfg, self.log = cfg, log
        self.proc = None
        self.trava = asyncio.Lock()

    def _prompt(self):
        p = _ler(os.path.join(AQUI, "personalidade.md"), 40000)
        mem = _ler(CADERNO)
        try:        # os processos e os projetos são lidos das pastas: criar ou editar um não exige mexer na personalidade
            import processos, conversas
            for bloco in (processos.para_o_cerebro(), conversas.projetos_para_o_cerebro()):
                if bloco:
                    p += "\n\n" + bloco
        except Exception as e:
            self.log(f"processos fora do prompt: {e}")
        if not shutil.which("codex"):       # só o Claude Code instalado: tudo vai para ele
            p += ("\n\n# Neste computador\nO Codex não está instalado. Mande todas as missões para o claude, inclusive imagem. "
                  "Se ele pedir o Codex pelo nome, diga em poucas palavras que só o Claude está instalado e mande para o claude.")
        sobre = _ler(SOBRE_MIM, 3000).strip()
        if sobre:
            p += "\n\n# Sobre {dono}\n" + sobre
        # o nome de quem usa e o jeito de chamar vêm da configuração
        p = p.replace("{dono}", configuracao.dono(self.cfg)).replace("{tratamento}", str(self.cfg.get("tratamento") or "mestre"))
        if mem:
            p += "\n\n# Seu caderno de memória\n" + mem
        for extra in self.cfg.get("cadernos_extras", []):      # outros arquivos de anotações que ele quer que você conheça
            if isinstance(extra, dict):
                t = _ler(extra.get("arquivo", ""), 2500)
                if t:
                    p += f"\n\n# {extra.get('titulo') or 'Anotações'}\n" + t
        return p

    async def _abrir(self):
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError("Claude Code não encontrado no PATH")
        arq = os.path.join(PASTA, "prompt.md")
        with open(arq, "w", encoding="utf-8") as f:
            f.write(self._prompt())
        args = ["-p", "--model", self.cfg.get("cerebro_modelo", "haiku"),
                "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
                "--include-partial-messages",
                "--system-prompt-file", arq, "--tools", "", "--strict-mcp-config",
                "--disable-slash-commands"]
        if exe.lower().endswith((".cmd", ".bat")):
            args = ["/c", exe] + args
            exe = os.environ.get("COMSPEC", "cmd.exe")
        amb = dict(os.environ)
        amb.pop("ANTHROPIC_BASE_URL", None)
        self.proc = await asyncio.create_subprocess_exec(
            exe, *args, cwd=PASTA, env=amb, limit=8 * 1024 * 1024,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, creationflags=0x08000000)
        self.log("cérebro: aberto")

    async def aquecer(self):
        try:
            await self.pensar("[sistema] Você acabou de ser ligado. Responda só com a fala \"\" e nenhuma ação.")
        except Exception as e:
            self.log(f"cérebro não abriu: {e}")

    async def pensar(self, texto, tentativa=0, ao_falar=None):
        async with self.trava:
            try:
                if self.proc is None or self.proc.returncode is not None:
                    await self._abrir()
                msg = {"type": "user", "message": {"role": "user", "content": texto}}
                self.proc.stdin.write((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))
                await self.proc.stdin.drain()
                saida, parcial, avisou = "", "", False
                while True:
                    linha = await asyncio.wait_for(self.proc.stdout.readline(), timeout=60)
                    if not linha:
                        raise RuntimeError("o cérebro fechou")
                    try:
                        ev = json.loads(linha.decode("utf-8", "replace"))
                    except Exception:
                        continue
                    if ev.get("type") == "rate_limit_event":
                        import cotas
                        cotas.evento_claude(ev.get("rate_limit_info"))
                    elif ev.get("type") == "stream_event":
                        d = (ev.get("event") or {}).get("delta") or {}
                        if d.get("type") == "text_delta" and ao_falar and not avisou:
                            parcial += d.get("text", "")
                            f = fala_parcial(parcial)
                            if f is not None:
                                avisou = True
                                try:
                                    ao_falar(f)
                                except Exception as e:
                                    self.log(f"fala adiantada falhou: {e}")
                    elif ev.get("type") == "assistant":
                        for b in ev.get("message", {}).get("content", []):
                            if b.get("type") == "text":
                                saida += b.get("text", "")
                    elif ev.get("type") == "result":
                        if not saida:
                            saida = ev.get("result") or ""
                        if ev.get("is_error"):
                            raise RuntimeError(saida[:200] or "erro do modelo")
                        break
                return extrair_json(saida)
            except Exception as e:
                self.log(f"cérebro: {type(e).__name__}: {e}")
                await self._fechar()
                erro = e
        if tentativa == 0:
            return await self.pensar(texto, 1, ao_falar)
        return {"fala": "Perdi o fio. Pode repetir?", "acoes": [], "erro": str(erro)}

    async def _fechar(self):
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None

    async def reiniciar(self):
        async with self.trava:
            await self._fechar()


class CerebroLocal:
    """Reserva: um modelo no próprio PC, pelo Ollama (http://127.0.0.1:11434). Mesmo jeito de responder, sem gastar cota.
    A conversa fica guardada aqui (o Ollama não lembra sozinho). O modelo sai da placa de vídeo depois de alguns minutos parado."""

    def __init__(self, cfg, log, prompt):
        self.cfg, self.log, self._prompt = cfg, log, prompt
        self.hist = []
        self.trava = asyncio.Lock()

    def _opc(self):
        r = self.cfg.get("cerebro_reserva") or {}
        return r.get("modelo", "gemma4:e2b-it-qat"), r.get("url", "http://127.0.0.1:11434"), r.get("manter_na_placa", "10m")

    async def disponivel(self):
        import aiohttp
        modelo, url, _ = self._opc()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as s:
                async with s.get(url + "/api/tags") as r:
                    nomes = {m.get("name") for m in (await r.json()).get("models", [])}
            return modelo in nomes or (modelo + ":latest") in nomes
        except Exception:
            return False

    async def aquecer(self):
        """Carrega o modelo na placa (a primeira carga leva até ~1 min) sem gerar nada."""
        import aiohttp
        modelo, url, manter = self._opc()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=240)) as s:
                async with s.post(url + "/api/chat", json={"model": modelo, "messages": [], "keep_alive": manter, "options": {"num_ctx": 8192}}) as r:
                    await r.read()
            self.log("cérebro local: pronto na placa")
        except Exception as e:
            self.log(f"cérebro local: não aqueceu ({type(e).__name__})")

    DICAS = ("\n\nResponda só com o objeto JSON, curto. Lembretes: conta de cabeça, calcule com cuidado e diga o número certo; "
             "despedida ('valeu', 'por hoje é só', 'tchau') leva a ação {\"tipo\":\"dormir\"}; "
             "abrir site é {\"tipo\":\"rapida\",\"alvo\":...} mais {\"tipo\":\"janela\",\"modo\":\"mini\"}; "
             "não copie as frases de exemplo ao pé da letra.")

    async def pensar(self, texto, tentativa=0, ao_falar=None):
        import aiohttp
        modelo, url, manter = self._opc()
        async with self.trava:
            msgs = [{"role": "system", "content": self._prompt() + self.DICAS}] + self.hist[-16:] + [{"role": "user", "content": texto}]
            corpo = {"model": modelo, "messages": msgs, "stream": True, "format": "json", "keep_alive": manter,
                     "options": {"temperature": 0.4, "num_ctx": 8192}}
            saida, avisou = "", False
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=240, sock_read=180)) as s:
                    async with s.post(url + "/api/chat", json=corpo) as r:
                        if r.status != 200:
                            raise RuntimeError(f"Ollama HTTP {r.status}: {(await r.text())[:120]}")
                        async for linha in r.content:
                            try:
                                ev = json.loads(linha)
                            except Exception:
                                continue
                            saida += (ev.get("message") or {}).get("content", "")
                            if ao_falar and not avisou:
                                f = fala_parcial(saida)
                                if f is not None:
                                    avisou = True
                                    try:
                                        ao_falar(f)
                                    except Exception as e:
                                        self.log(f"fala adiantada falhou: {e}")
                            if ev.get("done"):
                                break
                d = extrair_json(saida)
                self.hist += [{"role": "user", "content": texto}, {"role": "assistant", "content": json.dumps(d, ensure_ascii=False)}]
                del self.hist[:-16]
                return d
            except Exception as e:
                self.log(f"cérebro local: {type(e).__name__}: {e}")
                return {"fala": "O orbe local não respondeu. Pode repetir?", "acoes": [], "erro": str(e)}

    async def reiniciar(self):
        self.hist = []


class Cerebros:
    """Escolhe quem pensa: o Claude (padrão) ou o cérebro local, quando a cota do Claude passa do limite,
    quando o Claude falha ou quando o usuário pede. Missões continuam no Claude e no Codex de qualquer jeito."""

    def __init__(self, cfg, log):
        self.cfg, self.log = cfg, log
        self.claude = Cerebro(cfg, log)
        self.local = CerebroLocal(cfg, log, self.claude._prompt)
        self.modo = (cfg.get("cerebro_reserva") or {}).get("modo", "auto")     # auto | local | claude
        self.em_uso = "claude"
        self.falhas = 0

    def _cota_alta(self):
        """Só troca de cérebro por cota com leitura AO VIVO (a que o próprio Claude Code informa nesta abertura).
        Os arquivos atrasam e não veem um reset: em 17/11/2026 o arquivo dizia 92% e o real era 8%, e o Jarvis
        passou para o cérebro local sem precisar. Sem leitura ao vivo, fica no Claude (a primeira resposta já traz a cota)."""
        limite = (self.cfg.get("cerebro_reserva") or {}).get("limite_cota", 97)
        try:
            import cotas
            c = cotas.claude(self.cfg)
            return any((j.get("usado") or 0) >= limite for j in c.get("janelas", []) if j.get("fonte") == cotas.AO_VIVO)
        except Exception:
            return False

    async def _quem(self):
        querer_local = self.modo == "local" or (self.modo == "auto" and (self._cota_alta() or self.falhas >= 2))
        if querer_local and await self.local.disponivel():
            return "local"
        return "claude"

    async def aquecer(self):
        if await self._quem() == "claude":
            await self.claude.aquecer()
        else:
            await self.local.aquecer()

    async def pensar(self, texto, ao_falar=None):
        quem = await self._quem()
        if quem != self.em_uso:
            self.log(f"cérebro: passou para o {'local' if quem == 'local' else 'Claude'}")
            self.em_uso = quem
        if quem == "local":
            return await self.local.pensar(texto, ao_falar=ao_falar)
        r = await self.claude.pensar(texto, ao_falar=ao_falar)
        if r.get("erro"):
            self.falhas += 1
            if self.modo == "auto" and await self.local.disponivel():      # o Claude falhou duas vezes: tenta o local já
                self.log("cérebro: Claude falhou, respondendo pelo local")
                self.em_uso = "local"
                return await self.local.pensar(texto, ao_falar=ao_falar)
        else:
            self.falhas = 0
        return r

    async def redigir(self, linha, falas_antes=()):
        """Com o cérebro local em uso, a missão é redigida pelo Claude (Haiku): o local conversa bem e redige mal.
        Devolve a lista de ações de missão, ou None se o Claude não respondeu (aí valem as do local)."""
        contexto = ""
        if falas_antes:
            contexto = "[sistema] Falas dele logo antes (contexto): " + " | ".join(f"\"{x}\"" for x in falas_antes) + "\n"
        pedido = (contexto + linha + "\n[sistema] Quem está conversando com ele agora é o cérebro local, que já respondeu em voz. "
                  "Sua parte é só redigir a missão: devolva \"fala\" vazia e as ações de missão (delegar, continuar ou processo) "
                  "com a instrução completa, fiel ao que ele pediu.")
        try:
            r = await self.claude.pensar(pedido)
        except Exception as e:
            self.log(f"redigir: {type(e).__name__}: {e}")
            return None
        if r.get("erro"):
            return None
        acoes = [a for a in r.get("acoes", []) if isinstance(a, dict) and a.get("tipo") in ("delegar", "continuar", "processo")]
        return acoes or None

    def mudar(self, modo):
        if modo in ("auto", "local", "claude"):
            self.modo = modo
            self.falhas = 0
            self.log(f"cérebro: modo {modo}")

    async def reiniciar(self):
        await self.claude.reiniciar()
        await self.local.reiniciar()
