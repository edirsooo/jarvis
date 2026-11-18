"""Voz do Jarvis: ElevenLabs quando há chave, Edge como reserva. Gera um mp3 por frase."""
import asyncio, hashlib, os, re
import aiohttp

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "dados", "voz")
os.makedirs(PASTA, exist_ok=True)


def limpar(texto):
    texto = re.sub(r"[*_#`>\[\]{}]", "", texto)
    texto = re.sub(r"https?://\S+", "o link", texto)
    return re.sub(r"\s+", " ", texto).strip()


def partes(texto):
    """Primeira frase sozinha (sai rápido), o resto junto."""
    texto = limpar(texto)
    m = re.match(r"(.{12,}?[.!?…])\s+(.+)", texto)
    return [m.group(1), m.group(2)] if m else ([texto] if texto else [])


class Voz:
    def __init__(self, cfg, log):
        self.cfg, self.log = cfg, log
        self.motor_em_uso = "-"

    async def gerar(self, texto):
        """Devolve o nome do arquivo mp3 (dentro de dados/voz) ou None."""
        texto = limpar(texto)
        if not texto:
            return None
        motor = self.cfg.get("voz_motor", "edge")
        chave = self.cfg.get("elevenlabs_chave") or os.environ.get("ELEVENLABS_API_KEY", "")
        usar_eleven = motor == "elevenlabs" and chave and self.cfg.get("elevenlabs_voz")
        marca = f"{'el' if usar_eleven else 'ed'}|{self.cfg.get('elevenlabs_voz')}|{self.cfg.get('voz_edge')}|{self.cfg.get('voz_edge_velocidade')}|{texto}"
        nome = hashlib.sha1(marca.encode("utf-8")).hexdigest()[:20] + ".mp3"
        caminho = os.path.join(PASTA, nome)
        if os.path.exists(caminho) and os.path.getsize(caminho) > 500:
            return nome
        if usar_eleven:
            try:
                await self._eleven(texto, caminho, chave)
                self.motor_em_uso = "ElevenLabs"
                return nome
            except Exception as e:
                self.log(f"ElevenLabs falhou ({e}); usando a voz de reserva")
        try:
            await self._edge(texto, caminho)
            self.motor_em_uso = "Edge"
            return nome
        except Exception as e:
            self.log(f"voz falhou: {e}")
            return None

    async def _edge(self, texto, caminho):
        import edge_tts
        tmp = caminho + ".tmp"
        com = edge_tts.Communicate(texto, self.cfg.get("voz_edge", "pt-BR-AntonioNeural"),
                                   rate=self.cfg.get("voz_edge_velocidade", "+10%"))
        await asyncio.wait_for(com.save(tmp), timeout=25)
        os.replace(tmp, caminho)

    async def _eleven(self, texto, caminho, chave):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.cfg['elevenlabs_voz']}/stream"
        corpo = {"text": texto, "model_id": self.cfg.get("elevenlabs_modelo", "eleven_v4")}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
            async with s.post(url, json=corpo, headers={"xi-api-key": chave}) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                dados = await r.read()
        tmp = caminho + ".tmp"
        with open(tmp, "wb") as f:
            f.write(dados)
        os.replace(tmp, caminho)
