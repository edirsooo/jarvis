// Mini mago: o dono do Jarvis em voxel, morando na tela. Dá para pegar, balançar e soltar em cima dos quadros.
// Motor de desenho e de física próprio: caixas em projeção oblíqua, sem imagens.
// Sete classes (roupas), seis temas de tela, a forma do Jarvis (app.js) e o cenário (cenario.js). A escolha fica no servidor (/api/visual),
// que também recebe as poses já desenhadas para a esfera flutuante (mini.py) copiar.
(function () {
  const q = (s) => document.querySelector(s);
  const calmo = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const rnd = (a, b) => a + Math.random() * (b - a);
  const um = (L) => L[(Math.random() * L.length) | 0];
  const lim = (v, a, b) => Math.max(a, Math.min(b, v));
  const F = {
    pega: ['Ei!', 'Uooou!', 'Opa!'], chacoalha: ['Eita!', 'Paraaa!', 'Vou ficar tonto!'], tonto: ['Tudo girando…', 'Fiquei tonto…'],
    quadro: ['Boa vista daqui.', 'Cantinho novo!'], missao: ['Vigio essa missão.', 'Essa está andando.'], palco: ['De volta ao orbe.'], chao: ['Ufa!', 'Pousei!'],
    carinho: ['Hehe!', 'Mais um!'], pronta: ['Missão cumprida!', 'Está feito!', 'Mais uma!'], falhou: ['Essa escapou…', 'Não deu.'],
    acorda: ['Opa, voltei!', 'Cochilei…'], roupa: ['Gostei dessa!', 'Visual novo!', 'Pronto para a aventura.'],
  };
  const ROUPAS = [['torre', 'Mago da torre'], ['grimorio', 'Sábio'], ['cristal', 'Arcanista'], ['rpg', 'Aprendiz'],
    ['cavaleiro', 'Cavaleiro'], ['patrulheiro', 'Patrulheiro'], ['necro', 'Necromante']];
  const TEMAS = [['abismo', 'Abismo', '#c9a35a'], ['classico', 'Clássico', '#ff6b1a'], ['torre', 'Torre', '#c9772b'], ['grimorio', 'Grimório', '#5fa56f'], ['cristal', 'Cristal', '#8f6bff'], ['rpg', 'RPG', '#3f7bff']];
  const V = { roupa: 'torre', tema: 'abismo', tam: 1, mini_sempre: false, forma: 'orbe', cenario: 'ruinas' };

  // ----- desenho voxel: caixas [x, y, z, largura, altura, fundo, cor, flag]; x para a direita, y para cima, z para o fundo -----
  const KX = 0.34, KY = 0.3, tons = {};
  function tom(hex, k) {
    const id = hex + k; if (tons[id]) return tons[id];
    const n = parseInt(hex.slice(1), 16), f = (v) => Math.max(0, Math.min(255, v * k)) | 0;
    return (tons[id] = `rgb(${f((n >> 16) & 255)},${f((n >> 8) & 255)},${f(n & 255)})`);
  }
  function caixa(c, b, u, ox, oy) {
    const x = b[0], y = b[1], z = b[2], w = b[3], h = b[4], d = b[5], cor = b[6];
    const X = (px, pz) => ox + (px + pz * KX) * u, Y = (py, pz) => oy - (py + pz * KY) * u;
    c.lineWidth = 0.6; c.lineJoin = 'round';
    c.fillStyle = c.strokeStyle = tom(cor, 1.2); c.beginPath(); c.moveTo(X(x, z), Y(y + h, z)); c.lineTo(X(x + w, z), Y(y + h, z)); c.lineTo(X(x + w, z + d), Y(y + h, z + d)); c.lineTo(X(x, z + d), Y(y + h, z + d)); c.closePath(); c.fill(); c.stroke();
    c.fillStyle = c.strokeStyle = tom(cor, 0.7); c.beginPath(); c.moveTo(X(x + w, z), Y(y, z)); c.lineTo(X(x + w, z), Y(y + h, z)); c.lineTo(X(x + w, z + d), Y(y + h, z + d)); c.lineTo(X(x + w, z + d), Y(y, z + d)); c.closePath(); c.fill(); c.stroke();
    c.fillStyle = c.strokeStyle = cor; c.beginPath(); c.rect(X(x, z), Y(y + h, z), w * u, h * u); c.fill(); c.stroke();
  }
  function ordena(L) {   // ordem do pintor: quem está atrás, embaixo ou à esquerda é desenhado antes
    const n = L.length, ok = new Array(n).fill(false), out = [], e = 1e-6;
    const antes = (a, b) => a[2] >= b[2] + b[5] - e || a[1] + a[4] <= b[1] + e || a[0] + a[3] <= b[0] + e;
    for (let k = 0; k < n; k++) {
      let pick = -1;
      for (let i = 0; i < n && pick < 0; i++) {
        if (ok[i]) continue; let livre = true;
        for (let j = 0; j < n; j++) { if (j === i || ok[j]) continue; if (antes(L[j], L[i]) && !antes(L[i], L[j])) { livre = false; break; } }
        if (livre) pick = i;
      }
      if (pick < 0) pick = ok.indexOf(false);
      ok[pick] = true; out.push(L[pick]);
    }
    return out;
  }
  function apoio(L) { let g = Infinity; for (const b of L) if (!b[7]) g = Math.min(g, b[1] + b[2] * KY); return g === Infinity ? 0 : g; }
  function mk() { const L = []; let ox = 0, oy = 0, oz = 0; const b = (x, y, z, w, h, d, c, f) => { L.push([x + ox, y + oy, z + oz, w, h, d, c, f || 0]); }; b.em = (x, y, z) => { ox = x || 0; oy = y || 0; oz = z || 0; }; b.L = L; return b; }

  function olhos(b, p, ex, ey, zf, t, cor) {
    for (const s of [-1, 1]) {
      const cx = s * ex;
      if (p.olho === 'fechado') b(cx - t * 0.5, ey + t * 0.36, zf - 0.4, t, t * 0.3, 0.2, cor);
      else if (p.olho === 'feliz') { b(cx - t * 0.5, ey + t * 0.2, zf - 0.4, t * 0.34, t * 0.4, 0.2, cor); b(cx - t * 0.17, ey + t * 0.55, zf - 0.4, t * 0.34, t * 0.34, 0.2, cor); b(cx + t * 0.16, ey + t * 0.2, zf - 0.4, t * 0.34, t * 0.4, 0.2, cor); }
      else if (p.olho === 'tonto') { b(cx - t * 0.5, ey + t * 0.34, zf - 0.4, t, t * 0.32, 0.2, cor); b(cx - t * 0.16, ey, zf - 0.6, t * 0.32, t, 0.2, cor); }
      else {
        const w = t * (p.olho === 'arregalado' ? 1.2 : 1), x0 = cx - w / 2 + p.lx * 0.4, y0 = ey + (t - w) / 2 + p.ly * 0.3;
        b(x0, y0, zf - 0.4, w, w, 0.2, cor); b(x0 + w * 0.55, y0 + w * 0.55, zf - 0.5, w * 0.32, w * 0.32, 0.1, '#ffffff');
      }
    }
  }
  function boca(b, p, y, zf, cor) {
    if (p.boca === 'aberta') b(-0.8, y - 0.5, zf - 0.2, 1.6, 1.1, 0.2, cor);
    else if (p.boca === 'reta') b(-0.7, y, zf - 0.2, 1.4, 0.4, 0.2, cor);
    else { b(-0.9, y, zf - 0.2, 1.8, 0.45, 0.2, cor); b(-1.3, y + 0.4, zf - 0.2, 0.45, 0.45, 0.2, cor); b(0.85, y + 0.4, zf - 0.2, 0.45, 0.45, 0.2, cor); }
  }
  function extras(b, p, topo, t) {
    b.em(0, 0, 0);
    if (p.extra === 'estrelas') for (let i = 0; i < 3; i++) { const a = t * 4 + i * 2.09; b(Math.cos(a) * 4.5 - 0.5, topo + 1.2, 3 + Math.sin(a) * 3, 1, 1, 1, '#ffd84a'); }
    if (p.extra === 'pontos') for (let i = 0; i < 3; i++) b(-2.6 + i * 2.1, topo + 1.4 + Math.max(0, Math.sin(t * 6 - i * 0.9)) * 1.2, 2.5, 1.1, 1.1, 1.1, '#ffffff');
  }

  // ----- as quatro roupas: mesmo mago (moreno, cabelo cacheado, barba), muda o manto, a cabeça e a gema -----
  const PELE = '#b97f56', CABELO = '#2a1c16', BARBA = '#33231b';
  const R = {
    torre:    { cab: 'capuz',  roupa: '#4b2f8f', roupa2: '#38216e', borda: '#ff8a1f', cinto: '#2a1a50', bota: '#3a2a22', gema: '#ff7a1a', gema2: '#ffd27a', pau: '#7a4a26', topo: 21.4 },
    grimorio: { cab: 'chapeu', roupa: '#2f6b45', roupa2: '#234f34', borda: '#e0b040', cinto: '#5a3a1e', bota: '#4a3220', gema: '#ffb02e', gema2: '#fff0a8', pau: '#6a4424', topo: 25.4, estrela: '#e0b040' },
    cristal:  { cab: 'capuz',  roupa: '#1f2a66', roupa2: '#151c48', borda: '#5ad7ff', cinto: '#0f1436', bota: '#20263e', gema: '#b98cff', gema2: '#f0e4ff', pau: '#4a5a8a', topo: 21.4, cristais: '#9a7bff' },
    rpg:      { cab: 'chapeu', roupa: '#2b63d9', roupa2: '#1f49a6', borda: '#ffd23f', cinto: '#7a3a16', bota: '#5a3a22', gema: '#ff5a3a', gema2: '#ffd0a0', pau: '#8a5a30', topo: 25.4, estrela: '#ffd23f' },
    // classes de aventura: mesmo rosto, outro equipamento
    cavaleiro:   { cab: 'elmo',  roupa: '#5a6270', roupa2: '#3c424e', borda: '#c9a35a', cinto: '#3a2618', bota: '#2c2f36', gema: '#cfd6e0', gema2: '#ffffff', pau: '#4a3020', topo: 20.6, arma: 'espada', metal: '#8a93a3', pluma: '#9b2a24' },
    patrulheiro: { cab: 'capuz', roupa: '#2c3b26', roupa2: '#1f2a1b', borda: '#a8794a', cinto: '#4a3020', bota: '#3a2a1c', gema: '#7ddc6a', gema2: '#e4ffd0', pau: '#5a3a1e', topo: 21.4 },
    necro:       { cab: 'capuz', roupa: '#1c1a22', roupa2: '#111017', borda: '#58d68d', cinto: '#0a090d', bota: '#16151b', gema: '#58d68d', gema2: '#d8ffe4', pau: '#d6ccb4', topo: 21.4, cristais: '#58d68d' },
  };
  const LARG = 15, topoDe = (k) => (R[k] || R.torre).topo;
  function mago(p, t, k) {
    const o = R[k] || R.torre, b = mk(), by = (p.senta ? -1 : 0) + Math.max(0, p.bob);
    // pernas e botas (o manto cobre a parte de cima)
    if (p.senta && p.beira) [-3, 0.8].forEach((x) => { b(x, 0, -1.6, 2.2, 2, 3.6, o.roupa2); b(x, -2.4, -1.6, 2.2, 2.4, 1.6, o.roupa2, 1); b(x, -3.3, -2.2, 2.2, 0.9, 2.2, o.bota, 1); });
    else if (p.senta) { b(-3, 0, -1, 2.2, 2, 3, o.roupa2); b(0.8, 0, -1, 2.2, 2, 3, o.roupa2); b(-3, 0, -2, 2.2, 2.4, 1, o.bota); b(0.8, 0, -2, 2.2, 2.4, 1, o.bota); }
    else [[-3, p.pe], [0.8, p.pd]].forEach(([x, l]) => { l = Math.min(1.2, l); b(x, 1 + l, 1, 2.2, 2 - l, 3, o.roupa2); b(x, l, 0.2, 2.2, 1, 3.8, o.bota); });
    b.em(0, by, 0);
    if (!p.senta) { b(-4, 1.6, 0.3, 8, 1.6, 4.6, o.roupa); b(-4, 1.6, 0.1, 8, 0.5, 0.2, o.borda); }      // barra do manto
    b(-3.5, 3, 0.6, 7, 5, 4, o.roupa);
    b(-3.6, 3.7, 0.4, 7.2, 0.8, 0.2, o.cinto); b(-0.7, 3.6, 0.25, 1.4, 1, 0.15, o.borda);                // cinto e fivela
    b(-0.5, 4.7, 0.4, 1, 3.3, 0.2, o.borda);                                                               // faixa da frente
    // braços: 0 = solto, 1 = erguido, 2 = à frente. O cajado vai na mão direita do desenho.
    [[-1, p.be, p.bey], [1, p.bd, p.bdy]].forEach(([s, m, dy]) => {
      const e = Math.abs(dy || 0);
      if (m === 1) { const x = s < 0 ? -5.6 : 4.1; b(x, 6.5, -2.6, 1.5, 3 + e, 1.6, o.roupa); b(x, 9.5 + e, -2.6, 1.5, 1.2, 1.6, PELE); }
      else if (m === 2) { const x = s < 0 ? -5 : 3.5; b(x, 5 + e, -1.6, 1.5, 1.5, 3, o.roupa); b(x, 5 + e, -2.8, 1.5, 1.3, 1.2, PELE); }
      else { const x = s < 0 ? -5 : 3.5; b(x, 4.5 - e, 1.6, 1.5, 3.5, 2.2, o.roupa); b(x, 3.4 - e, 1.6, 1.5, 1.1, 2.2, PELE); }
    });
    if (!p.semCajado) {
      const e = Math.abs(p.bdy || 0), m = p.bd, cx = m === 1 ? 5.7 : m === 2 ? 5.1 : 5.1, cz = m === 1 ? -2.4 : m === 2 ? -3 : 1.9, y0 = (m === 1 ? 4.6 + e : m === 2 ? 1.8 + e : 0.3) - by * (m ? 0 : 1);
      const g = p.brilho > 0.5 ? o.gema2 : o.gema;
      if (o.arma === 'espada') {
        b(cx, y0, cz, 0.8, 3.2, 0.8, o.pau); b(cx - 0.1, y0 - 0.6, cz - 0.1, 1, 0.7, 1, o.borda);                 // cabo e pomo
        b(cx - 1.3, y0 + 3.2, cz - 0.45, 3.4, 0.8, 1.7, o.borda);                                                  // guarda
        b(cx - 0.15, y0 + 4, cz + 0.05, 1.1, 9.6, 0.7, g, p.brilho > 0.5 ? 2 : 0); b(cx + 0.1, y0 + 13.6, cz + 0.15, 0.6, 0.9, 0.5, g, p.brilho > 0.5 ? 2 : 0);   // lâmina
      } else {
        b(cx, y0, cz, 0.8, 14.6, 0.8, o.pau); b(cx - 0.35, y0 + 13.2, cz - 0.35, 1.5, 0.6, 1.5, o.borda);
        b(cx - 0.55, y0 + 14.6, cz - 0.55, 1.9, 1.9, 1.9, g, 2); b(cx - 0.1, y0 + 16.5, cz - 0.1, 1, 0.7, 1, g, 2);
      }
    }
    // cabeça, barba e cabelo cacheado
    b(-5, 8, -0.6, 10, 7.2, 6.6, PELE);
    b(-3.7, 8, -0.85, 7.4, 2.1, 0.25, BARBA); b(-5, 8.6, -0.85, 1.3, 3.4, 0.25, BARBA); b(3.7, 8.6, -0.85, 1.3, 3.4, 0.25, BARBA); b(-1.9, 10, -0.95, 3.8, 0.5, 0.15, BARBA);
    b(-2.2, 7.3, -0.75, 4.4, 0.7, 1.2, BARBA);
    olhos(b, p, 2.4, 10.9, -0.6, 1.5, '#1a120e');
    b(-3.4, 12.75, -0.75, 2, 0.4, 0.15, CABELO); b(1.4, 12.75, -0.75, 2, 0.4, 0.15, CABELO);                // sobrancelhas
    boca(b, p, 8.9, -0.95, '#f3d9c4');
    b(-4.5, 13.7, -1, 2.3, 1.3, 0.5, CABELO); b(-1.9, 14.1, -1, 2.3, 1, 0.5, CABELO); b(0.8, 13.6, -1, 2.1, 1.4, 0.5, CABELO); b(3, 14, -1, 1.6, 1.1, 0.5, CABELO);
    if (o.cab === 'elmo') {
      b(-5.6, 13.4, -1.2, 11.2, 2.8, 7.8, o.metal); b(-4.4, 16.2, -0.4, 8.8, 1.2, 6.2, o.metal);
      b(-6, 8.2, -1, 1.3, 5.4, 7.4, o.metal); b(4.7, 8.2, -1, 1.3, 5.4, 7.4, o.metal); b(-5.4, 8, 5.8, 10.8, 6, 1.4, o.metal);
      b(-5.6, 13.4, -1.4, 11.2, 0.7, 0.2, o.borda); b(-0.5, 10.6, -1.35, 1, 3, 0.3, o.metal);
      b(-0.7, 17.4, 0.6, 1.4, 2.6, 4.6, o.pluma); b(-0.7, 19.6, 3.8, 1.4, 1, 2.4, o.pluma);
      b(-4.6, 7.4, 0.2, 9.2, 1, 5.2, o.metal);                                                                    // gorjal
    } else if (o.cab === 'capuz') {
      b(-5.8, 15.2, -1.4, 11.6, 2.2, 8.2, o.roupa); b(-5.8, 6.5, 6, 11.6, 8.7, 1.8, o.roupa2);
      b(-6.7, 7, -0.2, 1.7, 8.4, 6.4, o.roupa); b(5, 7, -0.2, 1.7, 8.4, 6.4, o.roupa);
      b(-5.8, 15.2, -1.6, 11.6, 0.8, 0.2, o.borda); b(-6.7, 7, -0.4, 0.95, 8.2, 0.2, o.borda); b(5.75, 7, -0.4, 0.95, 8.2, 0.2, o.borda);
      b(-3.6, 17.4, 1.4, 7.2, 1.4, 5.2, o.roupa); b(-1.9, 18.8, 3, 3.8, 1.3, 3.2, o.roupa); b(-0.3, 20.1, 4.6, 1.7, 1.2, 1.6, o.roupa2);
      if (o.cristais) { b(-7.4, 12.5, 1.5, 0.8, 2.4, 1.2, o.cristais); b(6.7, 10.5, 2.4, 0.8, 2, 1.2, o.cristais); b(-0.6, 16.2, -1.75, 1.2, 1.2, 0.2, o.borda); }
    } else {
      b(-6.2, 8.4, 0.6, 1.3, 6.8, 5.2, CABELO); b(4.9, 8.4, 0.6, 1.3, 6.8, 5.2, CABELO); b(-5.4, 8, 6, 10.8, 7.4, 1.3, CABELO);
      b(-7.6, 15.2, -2.6, 15.2, 0.9, 10.6, o.roupa);                                                         // aba
      b(-4.4, 16.1, -0.3, 8.8, 1.2, 6, o.borda);                                                             // fita
      b(-4.2, 17.3, 0, 8.4, 2, 5.6, o.roupa); b(-3, 19.3, 0.8, 6, 1.9, 4.2, o.roupa); b(-1.8, 21.2, 1.8, 3.8, 1.8, 3, o.roupa); b(-0.4, 23, 3, 2, 1.4, 1.8, o.roupa2); b(0.9, 24.2, 3.4, 1.5, 1, 1.4, o.roupa2);
      if (o.estrela) { b(-2.2, 18, -0.15, 1.1, 1.1, 0.15, o.estrela); b(1.3, 19.9, 0.65, 0.9, 0.9, 0.15, o.estrela); b(-0.4, 21.8, 1.65, 0.8, 0.8, 0.15, o.estrela); }
    }
    extras(b, p, o.topo, t);
    if (p.prop) { b.em(0, 0, 0); b(-3.4, 2.1, -3.8, 6.8, 0.6, 3.4, '#6a3a1e', 1); b(-3.1, 2.7, -3.6, 6.2, 0.3, 3, '#f3e6c4', 1); b(-0.15, 2.7, -3.7, 0.3, 0.4, 3.2, o.borda, 1); }   // grimório no colo
    return b.L;
  }

  // ----- estado -----
  const P = { x: 0, y: 0, vx: 0, vy: 0, dir: -1, modo: 'cai', surf: null, tm: 1, alvo: 0, salto: 0, esp: 0, ang: 0, av: 0, tonto: 0, tontoPend: false, festa: 0, solto: false, quiques: 0, corre: false, ultPulo: 0, pulo: null };
  const mouse = { x: 0, y: 0, vx: 0, down: false, t0: 0, hist: [] }, olhar = { x: 0, y: 0 };
  let el, cv, c2, hit, balao, U = 3.4, CW = 0, CH = 0, BASE = 0, dpr = 1, ligado = false, ult = 0, par = false;
  let seg = null, ultTecla = -1e9, ultAcao = performance.now(), lista = [], listaT = 0, missoesAntes = null;
  const alt = () => topoDe(V.roupa) * U, meia = () => LARG * U / 2;
  const estadoJ = () => (typeof S === 'undefined' ? 'dormindo' : S.estado);
  const ativas = () => (typeof S === 'undefined' ? 0 : S.missoes.filter((m) => m.estado === 'trabalhando').length);

  function monta() {
    if (el) return;
    el = document.createElement('div'); el.id = 'mago';
    el.innerHTML = '<canvas class="mago-cv"></canvas><div class="mago-hit" role="img" aria-label="Mini mago" title="Clique: carinho. Segure e arraste: carregar. Botão direito: roupa e tema."></div><div class="mago-fala" hidden></div>';
    q('#app').appendChild(el);
    cv = el.children[0]; c2 = cv.getContext('2d'); hit = el.children[1]; balao = el.children[2];
    eventos();
  }
  function mede() {
    U = 5 * (+V.tam || 1) * (innerHeight < 820 ? 0.8 : 1);
    CW = Math.ceil(34 * U); CH = Math.ceil(38 * U); BASE = Math.ceil(5 * U);
    dpr = Math.min(devicePixelRatio || 1, 2);
    cv.width = CW * dpr; cv.height = CH * dpr;
    cv.style.cssText = `width:${CW}px;height:${CH}px;left:${-CW / 2}px;top:${-(CH - BASE)}px`;
    const hw = LARG * U, hh = alt();
    hit.style.cssText = `left:${-hw / 2}px;top:${-hh}px;width:${hw}px;height:${hh}px`;
  }
  const poe = () => { el.style.transform = `translate(${P.x.toFixed(1)}px,${(P.y - P.salto).toFixed(1)}px)`; };
  function diz(txt, ms) {
    if (!el || !ligado) return;
    balao.textContent = txt; balao.hidden = false;
    balao.style.bottom = (alt() + 12) + 'px'; balao.style.marginLeft = (lim(P.x, 90, innerWidth - 90) - P.x) + 'px';
    balao.classList.remove('on'); void balao.offsetWidth; balao.classList.add('on');
    clearTimeout(diz.t); diz.t = setTimeout(() => { balao.hidden = true; }, ms || 2200);
  }
  function festa(s) { if (!ligado) return; P.festa = Math.max(P.festa, s); if (P.modo === 'dorme' || P.modo === 'anda') P.modo = 'parado'; ultAcao = performance.now(); }

  // ----- onde ele pisa: dentro do palco (ao lado do orbe), em cima dos quadros e no chão (borda de cima do rodapé) -----
  const SEL = '#lado .bloco, #grade .missao, #palco, #trilho';
  function piso() { const b = q('footer'), r = b && b.getBoundingClientRect(); return (r && r.height > 0 ? r.top : innerHeight) - 2; }
  function faixaDe(e, k, l, d) {   // o chão do palco inteiro é dele (um clique leva a qualquer ponto)
    if (e && e.id === 'palco' && k === 'dentro') return [l + 6, d - 6];
    return [l, d];
  }
  function passeio(s, l, r) {      // passeando sozinho com o palco largo, fica no terço da esquerda, para não parar em cima da legenda
    if (s.el && s.el.id === 'palco' && !q('#app').classList.contains('trabalho') && r - l > 420) return [l, l + (r - l) * 0.3];
    return [l, r];
  }
  // clique em ponto livre da tela = destino. Dentro de um quadro, é o topo dele; dentro do palco, o chão do palco; senão, a superfície logo abaixo.
  function destino(ir) {
    const L = superficies(), m = meia();
    let o = L.find((c) => { if (!c.el) return false; const r = c.el.getBoundingClientRect(); return ir.x >= r.left && ir.x <= r.right && ir.y >= r.top - 12 && ir.y <= r.bottom; });
    if (!o) for (const c of L) if (ir.x >= c.l && ir.x <= c.r && c.y >= ir.y - 10 && (!o || c.y < o.y)) o = c;
    if (!o) o = L[L.length - 1];
    let a = o.l + m * 0.6, b = o.r - m * 0.6; if (b < a) a = b = (o.l + o.r) / 2;
    return { o, x: lim(ir.x, a, b) };
  }
  function vai(x, y) {
    if (!ligado || (seg && seg.ativo)) return;
    P.ir = { x, y, t: performance.now() }; ultAcao = P.ir.t;
    if (P.modo === 'dorme' || P.modo === 'senta') { P.modo = 'parado'; P.tm = 0.2; }
  }
  function superficies() {
    const out = [], ch = piso(), a = alt();
    if (q('#painel') && !q('#painel').hidden) { const r = q('#painel').getBoundingClientRect(); out.push({ el: q('#painel'), k: 'topo', l: r.left, r: r.right, y: r.top }); }
    else if (['#galeria', '#processos', '#conversas'].some((s) => q(s) && !q(s).hidden)) { /* outra aba aberta: só o chão */ }
    else document.querySelectorAll(SEL).forEach((e) => {
      const r = e.getBoundingClientRect(); if (r.width < 44 || r.height < 12) return;
      if (e.id !== 'palco' && r.top > 70 && r.top < ch - 6) out.push({ el: e, k: 'topo', l: r.left, r: r.right, y: r.top });
      const y2 = r.bottom - 3;
      if (e.id === 'palco' && r.height > a + 30 && y2 < ch) { const [l, d] = faixaDe(e, 'dentro', r.left + 4, r.right - 4); out.push({ el: e, k: 'dentro', l, r: d, y: y2 }); }
    });
    out.push({ el: null, k: 'chao', l: 0, r: innerWidth, y: ch });
    return out;
  }
  const mesma = (a, b) => !!a && !!b && a.el === b.el && a.k === b.k;
  function atualiza(s) {
    if (s.k === 'chao') { s.y = piso(); s.l = 0; s.r = innerWidth; return true; }
    if (!s.el.isConnected || s.el.hidden) return false;
    const r = s.el.getBoundingClientRect(); if (!r.width) return false;
    if (s.k === 'topo') { s.y = r.top; s.l = r.left; s.r = r.right; } else { s.y = r.bottom - 3; [s.l, s.r] = faixaDe(s.el, 'dentro', r.left + 4, r.right - 4); }
    return s.y < piso() + 1;
  }
  function reage(s) {
    const e = s.el; let f = F.chao;
    if (e) f = e.id === 'palco' ? F.palco : e.matches('.missao') ? F.missao : F.quadro;
    diz(um(f)); if (typeof SONS !== 'undefined') SONS.clique();
  }
  function pousa(s, quieto) {
    P.surf = s; P.y = s.y; P.vx = P.vy = 0; P.modo = 'parado'; P.tm = rnd(1.4, 3); P.esp = quieto ? 0.25 : 0.45; P.quiques = 0; P.pulo = null;
    el.classList.remove('pego');
    if (P.tontoPend) { P.tonto = 3.4; P.tontoPend = false; diz(um(F.tonto)); }
    else if (P.solto) reage(s);
    P.solto = false;
  }
  function cai(dt) {
    const m = meia(), y0 = P.y;
    P.vy += 2300 * dt; P.x += P.vx * dt; P.y += P.vy * dt;
    if (P.x < m) { P.x = m; P.vx = Math.abs(P.vx) * 0.5; } else if (P.x > innerWidth - m) { P.x = innerWidth - m; P.vx = -Math.abs(P.vx) * 0.5; }
    if (P.vy < 0 && P.y < alt()) { P.y = alt(); P.vy = Math.abs(P.vy) * 0.4; }
    if (P.vy <= 0) return;
    const now = performance.now(); if (now - listaT > 120) { lista = superficies(); listaT = now; }
    let s = null; for (const o of lista) if (P.x >= o.l - 2 && P.x <= o.r + 2 && y0 <= o.y + 1 && P.y >= o.y && (!s || o.y < s.y)) s = o;
    if (!s) { if (P.y > piso()) s = { el: null, k: 'chao', l: 0, r: innerWidth, y: piso() }; else return; }
    P.y = s.y;
    if (P.vy > 560 && P.quiques < 2) { P.vy = -P.vy * 0.32; P.vx *= 0.6; P.quiques++; P.esp = 0.4; }
    else pousa(s);
  }
  function pula(o, x1) {
    const d = Math.hypot(x1 - P.x, o.y - P.y);
    P.pulo = { x0: P.x, y0: P.y, x1, o, t: 0, T: lim(d / 620, 0.38, 0.85), h: 46 + Math.max(0, P.y - o.y) * 0.3 };
    P.modo = 'pulo'; P.surf = null; P.ultPulo = performance.now(); if (Math.abs(x1 - P.x) > 4) P.dir = x1 > P.x ? 1 : -1; P.esp = 0.3;
  }
  function voa(dt) {
    const j = P.pulo; if (!j || !atualiza(j.o)) { P.modo = 'cai'; P.vx = P.vy = 0; return; }
    j.t += dt; const k = Math.min(1, j.t / j.T);
    P.x = j.x0 + (lim(j.x1, j.o.l + 4, j.o.r - 4) - j.x0) * k; P.y = j.y0 + (j.o.y - j.y0) * k - 4 * j.h * k * (1 - k);
    if (k >= 1) pousa(j.o, true);
  }
  function sobCursor() { let s = null; for (const o of superficies()) if (mouse.x >= o.l && mouse.x <= o.r && o.y >= mouse.y - 10 && (!s || o.y < s.y)) s = o; return s; }
  function ocupado() { return estadoJ() !== 'dormindo' || ativas() > 0; }
  function pensa(dt, now) {
    let s = P.surf; const m = meia();
    if (!s || !atualiza(s)) {
      const n = superficies().find((o) => o.k !== 'chao' && Math.abs(o.y - P.y) < 8 && P.x >= o.l && P.x <= o.r);
      if (n) s = P.surf = n; else { P.surf = null; P.modo = 'cai'; P.vx = P.vy = 0; return; }
    }
    P.y = s.y;
    let l = s.l + m * 0.6, r = s.r - m * 0.6; if (r < l) l = r = (s.l + s.r) / 2;
    if (P.x < s.l - 24 || P.x > s.r + 24) { P.surf = null; P.modo = 'cai'; P.vx = P.vy = 0; return; }
    P.x = lim(P.x, l, r); P.corre = false;
    if (P.tonto > 0) { P.tonto -= dt; return; }
    if (P.festa > 0 || now - ultTecla < 1600) { if (P.modo === 'anda' || P.modo === 'dorme') P.modo = 'parado'; return; }
    if (mouse.down && now - mouse.t0 > 280 && !calmo) {   // botão segurado em outro lugar: ele corre atrás do cursor
      const dx = mouse.x - P.x; P.modo = 'parado'; P.tm = 1.5;
      if (Math.abs(dx) > 14) { P.dir = dx > 0 ? 1 : -1; const nx = lim(P.x + P.dir * 230 * dt, l, r); P.corre = Math.abs(nx - P.x) > 0.1; P.x = nx; }
      if (now - P.ultPulo > 900 && now - mouse.t0 > 620) { const o = sobCursor(); if (o && !mesma(o, s)) pula(o, lim(mouse.x, o.l + m * 0.6, o.r - m * 0.6)); }
      return;
    }
    if (P.ir) {   // foi mandado para um ponto: anda (perto) ou corre (longe); se o ponto é em outra superfície, vai até a beira e pula
      const d = now - P.ir.t < 8000 ? destino(P.ir) : null;
      if (!d) P.ir = null;
      else {
        const igual = mesma(d.o, s), x = lim(d.x, l, r), dx = x - P.x;
        if (Math.abs(dx) < 4) {
          if (igual) { P.ir = null; P.modo = 'parado'; P.tm = rnd(2, 4); P.viraEm = now + 1800; }
          else if (now - P.ultPulo > 250) pula(d.o, d.x);
        } else {
          const longe = !igual || Math.abs(dx) > 150;
          P.dir = dx > 0 ? 1 : -1; P.modo = 'anda'; P.corre = longe;
          P.x = lim(P.x + P.dir * (longe ? 260 : 115) * dt, Math.min(P.x, x), Math.max(P.x, x));
        }
        return;
      }
    }
    if (P.modo === 'anda') {
      const dx = P.alvo - P.x;
      if (Math.abs(dx) < 3) { P.modo = 'parado'; P.tm = rnd(1.5, 5); } else { P.dir = dx > 0 ? 1 : -1; P.x = lim(P.x + P.dir * 46 * dt, l, r); if (P.x === l || P.x === r) P.alvo = P.x; }
      return;
    }
    if (P.modo === 'dorme') { if (now - ultAcao < 1500 || ocupado()) { P.modo = 'parado'; P.tm = rnd(2, 4); if (!ocupado()) diz(um(F.acorda)); } return; }
    P.tm -= dt; if (P.tm > 0) return;
    const [pl, pr] = passeio(s, l, r);
    if (ocupado()) { P.modo = 'parado'; P.tm = rnd(3, 6); if (Math.random() < 0.3 && r - l > 30 && estadoJ() === 'dormindo') { P.modo = 'anda'; P.alvo = rnd(pl, pr); } return; }   // trabalhando: fica de olho no orbe
    if (now - ultAcao > 90000) { P.modo = 'dorme'; return; }
    if (calmo) { P.modo = 'parado'; P.tm = 5; return; }
    const z = Math.random();
    if (z < 0.5 && r - l > 30) { P.modo = 'anda'; P.alvo = rnd(pl, pr); }
    else if (z < 0.68) { P.modo = 'senta'; P.tm = rnd(4, 9); }
    else if (z < 0.78 && now - P.ultPulo > 9000) {
      const L = superficies().filter((o) => !mesma(o, s) && o.r - o.l > m * 2.5 && Math.abs((o.l + o.r) / 2 - P.x) < 700);
      if (L.length) { const o = um(L); pula(o, rnd(o.l + m, o.r - m)); } else { P.modo = 'parado'; P.tm = 2; }
    } else { P.modo = 'parado'; P.tm = rnd(2, 5); }
  }

  // ----- pegar, balançar, chacoalhar e soltar -----
  function segura(dt) {
    const tx = mouse.x, ty = mouse.y + alt() * 0.82, k = Math.min(1, dt * 24);
    P.x += (tx - P.x) * k; P.y += (ty - P.y) * k;
    const alvo = lim(-mouse.vx * 0.0011, -1.1, 1.1);
    P.av += ((alvo - P.ang) * 70 - P.av * 5) * dt; P.ang += P.av * dt;
    mouse.vx *= Math.exp(-dt * 8);
  }
  function ativa() { seg.ativo = true; P.surf = null; P.modo = 'parado'; P.tonto = 0; P.festa = 0; el.classList.add('pego'); if (Math.random() < 0.5) diz(um(F.pega), 1200); }
  function carinho() { P.festa = Math.max(P.festa, 0.9); if (typeof SONS !== 'undefined') SONS.clique(); if (Math.random() < 0.6) diz(um(F.carinho)); }
  function larga(semJogar) {
    if (!seg) return; const s = seg; seg = null;
    try { hit.releasePointerCapture(s.id); } catch (_) {}
    if (!s.ativo) { if (!semJogar && performance.now() - s.t0 < 450) carinho(); return; }
    let vx = 0, vy = 0; const h = mouse.hist, now = performance.now(), a = h.find((p) => now - p.t < 110), b = h[h.length - 1];
    if (!semJogar && a && b && b.t - a.t > 8) { vx = (b.x - a.x) / (b.t - a.t) * 1000; vy = (b.y - a.y) / (b.t - a.t) * 1000; }
    P.vx = lim(vx, -1600, 1600); P.vy = lim(vy, -1600, 1600); P.modo = 'cai'; P.surf = null; P.solto = true; P.quiques = 0; lista = []; listaT = 0;
  }
  function eventos() {
    hit.addEventListener('pointerdown', (e) => {
      if (e.button === 2 || seg) return;
      e.preventDefault(); e.stopPropagation(); try { hit.setPointerCapture(e.pointerId); } catch (_) {}
      const now = performance.now(); ultAcao = now;
      mouse.x = e.clientX; mouse.y = e.clientY; mouse.vx = 0; mouse.hist = [{ x: e.clientX, y: e.clientY, t: now }];
      seg = { id: e.pointerId, x0: e.clientX, y0: e.clientY, t0: now, ativo: false, sinal: 0, viradas: [] };
    });
    hit.addEventListener('pointermove', (e) => {
      if (!seg || e.pointerId !== seg.id) return;
      const now = performance.now(), u = mouse.hist[mouse.hist.length - 1], dtm = Math.max(1, now - u.t), vx = (e.clientX - u.x) / dtm * 1000;
      mouse.x = e.clientX; mouse.y = e.clientY; mouse.vx = mouse.vx * 0.5 + vx * 0.5;
      mouse.hist.push({ x: e.clientX, y: e.clientY, t: now }); if (mouse.hist.length > 12) mouse.hist.shift();
      if (!seg.ativo && Math.hypot(e.clientX - seg.x0, e.clientY - seg.y0) > 6) ativa();
      if (seg.ativo && Math.abs(vx) > 650 && Math.sign(vx) !== seg.sinal) {
        seg.sinal = Math.sign(vx); seg.viradas.push(now); seg.viradas = seg.viradas.filter((t) => now - t < 1400);
        if (seg.viradas.length >= 6 && !P.tontoPend) { P.tontoPend = true; diz(um(F.chacoalha), 1500); }
      }
    });
    hit.addEventListener('pointerup', () => larga(false));
    hit.addEventListener('pointercancel', () => larga(true));
    hit.addEventListener('click', (e) => e.stopPropagation());
    hit.addEventListener('contextmenu', (e) => { e.preventDefault(); e.stopPropagation(); larga(true); menu(true); });
    // ponto livre = fora de botão, campo, cartão clicável e do próprio orbe (clicar no orbe acorda o Jarvis)
    const OCUPADO = 'button,input,textarea,select,a,label,#visual,#painel,#galeria,#processos,#conversas,#procJanela,.m-tela,.ult,.tri,.aviso,.mago-hit';
    const noOrbe = (e) => { const o = typeof orbeTela === 'function' ? orbeTela() : null; return !!o && !!e.target.closest('#palco') && Math.hypot(e.clientX - o.x, e.clientY - o.y) <= o.r; };
    document.addEventListener('pointerdown', (e) => { ultAcao = performance.now(); if (e.target === hit || e.button !== 0 || e.target.closest(OCUPADO) || noOrbe(e)) return; mouse.down = true; mouse.t0 = ultAcao; mouse.x = e.clientX; mouse.y = e.clientY; }, true);
    document.addEventListener('pointermove', (e) => { if (!seg) { mouse.x = e.clientX; mouse.y = e.clientY; } }, true);
    const sobe = (e) => { if (mouse.down && e && e.type === 'pointerup') vai(e.clientX, e.clientY); mouse.down = false; };   // soltou: é para lá que ele vai
    document.addEventListener('pointerup', sobe, true); document.addEventListener('pointercancel', sobe, true); addEventListener('blur', sobe);
    document.addEventListener('keydown', (e) => { const t = e.target; ultAcao = performance.now(); if (t && t.id === 'campo' && (e.key.length === 1 || e.key === 'Backspace')) ultTecla = ultAcao; }, true);
    addEventListener('resize', () => { if (ligado) { mede(); P.x = lim(P.x, meia(), innerWidth - meia()); listaT = 0; } });
  }

  // ----- poses -----
  function anim(now) {
    if (seg && seg.ativo) return 'pendurado';
    if (P.modo === 'cai' || P.modo === 'pulo') return 'cai';
    if (P.tonto > 0) return 'tonto';
    if (P.festa > 0) return 'festa';
    if (P.corre) return 'corre';
    if (P.modo === 'anda') return 'anda';
    const e = estadoJ();
    if (e === 'pensando') return 'pensa';
    if (e === 'ouvindo') return 'ouve';
    if (e === 'falando') return 'conjura';
    if (now - ultTecla < 1600) return 'le';
    if (ativas() > 0) return 'conjura';
    if (P.modo === 'dorme') return 'dorme';
    return P.modo === 'senta' ? 'senta' : 'parado';
  }
  function pose(a, t) {
    const p = { bob: 0, pe: 0, pd: 0, be: 0, bd: 0, bey: 0, bdy: 0, olho: 'aberto', lx: olhar.x, ly: olhar.y, boca: 'sorriso', senta: false, prop: false, extra: '', incl: 0, brilho: 0, semCajado: false, beira: !!(P.surf && P.surf.k === 'topo') };
    const s = Math.sin, pisca = (t % 3.7) < 0.14, bal = (s(t * 2.2) + 1) / 2;
    if (pisca) p.olho = 'fechado';
    if (a === 'parado') { p.bob = bal * 0.25; }
    else if (a === 'anda' || a === 'corre') { const c = t * (a === 'corre' ? 17 : 9); p.pe = Math.max(0, s(c)) * 1.1; p.pd = Math.max(0, -s(c)) * 1.1; p.bob = Math.abs(s(c)) * 0.4; p.bey = Math.max(0, s(c)) * 0.6; p.lx = -0.7; p.ly = 0; if (a === 'corre') p.boca = 'aberta'; }
    else if (a === 'senta') { p.senta = true; p.bob = bal * 0.15; }
    else if (a === 'le') { p.senta = true; p.prop = true; p.be = 2; p.semCajado = true; p.bd = 2; p.lx = s(t * 3) * 0.4; p.ly = -1; p.bob = Math.abs(s(t * 6)) * 0.08; }
    else if (a === 'festa') { p.be = p.bd = 1; p.bey = p.bdy = Math.abs(s(t * 8)) * 0.8; p.olho = 'feliz'; p.boca = 'aberta'; p.brilho = 1; }
    else if (a === 'conjura') { p.bd = 1; p.bdy = (s(t * 3) + 1) * 0.35; p.brilho = (s(t * 7) + 1) / 2; p.bob = bal * 0.2; p.boca = 'reta'; }
    else if (a === 'ouve') { p.be = 2; p.bey = 0.3; p.bob = bal * 0.15; p.boca = 'reta'; p.brilho = 0.3; }
    else if (a === 'pensa') { p.be = 2; p.boca = 'reta'; p.extra = 'pontos'; p.bob = bal * 0.2; p.brilho = (s(t * 12) + 1) / 2; }
    else if (a === 'dorme') { p.senta = true; p.olho = 'fechado'; p.boca = 'reta'; p.bob = (s(t * 1.3) + 1) * 0.12; p.extra = 'zzz'; }
    else if (a === 'pendurado') { p.be = p.bd = 1; p.pe = -0.8 + s(t * 6) * 0.3; p.pd = -0.8 - s(t * 6) * 0.3; p.olho = P.tontoPend ? 'tonto' : 'arregalado'; p.boca = 'aberta'; }
    else if (a === 'cai') { p.be = p.bd = 1; p.pe = p.pd = -0.4; p.olho = P.tontoPend ? 'tonto' : 'arregalado'; p.boca = 'aberta'; }
    else if (a === 'tonto') { p.senta = true; p.olho = 'tonto'; p.boca = 'reta'; p.extra = 'estrelas'; p.incl = s(t * 4) * 0.12; }
    return p;
  }
  function brilho(c, L, u, ox, oy, forca) {   // halo da gema do cajado
    const g = L.find((b) => b[7] === 2); if (!g || forca <= 0.02) return;
    const x = ox + (g[0] + g[3] / 2 + (g[2] + g[5] / 2) * KX) * u, y = oy - (g[1] + g[4] / 2 + (g[2] + g[5] / 2) * KY) * u, r = u * (3 + forca * 4);
    const gr = c.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, tom(g[6], 1.2).replace('rgb', 'rgba').replace(')', `,${(0.5 * forca + 0.2).toFixed(2)})`)); gr.addColorStop(1, 'rgba(0,0,0,0)');
    c.save(); c.globalCompositeOperation = 'lighter'; c.fillStyle = gr; c.beginPath(); c.arc(x, y, r, 0, 6.3); c.fill(); c.restore();
  }
  function desenha(a, t) {
    const p = pose(a, t), L = ordena(mago(p, t, V.roupa)), chao = CH - BASE, oy = chao + apoio(L) * U, ox = CW / 2 - 3.5 * KX * U, pend = seg && seg.ativo;
    c2.setTransform(dpr, 0, 0, dpr, 0, 0); c2.clearRect(0, 0, CW, CH);
    if (P.surf && !P.salto) { c2.fillStyle = 'rgba(0,0,0,.35)'; c2.beginPath(); c2.ellipse(CW / 2, chao - U * 0.15, LARG * U * 0.45, U * 0.55, 0, 0, 6.3); c2.fill(); }
    for (const b of L) caixa(c2, b, U, ox, oy);
    brilho(c2, L, U, ox, oy, p.brilho);
    if (p.extra === 'zzz') {
      c2.save(); if (P.dir > 0) { c2.translate(CW, 0); c2.scale(-1, 1); }
      c2.font = `700 ${(U * 3.4).toFixed(1)}px monospace`; c2.fillStyle = '#9db4ff';
      for (let i = 0; i < 3; i++) { const k = (t * 0.45 + i / 3) % 1; c2.globalAlpha = 1 - k; c2.fillText('z', CW / 2 + U * (4 + k * 5), oy - alt() * 0.8 - k * U * 6); }
      c2.restore();
    }
    const e = P.esp, sx = (1 + e * 0.5) * -P.dir, sy = 1 - e * 0.45;   // o desenho base olha para a esquerda
    cv.style.transformOrigin = `50% ${pend ? CH - BASE - alt() * 0.85 : CH - BASE}px`;
    cv.style.transform = `rotate(${(P.ang + (pend ? 0 : p.incl)).toFixed(3)}rad) scale(${sx.toFixed(3)},${sy.toFixed(3)})`;
  }
  function orbe() {
    if (typeof orbeTela === 'function') { const o = orbeTela(); if (o) return o; }
    const e = q('#esfera'); if (!e) return null; const r = e.getBoundingClientRect(); return r.width ? { x: r.left + r.width / 2, y: r.top + r.height * 0.4 } : null;
  }
  function quadro(now) {
    requestAnimationFrame(quadro);
    if (!document.hasFocus() && now - ult < 1000 / 15 - 3) return;      // janela atrás de outra: 15 quadros por segundo
    const dt = Math.min(0.05, (now - ult) / 1000 || 0); ult = now;
    if (document.hidden || !ligado) return;
    // nas abas de lista (entregas, processos, conversas) ele sai de cena, para não ficar em cima do que se lê
    const fora = ['#galeria', '#processos', '#conversas'].some((s) => q(s) && !q(s).hidden);
    if (fora !== (el.style.display === 'none')) { el.style.display = fora ? 'none' : ''; if (!fora) { P.ir = null; mouse.down = false; } }
    if (fora) return;
    if (seg && !seg.ativo && now - seg.t0 > 220) ativa();
    if (seg && seg.ativo) segura(dt);
    else {
      if (P.modo === 'cai') cai(dt); else if (P.modo === 'pulo') voa(dt); else if (!seg) pensa(dt, now);
      P.ang += (0 - P.ang) * Math.min(1, dt * 9); P.av = 0;
    }
    if (P.festa > 0) P.festa -= dt;
    P.esp += (0 - P.esp) * Math.min(1, dt * 9);
    // olha para o orbe quando o Jarvis está acordado ou trabalhando; senão, para o mouse
    const o = ocupado() ? orbe() : null, ax = o ? o.x : mouse.x, ay = o ? o.y : mouse.y;
    // só vira para o orbe parado de verdade: nunca no meio de uma ida, com o botão segurado ou logo depois de chegar
    if (o && P.modo !== 'anda' && !P.corre && !P.ir && !mouse.down && now > (P.viraEm || 0) && Math.abs(o.x - P.x) > 30 && !(seg && seg.ativo)) P.dir = o.x > P.x ? 1 : -1;
    olhar.x += (lim((ax - P.x) / 240, -1, 1) * -P.dir - olhar.x) * 0.2; olhar.y += (lim((P.y - alt() * 0.6 - ay) / 240, -1, 1) - olhar.y) * 0.2;
    const a = anim(now), t = now / 1000;
    P.salto = a === 'festa' && P.surf ? Math.abs(Math.sin(t * 8)) * 5 * U : 0;
    poe();
    par = !par; if (par || a === 'pendurado' || a === 'cai') desenha(a, t);
    // missão que terminou: comemora ou lamenta (uma vez)
    if (typeof S !== 'undefined') {
      const agora = {}; S.missoes.forEach((m) => { agora[m.n] = m.estado; });
      if (missoesAntes) for (const n in agora) if (missoesAntes[n] === 'trabalhando' && agora[n] !== 'trabalhando') {
        if (agora[n] === 'concluida') { festa(2.4); diz(um(F.pronta), 2600); } else if (agora[n] === 'erro') { P.tonto = 1.6; diz(um(F.falhou)); }
      }
      missoesAntes = agora;
    }
  }

  // ----- roupa, tema e as poses que a esfera flutuante copia -----
  function retrato(c, k) {
    const x = c.getContext('2d'), u = c.width / 30, p = pose('parado', 1); p.lx = p.ly = 0; p.olho = 'aberto'; p.beira = false;
    x.clearRect(0, 0, c.width, c.height);
    const L = ordena(mago(p, 1, k));
    for (const b of L) caixa(x, b, u, c.width / 2 - 3.5 * KX * u - u, c.height - u * 2.4 + apoio(L) * u);
  }
  function poses() {   // listas de caixas já na ordem de desenho, para o mini.py
    const guarda = { x: olhar.x, y: olhar.y, s: P.surf }; olhar.x = olhar.y = 0; P.surf = null;
    const f = (a, ts) => ts.map((t) => { const p = pose(a, t); if (a !== 'dorme') p.olho = p.olho === 'fechado' ? 'aberto' : p.olho; const L = ordena(mago(p, t, V.roupa)); return { ap: +apoio(L).toFixed(2), br: +p.brilho.toFixed(2), cx: L.map((b) => [+b[0].toFixed(2), +b[1].toFixed(2), +b[2].toFixed(2), +b[3].toFixed(2), +b[4].toFixed(2), +b[5].toFixed(2), b[6], b[7]]) }; });
    const out = { topo: topoDe(V.roupa), larg: LARG, parado: f('parado', [1, 1.7]), conjura: f('conjura', [0.3, 0.52, 0.75, 1.05]), ouve: f('ouve', [1, 1.7]), pensa: f('pensa', [0.2, 0.46, 0.72, 0.98]), festa: f('festa', [0.1, 0.2, 0.3, 0.39]), dorme: f('dorme', [1, 2.2]) };
    olhar.x = guarda.x; olhar.y = guarda.y; P.surf = guarda.s;
    return out;
  }
  function tema() { const a = q('#app'); a.dataset.tema = V.tema; a.dataset.forma = V.forma; a.dataset.cenario = V.cenario; }
  function grava(extra) {
    fetch('/api/visual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({ roupa: V.roupa, tema: V.tema, tam: V.tam, mini_sempre: !!V.mini_sempre, forma: V.forma, cenario: V.cenario, poses: poses() }, extra || {})) }).catch(() => {});
  }
  function aplica(v, deFora) {
    if (v.roupa && R[v.roupa]) V.roupa = v.roupa;
    if (v.tema && TEMAS.some((x) => x[0] === v.tema)) V.tema = v.tema;
    if (v.tam) V.tam = +v.tam || 1;
    if ('mini_sempre' in v) V.mini_sempre = !!v.mini_sempre;
    if (v.forma && (window.FORMAS || []).some((x) => x[0] === v.forma)) V.forma = v.forma;
    if (v.cenario && (window.CENARIOS || []).some((x) => x[0] === v.cenario)) V.cenario = v.cenario;
    tema(); if (el) mede();
    if (!deFora) grava();
    marca();
  }
  function marca() {
    document.querySelectorAll('#visual [data-roupa]').forEach((b) => b.classList.toggle('on', b.dataset.roupa === V.roupa));
    document.querySelectorAll('#visual [data-tema]').forEach((b) => b.classList.toggle('on', b.dataset.tema === V.tema));
    document.querySelectorAll('#visual [data-forma]').forEach((b) => b.classList.toggle('on', b.dataset.forma === V.forma));
    document.querySelectorAll('#visual [data-cenario]').forEach((b) => b.classList.toggle('on', b.dataset.cenario === V.cenario));
    document.querySelectorAll('#visual [data-tam]').forEach((b) => b.classList.toggle('on', +b.dataset.tam === +V.tam));
    document.querySelectorAll('#visual [data-mini]').forEach((b) => b.classList.toggle('on', (b.dataset.mini === '1') === !!V.mini_sempre));
  }
  function menu(abre) {
    let m = q('#visual');
    if (!m) {
      m = document.createElement('div'); m.id = 'visual'; m.hidden = true;
      const ICONE = { orbe: '#8a90a8', fantasma: '#cfe6f2', chama: '#ff8a3a', eletrica: '#7ab8ff', espirito: '#e8c46a', ruinas: 'linear-gradient(#151426,#4a3a36)', masmorra: 'linear-gradient(#2a221d,#5a1e14)', floresta: 'linear-gradient(#071613,#1a3a30)', torre: 'linear-gradient(#1a1430,#3a2a6a)', nenhum: 'transparent' };
      m.innerHTML = `<div class="vis-cab"><b>Aparência</b><span>Escolhas guardadas para a próxima vez</span></div>
        <h2>FORMA DO JARVIS</h2><div class="vis-temas">${(window.FORMAS || []).map(([k, n]) => `<button data-forma="${k}"><i class="amostra" style="background:${ICONE[k] || '#888'}"></i>${n}</button>`).join('')}</div>
        <h2>CENÁRIO</h2><div class="vis-temas">${(window.CENARIOS || []).map(([k, n]) => `<button data-cenario="${k}"><i class="amostra" style="background:${ICONE[k] || '#888'}"></i>${n}</button>`).join('')}</div>
        <h2>CLASSE DO MAGO</h2><div class="vis-roupas">${ROUPAS.map(([k, n]) => `<button data-roupa="${k}"><canvas width="120" height="132"></canvas><span>${n}</span></button>`).join('')}</div>
        <h2>TEMA DA TELA</h2><div class="vis-temas">${TEMAS.map(([k, n, c]) => `<button data-tema="${k}"><i style="background:${c}"></i>${n}</button>`).join('')}</div>
        <h2>TAMANHO</h2><div class="vis-temas">${[[0.8, 'Pequeno'], [1, 'Médio'], [1.35, 'Grande']].map(([v, n]) => `<button data-tam="${v}">${n}</button>`).join('')}</div>
        <h2>ESFERA FLUTUANTE</h2><div class="vis-temas"><button data-mini="0">Some com o painel aberto</button><button data-mini="1">Sempre por cima (fica em dobro)</button></div>
        <small>Clique em qualquer ponto livre da tela e ele vai até lá (pula sozinho para cima dos quadros). Clique nele para um carinho. Segure e arraste para carregar. Segure o botão em outro lugar e ele corre atrás do cursor.</small>`;
      q('#app').appendChild(m);
      m.querySelectorAll('canvas').forEach((c) => retrato(c, c.parentNode.dataset.roupa));
      m.addEventListener('click', (e) => {
        const b = e.target.closest('button'); if (!b) return;
        if (b.dataset.roupa) { aplica({ roupa: b.dataset.roupa }); festa(1); diz(um(F.roupa)); }
        else if (b.dataset.tema) aplica({ tema: b.dataset.tema });
        else if (b.dataset.forma) aplica({ forma: b.dataset.forma });
        else if (b.dataset.cenario) aplica({ cenario: b.dataset.cenario });
        else if (b.dataset.tam) aplica({ tam: +b.dataset.tam });
        else if (b.dataset.mini) aplica({ mini_sempre: b.dataset.mini === '1' });
      });
      document.addEventListener('pointerdown', (e) => { if (!m.hidden && !e.target.closest('#visual,#btVisual,.mago-hit')) m.hidden = true; }, true);
      addEventListener('keydown', (e) => { if (e.key === 'Escape') m.hidden = true; });
    }
    m.hidden = abre === true ? false : !m.hidden; marca();
  }

  function liga() {
    monta(); mede(); tema();
    const p = q('#palco').getBoundingClientRect();
    ligado = true; P.x = p.left + Math.min(150, p.width * 0.2); P.y = Math.max(alt() + 10, p.top + 40); P.vx = P.vy = 0; P.modo = 'cai'; P.surf = null; P.dir = 1;
    ult = performance.now(); ultAcao = ult; requestAnimationFrame(quadro);
  }
  const bt = q('#btVisual'); if (bt) bt.onclick = () => menu();
  window.MAGO = { aplica, diz, festa, estado: P, poses, menu, vai };
  tema(); liga();
  fetch('/api/visual').then((r) => r.json()).then((v) => { aplica(v, true); grava(); }).catch(() => {});
})();
