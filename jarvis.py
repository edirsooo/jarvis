"""Jarvis: servidor local que junta ouvido, cérebro, voz, agentes e a tela."""
import asyncio, datetime, json, os, subprocess, sys, time, webbrowser
from aiohttp import web, WSMsgType

AQUI = os.path.dirname(os.path.abspath(__file__))
os.chdir(AQUI)
sys.path.insert(0, AQUI)

import configuracao
import cerebro as cerebro_mod
import janelas
import cotas as cotas_mod
import processos
import conversas as conversas_mod
from agentes import Agentes
from cerebro import Cerebros
from voz import Voz, partes as partes_da_fala, PASTA as PASTA_VOZ

RAIZ = os.environ.get("JARVIS_TESTE") or AQUI      # em teste, dados e missões vão para outra pasta e nenhuma janela é aberta
DADOS = os.path.join(RAIZ, "dados")
os.makedirs(DADOS, exist_ok=True)
ARQ_LOG = os.path.join(DADOS, "jarvis.log")
ARQ_XP = os.path.join(DADOS, "xp.json")
ARQ_VISUAL = os.path.join(DADOS, "visual.json")
ARQ_AGENDA = os.path.join(DADOS, "agenda.json")
ARQ_AJUSTES = os.path.join(DADOS, "ajustes.json")


