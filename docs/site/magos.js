// Personagens da página: cada seção com data-palco tem os seus bonecos voxel (o desenho do app, em magos-voxel.js), em
// visuais variados. Eles vivem sozinhos no chão da seção, num laço próprio que não depende da rolagem: andam de um lado
// para o outro, param, viram, pulam, acenam, leem, sentam, cumprimentam quem passa perto e vão até o Jarvis conjurar
// (o orbe responde). No computador dá para pegar, jogar e soltar em cima dos quadros ([data-piso]); um clique faz
// comemorar. Celular: os mesmos passeios, sem arrastar e com menos quadros. Movimento reduzido: todos parados.
(function () {
  const MV = window.MagoVoxel;
  if (!MV) return;
  const calmo = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const CEL = matchMedia('(max-width: 900px), (hover: none) and (pointer: coarse)'), cel = () => CEL.matches;
  const NOMES = Object.fromEntries(MV.CLASSES);
  // visuais dos personagens: mulheres e homens, vários tons de pele e cabelos (no app, cada um escolhe o seu)
  const VISUAIS = [
    { tipo: 'm', pele: '#8d5a3b', cabelo: 'longo', cor_cabelo: '#1a1210', barba: 'nenhuma' },
    { tipo: 'h', pele: '#f1c9a5', cabelo: 'curto', cor_cabelo: '#c98a3a', barba: 'nenhuma' },
    { tipo: 'm', pele: '#c68a5e', cabelo: 'cacheado', cor_cabelo: '#3b2416', barba: 'nenhuma' },
    { tipo: 'h', pele: '#5c3a24', cabelo: 'raspado', cor_cabelo: '#1a1210', barba: 'curta' },
    { tipo: 'm', pele: '#e8b48a', cabelo: 'longo', cor_cabelo: '#a8401e', barba: 'nenhuma' },
    { tipo: 'h', pele: '#a86f4a', cabelo: 'curto', cor_cabelo: '#c9c4bc', barba: 'curta' },
    { tipo: 'm', pele: '#f6d3b8', cabelo: 'curto', cor_cabelo: '#7a4a26', barba: 'nenhuma' },
  ];
  let nVisual = 0;
  const rnd = (a, b) => a + Math.random() * (b - a), um = (L) => L[(Math.random() * L.length) | 0], lim = (v, a, b) => Math.max(a, Math.min(b, v));
  const F = {
    pega: ['Ei!', 'Opa!', 'Me leva!'], chao: ['Ufa!', 'Pousei!'], quadro: ['Boa vista daqui.', 'Cantinho novo!'],
    festa: ['Missão cumprida!', 'Mais uma!', 'Está feito!'], oi: ['Oi!', 'E aí?', 'Bora?', 'Tudo certo?'], resposta: ['Oi!', 'Bora!', 'Tudo!'],
    jarvis: ['Jarvis!', 'Uma missão?', 'Acorda, Jarvis!'], pulo: ['Hop!'],
  };
  const estado = { pausado: false, mx: -9999, my: -9999 };
  const palcos = [];
  const camada = document.createElement('div'); camada.id = 'magos'; camada.setAttribute('aria-hidden', 'true');
  (document.getElementById('topo') || document.body).appendChild(camada);

  function Palco(sec) {
    this.sec = sec;
    this.ks = sec.dataset.palco.split(',').map((s) => s.trim()).filter((k) => MV.R[k]);
    this.cheio = this.ks.length > 2;
    this.pets = this.ks.map((k, i) => new Pet(this, k, i));
    this.ativo = false; this.lista = null; this.listaT = 0; this.W = 0; this.H = 0;
  }
  Palco.prototype.U = function () { return cel() ? 2.4 : this.cheio ? 3.3 : 3.5; };
  Palco.prototype.mede = function () { this.W = this.sec.clientWidth; this.H = this.sec.clientHeight; };
  // o chão: o pé da seção, ou o topo do elemento em data-chao (o rodapé, no final)
  Palco.prototype.chao = function () {
    const sel = this.sec.dataset.chao, el = sel && this.sec.querySelector(sel);
    if (el) return el.getBoundingClientRect().top - this.sec.getBoundingClientRect().top - 2;
    return this.H - (cel() ? 12 : 8);
  };
  Palco.prototype.superficies = function () {
    const now = performance.now();
    if (this.lista && now - this.listaT < 200) return this.lista;
    const sr = this.sec.getBoundingClientRect(), out = [];
    this.sec.querySelectorAll('[data-piso]').forEach((e) => {
      const r = e.getBoundingClientRect(); if (r.width < 80 || r.height < 8) return;
      out.push({ el: e, l: r.left - sr.left + 8, r: r.right - sr.left - 8, y: r.top - sr.top });
    });
    out.push({ el: null, l: 12, r: sr.width - 12, y: this.chao() });
    this.lista = out; this.listaT = now; return out;
  };
  // o Jarvis da seção (o orbe vivo): onde ele está, em coordenadas da seção
  Palco.prototype.jarvis = function () {
    const cv = this.sec.querySelector('canvas.orbe-cv'), o = cv && cv.__orbe; if (!o || !o.V.R) return null;
    const r = cv.getBoundingClientRect(), sr = this.sec.getBoundingClientRect(), k = r.width / Math.max(1, cv.width);
    const x = r.left - sr.left + o.V.cx * k; if (x < 0 || x > this.W) return null;
    return { x, y: r.top - sr.top + o.V.cy * k, api: o, ciclo: !!cv.closest('[data-ciclo]') };
  };
  // onde cada um começa: espalhados no chão; sozinho, na margem esquerda
  Palco.prototype.vaga = function (i) {
    const n = this.ks.length, W = this.W, c = this.chao(), margem = Math.max(20, (W - Math.min(W - 160, 1280)) / 2), hero = this.sec.classList.contains('hero');
    if (n === 1) return { x: cel() ? W - 48 : margem + 30, y: c };
    const larg = cel() ? W - 60 : Math.min(W - 80, hero ? 900 : 620), x0 = cel() ? 30 : hero ? (W - larg) / 2 : W - margem - larg;
    return { x: x0 + larg * (i + 0.5) / n, y: c };
  };
  Palco.prototype.poe = function () { this.mede(); this.lista = null; this.pets.forEach((p) => p.poe()); };
  Palco.prototype.festa = function () { this.pets.forEach((p, i) => setTimeout(() => p.festa(2.2, i === 0 ? um(F.festa) : ''), i * 90)); };
  // encontros: dois que passam perto um do outro param, se viram e se cumprimentam
  Palco.prototype.encontros = function (now) {
    const L = this.pets;
    for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) {
      const a = L[i], b = L[j];
      if (!a.livre(now) || !b.livre(now) || (a.surf && a.surf.el) !== (b.surf && b.surf.el)) continue;
      const d = Math.abs(a.x - b.x); if (d > 80 || d < 18 || Math.random() > 0.02) continue;
      a.cumprimenta(b, now, true); b.cumprimenta(a, now, false);
    }
  };
  Palco.prototype.quadro = function (now, dt) {
    const t = now / 1000;
    if (!calmo && !estado.pausado) this.encontros(now);
    for (const p of this.pets) { if (!calmo) p.passo(dt, now); p.desenha(t); }
  };

  function Pet(palco, k, i) {
    this.palco = palco; this.k = k; this.i = i; this.visual = VISUAIS[nVisual++ % VISUAIS.length];
    this.x = 0; this.y = 0; this.vx = 0; this.vy = 0; this.dir = i % 2 ? 1 : -1;
    this.modo = 'parado'; this.surf = null; this.tm = rnd(0.5, 2.5); this.alvo = 0; this.festaT = 0; this.esp = 0; this.ang = 0; this.vel = rnd(38, 58);
    this.depois = null; this.encontroAte = 0;
    this.hit = document.createElement('div'); this.hit.className = 'mago-hit'; this.hit.tabIndex = -1; this.hit.title = NOMES[k] || 'Personagem';
    this.cv = document.createElement('canvas'); this.cv.setAttribute('aria-hidden', 'true'); this.hit.appendChild(this.cv);
    camada.appendChild(this.hit);
    this.balao = document.createElement('div'); this.balao.className = 'fala'; this.balao.hidden = true; camada.appendChild(this.balao);
    this.eventos();
  }
  const P = Pet.prototype;
  P.u = function () { return this.palco.U(); };
  P.alt = function () { return MV.topo(this.k) * this.u(); };
  P.meia = function () { return MV.LARG * this.u() / 2; };
  P.livre = function (now) { return !this.seg && now > this.encontroAte && (this.modo === 'anda' || this.modo === 'parado') && this.festaT <= 0 && !this.depois && !this.missao; };
  P.poe = function () {
    const v = this.palco.vaga(this.i), chao = this.palco.superficies().slice(-1)[0];
    if (!this.cw || !this.surf || !this.surf.el) { this.x = this.cw ? lim(this.x, chao.l + 20, chao.r - 20) : v.x; this.y = chao.y; this.surf = chao; }
    if (this.modo === 'cai' || this.modo === 'pulo') this.modo = 'parado';
    this.vx = this.vy = 0; this.alvoY = null;
    const u = this.u(), d = Math.min(devicePixelRatio || 1, 2), w = Math.ceil(MV.LARG * u * 1.5), h = Math.ceil(this.alt() + 9 * u);
    this.cw = w; this.ch = h; this.d = d;
    if (this.cv.width !== Math.round(w * d) || this.cv.height !== Math.round(h * d)) { this.cv.width = Math.round(w * d); this.cv.height = Math.round(h * d); }
    this.cv.style.width = w + 'px'; this.cv.style.height = h + 'px';
    this.desenha(performance.now() / 1000);
  };
  P.diz = function (txt, ms) {
    if (!txt) return; clearTimeout(this.tFala); this.balao.textContent = txt; this.balao.hidden = false;
    this.tFala = setTimeout(() => { this.balao.hidden = true; }, ms || 1700);
  };
  P.festa = function (s, fala) { this.festaT = Math.max(this.festaT, s); if (this.modo !== 'cai' && this.modo !== 'pulo') this.modo = 'parado'; this.diz(fala); };
  P.pula = function () { this.vy = -560 - Math.random() * 180; this.modo = 'pulo'; this.alvoY = this.y; this.surf0 = this.surf; };
  P.cumprimenta = function (outro, now, primeiro) {
    this.modo = 'parado'; this.dir = outro.x > this.x ? 1 : -1; this.encontroAte = now + 9000 + Math.random() * 5000;
    setTimeout(() => { this.festa(1.3, Math.random() < 0.6 ? um(primeiro ? F.oi : F.resposta) : ''); }, primeiro ? 0 : 450);
    // depois do cumprimento, cada um segue para o seu lado
    this.depois = { ate: now + 2200, faz: () => { const s = this.surf; if (!s) return; this.modo = 'anda'; this.alvo = lim(this.x + (this.x < outro.x ? -1 : 1) * rnd(120, 260), s.l + this.meia(), s.r - this.meia()); } };
  };
  P.pousa = function (s) {
    this.surf = s; this.y = s.y; this.vx = this.vy = 0; this.esp = 0.35; this.modo = 'parado'; this.tm = rnd(0.8, 2); this.alvoY = null;
    if (this.solto) { this.solto = false; this.diz(um(s.el ? F.quadro : F.chao), 1400); }
  };
  // escolhe o que fazer agora
  P.decide = function () {
    const s = this.surf, l = s.l + this.meia(), r = s.r - this.meia(), z = Math.random(), jv = !s.el && this.palco.jarvis();
    if (z < 0.36 && r - l > 30) { this.modo = 'anda'; this.alvo = lim(this.x + (Math.random() < 0.5 ? -1 : 1) * rnd(90, 360), l, r); if (Math.abs(this.alvo - this.x) < 20) this.alvo = rnd(l, r); }
    else if (z < 0.46) { this.pula(); if (Math.random() < 0.25) this.diz(um(F.pulo), 900); }
    else if (z < 0.55) this.festa(1.1, '');
    else if (z < 0.66 && jv) {      // vai até o Jarvis e conjura para ele
      const lado = this.x < jv.x ? -1 : 1;
      this.modo = 'anda'; this.alvo = lim(jv.x + lado * rnd(70, 130), l, r); this.missao = { jv };
    }
    else if (z < 0.74) { this.modo = 'senta'; this.tm = rnd(2.5, 5); }
    else if (z < 0.82) { this.modo = 'le'; this.tm = rnd(2.5, 5); }
    else if (z < 0.9) { this.dir = -this.dir; this.modo = 'parado'; this.tm = rnd(0.8, 2); }   // vira para o outro lado
    else { this.modo = 'parado'; this.tm = rnd(1.5, 3.5); }
  };
  P.chegou = function () {
    if (this.missao) {        // chegou perto do Jarvis: vira para ele, conjura e o orbe responde
      const jv = this.palco.jarvis() || this.missao.jv; this.missao = null;
      this.dir = jv.x > this.x ? 1 : -1; this.modo = 'conjura'; this.tm = rnd(2.2, 3.2);
      if (Math.random() < 0.5) this.diz(um(F.jarvis), 1400);
      const O = jv.api.O;
      setTimeout(() => {
        O.explode = Math.max(O.explode || 0, 0.1);
        if (!jv.ciclo) { const antes = O.__antes || O.estado; O.__antes = antes; O.estado = 'falando'; clearTimeout(O.__tMago); O.__tMago = setTimeout(() => { O.estado = antes; O.__antes = null; }, 1600); }
      }, 700);
      return;
    }
    this.modo = 'parado'; this.tm = rnd(1, 3);
  };
  P.passo = function (dt, now) {
    const pal = this.palco;
    if (this.festaT > 0) this.festaT -= dt;
    this.esp += (0 - this.esp) * Math.min(1, dt * 9);
    if (this.seg && this.seg.ativo) {
      const tx = lim(this.mx, this.meia(), pal.W - this.meia()), ty = lim(this.my + this.alt() * 0.82, this.alt(), pal.H);
      const k = Math.min(1, dt * 24); this.x += (tx - this.x) * k; this.y += (ty - this.y) * k;
      this.ang += ((lim(-this.mvx * 0.0011, -1, 1) - this.ang) * 10) * dt; this.mvx *= Math.exp(-dt * 8);
      return;
    }
    this.ang += (0 - this.ang) * Math.min(1, dt * 9);
    if (this.modo === 'cai' || this.modo === 'pulo') {
      const y0 = this.y; this.vy += 2600 * dt; this.y += this.vy * dt; this.x += this.vx * dt; this.vx *= Math.exp(-dt * 1.2);
      if (this.x < this.meia()) { this.x = this.meia(); this.vx = Math.abs(this.vx) * 0.5; }
      if (this.x > pal.W - this.meia()) { this.x = pal.W - this.meia(); this.vx = -Math.abs(this.vx) * 0.5; }
      if (this.alvoY != null) { if (this.vy > 0 && this.y >= this.alvoY) { const s0 = this.surf0 || pal.superficies().slice(-1)[0]; this.pousa({ el: s0.el, l: s0.l, r: s0.r, y: this.alvoY }); } return; }
      if (this.vy > 0) for (const s of pal.superficies()) {
        if (y0 <= s.y + 1 && this.y >= s.y && this.x >= s.l && this.x <= s.r) { this.pousa(s); return; }
      }
      if (this.y > pal.H + 200) { this.surf = null; this.poe(); }
      return;
    }
    const s = this.surf; if (!s) { this.modo = 'cai'; return; }
    const atual = pal.superficies().find((o) => o.el === s.el); if (atual) { this.surf = atual; this.y = atual.y; } else { this.modo = 'cai'; this.surf = null; return; }
    if (estado.pausado) { if (this.modo === 'anda') this.modo = 'parado'; return; }
    if (this.depois && now > this.depois.ate) { const f = this.depois.faz; this.depois = null; f(); }
    if (this.festaT > 0 || this.depois) return;
    const l = this.surf.l + this.meia(), r = this.surf.r - this.meia();
    if (this.modo === 'anda') {
      const dx = this.alvo - this.x;
      if (Math.abs(dx) < 3) this.chegou();
      else { this.dir = dx > 0 ? 1 : -1; this.x = lim(this.x + this.dir * this.vel * dt, l, r); if (this.x === l || this.x === r) this.alvo = this.x; }
      return;
    }
    this.tm -= dt; if (this.tm > 0) return;
    this.decide();
  };
  P.anim = function () {
    if (this.seg && this.seg.ativo) return 'pendurado';
    if (this.modo === 'pulo') return 'festa';
    if (this.modo === 'cai') return 'cai';
    if (this.festaT > 0) return 'festa';
    return { anda: 'anda', senta: 'senta', le: 'le', conjura: 'conjura' }[this.modo] || 'parado';
  };
  P.desenha = function (t) {
    if (!this.cw) return;
    const u = this.u(), a = calmo ? 'parado' : this.anim();
    const sr = this.palco.sec.getBoundingClientRect(), px = estado.mx - sr.left, py = estado.my - sr.top, perto = Math.hypot(px - this.x, py - this.y) < 300;
    const lx = perto ? lim((px - this.x) / 200, -1, 1) * -this.dir : 0, ly = perto ? lim((this.y - this.alt() * 0.6 - py) / 200, -1, 1) : 0;
    const salto = a === 'festa' && this.surf && this.modo !== 'pulo' ? Math.abs(Math.sin(t * 8)) * 4 * u : 0;
    const c = this.cv.getContext('2d'), w = this.cw, h = this.ch, base = h - 2;
    c.setTransform(this.d, 0, 0, this.d, 0, 0); c.clearRect(0, 0, w, h);
    c.save();
    c.translate(w / 2, base - salto); c.rotate(this.ang); c.scale(1 + this.esp * 0.4, 1 - this.esp * 0.4); c.translate(-w / 2, -base);
    MV.desenha(c, this.k, a, t + this.i * 0.7, u, w / 2, base, { dir: this.dir, lx, ly, surf: this.modo === 'pulo' ? null : this.surf, sombra: !!this.surf && !salto && this.modo !== 'pulo', pers: this.visual });
    c.restore();
    this.salto = salto; this.posiciona();
  };
  // a posição na tela: a seção rola, o personagem vai junto
  P.posiciona = function () {
    if (!this.cw) return;
    const sr = this.palco.sec.getBoundingClientRect(), cr = camada.getBoundingClientRect(), ox = sr.left - cr.left, oy = sr.top - cr.top;
    this.hit.style.transform = `translate(${Math.round(ox + this.x - this.cw / 2)}px,${Math.round(oy + this.y - this.ch + 2)}px)`;
    if (!this.balao.hidden) { this.balao.style.left = Math.round(ox + this.x) + 'px'; this.balao.style.top = Math.round(oy + this.y - this.alt() - (this.salto || 0) - 10) + 'px'; }
  };
  P.local = function (e) { const r = this.palco.sec.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  P.eventos = function () {
    const hit = this.hit;
    hit.addEventListener('pointerdown', (e) => {
      if (e.button !== 0 || cel() || calmo) return;
      e.preventDefault(); try { hit.setPointerCapture(e.pointerId); } catch (_) {}
      const p = this.local(e); this.mx = p.x; this.my = p.y; this.mvx = 0; this.hist = [{ x: p.x, y: p.y, t: performance.now() }];
      this.seg = { id: e.pointerId, x0: e.clientX, y0: e.clientY, ativo: false };
    });
    hit.addEventListener('pointermove', (e) => {
      const s = this.seg; if (!s || e.pointerId !== s.id) return;
      const p = this.local(e), now = performance.now(), u = this.hist[this.hist.length - 1], vx = (p.x - u.x) / Math.max(1, now - u.t) * 1000;
      this.mx = p.x; this.my = p.y; this.mvx = this.mvx * 0.5 + vx * 0.5; this.hist.push({ x: p.x, y: p.y, t: now }); if (this.hist.length > 10) this.hist.shift();
      if (!s.ativo && Math.hypot(e.clientX - s.x0, e.clientY - s.y0) > 6) { s.ativo = true; this.surf = null; this.modo = 'parado'; this.festaT = 0; this.alvoY = null; this.missao = null; this.depois = null; hit.classList.add('pego'); if (Math.random() < 0.6) this.diz(um(F.pega), 1100); }
    });
    const larga = () => {
      const s = this.seg; if (!s) return; this.seg = null; hit.classList.remove('pego');
      if (!s.ativo) { this.festa(1.4, Math.random() < 0.7 ? um(F.festa) : ''); return; }
      const h = this.hist, now = performance.now(), a = h.find((q) => now - q.t < 110), b = h[h.length - 1];
      const ok = a && b && b.t - a.t > 8;
      this.vx = ok ? lim((b.x - a.x) / (b.t - a.t) * 1000, -1500, 1500) : 0; this.vy = ok ? lim((b.y - a.y) / (b.t - a.t) * 1000, -1500, 1500) : 0;
      this.modo = 'cai'; this.surf = null; this.solto = true; this.alvoY = null; this.palco.lista = null;
    };
    hit.addEventListener('pointerup', larga); hit.addEventListener('pointercancel', larga);
    hit.addEventListener('click', () => { if (cel() || calmo) this.festa(1.4, um(F.festa)); });
  };

  document.querySelectorAll('main > section[data-palco], footer.closing[data-palco]').forEach((s) => palcos.push(new Palco(s)));
  const io = new IntersectionObserver((es) => es.forEach((e) => { const p = palcos.find((x) => x.sec === e.target); if (p) { p.ativo = e.isIntersecting; p.pets.forEach((q) => { q.hit.style.display = p.ativo ? '' : 'none'; if (!p.ativo) q.balao.hidden = true; }); } }), { rootMargin: '80px 0px' });
  palcos.forEach((p) => { p.poe(); p.pets.forEach((q) => { q.hit.style.display = 'none'; }); io.observe(p.sec); });
  addEventListener('scroll', () => { for (const p of palcos) if (p.ativo) p.pets.forEach((q) => q.posiciona()); }, { passive: true });
  addEventListener('load', () => palcos.forEach((p) => p.poe()));
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => palcos.forEach((p) => p.poe()));
  addEventListener('pointermove', (e) => { estado.mx = e.clientX; estado.my = e.clientY; }, { passive: true });
  let tRes = 0;
  addEventListener('resize', () => { clearTimeout(tRes); tRes = setTimeout(() => palcos.forEach((p) => { p.pets.forEach((q) => { q.surf = null; }); p.poe(); }), 120); });

  let ult = performance.now();
  function quadro(now) {
    requestAnimationFrame(quadro);
    if ((calmo || estado.pausado) && now - ult < 400) return;
    if (cel() && now - ult < 1000 / 24) return;
    const dt = Math.min(0.05, (now - ult) / 1000); ult = now;
    for (const p of palcos) if (p.ativo) p.quadro(now, dt);
  }
  requestAnimationFrame(quadro);
  window.Magos = {
    estado,
    festa: (sec) => { const p = palcos.find((x) => x.sec === sec); if (p) p.festa(); },
    pausa: (on) => { estado.pausado = on; },
    reposiciona: () => palcos.forEach((p) => p.poe()),
  };
})();
