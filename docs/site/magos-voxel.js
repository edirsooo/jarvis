// Magos do Jarvis para o site: porte do desenho voxel do app (web/mago.js: caixa, ordena, mago, pose, brilho, as sete
// classes em R e o personagem em PERS_OP). Gerado a partir do app; só o desenho. Quem anda e reage na página é site/magos.js.
(function () {
  const olhar = { x: 0, y: 0 }, P = { surf: null, tontoPend: false };
  const V = { pers: null };   // o personagem de cada desenho (o site passa um visual por mascote)
  const ROUPAS = [['torre', 'Mago da torre'], ['grimorio', 'Sábio'], ['cristal', 'Arcanista'], ['rpg', 'Aprendiz'],
    ['cavaleiro', 'Cavaleiro'], ['patrulheiro', 'Patrulheiro'], ['necro', 'Necromante']];
  const PERS0 = { tipo: 'm', pele: '#c68a5e', cabelo: 'longo', cor_cabelo: '#3b2416', barba: 'nenhuma', roupa_cor: '' };
  const PERS_OP = {
    tipo: [['h', 'Homem'], ['m', 'Mulher']],
    pele: [['#f2d0b4', 'Clara'], ['#e0aa82', 'Morena clara'], ['#c68a5e', 'Morena'], ['#b97f56', 'Parda'], ['#8d5a3b', 'Negra'], ['#5e3a26', 'Retinta']],
    cabelo: [['curto', 'Curto'], ['cacheado', 'Cacheado'], ['longo', 'Longo'], ['raspado', 'Raspado']],
    cor_cabelo: [['#1a1210', 'Preto'], ['#3b2416', 'Castanho'], ['#7a4a26', 'Castanho claro'], ['#c98a3a', 'Loiro'], ['#a8401e', 'Ruivo'], ['#c9c4bc', 'Grisalho']],
    barba: [['nenhuma', 'Sem barba'], ['curta', 'Curta'], ['cheia', 'Cheia']],
  };
  const pers = () => Object.assign({}, PERS0, V.pers || {});
  const hexK = (hex, k) => '#' + [16, 8, 0].map((s) => (Math.max(0, Math.min(255, ((parseInt(hex.slice(1), 16) >> s) & 255) * k)) | 0).toString(16).padStart(2, '0')).join('');

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
    const pz = pers(), PELE = pz.pele, CABELO = pz.cor_cabelo, BARBA = pz.cor_cabelo, b = mk(), by = (p.senta ? -1 : 0) + Math.max(0, p.bob);
    let o = R[k] || R.torre;
    if (/^#[0-9a-f]{6}$/i.test(pz.roupa_cor || '')) o = Object.assign({}, o, { roupa: pz.roupa_cor, roupa2: hexK(pz.roupa_cor, 0.74) });
    // pernas e botas (o manto cobre a parte de cima)
    if (p.senta && p.beira) [-3, 0.8].forEach((x) => { b(x, 0, -1.6, 2.2, 2, 3.6, o.roupa2); b(x, -2.4, -1.6, 2.2, 2.4, 1.6, o.roupa2, 1); b(x, -3.3, -2.2, 2.2, 0.9, 2.2, o.bota, 1); });
    else if (p.senta) { b(-3, 0, -1, 2.2, 2, 3, o.roupa2); b(0.8, 0, -1, 2.2, 2, 3, o.roupa2); b(-3, 0, -2, 2.2, 2.4, 1, o.bota); b(0.8, 0, -2, 2.2, 2.4, 1, o.bota); }
    else [[-3, p.pe], [0.8, p.pd]].forEach(([x, l]) => { l = Math.min(1.2, l); b(x, 1 + l, 1, 2.2, 2 - l, 3, o.roupa2); b(x, l, 0.2, 2.2, 1, 3.8, o.bota); });
    b.em(0, by, 0);
    if (!p.senta) { b(-4, 1.6, 0.3, 8, 1.6, 4.6, o.roupa); b(-4, 1.6, 0.1, 8, 0.5, 0.2, o.borda); }      // barra do manto
    if (pz.tipo === 'm' && !p.senta) { b(-4.7, 0.9, -0.1, 9.4, 1.2, 5.4, o.roupa); b(-4.7, 0.9, -0.3, 9.4, 0.45, 0.2, o.borda); }   // vestido: barra mais rodada
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
    // cabeça, barba (cheia, curta ou sem) e cabelo do personagem
    b(-5, 8, -0.6, 10, 7.2, 6.6, PELE);
    if (pz.barba === 'cheia') { b(-3.7, 8, -0.85, 7.4, 2.1, 0.25, BARBA); b(-5, 8.6, -0.85, 1.3, 3.4, 0.25, BARBA); b(3.7, 8.6, -0.85, 1.3, 3.4, 0.25, BARBA); }
    if (pz.barba !== 'nenhuma') { b(-1.9, 10, -0.95, 3.8, 0.5, 0.15, BARBA); b(-2.2, 7.3, -0.75, 4.4, 0.7, 1.2, BARBA); }
    olhos(b, p, 2.4, 10.9, -0.6, 1.5, '#1a120e');
    if (pz.tipo === 'm' && p.olho !== 'fechado') [-1, 1].forEach((s) => b(s * 3.15 - 0.3, 12.15, -1.15, 0.6, 0.55, 0.2, '#1a120e'));   // cílios
    if (pz.tipo === 'm') [-1, 1].forEach((s) => b(s * 3.4 - 0.65, 9.55, -0.9, 1.3, 0.55, 0.15, '#e8848c'));   // bochechas
    b(-3.4, 12.75, -0.75, 2, 0.4, 0.15, CABELO); b(1.4, 12.75, -0.75, 2, 0.4, 0.15, CABELO);                // sobrancelhas
    boca(b, p, 8.9, -0.95, pz.barba === 'cheia' ? '#f3d9c4' : pz.tipo === 'm' ? '#b8435a' : hexK(PELE, 0.55));
    if (pz.cabelo === 'cacheado') { b(-4.5, 13.7, -1, 2.3, 1.3, 0.5, CABELO); b(-1.9, 14.1, -1, 2.3, 1, 0.5, CABELO); b(0.8, 13.6, -1, 2.1, 1.4, 0.5, CABELO); b(3, 14, -1, 1.6, 1.1, 0.5, CABELO); }
    else if (pz.cabelo === 'curto') b(-4.8, 13.9, -1, 9.6, 1.1, 0.5, CABELO);
    else if (pz.cabelo === 'longo') { b(-4.8, 13.9, -1, 4.3, 1.1, 0.5, CABELO); b(0.5, 13.9, -1, 4.3, 1.1, 0.5, CABELO); b(-5.5, 7.2, -1, 1.3, 6.8, 0.5, CABELO); b(4.2, 7.2, -1, 1.3, 6.8, 0.5, CABELO); }   // franja repartida e mechas dos lados do rosto
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
      if (pz.cabelo === 'longo') { b(-6.2, 4.6, 0.6, 1.3, 10.6, 5.2, CABELO); b(4.9, 4.6, 0.6, 1.3, 10.6, 5.2, CABELO); b(-5.4, 4.4, 6, 10.8, 11, 1.3, CABELO); }
      else if (pz.cabelo !== 'raspado') { b(-6.2, 8.4, 0.6, 1.3, 6.8, 5.2, CABELO); b(4.9, 8.4, 0.6, 1.3, 6.8, 5.2, CABELO); b(-5.4, 8, 6, 10.8, 7.4, 1.3, CABELO); }
      b(-7.6, 15.2, -2.6, 15.2, 0.9, 10.6, o.roupa);                                                         // aba
      b(-4.4, 16.1, -0.3, 8.8, 1.2, 6, o.borda);                                                             // fita
      b(-4.2, 17.3, 0, 8.4, 2, 5.6, o.roupa); b(-3, 19.3, 0.8, 6, 1.9, 4.2, o.roupa); b(-1.8, 21.2, 1.8, 3.8, 1.8, 3, o.roupa); b(-0.4, 23, 3, 2, 1.4, 1.8, o.roupa2); b(0.9, 24.2, 3.4, 1.5, 1, 1.4, o.roupa2);
      if (o.estrela) { b(-2.2, 18, -0.15, 1.1, 1.1, 0.15, o.estrela); b(1.3, 19.9, 0.65, 0.9, 0.9, 0.15, o.estrela); b(-0.4, 21.8, 1.65, 0.8, 0.8, 0.15, o.estrela); }
    }
    extras(b, p, o.topo, t);
    if (p.prop) { b.em(0, 0, 0); b(-3.4, 2.1, -3.8, 6.8, 0.6, 3.4, '#6a3a1e', 1); b(-3.1, 2.7, -3.6, 6.2, 0.3, 3, '#f3e6c4', 1); b(-0.15, 2.7, -3.7, 0.3, 0.4, 3.2, o.borda, 1); }   // grimório no colo
    return b.L;
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

  // desenha um mago de pé no ponto (cx, chao): u = tamanho do voxel; dir = 1 olha para a direita; pers = o personagem
  function desenhaMago(c, k, a, t, u, cx, chao, op) {
    op = op || {};
    olhar.x = op.lx || 0; olhar.y = op.ly || 0; P.surf = op.surf || null; P.tontoPend = !!op.tonto; V.pers = op.pers || null;
    const p = pose(a, t);
    if (op.semPiscar && p.olho === 'fechado' && a !== 'dorme') p.olho = 'aberto';
    const L = ordena(mago(p, t, k)), oy = chao + apoio(L) * u, ox = cx - 3.5 * KX * u;
    c.save();
    if ((op.dir || -1) > 0) { c.translate(cx * 2, 0); c.scale(-1, 1); }   // o desenho base olha para a esquerda
    if (op.sombra !== false) { c.fillStyle = 'rgba(0,0,0,.35)'; c.beginPath(); c.ellipse(cx, chao - u * 0.15, LARG * u * 0.45, u * 0.55, 0, 0, 6.3); c.fill(); }
    for (const b of L) caixa(c, b, u, ox, oy);
    brilho(c, L, u, ox, oy, p.brilho);
    c.restore();
    return p;
  }
  window.MagoVoxel = { desenha: desenhaMago, CLASSES: ROUPAS, R, LARG, topo: topoDe, PERS_OP };
})();
