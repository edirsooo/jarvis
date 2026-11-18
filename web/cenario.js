// Cenários voxel do palco: o fundo é pintado uma vez (duas camadas: longe e perto) e, a cada quadro, só entram a luz
// do Jarvis (que tinge o ambiente com a cor do estado dele), as tochas, a neblina e poucas partículas.
// Para criar um cenário novo: uma entrada em CENAS com o céu, a função que pinta as camadas, as tochas e as partículas.
(function () {
  const palco = document.getElementById('palco'), app = document.getElementById('app');
  if (!palco) return;
  const cv = document.createElement('canvas'); cv.id = 'cenario'; cv.setAttribute('aria-hidden', 'true'); palco.prepend(cv);
  const g = cv.getContext('2d');
  const calmo = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let W = 0, H = 0, dpr = 1, longe = null, perto = null, chave = '', parts = [], tAnt = 0, folga = 0;
  const mouse = { x: 0, alvo: 0 };

  // ----- utilidades -----
  function semente(s) { return () => ((s = (s * 16807) % 2147483647) / 2147483647); }
  function tom(hex, k) {
    const n = parseInt(hex.slice(1), 16), f = (v) => Math.max(0, Math.min(255, v * k)) | 0;
    return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`;
  }
  // um bloco voxel: frente, faixa de topo mais clara e lado mais escuro
  function bloco(c, x, y, w, h, cor, luz = 1) {
    c.fillStyle = tom(cor, luz); c.fillRect(x, y, w, h);
    const t = Math.max(1, Math.min(w, h) * 0.2);
    c.fillStyle = tom(cor, luz * 1.28); c.fillRect(x, y, w, t);
    c.fillStyle = tom(cor, luz * 0.62); c.fillRect(x + w - t, y + t, t, h - t);
  }
  function ceu(c, w, h, cores) {
    const gr = c.createLinearGradient(0, 0, 0, h);
    cores.forEach((cor, i) => gr.addColorStop(i / (cores.length - 1), cor));
    c.fillStyle = gr; c.fillRect(0, 0, w, h);
  }
  function estrelas(c, w, h, r, n, ate) {
    for (let i = 0; i < n; i++) { const s = r() < 0.15 ? 2 : 1; c.fillStyle = `rgba(230,225,255,${0.25 + r() * 0.6})`; c.fillRect(r() * w | 0, r() * h * ate | 0, s * dpr, s * dpr); }
  }
  function lua(c, x, y, raio, u, cor) {
    const hl = c.createRadialGradient(x, y, raio * 0.6, x, y, raio * 3.2);
    hl.addColorStop(0, 'rgba(240,226,190,.22)'); hl.addColorStop(1, 'rgba(240,226,190,0)');
    c.fillStyle = hl; c.fillRect(x - raio * 3.2, y - raio * 3.2, raio * 6.4, raio * 6.4);
    const r = semente(3), crateras = [[0.3, -0.2, 0.22], [-0.35, 0.25, 0.16], [0.1, 0.45, 0.12], [-0.15, -0.45, 0.1]];
    for (let i = -raio; i < raio; i += u) for (let j = -raio; j < raio; j += u)
      if (i * i + j * j < raio * raio) {
        let k = 0.93 + r() * 0.05 - (i + j) / raio * 0.06;             // luz vem de cima à esquerda
        for (const [cx, cy, cr] of crateras) if ((i / raio - cx) ** 2 + (j / raio - cy) ** 2 < cr * cr) k -= 0.12;
        c.fillStyle = tom(cor, k); c.fillRect(Math.round(x + i), Math.round(y + j), Math.ceil(u), Math.ceil(u));
      }
  }
  // serra de blocos: montanha, mata ou muralha ao longe
  function serra(c, w, base, alt, passo, r, cor, suave) {
    let hAt = alt * 0.5;
    for (let x = -passo; x < w + passo; x += passo) {
      hAt = Math.max(alt * 0.15, Math.min(alt, hAt + (r() - 0.5) * alt * (suave || 0.35)));
      c.fillStyle = cor; c.fillRect(x, base - hAt, passo + 1, hAt + 2);
      c.fillStyle = 'rgba(255,255,255,.035)'; c.fillRect(x, base - hAt, passo + 1, Math.max(1, passo * 0.25));
    }
  }
  function pinheiro(c, x, base, alt, u, cor) {
    c.fillStyle = cor; c.fillRect(x - u * 0.5, base - alt * 0.25, u, alt * 0.25);
    const camadas = Math.max(3, alt / (u * 2) | 0);
    for (let i = 0; i < camadas; i++) { const k = 1 - i / camadas, lw = alt * 0.42 * k + u; c.fillRect(x - lw / 2, base - alt * 0.22 - (i + 1) * (alt * 0.78 / camadas), lw, alt * 0.78 / camadas + 1); }
  }
  function tijolos(c, w, h, u, cores, r) {
    const bw = u * 6, bh = u * 3;
    for (let y = 0, lin = 0; y < h; y += bh, lin++)
      for (let x = (lin % 2) * -bw / 2; x < w; x += bw) { c.fillStyle = cores[(r() * cores.length) | 0]; c.fillRect(x + 1, y + 1, bw - 2, bh - 2); c.fillStyle = 'rgba(255,255,255,.04)'; c.fillRect(x + 1, y + 1, bw - 2, Math.max(1, u * 0.5)); }
  }
  function chao(c, w, h, topo, u, a, b, borda) {
    const lado = u * 4;
    for (let x = 0, i = 0; x < w; x += lado, i++) for (let y = topo, j = 0; y < h; y += lado, j++) bloco(c, x, y, lado, lado, (i + j) % 2 ? a : b, 1 - j * 0.12);
    c.fillStyle = borda; c.fillRect(0, topo, w, Math.max(2, u * 0.5));
  }
  function pilar(c, x, base, alt, u, cor, quebrado, r) {
    const lw = u * 5;
    for (let y = base, i = 0; y > base - alt; y -= u * 3, i++) bloco(c, x + (r() - 0.5) * u * 0.4, y - u * 3, lw, u * 3, cor, 0.85 + r() * 0.2);
    if (!quebrado) bloco(c, x - u, base - alt - u * 2, lw + u * 2, u * 2, cor, 1.1);
    c.fillStyle = 'rgba(70,110,60,.55)'; for (let i = 0; i < 5; i++) c.fillRect(x + r() * lw, base - r() * alt, u, u);   // musgo
  }

  // ----- os cenários -----
  const CENAS = {
    ruinas: {
      nome: 'Ruínas ao luar',
      longe(c, w, h, u, r) {
        ceu(c, w, h, ['#07080f', '#151426', '#2b2235', '#4a3a36']);
        estrelas(c, w, h, r, 140, 0.55);
        lua(c, w * 0.8, h * 0.2, h * 0.075, Math.max(2, u * 0.7), '#e9e0c6');
        serra(c, w, h * 0.74, h * 0.2, u * 3, r, '#1d1b2a', 0.4);
        // castelo ao longe, com janelas acesas
        const cx = w * 0.62, base = h * 0.74;
        [[0, 0.2, 0.05], [0.06, 0.13, 0.08], [0.15, 0.26, 0.04], [0.2, 0.15, 0.07], [-0.05, 0.12, 0.05]].forEach(([dx, hh, ww]) => {
          const x = cx + dx * w, tw = ww * w, th = hh * h; c.fillStyle = '#14121d'; c.fillRect(x, base - th, tw, th);
          for (let i = 0; i < tw; i += u * 2) if ((i / (u * 2) | 0) % 2 === 0) c.fillRect(x + i, base - th - u * 1.4, u * 1.4, u * 1.4);
          for (let k = 0; k < 2; k++) if (r() > 0.35) { c.fillStyle = r() > 0.5 ? '#c98a3c' : '#8a5a2a'; c.fillRect(x + tw * (0.3 + r() * 0.4), base - th * (0.3 + r() * 0.5), u * 0.9, u * 1.4); c.fillStyle = '#14121d'; }
        });
        // o farol de runas: um obelisco com luz no topo
        const ox = w * 0.24, oy = h * 0.74, oh = h * 0.34;
        c.fillStyle = '#191724'; c.fillRect(ox - u * 1.2, oy - oh, u * 2.4, oh);
        const fl = c.createRadialGradient(ox, oy - oh, 0, ox, oy - oh, h * 0.16);
        fl.addColorStop(0, 'rgba(255,205,120,.55)'); fl.addColorStop(1, 'rgba(255,205,120,0)');
        c.fillStyle = fl; c.fillRect(ox - h * 0.16, oy - oh - h * 0.16, h * 0.32, h * 0.32);
        c.fillStyle = '#ffd890'; c.fillRect(ox - u * 0.8, oy - oh - u * 1.6, u * 1.6, u * 1.6);
        serra(c, w, h * 0.86, h * 0.1, u * 2, r, '#121019', 0.5);
      },
      perto(c, w, h, u, r) {
        pilar(c, w * 0.04, h * 0.9, h * 0.42, u, '#3d3a48', false, r);
        pilar(c, w * 0.9, h * 0.9, h * 0.3, u, '#3d3a48', true, r);
        chao(c, w, h, h * 0.9, u, '#2c2833', '#25222c', '#4a4256');
        c.fillStyle = '#2f4a2c'; for (let i = 0; i < 26; i++) { const x = r() * w; c.fillRect(x, h * 0.9 - u, u * 0.8, u); c.fillRect(x + u, h * 0.9 - u * 1.6, u * 0.8, u * 1.6); }
      },
      tochas: [[0.04 + 0.022, 0.48 - 0.035, 1], [0.9 + 0.022, 0.6 - 0.035, 1]],
      neblina: 'rgba(170,160,200,.05)', parte: { tipo: 'graca', n: 30 },
    },
    masmorra: {
      nome: 'Masmorra',
      longe(c, w, h, u, r) {
        c.fillStyle = '#0d0a09'; c.fillRect(0, 0, w, h);
        tijolos(c, w, h, u, ['#241d19', '#2a221d', '#1f1915', '#2e2520'], r);
        // portal ao fundo, em degraus
        const pw = w * 0.22, px = w / 2 - pw / 2, pt = h * 0.18;
        c.fillStyle = '#060404';
        for (let i = 0; i < 6; i++) { const enc = (6 - i) * u * 1.6; c.fillRect(px + enc * (i < 3 ? 1 : 0.3), pt + i * u * 1.5, pw - enc * 2 * (i < 3 ? 1 : 0.3), u * 1.6); }
        c.fillRect(px, pt + 9 * u, pw, h);
        const fundo = c.createRadialGradient(w / 2, h * 0.75, 0, w / 2, h * 0.75, pw); fundo.addColorStop(0, 'rgba(90,40,120,.25)'); fundo.addColorStop(1, 'rgba(90,40,120,0)');
        c.fillStyle = fundo; c.fillRect(px, pt, pw, h);
        // estandartes
        [[0.3, '#5a1e14'], [0.7, '#5a1e14']].forEach(([fx, cor]) => {
          const x = w * fx - u * 3, y = h * 0.12, bw = u * 6, bh = h * 0.34;
          c.fillStyle = '#3a2a1a'; c.fillRect(x - u, y - u, bw + u * 2, u);
          bloco(c, x, y, bw, bh, cor, 0.9);
          c.fillStyle = cor; c.fillRect(x, y + bh, u * 2, u * 2); c.fillRect(x + bw - u * 2, y + bh, u * 2, u * 2);
          c.fillStyle = '#c9a35a'; const mx = x + bw / 2, my = y + bh * 0.42;
          for (let k = -3; k <= 3; k++) { const larg = (3 - Math.abs(k)) * u * 0.7 + u * 0.6; c.fillRect(mx - larg / 2, my + k * u * 0.8, larg, u * 0.8); }   // losango
          c.fillStyle = cor; c.fillRect(mx - u * 0.4, my - u * 0.4, u * 0.8, u * 0.8);
        });
      },
      perto(c, w, h, u, r) {
        chao(c, w, h, h * 0.88, u, '#3a322c', '#2e2723', '#5a4a3c');
        c.fillStyle = '#1a1412'; c.fillRect(0, 0, w, u * 2); c.fillRect(0, 0, u * 2, h); c.fillRect(w - u * 2, 0, u * 2, h);
      },
      tochas: [[0.16, 0.42, 1], [0.84, 0.42, 1]],
      parte: { tipo: 'brasa', n: 34 },
    },
    floresta: {
      nome: 'Floresta sombria',
      longe(c, w, h, u, r) {
        ceu(c, w, h, ['#03080a', '#071613', '#0f2620', '#1a3a30']);
        estrelas(c, w, h, r, 60, 0.4);
        lua(c, w * 0.2, h * 0.16, h * 0.045, Math.max(2, u * 0.6), '#cfe8dc');
        [['#10261f', 0.8, 0.5], ['#0c1d18', 0.86, 0.62], ['#08140f', 0.92, 0.78]].forEach(([cor, base, alt]) => {
          for (let x = -u * 4; x < w + u * 4; x += u * (5 + r() * 6)) pinheiro(c, x, h * base, h * alt * (0.55 + r() * 0.45), u, cor);
        });
      },
      perto(c, w, h, u, r) {
        chao(c, w, h, h * 0.9, u, '#1b2e1f', '#16261a', '#2c4a2e');
        for (let i = 0; i < 9; i++) { const x = r() * w; c.fillStyle = '#d9e6dc'; c.fillRect(x, h * 0.9 - u * 1.2, u * 0.6, u * 1.2); c.fillStyle = r() > 0.5 ? '#5ad7c4' : '#9a7bff'; c.fillRect(x - u * 0.6, h * 0.9 - u * 1.9, u * 1.8, u * 0.8); }
      },
      tochas: [], neblina: 'rgba(120,200,170,.05)', parte: { tipo: 'vagalume', n: 34 },
    },
    torre: {
      nome: 'Torre arcana',
      longe(c, w, h, u, r) {
        c.fillStyle = '#100c1e'; c.fillRect(0, 0, w, h);
        tijolos(c, w, h, u, ['#1a1430', '#1e1738', '#16112a', '#211a3e'], r);
        // janela em arco com o céu
        const jw = w * 0.2, jx = w / 2 - jw / 2, jt = h * 0.08, jh = h * 0.5;
        c.save(); c.beginPath();
        for (let i = 0; i < 5; i++) { const enc = (5 - i) * u * 1.4; c.rect(jx + enc, jt + i * u * 1.4, jw - enc * 2, u * 1.5); }
        c.rect(jx, jt + 7 * u, jw, jh - 7 * u); c.clip();
        ceu(c, w, h, ['#0a0820', '#22184a', '#3a2a6a']); estrelas(c, w, h, r, 90, 0.7); c.restore();
        c.fillStyle = '#2a2050'; c.fillRect(w / 2 - u * 0.5, jt + 6 * u, u, jh - 6 * u); c.fillRect(jx, jt + jh * 0.55, jw, u);
        // estantes com livros
        [[0.03, 0.2], [0.79, 0.2]].forEach(([fx, fw]) => {
          const x = w * fx, ew = w * fw * 0.9;
          for (let y = h * 0.14; y < h * 0.8; y += u * 7) {
            bloco(c, x, y + u * 6, ew, u, '#3a2618');
            for (let bx = x + u * 0.5; bx < x + ew - u; bx += u * (1.1 + r() * 0.8)) { const bh = u * (3.5 + r() * 2); c.fillStyle = ['#5a2a3a', '#2a4a5a', '#5a4a2a', '#3a2a5a', '#2a5a3a'][(r() * 5) | 0]; c.fillRect(bx, y + u * 6 - bh, u, bh); }
          }
        });
      },
      perto(c, w, h, u, r) {
        const topo = h * 0.89, lado = u * 3;
        for (let y = topo, j = 0; y < h; y += lado, j++) for (let x = (j % 2) * -lado * 2; x < w; x += lado * 4) bloco(c, x, y, lado * 4, lado, '#3a2636', 1 - j * 0.1);
        c.fillStyle = '#6a4a7a'; c.fillRect(0, topo, w, Math.max(2, u * 0.5));
      },
      tochas: [[0.3, 0.8, 0.55], [0.7, 0.8, 0.55]], parte: { tipo: 'runa', n: 16 },
    },
    nenhum: { nome: 'Sem cenário' },
  };
  window.CENARIOS = Object.entries(CENAS).map(([k, v]) => [k, v.nome]);

  // ----- partículas -----
  function nova(tipo, inicio) {
    const p = { tipo, x: Math.random() * W, y: inicio ? Math.random() * H : H * (0.75 + Math.random() * 0.2), v: 0, vida: Math.random(), fase: Math.random() * 6.28 };
    const cena = CENAS[chave] || {};
    if (tipo === 'brasa' && cena.tochas && cena.tochas.length) { const t = cena.tochas[(Math.random() * cena.tochas.length) | 0]; p.x = t[0] * W; p.y = t[1] * H - 10 * dpr; }
    p.v = { graca: 0.12, brasa: 0.55, vagalume: 0.05, runa: 0.18 }[tipo] * (0.6 + Math.random() * 0.8) * dpr * 60;
    return p;
  }
  const RUNAS = [[1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 1, 0, 1, 1, 1, 0, 1, 0], [1, 1, 0, 0, 1, 0, 0, 1, 1], [1, 0, 0, 1, 1, 1, 0, 0, 1]];
  function desenhaParte(p, dt, t) {
    p.vida += dt * 0.12;
    const u = Math.max(2, H / 260);
    if (p.tipo === 'vagalume') {
      p.x += Math.sin(t * 0.7 + p.fase) * dt * 14 * dpr; p.y += Math.cos(t * 0.5 + p.fase * 1.3) * dt * 9 * dpr;
      const a = Math.max(0, Math.sin(t * 1.7 + p.fase * 3)); g.fillStyle = `rgba(210,255,140,${a * 0.9})`; g.fillRect(p.x, p.y, u, u);
      if (a > 0.6) { g.fillStyle = `rgba(210,255,140,${(a - 0.6) * 0.35})`; g.fillRect(p.x - u, p.y - u, u * 3, u * 3); }
      if (p.vida > 1.2) Object.assign(p, nova(p.tipo, true), { vida: 0 });
      return;
    }
    p.y -= p.v * dt; p.x += Math.sin(t + p.fase) * dt * 8 * dpr;
    const a = Math.min(1, p.vida * 3) * Math.max(0, 1 - p.vida);
    if (p.tipo === 'graca') { g.fillStyle = `rgba(255,214,140,${a * 0.75})`; g.fillRect(p.x, p.y, u * 0.9, u * 0.9); }
    else if (p.tipo === 'brasa') { g.fillStyle = `rgba(255,${120 + (p.fase * 20 | 0)},40,${a})`; g.fillRect(p.x, p.y, u * 0.8, u * 0.8); }
    else if (p.tipo === 'runa') {
      const m = RUNAS[(p.fase * 10 | 0) % RUNAS.length], s = u * 0.7;
      g.fillStyle = `rgba(170,140,255,${a * 0.7})`;
      for (let i = 0; i < 9; i++) if (m[i]) g.fillRect(p.x + (i % 3) * s, p.y + ((i / 3) | 0) * s, s, s);
    }
    if (p.vida > 1 || p.y < -20) Object.assign(p, nova(p.tipo, false), { vida: 0 });
  }

  // ----- montagem e quadro -----
  function monta() {
    const b = palco.getBoundingClientRect();
    dpr = devicePixelRatio || 1; W = Math.max(1, b.width * dpr | 0); H = Math.max(1, b.height * dpr | 0);
    cv.width = W; cv.height = H; folga = 12 * dpr;
    const cena = CENAS[chave];
    longe = perto = null; parts = [];
    if (!cena || !cena.longe) return;
    const u = Math.max(2, H / 120);
    longe = document.createElement('canvas'); longe.width = W + folga * 2; longe.height = H;
    const cl = longe.getContext('2d'); cl.translate(folga, 0); cena.longe(cl, W, H, u, semente(7));
    perto = document.createElement('canvas'); perto.width = W; perto.height = H;
    cena.perto(perto.getContext('2d'), W, H, u, semente(11));
    if (cena.parte) for (let i = 0; i < cena.parte.n; i++) parts.push(nova(cena.parte.tipo, true));
  }
  function tocha(x, y, t, k, i) {
    const u = Math.max(2, H / 95) * k, fl = 0.85 + 0.15 * Math.sin(t * 13 + i * 2) * Math.sin(t * 7.3 + i);
    const luz = g.createRadialGradient(x, y, 0, x, y, H * 0.22 * k * fl);
    luz.addColorStop(0, 'rgba(255,170,70,.32)'); luz.addColorStop(0.4, 'rgba(255,120,40,.12)'); luz.addColorStop(1, 'rgba(255,120,40,0)');
    g.globalCompositeOperation = 'lighter'; g.fillStyle = luz; g.fillRect(x - H * 0.3, y - H * 0.3, H * 0.6, H * 0.6); g.globalCompositeOperation = 'source-over';
    bloco(g, x - u * 0.8, y + u * 0.6, u * 1.6, u * 3.2, '#4a3220');          // cabo
    bloco(g, x - u * 1.3, y, u * 2.6, u * 0.9, '#5a4a3a');                    // suporte
    const chamas = [[0, -1.6, 1.6, '#ff7a1a'], [-0.35, -2.6, 1.2, '#ffb02e'], [0.25, -3.4, 0.8, '#ffe08a']];
    chamas.forEach(([dx, dy, s, cor], j) => {
      const ox = Math.sin(t * 9 + i + j) * u * 0.25, oy = Math.sin(t * 11 + j * 2 + i) * u * 0.2;
      g.fillStyle = cor; g.fillRect(x + (dx - s / 2) * u + ox, y + dy * u * fl + oy, s * u, s * u);
    });
  }
  function quadro(agora) {
    requestAnimationFrame(quadro);
    const alvo = calmo ? 1 : !document.hasFocus() ? 12 : 30;
    if (agora - tAnt < 1000 / alvo - 3) return;
    const dt = Math.min(0.1, (agora - tAnt) / 1000); tAnt = agora;
    const nomeAgora = app.dataset.cenario || 'ruinas';
    const b = palco.getBoundingClientRect();
    if (nomeAgora !== chave || Math.abs(b.width * (devicePixelRatio || 1) - W) > 2 || Math.abs(b.height * (devicePixelRatio || 1) - H) > 2) { chave = nomeAgora; monta(); }
    const cena = CENAS[chave] || {}, t = agora / 1000;
    g.clearRect(0, 0, W, H);
    if (!longe) return;
    mouse.x += (mouse.alvo - mouse.x) * 0.06;
    g.drawImage(longe, -folga - mouse.x * folga, 0);
    // a luz do Jarvis tinge o cenário com a cor do estado dele
    if (typeof V !== 'undefined' && V.R && V.cor1) {
      const [r, gg, bb] = V.cor1.map((v) => v | 0), raio = V.R * 3.4;
      const luz = g.createRadialGradient(V.cx, V.cy, V.R * 0.3, V.cx, V.cy, raio);
      luz.addColorStop(0, `rgba(${r},${gg},${bb},.30)`); luz.addColorStop(1, `rgba(${r},${gg},${bb},0)`);
      g.globalCompositeOperation = 'lighter'; g.fillStyle = luz; g.fillRect(V.cx - raio, V.cy - raio, raio * 2, raio * 2); g.globalCompositeOperation = 'source-over';
    }
    if (cena.neblina) {
      g.fillStyle = cena.neblina;
      for (let i = 0; i < 3; i++) { const y = H * (0.62 + i * 0.09), x = ((t * (8 + i * 5) * dpr) % (W * 1.5)) - W * 0.5; g.fillRect(x, y, W * 0.9, H * 0.06); g.fillRect(x - W * 1.5, y, W * 0.9, H * 0.06); }
    }
    g.drawImage(perto, 0, 0);
    (cena.tochas || []).forEach(([fx, fy, k], i) => tocha(fx * W, fy * H, t, k, i));
    for (const p of parts) desenhaParte(p, dt, t);
    // vinheta: escurece as bordas e dá profundidade
    const vin = g.createRadialGradient(W / 2, H * 0.45, Math.min(W, H) * 0.35, W / 2, H * 0.45, Math.max(W, H) * 0.75);
    vin.addColorStop(0, 'rgba(0,0,0,0)'); vin.addColorStop(1, 'rgba(0,0,0,.55)'); g.fillStyle = vin; g.fillRect(0, 0, W, H);
  }
  palco.addEventListener('pointermove', (e) => { const b = palco.getBoundingClientRect(); mouse.alvo = (e.clientX - b.left) / b.width - 0.5; });
  palco.addEventListener('pointerleave', () => { mouse.alvo = 0; });
  requestAnimationFrame(quadro);
})();
