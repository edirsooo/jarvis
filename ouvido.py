"""Ouvido do Jarvis: microfone, palmas, palavra de ativação e transcrição. Tudo local."""
import importlib.util, os, queue, re, threading, time
import numpy as np

TAXA = 16000
BLOCO = 1280  # 80 ms

ALUCINACOES = ("amara.org", "legendas pela comunidade", "inscreva-se", "obrigado por assistir",
               "legenda adriana zanotto", "www.", "tchau, tchau", "e aí, pessoal")
NOME_RE = re.compile(r"\b(d?j[aá]r[vb][ie]s?|jarvys|j[aá]vis|jarbas|djarvis|jarviz|charvis|járvis)\b", re.I)


AGENTE_RE = re.compile(r"^\W*(claude|cloud|cl[aá]udio|codex|codecs|c[oó]dex)\b[,!.:]?\s+\w+", re.I)
CURTAS_OK = {"sim", "não", "nao", "pode", "isso", "beleza", "ok", "obrigado", "valeu", "para", "chega", "certo", "exato", "manda",
             "ei", "oi", "ô", "o", "e", "aí", "ai", "opa", "fala", "beijo", "beijos", "hey", "alô"}


def incompleta(txt):
    """Parece pedaço de frase: termina em reticências/vírgula ou é uma ou duas palavras soltas (fora 'Jarvis', 'sim', 'pode'...)."""
    t = txt.strip()
    if t.endswith(("...", "…", ",")):
        return True
    palavras = [p for p in re.findall(r"\w+", t.lower()) if not NOME_RE.fullmatch(p)]
    return 0 < len(palavras) <= 2 and not t.endswith("?") and not all(p in CURTAS_OK for p in palavras)


def _dll_cuda():
    """A placa precisa do cublas/cudnn; o torch instalado já traz as DLLs (Windows).
    No Linux vale a CUDA do sistema, se houver placa NVIDIA; no macOS não há CUDA: a transcrição usa o processador."""
    import sys
    if sys.platform == "darwin":
        return False
    if sys.platform != "win32":
        try:
            import ctranslate2
            return ctranslate2.get_cuda_device_count() > 0
        except Exception:
            return False
    try:
        spec = importlib.util.find_spec("torch")
        if spec and spec.submodule_search_locations:
            lib = os.path.join(list(spec.submodule_search_locations)[0], "lib")
            if os.path.isdir(lib):
                os.add_dll_directory(lib)
                os.environ["PATH"] = lib + os.pathsep + os.environ.get("PATH", "")
                return True
    except Exception:
        pass
    return False


class Transcritor:
    def __init__(self, cfg, log):
        self.cfg, self.log = cfg, log
        self.modelo = None
        self.onde = "-"
        self.trava = threading.Lock()

    def carregar(self):
        from faster_whisper import WhisperModel
        nome = self.cfg.get("whisper_modelo", "large-v3-turbo")
        if _dll_cuda():
            try:
                m = WhisperModel(nome, device="cuda", compute_type="int8_float16")
                # prova real: a falha de DLL só aparece ao transcrever
                list(m.transcribe(np.zeros(TAXA, dtype=np.float32), language="pt")[0])
                self.modelo, self.onde = m, f"{nome} (placa)"
                self.log(f"transcrição: {self.onde}")
                return
            except Exception as e:
                self.log(f"placa indisponível para transcrição ({type(e).__name__}); usando processador")
        nome = self.cfg.get("whisper_reserva", "small")
        self.modelo = WhisperModel(nome, device="cpu", compute_type="int8")
        self.onde = f"{nome} (processador)"
        self.log(f"transcrição: {self.onde}")

    def transcrever(self, audio):
        if self.modelo is None:
            return ""
        with self.trava:
            segs, _ = self.modelo.transcribe(
                audio, language="pt", beam_size=3,
                # detector de voz Silero (vem com o faster-whisper): corta o que não é fala antes de transcrever,
                # então teclado, batida e ruído não viram frase inventada
                vad_filter=bool(self.cfg.get("filtro_de_voz", True)),
                vad_parameters={"min_silence_duration_ms": 400, "speech_pad_ms": 250, "threshold": 0.45},
                condition_on_previous_text=False,
                initial_prompt=self.cfg.get("whisper_dica") or
                "Ei, Jarvis. Claude, Codex, Ollama, Gemma, YouTube, Google.")
            partes = []
            for s in segs:
                if s.no_speech_prob > 0.6 and s.avg_logprob < -0.8:
                    continue
                partes.append(s.text.strip())
        txt = " ".join(partes).strip()
        baixo = txt.lower()
        if any(a in baixo for a in ALUCINACOES):
            return ""
        # frases que o Whisper inventa em ruído curto
        if baixo.strip(" .!?") in ("obrigado", "obrigada", "tchau", "é", "e aí", "amém", "legenda", "música"):
            return ""
        return txt