def _ler_json(arq, padrao):
    try:
        with open(arq, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao


def _gravar_json(arq, dado):
    try:
        with open(arq + ".tmp", "w", encoding="utf-8") as f:
            json.dump(dado, f, ensure_ascii=False, indent=1)
        os.replace(arq + ".tmp", arq)
    except Exception as e:
        log(f"não gravei {os.path.basename(arq)}: {e}")


AJUSTES = _ler_json(ARQ_AJUSTES, {})
VISUAL = {"roupa": "torre", "tema": "cristal", "tam": 1, "v": 0}      # roupa do mago, tema da tela e poses desenhadas
try:
    with open(ARQ_VISUAL, encoding="utf-8") as f:
        VISUAL.update(json.load(f))
except Exception:
    pass

CFG = configuracao.carregar()        # padrões do config.exemplo.json + o seu config.json por cima
DONO = configuracao.dono(CFG)        # nome de quem usa o Jarvis
processos.DONO = DONO
if os.environ.get("JARVIS_PORTA"):
    CFG["porta"] = int(os.environ["JARVIS_PORTA"])
if os.environ.get("JARVIS_CEREBRO"):
    CFG.setdefault("cerebro_reserva", {})["modo"] = os.environ["JARVIS_CEREBRO"]
SEM_OUVIDO = "--sem-ouvido" in sys.argv


def log(txt):
    linha = f"{datetime.datetime.now():%H:%M:%S} {txt}"
    try:
        print(linha, flush=True)
    except Exception:
        pass
    try:
        with open(ARQ_LOG, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


SAUDACOES = CFG.get("saudacoes") or ["Diga.", "O orbe escuta.", "Estou aqui.", "Às ordens, mestre."]
_SO_NOME = {"jarvis", "ô", "o", "ei", "oi", "e", "aí", "ai", "fala", "hey", "go", "ok", "opa", "alô", "alo",
            "beijo", "beijos", "temos"}   # "Ei, Jarvis" o Whisper às vezes ouve como "Beijo, Jarvis"
_PERGUNTA_RE = __import__("re").compile(
    r"\?\s*$|^\W*(jarvis\W+)?(o que|qual|quais|quanto|quantos|quantas|como|por ?que|quando|onde|quem|explica|me conta|"
    r"me fala|fala mais|detalha|resume|você acha|tem como|dá pra|da pra|consegue)\b", __import__("re").I)


def enxugar(fala, pedido, origem):
    """Freio no tamanho da fala, independente do cérebro: uma frase, mais a do próximo passo se for pergunta.
    Pergunta dele ('qual...?', 'como...', 'explica') libera até três frases."""
    import re
    fala = re.sub(r"\s+", " ", (fala or "")).strip()
    if not fala:
        return ""
    frases = re.findall(r"[^.!?…]+(?:[.!?…]+|$)", fala)
    frases = [f.strip() for f in frases if f.strip()]
    if origem == "dono" and _PERGUNTA_RE.search(pedido.strip()):
        return " ".join(frases[:3])
    out = frases[:1]
    perguntas = [f for f in frases[1:] if f.endswith("?")]
    if perguntas:
        out.append(perguntas[-1])  # o próximo passo: "O site ficou pronto. Ajusto o topo ou escrevo o e-mail?"
    return " ".join(out)


NAO_E_CONTIGO = __import__("re").compile(
    r"n[aã]o (é|e|era|foi|t[oô]|estou|tava|estava)\b.{0,24}\b(contigo|com voc[eê]|pra ti|para ti|pra voc[eê]|para voc[eê])\b|"
    r"\b(t[oô]|estou|tava|estava) falando com (?:(?:a|o|minha|meu) ){0,2}(" + "|".join(
        ["esposa", "esposo", "marido", "amor", "outra pessoa", "ele", "ela"]
        + [__import__("re").escape(str(n).lower()) for n in CFG.get("pessoas_por_perto", []) if str(n).strip()]) + r")\b", __import__("re").I)


def juntar_falas(pedacos):
    """'Busca academias em Valinhos.' + 'Que você faça um relatório.' -> uma frase só, na ordem em que foi dita."""
    out = ""
    for p in pedacos:
        p = p.strip()
        if not p:
            continue
        if out and out.rstrip().endswith(("...", "…", ",")):
            out = out.rstrip(" .…") + " " + p[0].lower() + p[1:]
        else:
            out = (out + " " + p).strip()
    return out


def so_chamou(texto):
    """True quando ele só disse o nome ("Jarvis", "Ô Jarvis", "Ei, Jarvis?")."""
    import re
    palavras = re.sub(r"[^\wÀ-ÿ ]", " ", texto.lower()).split()
    return 0 < len(palavras) <= 3 and "jarvis" in palavras and all(p in _SO_NOME for p in palavras)


class Jarvis:
    def __init__(self):
        self.laco = None
        self.clientes = set()
        self.principal = None
        self.estado = "dormindo"     # dormindo | ouvindo | pensando | falando
        self.mudo = False
        self.acordado_ate = 0.0
        self.falando_ate = 0.0
        self.fila_fala = 0
        self.painel = None            # {"missao": n, "entrega": rel}
        self.conversa = []
        self.nivel_mic = 0.0
        self.legenda = ""
        self.cotas = []
        self.xp = self._ler_xp()
        self.cerebro = Cerebros(CFG, log)
        self.voz = Voz(CFG, log)
        self.agentes = Agentes(CFG, log, self._missoes_mudaram, self._missao_terminou, self._marco, self._passou_do_tempo)
        self.so_nome = bool(AJUSTES.get("so_pelo_nome", CFG.get("so_pelo_nome", False)))   # só responde a frase com "Jarvis"
        self.agenda = _ler_json(ARQ_AGENDA, [])
        self._ult_marco = 0.0
        self.ouvido = None
        self._pendente_missoes = False
        self.vez = asyncio.Lock()
        self._espera = []             # falas ouvidas que ainda não viraram pedido
        self._despachando = False

    # ---------- utilidades ----------
    def _ler_xp(self):
        try:
            with open(ARQ_XP, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"xp": 0, "missoes": 0}

    def _salvar_xp(self):
        with open(ARQ_XP, "w", encoding="utf-8") as f:
            json.dump(self.xp, f)

    def acordado(self):
        return time.time() < self.acordado_ate or self.estado in ("pensando", "falando")

    def manter_acordado(self, s=None, forcar=False):
        """Janela de conversa aberta (ele fala sem repetir o nome). No modo 'só pelo nome' ela não existe, a não ser por clique."""
        if self.so_nome and not forcar:
            self.acordado_ate = min(self.acordado_ate, time.time())
            return
        self.acordado_ate = time.time() + (s or CFG.get("conversa_aberta_s", 12))

    def enviar(self, **msg):
        if not self.clientes:
            return
        dado = json.dumps(msg, ensure_ascii=False)
        for ws in list(self.clientes):
            asyncio.ensure_future(self._mandar(ws, dado))

    async def _mandar(self, ws, dado):
        try:
            await ws.send_str(dado)
        except Exception:
            self.clientes.discard(ws)

    def do_fio(self, fn, *a):
        """Chamado pelos fios do ouvido."""
        if self.laco:
            self.laco.call_soon_threadsafe(fn, *a)

    def mudar_estado(self, novo):
        if self.ouvido:
            self.ouvido.jarvis_falando = novo == "falando"
        if novo != self.estado:
            self.estado = novo
            self.enviar(t="estado", v=novo, mudo=self.mudo)

    def retrato(self):
        return {"t": "tudo", "estado": self.estado, "mudo": self.mudo, "painel": self.painel,
                "missoes": [m.publico() for m in self.agentes.missoes.values()],
                "conversa": self.conversa[-30:], "xp": self.xp, "cotas": self.cotas, "nome": CFG.get("nome", "Jarvis"), "dono": DONO,
                "info": {"mic": getattr(self.ouvido, "dispositivo", "desligado") if self.ouvido else "desligado",
                         "stt": self.ouvido.stt.onde if self.ouvido else "-", "voz": self.voz.motor_em_uso,
                         "cerebro": "local" if self.cerebro.em_uso == "local" else "Claude",
                         "cerebro_modo": self.cerebro.modo, "escuta": "nome" if self.so_nome else "aberta"},
                "agenda": self.agenda}

    # ---------- eventos do ouvido ----------
    def _nivel(self, v):
        self.nivel_mic = min(1.0, v * 9)
        self.enviar(t="nivel", v=round(min(1.0, v * 9), 3))

    def _acordou(self, motivo):
        if self.mudo:
            return
        log(f"acordei por {motivo}")
        self.manter_acordado(forcar=motivo in ("clique", "palmas"))
        if motivo == "palmas":
            try:   # acende a tela se ela estiver apagada (um toque mínimo no mouse)
                import ctypes
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                ctypes.windll.user32.mouse_event(0x0001, 0, -1, 0, 0)
                ctypes.windll.kernel32.SetThreadExecutionState(0x00000002)
            except Exception:
                pass
            self.enviar(t="frente")
        if self.estado == "dormindo":
            self.mudar_estado("ouvindo")
            self.enviar(t="som", v="acordar")
            if motivo == "palmas":
                asyncio.ensure_future(self.falar("Estou aqui."))

    def _comecou_fala(self):
        if self.estado == "falando":
            self.enviar(t="calar")
            self.fila_fala = 0
            self.mudar_estado("ouvindo")
        # a janela não é mais esticada aqui: a fala que começou com ele acordado vale inteira (ouvido.py),
        # e conversa de outra pessoa na sala deixa de manter o Jarvis acordado sem parar

    def _ouviu(self, texto, tem_nome):
        if self.mudo:
            return
        if NAO_E_CONTIGO.search(texto):      # "não é contigo", "tô falando com a minha esposa": dorme na hora, sem responder
            log("não era comigo: dormindo")
            self._espera.clear()
            self.acordado_ate = 0
            if self.estado == "falando":
                self.enviar(t="calar")
                self.fila_fala = 0
            if self.estado in ("ouvindo", "falando"):
                self.mudar_estado("dormindo")
            return
        self.manter_acordado()
        self._espera.append(texto)
        if not self._despachando:
            self._despachando = True
            asyncio.ensure_future(self._despachar())

    async def _assentar(self, max_s=6.0):
        """Espera ele terminar de falar (fala sendo gravada ou virando texto). Com o Jarvis falando, o microfone não conta."""
        o, t0 = self.ouvido, time.time()
        while o and o.ocupado() and self.estado != "falando" and time.time() - t0 < max_s:
            await asyncio.sleep(0.1)

    async def _despachar(self):
        """Pedido dito em pedaços vira um pedido só: junta o que chegou enquanto ele ainda falava ou enquanto o cérebro pensava."""
        try:
            refeito = False
            while self._espera:
                await self._assentar()
                pedacos, self._espera = self._espera, []
                texto = juntar_falas(pedacos)
                if len(pedacos) > 1:
                    log(f"juntei {len(pedacos)} pedaços: {texto}")
                feito = await self.pedido(texto, falado=True, refeito=refeito)
                refeito = feito is False
                if refeito:                  # ele continuou falando antes de qualquer ação: refaz com a frase inteira
                    self._espera.insert(0, texto)
        except Exception as e:
            log(f"despacho falhou: {type(e).__name__}: {e}")
        finally:
            self._despachando = False

    # ---------- conversa ----------
    def _linha_estado(self):
        ms = list(self.agentes.missoes.values())[-8:]
        linhas = "; ".join(m.linha_estado() for m in ms) or "nenhuma missão"
        p = "nenhum"
        if self.painel:
            p = f"missão #{self.painel['missao']} ({self.painel.get('entrega') or 'atividade'})"
        extra = ""
        try:
            pl = self._planilhas()[:4]
            if pl:
                extra += " | planilhas de leads: " + "; ".join(
                    f"{x['nicho']} em {x['cidade']} ({x['total']} empresas, {x['por_situacao'].get('novo', 0)} na fila)" for x in pl)
            cs = conversas_mod.conversas_para_o_cerebro()
            if cs:
                extra += " | " + cs
            if self.agenda:
                extra += " | agendados: " + "; ".join(f"[{x['id']}] {x['processo']} às {x['hora']} ({x['dias']})" for x in self.agenda)
            if self.so_nome:
                extra += " | escuta: só pelo nome"
        except Exception as e:
            log(f"estado: {e}")
        return (f"[estado] hora {datetime.datetime.now():%H:%M} | missões: {linhas} | painel aberto: {p}"
                f" | cotas das assinaturas: {cotas_mod.frase(self.cotas) or 'sem leitura'}{extra}")

    def _planilhas(self):
        """Planilhas de leads das prospecções (ferramentas\\leads.py), da mais recente para a mais antiga."""
        import importlib.util
        if not hasattr(self, "_leads_mod"):
            spec = importlib.util.spec_from_file_location("leads", os.path.join(AQUI, "ferramentas", "leads.py"))
            self._leads_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self._leads_mod)
        return sorted(self._leads_mod.planilhas(), key=lambda x: -x["mod"])

    def _registrar(self, quem, txt):
        if quem == "jarvis":
            log(f"falei ({self.cerebro.em_uso}): {txt}")
        self.conversa.append({"quem": quem, "txt": txt, "t": time.time()})
        del self.conversa[:-60]
        self.enviar(t="linha", quem=quem, txt=txt)

    def _falas_recentes(self, fora="", n=2, janela_s=240):
        """As últimas falas dele (para o agente ler o contexto original), sem a atual."""
        agora, out = time.time(), []
        for c in reversed(self.conversa):
            if c["quem"] == "voce" and c["txt"] != fora and agora - c["t"] < janela_s:
                out.append(c["txt"])
                if len(out) >= n:
                    break
        return list(reversed(out))

    async def pedido(self, texto, origem="dono", falado=False, refeito=False):
        """Devolve False quando o pedido falado foi abandonado porque ele continuou falando (quem chamou junta e refaz)."""
        texto = texto.strip()
        if not texto:
            return
        baixo = texto.lower()
        anteriores = self._falas_recentes(texto) if origem == "dono" else []
        if origem == "dono":
            self._registrar("voce", texto)
            if any(x in baixo for x in ("para tudo", "pare tudo", "cancela tudo")):
                n = await self.agentes.parar("todas")
                self.enviar(t="calar")
                await self.falar("Tudo parado." if n else "Não havia nada rodando.")
                return
            if so_chamou(texto):
                # só o nome: resposta pronta, na hora, sem passar pelo cérebro
                fala = SAUDACOES[int(time.time()) % len(SAUDACOES)]
                self._registrar("jarvis", fala)
                self.manter_acordado(40)
                await self.falar(fala)
                return
        async with self.vez:
            self.mudar_estado("pensando")
            dita = []           # a fala sai assim que o cérebro termina de escrevê-la, antes das ações

            def falando_ele():      # ele está no meio de outra fala: não falo por cima nem ajo ainda
                return falado and self.ouvido is not None and self.ouvido.ocupado() and self.estado != "falando"

            def cedo(f):
                f = enxugar(f, texto, origem)
                if f and not dita and not falando_ele() and not self._espera:
                    self._registrar("jarvis", f)
                    dita.append(asyncio.ensure_future(self.falar(f)))

            linha = f"{self._linha_estado()}\n"
            if refeito:
                linha += ("[sistema] A fala anterior dele foi cortada no meio. A resposta que você deu a ela foi descartada "
                          "e nada foi executado. O pedido completo é o de baixo: responda só a ele.\n")
            linha += f"[{origem}] {texto}"
            r = await self.cerebro.pensar(linha, ao_falar=cedo)
            if self.cotas:      # a resposta do cérebro traz a cota do Claude atualizada
                try:
                    nova = cotas_mod.claude(CFG)
                    if nova != self.cotas[0]:
                        self.cotas[0] = nova
                        self.enviar(t="cotas", v=self.cotas)
                except Exception:
                    pass
            if falado:
                await self._assentar()
                if self._espera:        # chegou mais fala antes de qualquer ação: este pedido estava pela metade
                    if dita:
                        self.enviar(t="calar")
                        self._fala_acabou(forcar=True)
                    log("pedido refeito: ele continuou falando")
                    return False
            acoes = [a for a in r.get("acoes", []) if isinstance(a, dict)]
            # o cérebro local conversa bem, mas redige missão mal: quando o pedido vira missão, quem escreve é o Claude
            if (self.cerebro.em_uso == "local" and (CFG.get("cerebro_reserva") or {}).get("missao_pelo_claude", True)
                    and any(a.get("tipo") in ("delegar", "continuar", "processo") for a in acoes)):
                novo = await self.cerebro.redigir(linha, self._falas_recentes(texto, n=4))
                if novo is not None:
                    log(f"missão redigida pelo Claude ({len(novo)} ação(ões))")
                    acoes = [a for a in acoes if a.get("tipo") not in ("delegar", "continuar", "processo")] + novo
            if conversas_mod.chave(r.get("fala", "")) in ("dormir", "escuta", "abrir", "fechar", "parar", "janela", "anotar", "processo", "delegar", "continuar"):
                r["fala"] = ""
            cedo(r.get("fala"))
            extras = []
            for a in acoes:
                try:
                    if origem == "dono" and a.get("tipo") in ("delegar", "continuar", "processo"):
                        a["_literal"], a["_anteriores"] = texto, anteriores
                    extra = await self.acao(a)
                    if extra:
                        extras.append(extra)
                except Exception as e:
                    log(f"ação falhou {a}: {e}")
            if dita:
                await dita[0]
            if extras:
                fala = " ".join(extras)
                self._registrar("jarvis", fala)
                await self.falar(fala)
            elif not dita:
                self.mudar_estado("ouvindo" if time.time() < self.acordado_ate else "dormindo")
            if any(a.get("tipo") == "dormir" for a in acoes):
                self.acordado_ate = 0
                if not dita and not extras:
                    self.mudar_estado("dormindo")

    @staticmethod
    def _com_literal(instrucao, a):
        """Junta à missão o que ele disse de verdade: o agente lê o original, não só o resumo do cérebro."""
        lit = str(a.get("_literal") or "").strip()
        if not lit:
            return instrucao
        txt = (f"{instrucao}\n\n---\nPedido literal de {DONO} (transcrição de voz, pode ter palavra errada). "
               f"Se o texto acima e este divergirem em nome, cidade, número ou no que é para fazer, vale este:\n\"{lit}\"")
        ant = [x for x in (a.get("_anteriores") or []) if x]
        if ant:
            txt += "\nFalas dele logo antes (contexto): " + " | ".join(f"\"{x}\"" for x in ant)
        return txt

    def achar_missao(self, assunto):
        """A missão que melhor bate com o assunto falado ('o site das academias'). A mais nova ganha no empate."""
        palavras = [p for p in conversas_mod.chave(assunto).split() if len(p) > 2 and p not in
                    ("das", "dos", "para", "que", "com", "uma", "missao", "site", "imagem", "video", "email", "relatorio", "abre", "abrir", "mostra")]
        melhor, pontos = None, 0
        for m in self.agentes.missoes.values():
            alvo = conversas_mod.chave(m.titulo + " " + m.instrucao[:300] + " " + m.projeto)
            p = sum(1 for w in palavras if w in alvo) + (0.5 if any(w in conversas_mod.chave(m.titulo) for w in palavras) else 0)
            if p > 0 and p >= pontos:
                melhor, pontos = m, p
        return melhor

    async def rodar_processo(self, ident, parametros=None, pedido="", titulo="", agente=None, nivel=None, projeto=None, a=None):
        """Abre uma missão a partir de um processo salvo (modelos\\). Devolve (missão, erro)."""
        p = processos.ler(ident)
        if not p:
            return None, f"não achei o processo {ident}"
        vals = processos.valores(p, parametros)
        if p["id"] == "prospeccao" and vals.get("etapa", "tudo") == "tudo":
            lit = conversas_mod.chave((a or {}).get("_literal", "") + " " + pedido)
            if any(w in lit.split() for w in ("proxima", "proximo", "continua", "continuar", "segue", "seguinte")):
                try:
                    pl = self._planilhas()
                    alvo = (conversas_mod.chave(vals.get("nicho", "")), conversas_mod.chave(vals.get("cidade", "")))
                    achou = next((x for x in pl if conversas_mod.chave(x["nicho"]) == alvo[0] and conversas_mod.chave(x["cidade"]) == alvo[1]), None)                         or (pl[0] if not vals.get("nicho") and pl else None)
                    if achou and achou["total"]:
                        vals["etapa"] = "proxima"
                        vals.setdefault("nicho", achou["nicho"]); vals.setdefault("cidade", achou["cidade"])
                except Exception as e:
                    log(f"próxima: {e}")
        proj = conversas_mod.projeto(projeto or vals.get("projeto", "")) if (projeto or vals.get("projeto")) else None
        if (projeto or vals.get("projeto")) and not proj:
            return None, f"não conheço o projeto {projeto or vals.get('projeto')}"
        if not titulo:
            titulo = p["nome"] + (": " + ", ".join(str(v) for k, v in list(vals.items())[:2] if k not in ("nota_minima", "quantos_alvos", "etapa")) if vals else "")
        instr = (pedido or "").strip() or f"Rodar o processo {p['nome']}."
        if a is not None:
            instr = self._com_literal(instr, a)
        m, erro = await self.agentes.criar(agente or p["agente"] or "claude", titulo[:60], instr, p["id"],
                                           nivel or p["nivel"] or "medio", params=vals,
                                           projeto={"nome": proj["nome"], "pasta": proj["pasta"]} if proj else None)
        if m:
            self.enviar(t="som", v="missao")
            if p["id"] == "computador":
                self.janela("mini")
        return m, erro

    async def acao(self, a):
        tipo = a.get("tipo")
        if tipo == "delegar":
            if a.get("modelo") and processos.ler(a["modelo"]):      # modelo antigo = processo de hoje
                m, erro = await self.rodar_processo(a["modelo"], a.get("parametros"), a.get("missao", ""), a.get("titulo", ""),
                                                    a.get("agente"), a.get("nivel"), a.get("projeto"), a)
                return f"Não consegui abrir a missão: {erro}." if erro else None
            proj = conversas_mod.projeto(a.get("projeto")) if a.get("projeto") else None
            if a.get("projeto") and not proj:
                return f"Não conheço o projeto {a.get('projeto')}."
            m, erro = await self.agentes.criar(a.get("agente", "claude"), a.get("titulo", "Missão"),
                                               self._com_literal(a.get("missao", ""), a), a.get("modelo"), a.get("nivel", "medio"),
                                               projeto={"nome": proj["nome"], "pasta": proj["pasta"]} if proj else None)
            if erro:
                return f"Não consegui abrir a missão: {erro}."
            self.enviar(t="som", v="missao")
        elif tipo == "processo":
            m, erro = await self.rodar_processo(a.get("id") or a.get("processo") or a.get("modelo"), a.get("parametros"),
                                                a.get("pedido") or a.get("missao", ""), a.get("titulo", ""),
                                                a.get("agente"), a.get("nivel"), a.get("projeto"), a)
            if erro:
                return f"Não consegui abrir a missão: {erro}."
        elif tipo == "continuar":
            agora = str(a.get("quando", "agora")).lower() != "depois"
            m, erro = await self.agentes.continuar(a.get("missao", 0), self._com_literal(a.get("instrucao", ""), a), agora=agora)
            if erro:
                return f"Não deu para continuar: {erro}."
            if str(m.modelo or "").lower() == "computador":
                self.janela("mini")
        elif tipo == "conversa":
            # conversa do Claude Code deste computador, pelo número fixo dela: continua numa cópia, como missão do Jarvis
            c = conversas_mod.conversa(a.get("numero"))
            if not c:
                return f"Não achei a conversa {a.get('numero')}."
            ja = next((m for m in reversed(list(self.agentes.missoes.values())) if m.conversa == c["numero"] and m.sessao), None)
            instr = self._com_literal(a.get("instrucao", "") or "Continue o trabalho de onde parou.", a)
            if ja:      # já foi trazida antes: segue na mesma cópia, para o contexto acumular
                m, erro = await self.agentes.continuar(ja.n, instr)
            else:
                m, erro = await self.agentes.criar_de_conversa(c["numero"], c["sessao"], c["pasta"], a.get("titulo") or c["titulo"][:60],
                                                               instr, a.get("nivel", "medio"))
            if erro:
                return f"Não deu para continuar a conversa {c['numero']}: {erro}."
            self.enviar(t="som", v="missao")
        elif tipo == "abrir":
            n = a.get("missao")
            if not n and a.get("assunto"):
                m = self.achar_missao(a["assunto"])
                if not m:
                    return "Não achei entrega com esse assunto."
                n = m.n
            self.abrir_painel(n, a.get("entrega"))
        elif tipo == "escuta":
            self.so_nome = str(a.get("modo", "aberta")).lower() in ("nome", "so_nome", "só pelo nome", "reuniao", "reunião")
            AJUSTES["so_pelo_nome"] = self.so_nome
            _gravar_json(ARQ_AJUSTES, AJUSTES)
            log(f"escuta: {'só pelo nome' if self.so_nome else 'conversa aberta'}")
            self.enviar(**self.retrato())
        elif tipo == "agendar":
            p = processos.ler(a.get("processo") or a.get("id"))
            hora = str(a.get("hora", "")).strip()
            if not p or not __import__("re").fullmatch(r"\d{1,2}:\d{2}", hora):
                return "Para agendar preciso do processo e da hora."
            item = {"id": max([x.get("id", 0) for x in self.agenda] + [0]) + 1, "hora": hora.zfill(5), "dias": str(a.get("dias", "todos")).lower(),
                    "processo": p["id"], "parametros": a.get("parametros") or {}, "pedido": a.get("pedido", ""), "ultima": ""}
            self.agenda.append(item)
            _gravar_json(ARQ_AGENDA, self.agenda)
            log(f"agendado: {p['id']} às {item['hora']} ({item['dias']})")
            self.enviar(t="agenda", v=self.agenda)
        elif tipo == "desagendar":
            alvo = str(a.get("id") or a.get("processo") or "")
            antes = len(self.agenda)
            self.agenda = [x for x in self.agenda if str(x.get("id")) != alvo and x.get("processo") != processos.slug(alvo)]
            _gravar_json(ARQ_AGENDA, self.agenda)
            self.enviar(t="agenda", v=self.agenda)
            if len(self.agenda) == antes:
                return "Não achei esse agendamento."
        elif tipo == "salvar_processo":
            # "salva isso como processo": a última missão (ou a indicada) vira roteiro reaproveitável
            ms = list(self.agentes.missoes.values())
            m = self.agentes.missoes.get(int(a["missao"])) if str(a.get("missao", "")).isdigit() else (ms[-1] if ms else None)
            corpo = str(a.get("roteiro") or (m.instrucao.split("\n\n---\nPedido literal")[0] if m else "")).strip()
            nome = str(a.get("nome") or (m.titulo if m else "")).strip()
            p, erro = processos.salvar(nome, {"nome": nome, "quando": a.get("quando") or nome, "gatilhos": a.get("gatilhos", ""),
                                              "agente": a.get("agente") or (m.agente if m else "claude"),
                                              "nivel": a.get("nivel") or (m.nivel if m else "medio"),
                                              "parametros": a.get("parametros_txt", "")}, corpo)
            if erro:
                return f"Não salvei o processo: {erro}."
            await self.processos_mudaram()
        elif tipo == "fechar":
            self.painel = None
            self.enviar(t="painel", v=None)
        elif tipo == "parar":
            alvo = a.get("missao", "todas")
            await self.agentes.parar(alvo if alvo == "todas" else int(alvo))
        elif tipo == "janela":
            self.janela(a.get("modo", "mini"), a.get("canto"))
        elif tipo == "anotar":
            cerebro_mod.anotar(a.get("texto", ""))
        elif tipo == "cerebro":
            self.cerebro.mudar(str(a.get("modo", "auto")).lower())
            if self.cerebro.modo == "local" and not await self.cerebro.local.disponivel():
                return "O cérebro local ainda não está instalado."
        elif tipo == "rapida":
            alvo = str(a.get("alvo", "")).strip()
            j = a.get("janela")          # o cérebro local às vezes põe a janela dentro da ação
            if j:
                self.janela(j.get("modo", "mini") if isinstance(j, dict) else str(j), None)
            if alvo.startswith(("http://", "https://")):
                janelas.abrir_site(alvo, CFG)
            elif os.path.exists(alvo):
                os.startfile(alvo)
            else:
                m = self.achar_missao(alvo)      # "site das academias": é uma entrega, não um caminho
                if not m:
                    return "Não achei isso no computador."
                tipo_pedido = next((t for t in ("site", "imagem", "video", "email", "relatorio") if t in conversas_mod.chave(alvo)), None)
                self.abrir_painel(m.n, tipo_pedido)
        return None

    def janela(self, modo, canto=None):
        """mini = só a esfera flutuando por cima; grande = painel inteiro."""
        cantos = {"esquerda": "esq-baixo", "direita": "dir-baixo", "cima": "dir-cima", "baixo": "dir-baixo",
                  "esquerda-cima": "esq-cima", "direita-cima": "dir-cima", "esquerda-baixo": "esq-baixo",
                  "direita-baixo": "dir-baixo", "livre": "livre"}
        c = cantos.get(str(canto or "").lower().replace(" ", "-").replace("_", "-"))
        if modo == "grande":
            janelas.fechar_mini()
            janelas.mostrar_grande()
        elif modo == "canto" and c:
            janelas.canto(c)
            janelas.abrir_mini()
        else:
            janelas.abrir_mini(c if c and c != "livre" else None)
            janelas.esconder_grande()

    def abrir_painel(self, n, entrega=None):
        try:
            m = self.agentes.missoes.get(int(n))
        except Exception:
            m = None
        if not m:
            ms = list(self.agentes.missoes.values())
            m = ms[-1] if ms else None
        if not m:
            return
        self.agentes.varrer(m)
        rel = None
        alvo = str(entrega or "").lower().strip()
        if alvo.startswith("@"):
            rel = alvo
        elif alvo in ("antes_depois", "antes e depois"):
            rel = "@antes_depois"
        elif alvo in ("atividade", "log"):
            rel = "@atividade"
        elif alvo:
            apelidos = {"email": "texto", "e-mail": "texto", "site": "site", "imagem": "imagem",
                        "video": "video", "vídeo": "video", "reels": "video", "corte": "video"}
            for e in reversed(m.entregas):
                if alvo in e["nome"].lower():
                    rel = e["rel"]
                    break
            if not rel and alvo in apelidos:
                for e in reversed(m.entregas):
                    if e["tipo"] == apelidos[alvo]:
                        rel = e["rel"]
                        break
        if not rel:
            rel = self.melhor_entrega(m)
        self.painel = {"missao": m.n, "entrega": rel}
        self.enviar(t="painel", v=self.painel)
        janelas.fechar_mini()
        janelas.mostrar_grande()

    def melhor_entrega(self, m):
        """O que vale mais a pena mostrar primeiro: vídeo, antes e depois, site, imagem, o resto."""
        nomes = {e["nome"].lower().rsplit(".", 1)[0] for e in m.entregas}
        for tipo in ("video",):
            for e in reversed(m.entregas):
                if e["tipo"] == tipo:
                    return e["rel"]
        if {"antes", "depois"} <= nomes:
            return "@antes_depois"
        for tipo in ("site", "imagem", "pdf", "audio", "texto"):
            for e in reversed(m.entregas):
                if e["tipo"] == tipo:
                    return e["rel"]
        return m.entregas[-1]["rel"] if m.entregas else "@atividade"

    # ---------- voz ----------
    async def falar(self, texto):
        self.mudar_estado("falando")
        self.legenda = texto
        pedacos = partes_da_fala(texto)
        self.enviar(t="legenda", txt=texto)
        mandou = False
        for p in pedacos:
            nome = await self.voz.gerar(p)
            if not nome:
                continue
            if self.clientes:
                # com mais de uma tela aberta, só uma toca a voz: a última em que ele mexeu
                alvo = self.principal if self.principal in self.clientes else next(iter(self.clientes))
                self.fila_fala += 1
                asyncio.ensure_future(self._mandar(alvo, json.dumps({"t": "fala", "url": f"/voz/{nome}", "txt": p}, ensure_ascii=False)))
                mandou = True
            else:
                await self._tocar_sem_tela(os.path.join(PASTA_VOZ, nome))
        self.falando_ate = time.time() + 3 + len(texto) * 0.09
        if not mandou:
            self._fala_acabou(forcar=True)
        else:
            asyncio.ensure_future(self._vigia_fala())

    async def _vigia_fala(self):
        while self.estado == "falando" and time.time() < self.falando_ate:
            await asyncio.sleep(0.4)
        if self.estado == "falando":
            self._fala_acabou(forcar=True)

    def _fala_acabou(self, forcar=False):
        self.fila_fala = 0 if forcar else max(0, self.fila_fala - 1)
        if self.fila_fala == 0 and self.estado == "falando":
            self.manter_acordado()
            self.mudar_estado("ouvindo")
            asyncio.ensure_future(self._adormecer())

    async def _adormecer(self):
        while time.time() < self.acordado_ate:
            await asyncio.sleep(1)
        if self.estado == "ouvindo":
            self.mudar_estado("dormindo")

    async def _tocar_sem_tela(self, caminho):
        if janelas.TESTE:       # em teste, nada toca nas caixas de som dele
            return
        try:
            p = await asyncio.create_subprocess_exec(
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", caminho, creationflags=0x08000000)
            await p.wait()
        except Exception:
            pass

    # ---------- missões ----------
    def _missoes_mudaram(self):
        if self._pendente_missoes:
            return
        self._pendente_missoes = True

        def mandar():
            self._pendente_missoes = False
            self.enviar(t="missoes", v=[m.publico() for m in self.agentes.missoes.values()])
        self.laco.call_later(0.25, mandar)

    def _missao_terminou(self, m):
        if m.estado == "concluida":
            self.xp["xp"] += 50 + 10 * len(m.entregas)
            self.xp["missoes"] += 1
            self._salvar_xp()
            self.enviar(t="xp", v=self.xp)
            self.enviar(t="som", v="pronto")
            no_pc = any(str(x.modelo or "").lower() == "computador" for x in self.agentes.ativas())
            if m.entregas and CFG.get("abrir_ao_terminar", True) and not no_pc:   # não toma a tela se um agente está usando o computador
                self.abrir_painel(m.n)      # terminou: já aparece grande na tela (vídeo começa a tocar)
        else:
            self.enviar(t="som", v="erro")
        tipos = ", ".join(sorted({e["tipo"] for e in m.entregas})) or "nenhuma"
        aviso = (f"A missão #{m.n} \"{m.titulo}\" terminou com estado {m.estado}. "
                 f"Resumo do aprendiz (para você entender; não leia em voz alta): {m.resumo[:500]} "
                 f"| Entregas na tela: {tipos}")
        self.manter_acordado()
        asyncio.ensure_future(self.pedido(aviso, origem="sistema"))

    def _marco(self, m, txt):
        """Marco que o agente avisou no meio da missão: aparece na tela e é dito em voz assim que o Jarvis estiver livre."""
        self.enviar(t="marco", missao=m.n, txt=txt)
        log(f"marco #{m.n}: {txt}")
        fala = enxugar(txt, "", "sistema")

        async def diz():
            t0 = time.time()        # não fala por cima dele nem de si mesmo: espera uma brecha (até 25 s; depois disso o marco fica só na tela)
            while time.time() - t0 < 25:
                livre = (self.estado in ("dormindo", "ouvindo") and not self._espera and not self.vez.locked()
                         and not (self.ouvido and self.ouvido.ocupado()))
                if livre and time.time() - self._ult_marco >= CFG.get("marcos_intervalo_s", 20):
                    self._ult_marco = time.time()
                    self._registrar("jarvis", fala)
                    await self.falar(fala)
                    return
                await asyncio.sleep(0.5)
        if not self.mudo and fala:
            asyncio.ensure_future(diz())

    def _passou_do_tempo(self, m):
        minutos = int(m.tempo_max / 60)
        log(f"missão #{m.n} passou de {minutos} min")
        aviso = (f"A missão #{m.n} \"{m.titulo}\" passou do tempo previsto ({minutos} minutos) e continua trabalhando "
                 f"(etapa: {m.etapa[:80]}). Avise em poucas palavras e pergunte se ele quer que siga ou pare.")
        asyncio.ensure_future(self.pedido(aviso, origem="sistema"))

    async def processos_mudaram(self):
        """Processo criado ou editado: o cérebro do Claude reabre com a lista nova (o local lê a cada resposta)."""
        try:
            await self.cerebro.claude.reiniciar()
        except Exception:
            pass
        self.enviar(t="processos", v=self._processos_publico())

    def _processos_publico(self):
        return [{k: p[k] for k in ("id", "nome", "quando", "gatilhos", "agente", "nivel", "tempo_max_min", "parametros", "parametros_txt", "entregas", "corpo", "mod")}
                for p in processos.todos()]

    async def laco_agenda(self):
        """Processos agendados (por voz ou pela tela): roda uma vez por dia no horário, se o Jarvis estiver aberto."""
        dias_uteis = {0, 1, 2, 3, 4}
        while True:
            await asyncio.sleep(30)
            try:
                agora = datetime.datetime.now()
                hoje = agora.strftime("%Y-%m-%d")
                for item in self.agenda:
                    if item.get("ultima") == hoje:
                        continue
                    h, mi = (int(x) for x in item["hora"].split(":"))
                    alvo = agora.replace(hour=h, minute=mi, second=0, microsecond=0)
                    if not (0 <= (agora - alvo).total_seconds() < 2 * 3600):
                        continue
                    if item.get("dias") in ("uteis", "úteis", "dias uteis", "seg-sex") and agora.weekday() not in dias_uteis:
                        continue
                    item["ultima"] = hoje
                    _gravar_json(ARQ_AGENDA, self.agenda)
                    log(f"agenda: rodando {item['processo']}")
                    m, erro = await self.rodar_processo(item["processo"], item.get("parametros"), item.get("pedido") or "Rodada agendada.")
                    if erro:
                        log(f"agenda: {erro}")
            except Exception as e:
                log(f"agenda: {type(e).__name__}: {e}")

    # ---------- web ----------
    async def api_processos(self, req):
        """Lista, cria, edita e roda processos (aba PROCESSOS)."""
        if req.method == "POST":
            d = await req.json()
            if d.get("rodar"):
                m, erro = await self.rodar_processo(d["rodar"], d.get("parametros"), d.get("pedido", ""), d.get("titulo", ""), projeto=d.get("projeto"))
                return web.json_response({"ok": not erro, "erro": erro, "missao": m.n if m else None})
            p, erro = processos.salvar(d.get("id") or d.get("nome"), d, d.get("corpo", ""))
            if erro:
                return web.json_response({"ok": False, "erro": erro})
            await self.processos_mudaram()
            return web.json_response({"ok": True, "id": p["id"]})
        return web.json_response({"processos": self._processos_publico(), "agenda": self.agenda,
                                  "projetos": [{"nome": p["nome"], "pasta": p["pasta"], "existe": p["existe"]} for p in conversas_mod.projetos()]})

    async def api_conversas(self, req):
        """Conversas do Claude Code deste computador (só número, título, projeto e data) e projetos cadastrados."""
        if req.method == "POST":
            d = await req.json()
            if d.get("projeto"):
                p, erro = conversas_mod.salvar_projeto(d["projeto"].get("nome"), d["projeto"].get("pasta"), d["projeto"].get("apelidos"))
                if not erro:
                    await self.processos_mudaram()
                return web.json_response({"ok": not erro, "erro": erro})
            a = {"tipo": "conversa", "numero": d.get("numero"), "instrucao": d.get("instrucao", "")}
            erro = await self.acao(a)
            return web.json_response({"ok": not erro, "erro": erro})
        laco = asyncio.get_running_loop()
        cs = await laco.run_in_executor(None, conversas_mod.conversas)
        ligadas = {m.conversa: m.n for m in self.agentes.missoes.values() if m.conversa}
        return web.json_response({"conversas": [dict(c, sessao=None, missao=ligadas.get(c["numero"])) for c in cs],
                                  "projetos": [{"nome": p["nome"], "pasta": p["pasta"], "existe": p["existe"], "apelidos": p.get("apelidos", [])} for p in conversas_mod.projetos()],
                                  "leads": self._planilhas()})

    async def api_ajuste(self, req):
        """Etiquetas do topo: trocar o cérebro (auto, local, claude) e o modo de escuta (aberta, nome)."""
        d = await req.json()
        if d.get("cerebro") in ("auto", "local", "claude"):
            self.cerebro.mudar(d["cerebro"])
            if d["cerebro"] == "local" and not await self.cerebro.local.disponivel():
                self.cerebro.mudar("auto")
                return web.json_response({"ok": False, "erro": "O cérebro local não está instalado."})
            AJUSTES["cerebro"] = d["cerebro"]
        if d.get("escuta") in ("aberta", "nome"):
            await self.acao({"tipo": "escuta", "modo": d["escuta"]})
        _gravar_json(ARQ_AJUSTES, AJUSTES)
        self.enviar(**self.retrato())
        return web.json_response({"ok": True})

    async def ws(self, req):
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(req)
        self.clientes.add(ws)
        self.principal = ws
        await ws.send_str(json.dumps(self.retrato(), ensure_ascii=False))
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                d = json.loads(msg.data)
            except Exception:
                continue
            t = d.get("t")
            if t in ("texto", "acordar", "mudo", "abrir", "aqui"):
                self.principal = ws
            if t == "texto":
                self.manter_acordado()
                asyncio.ensure_future(self.pedido(str(d.get("v", ""))))
            elif t == "mudo":
                self.mudo = bool(d.get("v"))
                if self.ouvido:
                    self.ouvido.mudo = self.mudo
                self.enviar(t="estado", v=self.estado, mudo=self.mudo)
            elif t == "fala_fim":
                self._fala_acabou()
            elif t == "acordar":
                self._acordou("clique")
            elif t == "calar":
                self.enviar(t="calar")
                self._fala_acabou(forcar=True)
            elif t == "parar":
                await self.agentes.parar(d.get("v", "todas"))
            elif t == "abrir":
                self.abrir_painel(d.get("missao"), d.get("entrega"))
            elif t == "fechar":
                self.painel = None
                self.enviar(t="painel", v=None)
            elif t == "janela":
                self.janela(d.get("modo", "mini"), d.get("canto"))
            elif t == "recado":
                m, erro = await self.agentes.continuar(d.get("missao", 0), str(d.get("txt", "")).strip())
                if erro:
                    await ws.send_str(json.dumps({"t": "aviso", "txt": erro}, ensure_ascii=False))
            elif t == "pasta":
                m = self.agentes.missoes.get(int(d.get("missao", 0)))
                if m:
                    os.startfile(m.pasta)
            elif t == "zerar":
                await self.cerebro.reiniciar()
                self.conversa.clear()
                self.enviar(**self.retrato())
        self.clientes.discard(ws)
        return ws

    async def arquivo_missao(self, req):
        m = self.agentes.missoes.get(int(req.match_info["n"]))
        if not m:
            raise web.HTTPNotFound()
        alvo = os.path.normpath(os.path.join(m.pasta, req.match_info["resto"]))
        if not alvo.startswith(os.path.normpath(m.pasta)) or not os.path.isfile(alvo):
            raise web.HTTPNotFound()
        return web.FileResponse(alvo, headers={"Cache-Control": "no-store"})

    async def indice(self, req):
        return web.FileResponse(os.path.join(AQUI, "web", "index.html"), headers={"Cache-Control": "no-store"})

    async def saude(self, req):
        return web.json_response({"ok": True, "estado": self.estado, "missoes": len(self.agentes.missoes)})

    async def api_texto(self, req):
        d = await req.json()
        self.manter_acordado()
        asyncio.ensure_future(self.pedido(str(d.get("texto", ""))))
        return web.json_response({"ok": True})

    async def api_estado(self, req):
        return web.json_response(self.retrato())

    async def api_sair(self, req):
        log("saindo a pedido")
        janelas.fechar_mini()
        await self.agentes.parar("todas")
        self.agentes.salvar()
        asyncio.get_running_loop().call_later(0.4, lambda: os._exit(0))
        return web.json_response({"ok": True})

    async def api_mini(self, req):
        """O que a esfera flutuante precisa saber, lido várias vezes por segundo."""
        lista = self.agentes.ativas()
        ativas = len(lista)
        m = lista[-1] if lista else None
        return web.json_response(dict(
            quem=f"{m.agente.capitalize()} #{m.n}" if m else "",
            acao=" ".join(str(m.etapa).replace("*", "").replace("`", "").split())[:90] if m else "",
            pc=any(str(x.modelo or "").lower() == "computador" for x in lista),
            estado=self.estado, mudo=self.mudo, nivel=round(self.nivel_mic, 3),
            legenda=self.legenda if self.estado == "falando" else "",
            ativas=ativas, total=len(self.agentes.missoes), mago_v=VISUAL.get("v", 0),
            # com o painel grande em uso, a esfera some (não cobre botão); volta quando ele vai para outra janela
            # painel grande aberto (mesmo sem foco, ex.: restaurado pela barra de tarefas): só uma esfera na tela
            painel_frente=(janelas.grande_na_frente() or janelas.grande_visivel()) and not VISUAL.get("mini_sempre"), **janelas.estado_mini()))

    async def api_visual(self, req):
        """Roupa do mago e tema da tela. A tela desenha o mago e manda as poses prontas; a esfera flutuante só as copia."""
        if req.method == "POST":
            d = await req.json()
            for k in ("roupa", "tema", "tam", "mini_sempre"):
                if k in d:
                    VISUAL[k] = d[k]
            if isinstance(d.get("poses"), dict):
                VISUAL["poses"] = d["poses"]
            VISUAL["v"] = int(time.time() * 1000) % 10 ** 9
            try:
                with open(ARQ_VISUAL, "w", encoding="utf-8") as f:
                    json.dump(VISUAL, f, ensure_ascii=False)
            except Exception as e:
                log(f"visual: {e}")
            if "roupa" in d or "tema" in d:      # as outras telas abertas trocam junto
                self.enviar(t="visual", v={k: VISUAL.get(k) for k in ("roupa", "tema", "tam", "mini_sempre")})
        cheio = req.query.get("poses") == "1"
        return web.json_response({k: v for k, v in VISUAL.items() if cheio or k != "poses"})

    async def laco_cotas(self):
        while True:
            try:
                self.cotas = await cotas_mod.ler(CFG)
                self.enviar(t="cotas", v=self.cotas)
            except Exception as e:
                log(f"cotas: {e}")
            await asyncio.sleep(CFG.get("cotas_intervalo_s", 240))

    async def api_parar(self, req):
        n = await self.agentes.parar("todas")
        self.enviar(t="calar")
        self.enviar(t="som", v="erro")
        log(f"parei {n} missão(ões) pelo botão da esfera")
        return web.json_response({"paradas": n})

    async def api_janela(self, req):
        self.janela(req.match_info["modo"])
        return web.json_response({"ok": True})

    async def api_mudo(self, req):
        self.mudo = not self.mudo
        if self.ouvido:
            self.ouvido.mudo = self.mudo
        self.enviar(t="estado", v=self.estado, mudo=self.mudo)
        return web.json_response({"mudo": self.mudo})

    async def ao_iniciar(self, app):
        self.laco = asyncio.get_running_loop()
        asyncio.ensure_future(self.agentes.vigiar())
        async def aquecer_cerebro():       # a primeira resposta do cérebro já traz a cota do Claude na hora
            await self.cerebro.aquecer()
            if self.cotas:
                self.cotas[0] = cotas_mod.claude(CFG)
                self.enviar(t="cotas", v=self.cotas)
        asyncio.ensure_future(aquecer_cerebro())
        asyncio.ensure_future(self.laco_cotas())
        asyncio.ensure_future(self.laco_agenda())
        if AJUSTES.get("cerebro") in ("local", "claude") and not os.environ.get("JARVIS_CEREBRO"):
            self.cerebro.mudar(AJUSTES["cerebro"])

        async def aquecer_saudacoes():      # deixa as respostas prontas já gravadas, para saírem na hora
            for s in SAUDACOES:
                for p in partes_da_fala(s):
                    await self.voz.gerar(p)
        asyncio.ensure_future(aquecer_saudacoes())
        if not SEM_OUVIDO:
            from ouvido import Ouvido
            self.ouvido = Ouvido(
                CFG, log,
                ao_nivel=lambda v: self.do_fio(self._nivel, v),
                ao_acordar=lambda m: self.do_fio(self._acordou, m),
                ao_comecar_fala=lambda: self.do_fio(self._comecou_fala),
                ao_falar=lambda t, n: self.do_fio(self._ouviu, t, n))
            self.ouvido.acordado = self.acordado
            self.ouvido.iniciar()
        log(f"Jarvis no ar em http://127.0.0.1:{CFG['porta']}")


janelas.iniciar(CFG["porta"], DADOS, log)


def abrir_janela():
    janelas.mostrar_grande()


def ja_rodando():
    import urllib.request
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{CFG['porta']}/saude", timeout=1.5)
        return True
    except Exception:
        return False


def bandeja():
    """Ícone ao lado do relógio: abrir, silenciar, sair."""
    try:
        import pystray, urllib.request
        from PIL import Image, ImageDraw
        try:
            img = Image.open(os.path.join(AQUI, "web", "icone.png")).resize((64, 64))
        except Exception:
            img = Image.new("RGBA", (64, 64), (11, 12, 16, 255))
            ImageDraw.Draw(img).rectangle((14, 14, 50, 50), fill=(255, 107, 26, 255))

        def chamar(caminho):
            try:
                urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{CFG['porta']}{caminho}", data=b"{}", method="POST"), timeout=3)
            except Exception:
                pass
        menu = pystray.Menu(
            pystray.MenuItem("Abrir o Jarvis", lambda: chamar("/api/janela/grande"), default=True),
            pystray.MenuItem("Só a esfera flutuando", lambda: chamar("/api/janela/mini")),
            pystray.MenuItem("Ligar/desligar o microfone", lambda: chamar("/api/mudo")),
            pystray.MenuItem("Fechar o Jarvis", lambda icone: (chamar("/api/sair"), icone.stop())))
        pystray.Icon("Jarvis", img, "Jarvis", menu).run()
    except Exception as e:
        log(f"bandeja indisponível: {e}")


@web.middleware
async def so_local(req, handler):
    """Só a própria tela do Jarvis fala com ele. Pedido vindo de outro site aberto no navegador, ou feito por um nome de
    servidor que não seja este computador, é recusado: sem isto, qualquer página poderia mandar um pedido ao Jarvis."""
    bons = {f"127.0.0.1:{CFG['porta']}", f"localhost:{CFG['porta']}"}
    if req.headers.get("Host", "").lower() not in bons:
        return web.Response(status=403, text="recusado")
    origem = req.headers.get("Origin")
    if origem and (req.method != "GET" or req.headers.get("Upgrade", "").lower() == "websocket") \
            and origem.lower() not in {"http://" + b for b in bons}:
        return web.Response(status=403, text="recusado")
    return await handler(req)


def main():
    if "--janela" in sys.argv:
        if ja_rodando():
            abrir_janela()
            return
        import threading
        threading.Thread(target=bandeja, daemon=True).start()
        threading.Timer(2.5, abrir_janela).start()
    j = Jarvis()
    app = web.Application(client_max_size=4 * 1024 * 1024, middlewares=[so_local])
    app.on_startup.append(j.ao_iniciar)
    app.router.add_get("/", j.indice)
    app.router.add_get("/ws", j.ws)
    app.router.add_get("/saude", j.saude)
    app.router.add_get("/api/estado", j.api_estado)
    app.router.add_post("/api/texto", j.api_texto)
    app.router.add_post("/api/sair", j.api_sair)
    app.router.add_get("/api/mini", j.api_mini)
    app.router.add_post("/api/janela/{modo}", j.api_janela)
    app.router.add_post("/api/mudo", j.api_mudo)
    app.router.add_post("/api/parar", j.api_parar)
    app.router.add_get("/api/visual", j.api_visual)
    app.router.add_post("/api/visual", j.api_visual)
    app.router.add_get("/api/processos", j.api_processos)
    app.router.add_post("/api/processos", j.api_processos)
    app.router.add_get("/api/conversas", j.api_conversas)
    app.router.add_post("/api/conversas", j.api_conversas)
    app.router.add_post("/api/ajuste", j.api_ajuste)
    app.router.add_get("/m/{n}/{resto:.*}", j.arquivo_missao)
    app.router.add_static("/voz", PASTA_VOZ)
    app.router.add_static("/", os.path.join(AQUI, "web"))
    web.run_app(app, host="127.0.0.1", port=CFG["porta"], print=None, access_log=None)


if __name__ == "__main__":
    main()
