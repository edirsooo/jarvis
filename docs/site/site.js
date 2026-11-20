// Página do Jarvis: orbes e cenários vivos (desenho do app), transição de cada seção, música por seção, a demonstração
// da voz, o palco da Aparência, a janela de atualização, os vídeos, copiar comandos, menu do celular e pausa.
(function () {
  const q = (s, r) => (r || document).querySelector(s), qa = (s, r) => [...(r || document).querySelectorAll(s)];
  const calmo = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const CEL = matchMedia('(max-width: 900px), (hover: none) and (pointer: coarse)'), cel = () => CEL.matches;
  const pausado = () => document.body.classList.contains('pausado');
  const MV = window.MagoVoxel;

  // ---------- orbes e cenários: cada canvas tem o seu; só desenha o que está na tela ----------
  const vivos = [];   // { el, tipo, api, visivel, sec, pausa }
  function dimensiona(cv) {
    const d = Math.min(devicePixelRatio || 1, cel() ? 1.25 : 1.5), b = cv.getBoundingClientRect();
    const w = Math.max(1, Math.round(b.width * d)), h = Math.max(1, Math.round(b.height * d));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
  }
  qa('canvas.orbe-cv').forEach((cv) => {
    if (!window.criaOrbe) return;
    const d = cv.dataset, sec = cv.closest('section, footer');
    const api = criaOrbe(cv, { forma: d.forma, estado: d.estado || 'ouvindo', x: +d.ox || .5, y: +d.oy || .5, r: +d.or || .3, anel: d.anel === '1', cor: sec && sec.dataset.corOrbe || '' });
    cv.__orbe = api; vivos.push({ el: cv, tipo: 'orbe', api, sec, visivel: false });
    // cenário pintado por baixo do orbe no mesmo canvas (a abertura tem uma camada de fundo só)
    if (d.cenarioFundo && window.criaCenario) {
      const off = document.createElement('canvas'), cena = criaCenario(off, d.cenarioFundo, api); let tc = 0;
      api.O.fundo = (g, W, H, agora) => {
        if (off.width !== W || off.height !== H) { off.width = W; off.height = H; tc = 0; }
        const congela = pausado() || calmo;
        cena.semLua = cel();
        if (!tc || (!congela && agora - tc > 1000 / (cel() ? 15 : 30))) { cena.quadro(agora, congela); tc = agora; }
        g.drawImage(off, 0, 0);
        const veu = g.createLinearGradient(0, 0, 0, H * .62); veu.addColorStop(0, 'rgba(7,8,15,.62)'); veu.addColorStop(.7, 'rgba(7,8,15,.3)'); veu.addColorStop(1, 'rgba(7,8,15,0)');
        g.fillStyle = veu; g.fillRect(0, 0, W, H * .62);
      };
      cv.addEventListener('pointermove', () => {}, { passive: true });
      api.olhaCena = (fx) => cena.olha(fx);
    }
  });
  qa('canvas.cena-cv').forEach((cv) => {
    if (!window.criaCenario) return;
    const palco = cv.parentElement, orbeCv = q('canvas.orbe-cv', palco);
    const api = criaCenario(cv, cv.dataset.cenario || 'ruinas', orbeCv && orbeCv.__orbe);
    cv.__cena = api; vivos.push({ el: cv, tipo: 'cena', api, sec: cv.closest('section'), visivel: false });
  });
  // o mago do palco da Aparência (a classe escolhida, conjurando para o orbe)
  const magoCv = q('.mago-cv'); let magoClasse = 'torre';
  // visuais do personagem (o mesmo pers do app: corpo, pele, cabelo, barba, cor da roupa)
  const VISUAIS = [
    { tipo: 'm', pele: '#8d5a3b', cabelo: 'longo', cor_cabelo: '#1a1210', barba: 'nenhuma', roupa_cor: '' },
    { tipo: 'h', pele: '#e0aa82', cabelo: 'curto', cor_cabelo: '#7a4a26', barba: 'curta', roupa_cor: '#2f6b45' },
    { tipo: 'm', pele: '#c68a5e', cabelo: 'cacheado', cor_cabelo: '#3b2416', barba: 'nenhuma', roupa_cor: '#a8401e' },
  ];
  let magoVisual = VISUAIS[0];
  if (magoCv && MV) vivos.push({ el: magoCv, tipo: 'mago', sec: magoCv.closest('section'), visivel: false });

  const io = new IntersectionObserver((es) => es.forEach((e) => { const v = vivos.find((x) => x.el === e.target); if (v) v.visivel = e.isIntersecting; }), { rootMargin: '60px 0px' });
  vivos.forEach((v) => io.observe(v.el));
  addEventListener('pointermove', (e) => {
    for (const v of vivos) if (v.tipo === 'orbe' && v.visivel) {
      const b = v.el.getBoundingClientRect(), dentro = e.clientX >= b.left - 60 && e.clientX <= b.right + 60 && e.clientY >= b.top - 60 && e.clientY <= b.bottom + 60;
      v.api.ponteiro(e.clientX, e.clientY, dentro);
    }
    for (const v of vivos) if ((v.tipo === 'cena' || v.api && v.api.olhaCena) && v.visivel) { const b = v.el.getBoundingClientRect(), fx = Math.max(-.5, Math.min(.5, (e.clientX - b.left) / b.width - .5)); if (v.tipo === 'cena') v.api.olha(fx); else v.api.olhaCena(fx); }
  }, { passive: true });
  // clicar no orbe: ele acorda e fala um instante (como no painel)
  addEventListener('click', (e) => {
    for (const v of vivos) if (v.tipo === 'orbe' && v.visivel && !v.el.closest('[data-ciclo]') && v.api.emCima(e.clientX, e.clientY)) {
      const O = v.api.O, antes = O.estado; O.explode = .5; O.estado = 'falando'; clearTimeout(v.tFala); v.tFala = setTimeout(() => { O.estado = antes === 'falando' ? 'ouvindo' : antes; }, 1800);
    }
  });
  let tAnt = 0, tCena = 0;
  function quadro(now) {
    requestAnimationFrame(quadro);
    const alvo = cel() ? 30 : 50;
    if (now - tAnt < 1000 / alvo - 2) return; tAnt = now;
    const congela = pausado() || calmo, cenaVez = now - tCena > 1000 / (cel() ? 15 : 30);
    if (cenaVez) tCena = now;
    for (const v of vivos) {
      if (!v.visivel) continue;
      if ((congela || v.parado) && v.feito) continue;
      dimensiona(v.el);
      if (v.tipo === 'orbe') v.api.quadro(now);
      else if (v.tipo === 'cena') { if (cenaVez || congela) v.api.quadro(now, congela); }
      else if (v.tipo === 'mago') desenhaMagoPalco(now);
      v.feito = true;
    }
  }
  requestAnimationFrame(quadro);
  addEventListener('resize', () => vivos.forEach((v) => { v.feito = false; }));
  function desenhaMagoPalco(now) {
    const cv = magoCv, c = cv.getContext('2d'), W = cv.width, H = cv.height, u = H / 150, t = now / 1000;
    c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, W, H);
    MV.desenha(c, magoClasse, calmo ? 'parado' : 'conjura', t, u, W * .2, H * .9, { dir: 1, lx: -.6, ly: .4, surf: { k: 'chao' }, pers: magoVisual });
  }

  // ---------- Voz: o painel ouvindo o pedido, pensando e respondendo ----------
  const ciclo = q('[data-ciclo="voz"]');
  if (ciclo) {
    const orbe = ciclo.__orbe, tela = ciclo.closest('figure'), est = q('.estado-txt', tela), leg = q('.legenda-txt', tela), voce = q('.voce-txt span', tela), bt = q('.pausa-palco', tela);
    const PEDIDO = voce.textContent, RESPOSTA = 'Achei 9 academias, 5 sem site.';
    const passos = [['ouvindo', 3200], ['pensando', 1500], ['falando', 3400], ['dormindo', 1600]];
    let i = 0, tm = 0, parado = calmo, tipo = 0;
    const NOME = { ouvindo: 'Ouvindo', pensando: 'Pensando', falando: 'Falando', dormindo: 'Dormindo' };
    const escreve = (el, txt, ms) => { clearInterval(tipo); let n = 0; el.textContent = ''; tipo = setInterval(() => { n++; el.textContent = txt.slice(0, n); if (n >= txt.length) clearInterval(tipo); }, ms / txt.length); };
    function passo() {
      if (parado || pausado()) return;
      const [e, ms] = passos[i]; orbe.O.estado = e; est.textContent = '✦ ' + NOME[e] + ' ✦';
      if (e === 'ouvindo') { leg.textContent = ''; escreve(voce, PEDIDO, 1800); }
      if (e === 'falando') escreve(leg, RESPOSTA, 1200);
      i = (i + 1) % passos.length; tm = setTimeout(passo, ms);
    }
    if (calmo) { orbe.O.estado = 'falando'; est.textContent = '✦ Falando ✦'; leg.textContent = RESPOSTA; }
    else { leg.textContent = ''; voce.textContent = ''; }
    const io2 = new IntersectionObserver(([en]) => { if (en.isIntersecting && !tm && !parado) passo(); });
    io2.observe(tela);
    bt.addEventListener('click', () => {
      parado = !parado; bt.setAttribute('aria-pressed', parado); bt.setAttribute('aria-label', parado ? 'Continuar a demonstração' : 'Pausar a demonstração'); bt.firstChild.textContent = parado ? '▶' : '❚❚';
      clearTimeout(tm); tm = 0; clearInterval(tipo); if (!parado) passo();
    });
    window.__vozRetoma = () => { if (!parado && !tm) passo(); };
    window.__vozPara = () => { clearTimeout(tm); tm = 0; clearInterval(tipo); };
  }

  // ---------- Aparência: as escolhas mudam o palco vivo ----------
  const sAp = q('#aparencia');
  if (sAp) {
    const orbeAp = q('.orbe-cv', sAp).__orbe, cenaAp = q('.cena-cv', sAp).__cena, grupoMagos = q('.magos', sAp);
    if (MV && grupoMagos) MV.CLASSES.forEach(([k, n], i) => {
      const b = document.createElement('button'); b.type = 'button'; b.dataset.classe = k; b.setAttribute('aria-label', n); b.title = n; b.setAttribute('aria-pressed', i === 0);
      const c = document.createElement('canvas'); c.width = 80; c.height = 108; c.setAttribute('aria-hidden', 'true'); b.appendChild(c); grupoMagos.appendChild(b);
    });
    const retratos = () => qa('canvas', grupoMagos).forEach((c) => { const x = c.getContext('2d'); x.clearRect(0, 0, c.width, c.height); MV.desenha(x, c.parentElement.dataset.classe, 'parado', 1, 3.4, 40, 104, { dir: 1, sombra: false, semPiscar: true, pers: magoVisual }); });
    retratos();
    qa('.grupo', sAp).forEach((gp) => gp.addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      qa('button', gp).forEach((x) => x.setAttribute('aria-pressed', x === b));
      const d = b.dataset;
      if (d.forma) { orbeAp.O.forma = d.forma; orbeAp.O.explode = .35; }
      if (d.corpo) orbeAp.O.corpo = d.corpo;
      if (d.cor !== undefined) orbeAp.O.cor = d.cor;
      if (d.cenario && cenaAp) cenaAp.nome = d.cenario;
      if (d.classe) magoClasse = d.classe;
      if (d.visual) { magoVisual = VISUAIS[+d.visual] || VISUAIS[0]; retratos(); }
      vivos.forEach((v) => { v.feito = false; });
    }));
  }
  qa('.palco-vivo .pausa-palco, .palco-final .pausa-palco').forEach((bt) => {
    const fig = bt.closest('figure');
    bt.addEventListener('click', () => {
      const on = bt.getAttribute('aria-pressed') !== 'true'; bt.setAttribute('aria-pressed', on); bt.setAttribute('aria-label', on ? 'Continuar o palco' : 'Pausar o palco'); bt.firstChild.textContent = on ? '▶' : '❚❚';
      vivos.filter((v) => fig.contains(v.el)).forEach((v) => { v.parado = on; v.feito = false; });
    });
  });
  // ---------- Atualização: a janela do app, com o botão funcionando de mentira ----------
  const btAtu = q('[data-atualiza]');
  if (btAtu) {
    const msg = q('.dlg-msg'), sec = btAtu.closest('section'), orbe = q('.orbe-cv', sec).__orbe;
    btAtu.addEventListener('click', () => {
      btAtu.disabled = true; msg.textContent = 'Baixando a versão nova…'; orbe.O.estado = 'pensando';
      setTimeout(() => { msg.textContent = 'Atualizado! O Jarvis está reiniciando e volta em instantes.'; orbe.O.estado = 'falando'; orbe.O.explode = .6; if (window.Magos) Magos.festa(sec); }, 1400);
      setTimeout(() => { btAtu.disabled = false; msg.textContent = ''; orbe.O.estado = 'ouvindo'; }, 6000);
    });
  }

  // ---------- Missões: as abas trocam a tela ----------
  const ALT = { 'missao-rodando': 'Painel do Jarvis com a missão 1, Prospecção de academias em Valinhos, rodando no Claude Code', processos: 'Aba Processos com oito roteiros prontos: computador, corte para Reels, imagem, pesquisa de mercado, programar, prospecção, resumo do dia e site' };
  qa('#missoes [role="tab"]').forEach((b, i, abas) => {
    b.id = 'missoes-aba-' + i; b.setAttribute('aria-controls', 'missoes-tela'); b.tabIndex = b.getAttribute('aria-selected') === 'true' ? 0 : -1;
    const ativa = (foco) => {
      abas.forEach((x) => { const on = x === b; x.setAttribute('aria-selected', on); x.tabIndex = on ? 0 : -1; });
      const img = q('#missoes-tela img'), src = 'site/telas/' + b.dataset.tela + '.webp?v=20261119b';
      if (img.getAttribute('src') !== src) { img.classList.remove('troca'); void img.offsetWidth; img.src = src; img.alt = ALT[b.dataset.tela]; if (!calmo) img.classList.add('troca'); }
      if (foco) b.focus();
    };
    b.addEventListener('click', () => ativa());
    b.addEventListener('keydown', (e) => { const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key]; if (d) { e.preventDefault(); abas[(i + d + abas.length) % abas.length].click(); abas[(i + d + abas.length) % abas.length].focus(); } });
    b.addEventListener('pointerenter', () => { new Image().src = 'site/telas/' + b.dataset.tela + '.webp?v=20261119b'; }, { once: true });
  });
  const tp = q('#missoes-tela'); if (tp) tp.setAttribute('aria-labelledby', 'missoes-aba-0');

  // ---------- Vídeo: três vídeos num player só ----------
  const vTela = q('#video-tela'), vid = vTela && q('video', vTela);
  qa('.videos [role="tab"]').forEach((b, i, abas) => {
    b.id = 'video-aba-' + i; b.setAttribute('aria-controls', 'video-tela'); b.tabIndex = i ? -1 : 0;
    b.addEventListener('click', () => {
      abas.forEach((x) => { const on = x === b; x.setAttribute('aria-selected', on); x.tabIndex = on ? 0 : -1; });
      vTela.dataset.v = b.dataset.formaV; vTela.setAttribute('aria-labelledby', b.id);
      vid.pause(); vid.poster = b.dataset.poster; q('source', vid).src = b.dataset.src; vid.setAttribute('width', b.dataset.formaV === 'deitado' ? 1280 : 720); vid.setAttribute('height', b.dataset.formaV === 'deitado' ? 720 : 1280); vid.load();
    });
    b.addEventListener('keydown', (e) => { const d = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key]; if (d) { e.preventDefault(); const n = abas[(i + d + abas.length) % abas.length]; n.click(); n.focus(); } });
  });

  // ---------- a animação 3D da seção final: toca muda quando aparece; o botão pausa ----------
  const loop = q('.v-loop');
  if (loop) {
    const bt = loop.parentElement.querySelector('.pausa-palco'); let quer = !calmo;
    const marca = () => { const p = loop.paused; bt.setAttribute('aria-pressed', p); bt.setAttribute('aria-label', p ? 'Tocar a animação' : 'Pausar a animação'); bt.firstChild.textContent = p ? '▶' : '❚❚'; };
    loop.addEventListener('play', marca); loop.addEventListener('pause', marca);
    new IntersectionObserver(([e]) => { if (e.isIntersecting && quer && !pausado()) loop.play().catch(() => {}); else loop.pause(); }).observe(loop);
    bt.addEventListener('click', () => { if (loop.paused) { quer = true; loop.play().catch(() => {}); } else { quer = false; loop.pause(); } });
  }

  // ---------- copiar os comandos de instalação ----------
  qa('[data-copia]').forEach((b) => b.addEventListener('click', () => {
    const txt = q('#' + b.dataset.copia).textContent;
    const ok = () => { b.textContent = 'Copiado'; b.classList.add('ok'); setTimeout(() => { b.textContent = 'Copiar'; b.classList.remove('ok'); }, 1800); };
    if (navigator.clipboard) navigator.clipboard.writeText(txt).then(ok).catch(() => {}); else ok();
  }));
  const baixar = q('#btnBaixar');
  if (baixar) baixar.addEventListener('click', () => { if (window.Magos) Magos.festa(q('#baixar')); });

  // ---------- menu do celular ----------
  const bt = q('.menu-bt'), menu = q('#menu');
  const fecha = () => { document.body.classList.remove('menu-aberto'); bt.setAttribute('aria-expanded', 'false'); bt.setAttribute('aria-label', 'Abrir o menu'); };
  bt.addEventListener('click', () => {
    const abre = !document.body.classList.contains('menu-aberto');
    document.body.classList.toggle('menu-aberto', abre); bt.setAttribute('aria-expanded', abre); bt.setAttribute('aria-label', abre ? 'Fechar o menu' : 'Abrir o menu');
    if (abre) q('a', menu).focus();
  });
  qa('a', menu).forEach((a) => a.addEventListener('click', fecha));
  addEventListener('keydown', (e) => { if (e.key === 'Escape' && document.body.classList.contains('menu-aberto')) { fecha(); bt.focus(); } });

  // ---------- pausar tudo ----------
  const pausa = q('.pausa');
  pausa.addEventListener('click', () => {
    const on = pausa.getAttribute('aria-pressed') !== 'true';
    pausa.setAttribute('aria-pressed', on); const t = on ? 'Retomar animações' : 'Pausar animações'; pausa.setAttribute('aria-label', t); pausa.title = t; pausa.firstChild.textContent = on ? '▶' : '❚❚';
    document.body.classList.toggle('pausado', on); if (window.Magos) Magos.pausa(on);
    vivos.forEach((v) => { v.feito = false; });
    if (on) { if (window.__vozPara) __vozPara(); if (loop) loop.pause(); } else if (window.__vozRetoma) __vozRetoma();
  });

  const secoes = qa('main > section, footer.closing');

  // ---------- música: uma faixa por seção, troca com crossfade; só toca depois do ♪ ----------
  const som = q('.som'), vol = q('.vol'), players = [new Audio(), new Audio()]; let atual = 0, faixa = '', tocando = false, volume = .35, ativa = null;
  try { const v = parseFloat(localStorage.getItem('jarvis-site-volume')); if (v >= 0 && v <= 1) { volume = v; vol.value = Math.round(v * 100); } } catch (_) {}
  vol.addEventListener('input', () => { volume = vol.value / 100; players[atual].volume = volume; try { localStorage.setItem('jarvis-site-volume', volume); } catch (_) {} });
  players.forEach((a) => { a.loop = true; a.preload = 'none'; a.volume = 0; });
  function fade(a, alvo, ms, fim) {
    const v0 = a.volume, t0 = performance.now();
    const f = (now) => { const k = Math.min(1, (now - t0) / ms); a.volume = Math.max(0, Math.min(1, v0 + (alvo - v0) * k)); if (k < 1) requestAnimationFrame(f); else if (fim) fim(); };
    requestAnimationFrame(f);
  }
  function toca(nome) {
    if (!tocando || nome === faixa) return;
    if (!nome) { faixa = ''; players.forEach((a) => fade(a, 0, 600, () => a.pause())); return; }
    faixa = nome; const velho = players[atual]; atual = 1 - atual; const novo = players[atual];
    novo.src = 'site/musica/' + nome + '.mp3'; novo.currentTime = 0; novo.volume = 0;
    novo.play().then(() => fade(novo, volume, 700)).catch(() => {});
    fade(velho, 0, 700, () => velho.pause());
  }
  function liga(on) {
    tocando = on; som.setAttribute('aria-pressed', on); const t = on ? 'Parar a música' : 'Tocar a música'; som.setAttribute('aria-label', t); som.title = t;
    if (on) { faixa = '-'; toca((ativa || secoes[0]).dataset.faixa || ''); } else { faixa = ''; players.forEach((a) => fade(a, 0, 400, () => a.pause())); }
  }
  som.addEventListener('click', () => liga(!tocando));
  if (vid) vid.addEventListener('play', () => { if (tocando) liga(false); });

  // ---------- seção ativa: a última cujo topo passou de 80% da tela (só troca a música; nada se anima com a rolagem) ----------
  let ordem = -1, rTick = 0;
  function confere() {
    rTick = 0; const linha = innerHeight * .8; let i = 0;
    secoes.forEach((s, n) => { if (s.getBoundingClientRect().top <= linha) i = n; });
    if (i === ordem) return;
    ordem = i; ativa = secoes[i];
    toca(ativa.dataset.faixa || '');
  }
  addEventListener('scroll', () => { if (!rTick) rTick = requestAnimationFrame(confere); }, { passive: true });
  addEventListener('resize', () => { if (!rTick) rTick = requestAnimationFrame(confere); });
  confere();

  // celular: cada seção cresce com o que tem, mas sempre em telas inteiras (nenhuma vizinha aparece pela metade)
  function telas() {
    secoes.forEach((sec) => {
      if (sec.classList.contains('hero')) return;
      sec.style.minHeight = '';
      if (!cel()) return;
      const vh = innerHeight, h = sec.scrollHeight, n = Math.max(1, Math.round(h / vh));
      if (h < n * vh) sec.style.minHeight = n * vh + 'px';
    });
    if (window.Magos) Magos.reposiciona();
  }
  let tTelas = 0; addEventListener('resize', () => { clearTimeout(tTelas); tTelas = setTimeout(telas, 150); });
  telas(); if (document.fonts && document.fonts.ready) document.fonts.ready.then(telas);

  // topo com fundo depois de rolar
  const topo = q('#topo'), rola = () => topo.classList.toggle('cheio', scrollY > 20);
  addEventListener('scroll', rola, { passive: true }); rola();
})();