class Ouvido:
    """Chama: ao_nivel(rms), ao_acordar(motivo), ao_comecar_fala(), ao_falar(texto, tem_nome)."""

    def __init__(self, cfg, log, ao_nivel, ao_acordar, ao_comecar_fala, ao_falar):
        self.cfg, self.log = cfg, log
        self.ao_nivel, self.ao_acordar = ao_nivel, ao_acordar
        self.ao_comecar_fala, self.ao_falar = ao_comecar_fala, ao_falar
        self.fila = queue.Queue()
        self.falas = queue.Queue()
        self.stt = Transcritor(cfg, log)
        self.mudo = False
        self.jarvis_falando = False      # informado pelo servidor
        self.acordado = lambda: False    # informado pelo servidor
        self.oww = None
        self.ruido = 0.004
        self.vivo = True
        self.dispositivo = "-"
        self._palma_t = 0.0
        self._ant_pico = 0.0
        self._ult_acordar = 0.0
        self.gravando = False            # há uma fala sendo gravada agora
        self.transcrevendo = False       # há uma fala sendo passada para texto agora

    def ocupado(self):
        """Ele ainda está falando, ou há fala gravada esperando virar texto. O servidor usa isto para juntar um pedido dito em pedaços."""
        return self.gravando or self.transcrevendo or not self.falas.empty()

    # ---------- início ----------
    def iniciar(self):
        threading.Thread(target=self._preparar, daemon=True).start()

    def _preparar(self):
        try:
            self.stt.carregar()
        except Exception as e:
            self.log(f"ERRO ao carregar a transcrição: {e}")
        if self.cfg.get("acordar_por_nome", True):
            try:
                import openwakeword
                from openwakeword.model import Model
                try:
                    openwakeword.utils.download_models(["hey_jarvis"])
                except Exception:
                    pass
                self.oww = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
                self.log("palavra de ativação: pronta")
            except Exception as e:
                self.log(f"palavra de ativação indisponível ({type(e).__name__}: {e}); uso só a transcrição")
        threading.Thread(target=self._transcrever_laco, daemon=True).start()
        self._microfone()

    def _microfone(self):
        try:
            import sounddevice as sd
        except Exception as e:
            self.dispositivo = "indisponível"
            self.log(f"microfone indisponível ({e}); instale a biblioteca PortAudio ou use escrevendo no painel")
            return
        ult_erro, espera = "", 5
        while self.vivo:
            try:
                dev = self.cfg.get("microfone")
                info = sd.query_devices(dev, "input") if dev is not None else sd.query_devices(kind="input")
                self.dispositivo = info["name"]
                self.log(f"microfone: {self.dispositivo}")
                ult_erro, espera = "", 5
                try:
                    with sd.InputStream(samplerate=TAXA, channels=1, dtype="float32", blocksize=BLOCO,
                                        device=dev, callback=lambda d, f, t, s: self.fila.put(d[:, 0].copy())):
                        self._laco()
                except Exception as e1:
                    # no macOS e no Linux alguns microfones (Bluetooth, USB, ALSA puro) não aceitam 16 kHz direto:
                    # abre na taxa nativa do dispositivo e reamostra cada bloco para 16 kHz
                    sr = int(round(info.get("default_samplerate") or 0))
                    if sr and sr != TAXA:
                        bloco_nat = max(1, int(round(BLOCO * sr / TAXA)))
                        self.log(f"microfone: taxa nativa {sr} Hz (reamostrando para {TAXA} Hz)")
                        def cb(d, f, t, s):
                            x = d[:, 0]
                            if len(x) == BLOCO:
                                self.fila.put(x.copy())
                            else:
                                self.fila.put(np.interp(np.linspace(0, len(x) - 1, BLOCO), np.arange(len(x)), x).astype(np.float32))
                        with sd.InputStream(samplerate=sr, channels=1, dtype="float32", blocksize=bloco_nat, device=dev, callback=cb):
                            self._laco()
                    else:
                        raise e1
            except Exception as e:
                msg = str(e)
                if msg != ult_erro:
                    self.log(f"microfone falhou ({msg}); tento de novo em {espera} s")
                    ult_erro = msg
                time.sleep(espera)
                espera = min(60, espera * 2)

    # ---------- laço principal ----------
    def _laco(self):
        pausa = self.cfg.get("pausa_fim_de_fala_ms", 800) / 1000
        pre = []            # ~480 ms antes da fala
        gravando = False
        trecho = []
        silencio = 0.0
        voz_seg = 0
        ult_nivel = 0.0
        ini_acordado = False    # ele estava acordado quando esta fala começou (vale para a fala inteira, mesmo longa)
        while self.vivo:
            self.gravando = gravando
            try:
                b = self.fila.get(timeout=1)
            except queue.Empty:
                continue
            rms = float(np.sqrt(np.mean(b * b)))
            agora = time.time()
            if agora - ult_nivel > 0.07:
                ult_nivel = agora
                self.ao_nivel(0.0 if self.mudo else rms)
            if self.mudo:
                gravando, trecho, pre = False, [], []
                continue

            # palmas
            # (vale também com a gravação de fala aberta: a 1ª palma já abre a gravação, e a 2ª não pode se perder)
            if self.cfg.get("acordar_por_palmas", True) and not self.jarvis_falando:
                self._palmas(b, agora)
            if getattr(self, "_guardar", 0) > 0 and self.cfg.get("palmas_diagnostico"):
                self._guardar -= 1
                self._amostra = getattr(self, "_amostra", []) + [b]
                if self._guardar == 0:
                    try:
                        pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados", "estalos")
                        os.makedirs(pasta, exist_ok=True)
                        np.save(os.path.join(pasta, f"{time.strftime('%H%M%S')}_{int(agora * 10) % 10}.npy"), np.concatenate(self._amostra))
                    except Exception:
                        pass
                    self._amostra = []

            # palavra de ativação
            if self.oww is not None and not self.acordado():
                try:
                    p = self.oww.predict((b * 32767).astype(np.int16))
                    if max(p.values()) >= self.cfg.get("limiar_wakeword", 0.45):
                        self._acordar("nome")
                        self.oww.reset()
                except Exception:
                    pass

            # detector de fala por energia, com piso de ruído que se adapta
            limiar = max(self.cfg.get("limiar_voz", 0.012), self.ruido * 3.2)
            if self.jarvis_falando:
                if not self.cfg.get("interromper_por_fala", True):
                    gravando, trecho = False, []
                    continue
                limiar *= 2.2   # com ele falando, só voz firme interrompe
            tem_voz = rms > limiar
            if not tem_voz and not gravando:
                self.ruido = 0.97 * self.ruido + 0.03 * rms

            if not gravando:
                pre.append(b)
                if len(pre) > 6:
                    pre.pop(0)
                voz_seg = voz_seg + 1 if tem_voz else 0
                if voz_seg >= 2:
                    gravando, trecho, silencio = True, list(pre), 0.0
                    pre = []
                    ini_acordado = self.acordado()
                    if ini_acordado:
                        self.ao_comecar_fala()
            else:
                trecho.append(b)
                silencio = 0.0 if tem_voz else silencio + BLOCO / TAXA
                dur = len(trecho) * BLOCO / TAXA
                # fala bem curta ("Jarvis", "sim", "não") fecha mais rápido, para a resposta sair logo
                espera = min(pausa, self.cfg.get("pausa_fala_curta_ms", 600) / 1000) if dur - silencio < 0.9 else pausa
                if silencio >= espera or dur > 40:
                    gravando, voz_seg = False, 0
                    if dur - silencio >= 0.35:
                        self.falas.put((np.concatenate(trecho), ini_acordado))
                    trecho = []

    def _palmas(self, b, agora):
        cfg = self.cfg
        pico_min = cfg.get("palmas_pico", 0.22)
        sub = np.abs(b).reshape(-1, 160).max(axis=1)   # janelas de 10 ms
        for i, pico in enumerate(sub):
            t = agora - (len(sub) - i) * 0.01
            estalo = pico > pico_min and pico > self._ant_pico * 4 and pico > self.ruido * 25
            if pico > 0.015 and pico > self._ant_pico * 3 and t - getattr(self, "_ult_diag", 0) > 0.09:
                self._ult_diag = t       # registro para regular a sensibilidade: todo estalo forte aparece no log
                self._guardar = 5        # guarda este bloco e os próximos (0,4 s) para análise
                self.log(f"estalo: pico {pico:.2f} (mínimo {pico_min}), antes {self._ant_pico:.3f}, ruído {self.ruido:.4f}"
                         f"{'' if estalo else ' -> fraco demais'}")
            self._ant_pico = 0.6 * self._ant_pico + 0.4 * pico
            if not estalo:
                continue
            dt = t - self._palma_t
            if dt < 0.09:
                continue   # mesmo estalo
            if cfg.get("palmas_intervalo_min", 0.15) <= dt <= cfg.get("palmas_intervalo_max", 0.75):
                self._palma_t = 0.0
                self._acordar("palmas")
                return
            self._palma_t = t

    def _acordar(self, motivo):
        if time.time() - self._ult_acordar < 1.5:
            return
        self._ult_acordar = time.time()
        self.ao_acordar(motivo)

    # ---------- transcrição ----------
    def _transcrever_laco(self):
        while self.vivo:
            audio, acordado0 = self.falas.get()
            self.transcrevendo = True
            try:
                self._uma_fala(audio, acordado0)
            except Exception as e:
                self.log(f"transcrição falhou: {e}")
            self.transcrevendo = False

    def _uma_fala(self, audio, acordado0):
        # vale o que valia quando ele começou a falar: uma frase longa não se perde se a janela fechar no meio
        acordado = acordado0 or self.acordado()
        # dormindo, só vale a pena transcrever frase curta (procura o nome)
        if not acordado and (not self.cfg.get("acordar_por_nome", True) or len(audio) > TAXA * 12):
            return
        t0 = time.time()
        txt = self.stt.transcrever(audio)
        dt = time.time() - t0
        if not txt:
            return
        # frase cortada no meio ("Pesquisa..." + "como fazer frango frito"): espera o resto e junta
        while acordado and incompleta(txt):
            try:
                resto = self.falas.get(timeout=self.cfg.get("espera_continuacao_s", 1.8))
            except queue.Empty:
                break
            t0 = time.time()
            mais = self.stt.transcrever(resto[0])
            dt += time.time() - t0
            if mais:
                txt = txt.rstrip(" .…") + " " + mais[0].lower() + mais[1:]
        # "Jarvis" em qualquer ponto, ou a frase já começando por "Claude," / "Codex,"
        tem_nome = bool(NOME_RE.search(txt) or AGENTE_RE.match(txt))
        if not acordado and not tem_nome:
            return
        self.log(f"ouvi ({dt:.1f}s): {txt}")
        self.ao_falar(txt, tem_nome)
