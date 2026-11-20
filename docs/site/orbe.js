// Orbe do Jarvis para o site: porte do desenho do app (web/app.js: formaPonto, voxForma, voxPos, desenhaVoxel, rosto,
// PALETA e PALETA_FORMA). Gerado a partir do app; o miolo é o código do app, só embrulhado numa fábrica
// (cada canvas da página tem o seu orbe) e com o nível de voz simulado, já que aqui não há microfone nem fala.
(function () {
  const calmo = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function criaOrbe(cv, op) {
    const g = cv.getContext('2d');
    // O: o que a página escolhe. forma, corpo, cor (hex ou ''), estado, anel (anel de nível); x, y, r em fração do canvas
    const O = Object.assign({ forma: 'orbe', corpo: 'voxel', cor: '', estado: 'ouvindo', anel: false, x: .5, y: .5, r: .36, nivelFalso: true, explode: 0 }, op || {});
    const N = 620, pts = [];
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), th = i * Math.PI * (3 - Math.sqrt(5));
      pts.push({ x: Math.cos(th) * r, y, z: Math.sin(th) * r, f: Math.random() * 6.28, s: .6 + Math.random() * .8 });
    }
    const PALETA = {
      dormindo: [[70, 78, 100], [40, 44, 58]], ouvindo: [[90, 215, 255], [230, 250, 255]],
      pensando: [[255, 210, 63], [255, 107, 26]], falando: [[255, 107, 26], [255, 190, 120]],
      trabalhando: [[25, 195, 125], [255, 107, 26]], mudo: [[120, 40, 50], [60, 30, 36]],
    };
    // formas do Jarvis: cada uma com paleta própria por estado (o corpo muda em formaPonto, os enfeites em formaEnfeite)
    const FORMAS = [['orbe', 'Orbe de cubos'], ['fantasma', 'Fantasminha'], ['chama', 'Bola de fogo'], ['eletrica', 'Entidade elétrica'], ['espirito', 'Espírito dourado']];
    const PALETA_FORMA = {
      fantasma: { dormindo: [[120, 140, 170], [70, 80, 100]], ouvindo: [[170, 240, 255], [240, 255, 255]], pensando: [[220, 230, 255], [170, 180, 255]], falando: [[200, 255, 240], [255, 255, 255]], trabalhando: [[150, 255, 200], [220, 255, 240]], mudo: [[110, 70, 80], [60, 40, 50]] },
      chama: { dormindo: [[150, 50, 20], [90, 30, 14]], ouvindo: [[255, 170, 60], [255, 240, 180]], pensando: [[255, 120, 30], [255, 220, 90]], falando: [[255, 140, 40], [255, 230, 150]], trabalhando: [[255, 130, 40], [255, 200, 80]], mudo: [[90, 40, 36], [50, 30, 28]] },
      eletrica: { dormindo: [[60, 70, 140], [40, 40, 90]], ouvindo: [[120, 220, 255], [240, 250, 255]], pensando: [[180, 120, 255], [120, 220, 255]], falando: [[140, 200, 255], [255, 255, 255]], trabalhando: [[100, 160, 255], [200, 140, 255]], mudo: [[70, 40, 70], [40, 30, 45]] },
      espirito: { dormindo: [[150, 120, 60], [90, 70, 40]], ouvindo: [[255, 220, 140], [255, 250, 220]], pensando: [[255, 200, 90], [255, 160, 60]], falando: [[255, 210, 120], [255, 245, 200]], trabalhando: [[230, 200, 110], [140, 220, 160]], mudo: [[90, 60, 50], [50, 40, 36]] },
    };
    // cor escolhida para o Jarvis: a mesma cor em todos os estados, mudando só o brilho (o estado continua legível)
    function paletaDaCor(hex, e) {
      const n = parseInt(hex.slice(1), 16), c = [n >> 16, (n >> 8) & 255, n & 255];
      const k = (f) => c.map((v) => Math.min(255, v * f)), claro = c.map((v) => v + (255 - v) * .55);
      return { dormindo: [k(.55), k(.3)], ouvindo: [c, claro], pensando: [claro, k(.75)], falando: [c, claro], trabalhando: [c, k(.7)], mudo: [[120, 40, 50], [60, 30, 36]] }[e];
    }
    // estilos do corpo: voxel brilhante (volume de cubinhos de luz, o padrão), cubos 3D (o original), pixel (um quadrado por ponto, o mais leve), luz (partículas que brilham), liso (massinha)
    const CORPOS = [['voxel', 'Voxel brilhante'], ['cubos', 'Cubos 3D'], ['pixel', 'Pixel leve'], ['luz', 'Luz suave'], ['liso', 'Bolhas macias']];
    const corpoAtual = () => (CORPOS.some((x) => x[0] === O.corpo) ? O.corpo : 'voxel');
    // luz: uma bolinha de brilho pronta por cor, refeita só quando a cor muda
    const SPR = [document.createElement('canvas'), document.createElement('canvas')];
    SPR.forEach((c) => { c.width = c.height = 48; });
    let sprChave = '';
    function prepSprites() {
      const chave = V.cor1.map((v) => v >> 3).join() + '|' + V.cor2.map((v) => v >> 3).join();
      if (chave === sprChave) return; sprChave = chave;
      [V.cor1, V.cor2].forEach((cor, i) => {
        const x = SPR[i].getContext('2d'), c = cor.map((v) => v | 0).join(), cl = cor.map((v) => (v + (255 - v) * .6) | 0).join();
        const gr = x.createRadialGradient(24, 24, 0, 24, 24, 24);
        gr.addColorStop(0, `rgba(${cl},1)`); gr.addColorStop(.3, `rgba(${c},.6)`); gr.addColorStop(1, `rgba(${c},0)`);
        x.clearRect(0, 0, 48, 48); x.fillStyle = gr; x.fillRect(0, 0, 48, 48);
      });
    }
    // rosto do fantasminha e da bola de fogo: olhos que seguem o mouse e piscam, sorriso no carinho, boca que fala
    const ROSTO = { piscaAte: 0, proxPisca: 2 };
    function bloco(x, y, w, h, redondo) {
      g.beginPath();
      if (g.roundRect) g.roundRect(x, y, w, h, redondo ? Math.min(w, h) / 2 : Math.min(w, h) * .22); else g.rect(x, y, w, h);
      g.fill();
    }
    function rosto(cx, cy, R, t, e, redondo) {
      if (t > ROSTO.proxPisca) { ROSTO.piscaAte = t + .12; ROSTO.proxPisca = t + 2.2 + Math.random() * 3.8; }
      const pisca = t < ROSTO.piscaAte, tinta = 'rgba(14,16,30,.95)';
      const perto = MOUSE.dentro && Math.hypot(MOUSE.x - cx, MOUSE.y - cy) < R * 1.15;      // mouse em cima: carinho
      const feliz = perto || (e === 'falando' && V.nivel > .55);
      const fx = cx + V.olhaX * R * .25, oy = V.olhaY * R * .16;      // o rosto vira para o cursor
      const ex = R * .3, ey = cy - R * .06 + oy, w = R * .19;
      let h = R * .28;
      const claro = V.cor2.map((v) => (v + (255 - v) * .55) | 0).join(), fundo = g.createRadialGradient(fx, cy + oy, 0, fx, cy + oy, R * .72);
      fundo.addColorStop(0, `rgba(${claro},.7)`); fundo.addColorStop(.6, `rgba(${claro},.35)`); fundo.addColorStop(1, `rgba(${claro},0)`);
      g.fillStyle = fundo; g.beginPath(); g.ellipse(fx, cy + oy, R * .72, R * .6, 0, 0, 6.2832); g.fill();
      g.fillStyle = tinta; g.strokeStyle = tinta; g.lineCap = 'round'; g.lineWidth = Math.max(2.5, R * .06);
      if (feliz && e !== 'mudo') {                                  // ^ ^ (até dormindo ele sorri no carinho)
        for (const s of [-1, 1]) { g.beginPath(); g.arc(fx + s * ex, ey + w * .25, w * .55, 1.15 * Math.PI, 1.85 * Math.PI); g.stroke(); }
      } else if (e === 'dormindo' || e === 'mudo') {                // dormindo: olhos fechados em arco; mudo: risquinho
        for (const s of [-1, 1]) {
          g.beginPath();
          if (e === 'dormindo') g.arc(fx + s * ex, ey - w * .2, w * .55, .15 * Math.PI, .85 * Math.PI);
          else { g.moveTo(fx + s * ex - w * .5, ey); g.lineTo(fx + s * ex + w * .5, ey); }
          g.stroke();
        }
      } else {
        if (e === 'ouvindo') h *= 1.1 + V.nivel * .25;
        if (e === 'pensando') h *= .82;
        if (pisca) h = R * .04;
        const lx = e === 'pensando' ? Math.sin(t * 1.4) * w * .22 : V.olhaX * w * .55;
        const ly = e === 'pensando' ? -h * .22 : e === 'trabalhando' ? h * .18 : V.olhaY * h * .45;
        for (const s of [-1, 1]) {
          const x0 = fx + s * ex;
          g.fillStyle = tinta; bloco(x0 - w / 2, ey - h / 2, w, h, redondo);
          if (!pisca) {                                              // brilho do olho, que anda junto com o olhar
            const b = w * .36; g.fillStyle = 'rgba(255,255,255,.92)';
            bloco(x0 - w * .14 - b / 2 + lx, ey - h * .2 - b / 2 + ly, b, b, redondo);
          }
        }
      }
      g.fillStyle = tinta;
      const my = cy + R * .22 + oy;
      if (e === 'falando') { const bw = R * (.13 + V.nivel * .1), bh = R * (.05 + V.nivel * .22); bloco(fx - bw / 2, my - bh / 2, bw, bh, true); }
      else if (feliz || e === 'ouvindo') { g.beginPath(); g.arc(fx, my - R * .06, R * .085, .18 * Math.PI, .82 * Math.PI); g.stroke(); }
      else if (e === 'pensando') bloco(fx + R * .06, my - R * .03, R * .07, R * .07, true);
      if (feliz) { g.fillStyle = 'rgba(255,120,150,.4)'; for (const s of [-1, 1]) bloco(fx + s * ex * 1.5 - R * .075, ey + R * .14, R * .15, R * .07, true); }
    }
    const formaAtual = () => (PALETA_FORMA[O.forma] || O.forma === 'orbe' ? O.forma : 'orbe');
    // o corpo de cada forma, no espaço do próprio Jarvis (y para baixo); devolve [x, y, z]
    function formaPonto(fm, p, t) {
      let x = p.x, y = p.y, z = p.z;
      if (fm === 'fantasma') {
        if (y > 0) { const s = 1 + y * 0.22; x *= s; z *= s; y = y * 1.5 + 0.09 * Math.sin(Math.atan2(z, x) * 6 + t * 4) * y; }   // a barra do lençol ondula
      } else if (fm === 'chama') {
        const up = Math.max(0, -y), sc = 1 - up * 0.6;
        x = x * sc + 0.07 * Math.sin(t * 7 + y * 5 + p.f) * up; z *= sc; y = y * 1.2 - up * up * 0.55;
        if (p.s > 1.3 && up > 0.25) { const k = (t * 0.45 * p.s + p.f) % 1; y -= k * 1.1; x *= 1 - k * 0.6; z *= 1 - k * 0.6; }   // fagulhas que sobem
      } else if (fm === 'espirito') {
        if (p.s >= 1.22) { const a = p.f * 3 + t * 0.7 * p.s, rr = 1.35 + 0.12 * Math.sin(t + p.f); x = Math.cos(a) * rr; z = Math.sin(a) * rr; y = 0.22 * Math.sin(a * 2 + p.f); }   // luzes em órbita
        else { x *= 0.62; y *= 0.62; z *= 0.62; }
      }
      return [x, y, z];
    }
    // voxel brilhante: o corpo é um volume de cubinhos de luz com silhueta cheia (como na abertura 3D do vídeo):
    // fantasma com barra ondulando, chama com línguas e brasas, elétrica com espinhos que piscam, espírito com cauda e luzes em órbita
    const VOX = {};
    function voxForma(fm) {
      if (VOX[fm]) return VOX[fm];
      const dentro = {
        fantasma: (x, y, z) => { const r = Math.hypot(x, z); if (y < -.05) return r * r + (y + .05) ** 2 / .9 <= .74; return r <= .86 && y <= .92 - .16 * (.5 + .5 * Math.sin(Math.atan2(z, x) * 4)); },
        chama: (x, y, z) => { const r = Math.hypot(x, z); if (y >= .25) return r * r + (y - .25) ** 2 <= .6; const k = (y + 1.25) / 1.5; return k > 0 && r <= .77 * Math.pow(k, 1.25); },
        eletrica: (x, y, z) => x * x + y * y + z * z <= .6,
        espirito: (x, y, z) => { if (x * x + (y + .3) ** 2 + z * z <= .34) return true;
          for (let i = 1; i <= 7; i++) { const u = i / 7, px = .38 * Math.sin(u * 2.8), py = .1 + u * .95, rr = .44 * (1 - u * .78); if ((x - px) ** 2 + (y - py) ** 2 + z * z <= rr * rr) return true; }
          return false; },
      }[fm] || ((x, y, z) => x * x + y * y + z * z <= .92);
      const n = 20, cel = 2.6 / n, P = (i) => -1.3 + (i + .5) * cel, L = [];
      const em = (i, j, k) => i >= 0 && j >= 0 && k >= 0 && i < n && j < n && k < n && dentro(P(i), P(j), P(k));
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) for (let k = 0; k < n; k++) {
        if (!em(i, j, k)) continue;
        if (em(i + 1, j, k) && em(i - 1, j, k) && em(i, j + 1, k) && em(i, j - 1, k) && em(i, j, k + 1) && em(i, j, k - 1)) continue;   // só a casca
        L.push({ x: P(i), y: P(j), z: P(k), f: Math.random() * 6.28, tom: .82 + Math.random() * .3, k: 'corpo' });
      }
      if (fm === 'eletrica') for (let a = 0; a < 12; a++) {              // espinhos: fileiras de cubos para fora
        const yy = 1 - (a + .5) / 6, rr = Math.sqrt(Math.max(0, 1 - yy * yy)), th = a * 2.39996, dx = Math.cos(th) * rr, dz = Math.sin(th) * rr;
        for (let r = .82; r < 1.36; r += cel) L.push({ x: dx * r, y: yy * r, z: dz * r, f: Math.random() * 6.28, tom: 1.15, k: 'raio', gr: a });
      }
      if (fm === 'espirito') for (let a = 0; a < 7; a++) L.push({ x: 0, y: 0, z: 0, f: a / 7 * 6.28, tom: 1.2, k: 'orbita' });
      if (fm === 'chama') for (let a = 0; a < 16; a++) { const th = Math.random() * 6.28, r = Math.random() * .45; L.push({ x: Math.cos(th) * r, y: 0, z: Math.sin(th) * r, f: Math.random() * 6.28, tom: 1.2, k: 'brasa' }); }
      L.cel = cel; return (VOX[fm] = L);
    }
    // posição de cada cubinho no instante t (+ tamanho); null = apagado neste quadro
    function voxPos(fm, v, t) {
      let x = v.x, y = v.y, z = v.z;
      if (v.k === 'orbita') { const a = v.f + t * .8; return [Math.cos(a) * 1.3, -.15 + .25 * Math.sin(a * 2 + v.f), Math.sin(a) * 1.3, 1.25]; }
      if (v.k === 'brasa') { const u = (t * .45 + v.f / 6.28) % 1; return [x * (1 - u * .6) + .12 * Math.sin(t * 3 + v.f), -.55 - u * 1.05, z * (1 - u * .6), .9 * (1 - u)]; }
      if (v.k === 'raio') { if (Math.sin(t * 9 + v.gr * 2.3) < -.25) return null; return [x + (Math.random() - .5) * .04, y + (Math.random() - .5) * .04, z, 1]; }
      if (fm === 'fantasma' && y > .35) { const k = (y - .35) * 1.6; x += .06 * k * Math.sin(t * 3 + y * 5); y += .06 * k * Math.sin(Math.atan2(z, x) * 4 + t * 4); }
      else if (fm === 'chama') { const up = Math.max(0, .3 - y); x += .09 * up * Math.sin(t * 8 + y * 6); z += .05 * up * Math.cos(t * 6.5 + y * 5); }
      else if (fm === 'espirito' && y > .1) x += .13 * (y - .1) * Math.sin(t * 2.2 - y * 3);
      return [x, y, z, 1];
    }
    function desenhaVoxel(fm, e, t, cx, cy, R, cs, sn, ci, si) {
      const vs = voxForma(fm), lista = [];
      const hal = g.createRadialGradient(cx, cy, R * .15, cx, cy, R * 1.5), ch = V.cor1.map((v) => v | 0).join();
      hal.addColorStop(0, `rgba(${ch},.32)`); hal.addColorStop(.55, `rgba(${ch},.1)`); hal.addColorStop(1, `rgba(${ch},0)`);
      g.globalCompositeOperation = 'lighter'; g.fillStyle = hal; g.fillRect(cx - R * 1.5, cy - R * 1.5, R * 3, R * 3); g.globalCompositeOperation = 'source-over';
      for (const v of vs) {
        const q = voxPos(fm, v, t); if (!q) continue;
        let d = 1 + V.amp * .6 * Math.sin(t * 1.3 + v.f);
        if (e === 'falando') d += V.nivel * .12 * (.5 + .5 * Math.sin(q[1] * 7 - t * 9));
        else if (e === 'ouvindo') d += V.nivel * .15 * (.4 + .6 * Math.abs(Math.sin(v.f * 3 + t * 5)));
        else if (e === 'pensando') d += .06 * Math.sin(q[1] * 9 + t * 7);
        d += V.espalha;
        const x = q[0] * cs - q[2] * sn, z = q[0] * sn + q[2] * cs, y2 = q[1] * ci - z * si, z2 = q[1] * si + z * ci;
        lista.push([x * d, y2 * d, z2 * d, v, q[3]]);
      }
      lista.sort((a, b) => a[2] - b[2]);
      const lado0 = R * vs.cel * .5 * .93;
      for (const [x, y, z, v, sz] of lista) {
        const prof = Math.max(0, Math.min(1, (z + 1.4) / 2.8)), l = lado0 * 2 * (.82 + prof * .32) * sz;
        if (l < 1) continue;
        let px = cx + x * R, py = cy + y * R;
        const mdx = px - MOUSE.x, mdy = py - MOUSE.y, md = Math.hypot(mdx, mdy), alc = R * .55;
        if (md < alc && md > .01) { const f = (1 - md / alc) ** 2 * R * .22; px += mdx / md * f; py += mdy / md * f; }
        const mix = .5 + .5 * Math.sin(v.f + t * .6), luz = (.62 + prof * .55) * v.tom, bri = 34 * prof;
        const c = (i) => Math.min(255, (V.cor1[i] * (1 - mix) + V.cor2[i] * mix) * luz + bri) | 0;
        const r = c(0), gg = c(1), b = c(2);
        g.fillStyle = `rgb(${r},${gg},${b})`; g.fillRect(px - l / 2, py - l / 2, l, l);
        if (l < 5) continue;
        const o = l * .28;
        g.fillStyle = `rgb(${Math.min(255, r * 1.25 + 30) | 0},${Math.min(255, gg * 1.25 + 30) | 0},${Math.min(255, b * 1.25 + 30) | 0})`;
        g.beginPath(); g.moveTo(px - l / 2, py - l / 2); g.lineTo(px - l / 2 + o, py - l / 2 - o); g.lineTo(px + l / 2 + o, py - l / 2 - o); g.lineTo(px + l / 2, py - l / 2); g.fill();
        g.fillStyle = `rgb(${r * .62 | 0},${gg * .62 | 0},${b * .62 | 0})`;
        g.beginPath(); g.moveTo(px + l / 2, py - l / 2); g.lineTo(px + l / 2 + o, py - l / 2 - o); g.lineTo(px + l / 2 + o, py + l / 2 - o); g.lineTo(px + l / 2, py + l / 2); g.fill();
      }
    }
    // enfeites desenhados por cima: olhos do fantasma, raios da entidade elétrica
    function formaEnfeite(fm, cx, cy, R, t, e) {
      const redondo = corpoAtual() === 'luz' || corpoAtual() === 'liso';
      if (fm === 'fantasma') rosto(cx, cy - R * .02, R, t, e, redondo);
      else if (fm === 'chama') rosto(cx, cy + R * .12, R * .82, t, e, redondo);
      else if (fm === 'eletrica') {
        const n = e === 'falando' || e === 'pensando' ? 3 : e === 'dormindo' || e === 'mudo' ? (Math.random() < 0.45 ? 1 : 0) : 2;
        g.globalCompositeOperation = 'lighter'; g.lineWidth = Math.max(1.5, R * 0.018);
        for (let i = 0; i < n; i++) {
          const a = Math.random() * 6.28, r0 = R * 0.7, r1 = R * (1.15 + Math.random() * 0.45);
          g.strokeStyle = `rgba(${V.cor2.map((v) => v | 0)},.85)`; g.beginPath(); g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
          for (let k = 1; k <= 5; k++) { const rr = r0 + (r1 - r0) * k / 5, aa = a + (Math.random() - 0.5) * 0.35; g.lineTo(cx + Math.cos(aa) * rr, cy + Math.sin(aa) * rr); }
          g.stroke();
        }
        g.globalCompositeOperation = 'source-over';
      }
    }
    const V = { cor1: [70, 78, 100], cor2: [40, 44, 58], vel: .15, amp: .04, raio: .8, nivel: 0, rot: 0, espalha: 0 };
    const ALVO = {
      dormindo: { vel: .12, amp: .03, raio: .72, espalha: 0 }, ouvindo: { vel: .35, amp: .04, raio: .78, espalha: .04 },
      pensando: { vel: 1.6, amp: .08, raio: .76, espalha: .02 }, falando: { vel: .5, amp: .05, raio: .8, espalha: 0 },
      trabalhando: { vel: .7, amp: .05, raio: .76, espalha: .03 }, mudo: { vel: .05, amp: .01, raio: .66, espalha: 0 },
    };
    V.olhaX = 0; V.olhaY = 0; V.cx = 0; V.cy = 0; V.R = 0;
    const MOUSE = { x: -9999, y: -9999, nx: 0, ny: 0, dentro: false };
    let tAnt = performance.now(), primeiro = true;
    // o ponteiro em coordenadas do canvas: a página manda a posição; perto do orbe ele vira o rosto e os cubos se afastam
    function ponteiro(px, py, dentro) {
      const b = cv.getBoundingClientRect(), r = cv.width / Math.max(1, b.width);
      if (!dentro || !b.width) { MOUSE.dentro = false; MOUSE.x = MOUSE.y = -9999; return; }
      MOUSE.x = (px - b.left) * r; MOUSE.y = (py - b.top) * r; MOUSE.dentro = true;
      MOUSE.nx = Math.max(-.5, Math.min(.5, (px - b.left) / b.width - .5)); MOUSE.ny = Math.max(-.5, Math.min(.5, (py - b.top) / b.height - .5));
    }
    function quadro(agora) {
      const dt = primeiro ? 1 : Math.min(.05, (agora - tAnt) / 1000); tAnt = agora; primeiro = false;
      const W = cv.width, H = cv.height; if (!W || !H) return;
      const fm = formaAtual(), e = O.estado, alvo = ALVO[e] || ALVO.ouvindo,
        pal = /^#[0-9a-f]{6}$/i.test(O.cor || '') ? paletaDaCor(O.cor, e) : (PALETA_FORMA[fm] || PALETA)[e], k = 1 - Math.pow(.02, dt);
      for (const c of ['vel', 'amp', 'raio', 'espalha']) V[c] += (alvo[c] - V[c]) * k;
      V.espalha += O.explode; O.explode *= Math.pow(.002, dt);
      for (let i = 0; i < 3; i++) { V.cor1[i] += (pal[0][i] - V.cor1[i]) * k; V.cor2[i] += (pal[1][i] - V.cor2[i]) * k; }
      // nível da voz: aqui não há microfone; a fala e a escuta são simuladas
      let nv = 0;
      if (O.nivelFalso && !calmo) {
        const s = agora / 1000;
        if (e === 'falando') nv = Math.max(0, Math.sin(s * 11) * .5 + Math.sin(s * 4.3) * .4 + .25);
        else if (e === 'ouvindo') nv = Math.max(0, Math.sin(s * 2.2) * .25 + .1);
      }
      V.nivel += (nv - V.nivel) * (nv > V.nivel ? .5 : .12);
      V.rot += dt * V.vel * (calmo ? 0 : 1);
      const faixa = false, desvio = { fantasma: -.16, chama: .14 }[fm] || 0, flutua = (fm === 'fantasma' || fm === 'espirito') && !calmo ? Math.sin(agora / 650) * .035 : 0;
      const cx = W * O.x, R = Math.min(W, H) * O.r * V.raio / .8, cy = H * O.y + R * (desvio + flutua);
      V.cx = cx; V.cy = cy; V.R = R;
      g.clearRect(0, 0, W, H);
      if (O.fundo) O.fundo(g, W, H, agora);
      V.olhaX += ((MOUSE.dentro ? MOUSE.nx : 0) - V.olhaX) * .08; V.olhaY += ((MOUSE.dentro ? MOUSE.ny : 0) - V.olhaY) * .08;
      const t = agora / 1000, cs = Math.cos(V.rot + V.olhaX * 1.2), sn = Math.sin(V.rot + V.olhaX * 1.2), inc = .35 + V.olhaY * .9, ci = Math.cos(inc), si = Math.sin(inc);
      const corpo = corpoAtual();
      if (corpo === 'voxel') desenhaVoxel(fm, e, t, cx, cy, R, cs, sn, ci, si);
      const lista = [];
      if (corpo !== 'voxel') for (const p of pts) {
        let d = 1 + V.amp * Math.sin(t * 1.3 * p.s + p.f);
        if (e === 'falando') d += V.nivel * .16 * (.5 + .5 * Math.sin(p.y * 7 - t * 9));     // pulsa com a voz sem estourar de tamanho
        else if (e === 'ouvindo') d += V.nivel * .2 * p.s * (.4 + .6 * Math.abs(Math.sin(p.f * 3 + t * 5)));
        else if (e === 'pensando') d += .09 * Math.sin(p.y * 9 + t * 7);
        else if (e === 'trabalhando') d += .05 * Math.sin(Math.atan2(p.z, p.x) * 4 + t * 3);
        d += V.espalha * p.s;
        if (fm === 'eletrica') d += (Math.random() - .5) * .12 * (1 + V.nivel * 4);      // o corpo treme como faísca
        const [fx, fy, fz] = fm === 'orbe' ? [p.x, p.y, p.z] : formaPonto(fm, p, t);
        let x = fx * cs - fz * sn, z = fx * sn + fz * cs, y = fy;
        const y2 = y * ci - z * si, z2 = y * si + z * ci;
        lista.push([x * d, y2 * d, z2 * d, p]);
      }
      lista.sort((a, b) => a[2] - b[2]);
      const base = Math.max(3, R * .052);
      if (corpo === 'luz') { prepSprites(); g.globalCompositeOperation = 'lighter'; }
      for (const [x, y, z, p] of lista) {
        const prof = (z + 1.4) / 2.8, esc2 = .55 + prof * .75, l = base * esc2 * (.75 + .5 * p.s * .6);
        let px = cx + x * R, py = cy + y * R;
        const mdx = px - MOUSE.x, mdy = py - MOUSE.y, md = Math.hypot(mdx, mdy), alc = R * .55;
        if (md < alc && md > .01) { const f = (1 - md / alc) ** 2 * R * .28; px += mdx / md * f; py += mdy / md * f; }
        const mix = .5 + .5 * Math.sin(p.f + t * .6), luz = .35 + prof * .75;
        if (corpo === 'luz') { const s = l * 2.8; g.globalAlpha = .2 + prof * .42; g.drawImage(SPR[mix < .5 ? 0 : 1], px - s / 2, py - s / 2, s, s); continue; }
        const c = i => Math.min(255, (V.cor1[i] * (1 - mix) + V.cor2[i] * mix) * luz) | 0;
        const r = c(0), gg = c(1), b = c(2);
        g.fillStyle = `rgb(${r},${gg},${b})`;
        if (corpo === 'liso') { g.beginPath(); g.arc(px, py, l * 1.3, 0, 6.2832); g.fill(); continue; }      // bolas grandes que se fundem: superfície lisa
        g.fillRect(px - l / 2, py - l / 2, l, l);               // frente
        if (corpo === 'pixel' || l < 5) continue;               // pixel (e cubos minúsculos): só a frente, bem mais leve
        g.fillStyle = `rgb(${Math.min(255, r * 1.35) | 0},${Math.min(255, gg * 1.35) | 0},${Math.min(255, b * 1.35) | 0})`;
        g.beginPath(); g.moveTo(px - l / 2, py - l / 2); g.lineTo(px - l / 2 + l * .3, py - l / 2 - l * .3);
        g.lineTo(px + l / 2 + l * .3, py - l / 2 - l * .3); g.lineTo(px + l / 2, py - l / 2); g.fill();  // topo
        g.fillStyle = `rgb(${r * .55 | 0},${gg * .55 | 0},${b * .55 | 0})`;
        g.beginPath(); g.moveTo(px + l / 2, py - l / 2); g.lineTo(px + l / 2 + l * .3, py - l / 2 - l * .3);
        g.lineTo(px + l / 2 + l * .3, py + l / 2 - l * .3); g.lineTo(px + l / 2, py + l / 2); g.fill();  // lado
      }
      if (corpo === 'luz') { g.globalAlpha = 1; g.globalCompositeOperation = 'source-over'; }
      if (!faixa) formaEnfeite(fm, cx, cy, R, t, e);
      // anel de nível, em blocos
      const blocos = faixa || !O.anel ? 0 : 48, on = Math.round(V.nivel * blocos);
      for (let i = 0; i < blocos; i++) {
        const a = -Math.PI / 2 + (i / blocos) * Math.PI * 2, rr = R * 1.42, lado = Math.max(3, R * .035);
        g.fillStyle = i < on ? `rgb(${V.cor1.map(v => v | 0)})` : '#ffffff10';
        g.fillRect(cx + Math.cos(a) * rr - lado / 2, cy + Math.sin(a) * rr * .98 - lado / 2, lado, lado);
      }
    }
    // o ponteiro está em cima do orbe (carinho: o rosto sorri)
    function emCima(px, py) { const b = cv.getBoundingClientRect(), r = cv.width / Math.max(1, b.width); return Math.hypot((px - b.left) * r - V.cx, (py - b.top) * r - V.cy) < V.R * 1.15; }
    return { O, V, quadro, ponteiro, emCima };
  }
  window.criaOrbe = criaOrbe;
  window.ORBE_FORMAS = [['orbe', 'Orbe de cubos'], ['fantasma', 'Fantasminha'], ['chama', 'Bola de fogo'], ['eletrica', 'Entidade elétrica'], ['espirito', 'Espírito dourado']];
  window.ORBE_CORPOS = [['voxel', 'Voxel brilhante'], ['cubos', 'Cubos 3D'], ['pixel', 'Pixel leve'], ['luz', 'Luz suave'], ['liso', 'Bolhas macias']];
})();
