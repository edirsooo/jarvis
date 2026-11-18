/* Jarvis — tela: esfera voxel, cartões de missão, painel e som. */
const $ = s => document.querySelector(s);
document.title = 'Jarvis · painel';
const S = { estado: 'dormindo', mudo: false, missoes: [], painel: null, xp: { xp: 0, missoes: 0 }, vista: 'painel', nivelMic: 0, nivelVoz: 0, conectado: false };
let ws, ctx, analisador, dadosAn, filaVoz = [], tocando = null;

/* ---------- som ---------- */
function audio() {
  if (!ctx) {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    analisador = ctx.createAnalyser(); analisador.fftSize = 256;
    dadosAn = new Uint8Array(analisador.frequencyBinCount);
    analisador.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}
function bip(notas, tipo = 'square', vol = 0.05) {
  try {
    const c = audio(); let t = c.currentTime;
    for (const [f, d] of notas) {
      const o = c.createOscillator(), g = c.createGain();
      o.type = tipo; o.frequency.value = f;
      g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + d);
      o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + d); t += d * 0.8;
    }
  } catch (e) {}
}
const SONS = {
  acordar: () => bip([[660, .08], [990, .12]]),
  missao: () => bip([[440, .06], [660, .06], [880, .1]]),
  pronto: () => bip([[523, .09], [659, .09], [784, .09], [1047, .22]], 'square', .06),
  erro: () => bip([[220, .15], [165, .25]], 'sawtooth', .05),
  clique: () => bip([[880, .04]], 'square', .03),
};
function tocarProxima() {
  if (tocando || !filaVoz.length) return;
  const item = filaVoz.shift();
  const a = new Audio(item.url); a.crossOrigin = 'anonymous';
  tocando = a;
  try { const fonte = audio().createMediaElementSource(a); fonte.connect(analisador); } catch (e) {}
  const fim = () => { if (tocando === a) { tocando = null; legendaParar(); manda({ t: 'fala_fim' }); tocarProxima(); } };
  a.onended = fim; a.onerror = fim;
  // a legenda segue o áudio: só aparece quando o som começa, bloco a bloco
  a.onplaying = () => {
    legPend = '';
    legendaSeguir(item.txt, () => a.currentTime, () => (isFinite(a.duration) && a.duration > 0) ? a.duration : Math.max(2, String(item.txt || '').length / LEG.porSeg));
  };
  a.play().catch(() => { $('#entrada').hidden = false; filaVoz.unshift(item); tocando = null; });
}
function calar() { filaVoz = []; if (tocando) { try { tocando.pause(); } catch (e) {} tocando = null; } legPend = ''; legendaParar(); }

/* ---------- ligação ---------- */
function manda(o) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(o)); }
function ligar() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => { S.conectado = true; rodape(); };
  ws.onclose = () => { S.conectado = false; rodape(); setTimeout(ligar, 1500); };
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    switch (m.t) {
      case 'tudo':
        Object.assign(S, { estado: m.estado, mudo: m.mudo, missoes: m.missoes, painel: m.painel, xp: m.xp, cotas: m.cotas, dono: m.dono || '' });
        $('#nome').textContent = (m.nome || 'Jarvis').toUpperCase();
        $('#info').textContent = `${m.info.mic} · ${m.info.stt}` + (m.info.cerebro === 'local' ? ' · cérebro local' : '');
        S.info = m.info; S.agenda = m.agenda || []; etiquetas();
        const u = [...m.conversa].reverse().find(c => c.quem === 'voce');
        if (u) ultima(u.txt);
        estado(); cartoes(); painel(); xp(); cotas(); break;
      case 'cotas': S.cotas = m.v; cotas(); etiquetas(); break;
      case 'marco': aviso('MARCO · MISSÃO #' + m.missao, m.txt, () => manda({ t: 'abrir', missao: m.missao, entrega: 'atividade' })); break;
      case 'aviso': aviso('AVISO', m.txt, null, true); break;
      case 'processos': S.processos = m.v; if (S.vista === 'processos') telaProcessos(); break;
      case 'agenda': S.agenda = m.v; if (S.vista === 'processos') telaProcessos(); break;
      case 'estado': S.estado = m.v; S.mudo = m.mudo; estado(); break;
      case 'nivel': S.nivelMic = m.v; break;
      case 'linha': if (m.quem === 'voce') ultima(m.txt); break;
      case 'legenda': legPend = m.txt || ''; break;   // não mostra já: espera o áudio (ver legendaSeguir)
      case 'fala': filaVoz.push(m); tocarProxima(); break;
      case 'calar': calar(); break;
      case 'visual': if (window.MAGO) MAGO.aplica(m.v, true); break;
      case 'missoes': antes = S.missoes; S.missoes = m.v; cartoes(); if (S.painel) painel(true); avisar(antes); break;
      case 'painel': S.painel = m.v; painel(); SONS.clique(); break;
      case 'xp': S.xp = m.v; xp(); break;
      case 'som': (SONS[m.v] || (() => {}))(); break;
    }
  };
}
let antes = [];

/* ---------- textos ---------- */
const NOMES = { dormindo: 'DORMINDO', ouvindo: 'OUVINDO', pensando: 'PENSANDO', falando: 'FALANDO', trabalhando: 'TRABALHANDO' };
function estadoVisual() {
  if (S.estado === 'dormindo' && S.missoes.some(m => m.estado === 'trabalhando')) return 'trabalhando';
  return S.estado;
}
function estado() {
  const e = estadoVisual();
  $('#estado').textContent = S.mudo ? 'MICROFONE DESLIGADO' : NOMES[e];
  $('#app').classList.toggle('conversa', S.estado !== 'dormindo');
  const h = new Date().getHours();
  $('#saudacao b').textContent = (h < 5 ? 'Boa madrugada' : h < 12 ? 'Bom dia' : h < 18 ? 'Boa tarde' : 'Boa noite') + (S.dono ? ', ' + S.dono : '') + '.';
  $('#estado').style.color = { ouvindo: 'var(--ciano)', pensando: 'var(--amarelo)', falando: 'var(--laranja)', trabalhando: 'var(--verde)' }[e] || '';
  // a legenda não some mais ao voltar a ouvir: quem apaga é o relógio de legendaParar().
  // Reserva: se a fala terminou e nenhum áudio tocou nesta tela, mostra o texto em blocos no ritmo estimado.
  if (S.estado !== 'falando' && legPend) {
    const t = legPend; legPend = '';
    if (!tocando && !filaVoz.length) {
      const t0 = performance.now(), d = Math.max(2, t.length / LEG.porSeg);
      legendaSeguir(t, () => (performance.now() - t0) / 1000, () => d, true);
    }
  }
  rodape();
}
function rodape() {
  const mic = $('#mic');
  mic.className = S.mudo ? 'mudo' : S.conectado ? 'on' : '';
  $('#rodape').innerHTML = !S.conectado ? 'Sem ligação com o Jarvis. Tentando de novo…'
    : S.mudo ? 'Microfone desligado. <b>ESPAÇO</b> liga de novo.'
    : S.estado === 'dormindo' ? 'Diga <b>"Jarvis"</b>. <b>ESPAÇO</b> silencia.'
    : 'Pode falar. <b>ESPAÇO</b> silencia.';
}
/* legenda no ritmo da fala: blocos curtos, trocados conforme o áudio avança */
const LEG = { maxBloco: 56, ficaMs: 6000, porSeg: 15 };   // tamanho do bloco (letras), tempo na tela depois da fala, letras por segundo (reserva)
let legRelogio, legSome, legPend = '';
function blocos(txt) {
  const out = []; let b = '';
  for (const p of String(txt || '').split(/\s+/).filter(Boolean)) {
    if (b && b.length + 1 + p.length > LEG.maxBloco) { out.push(b); b = ''; }
    b = b ? b + ' ' + p : p;
    if ((/[.!?…]$/.test(p) && b.length >= 18) || (/[,;:]$/.test(p) && b.length >= 34)) { out.push(b); b = ''; }
  }
  if (b) out.push(b);
  return out;
}
function legendaSeguir(txt, tempoAgora, duracao, sozinha) {
  clearInterval(legRelogio); clearTimeout(legSome); clearInterval(digita);
  const bl = blocos(txt); if (!bl.length) return;
  const total = bl.reduce((s, b) => s + b.length, 0), ini = [];
  let ac = 0; for (const b of bl) { ini.push(ac / total); ac += b.length; }
  let atual = -1;
  const passo = () => {
    const f = tempoAgora() / duracao();
    let i = 0; while (i + 1 < bl.length && f >= ini[i + 1]) i++;
    if (i !== atual) { atual = i; $('#legenda').textContent = bl[i]; }
    if (sozinha && f >= 1) legendaParar();
  };
  passo(); legRelogio = setInterval(passo, 80);
}
function legendaParar() {   // para de trocar e deixa o último bloco na tela por um tempo
  clearInterval(legRelogio); clearTimeout(legSome);
  legSome = setTimeout(() => { $('#legenda').textContent = ''; }, LEG.ficaMs);
}
let digita;
function legenda(txt) {
  clearInterval(digita); clearInterval(legRelogio); clearTimeout(legSome);
  const el = $('#legenda');
  if (!txt) { el.textContent = ''; return; }
  let i = 0;
  digita = setInterval(() => {
    i += 2; el.innerHTML = esc(txt.slice(0, i)) + (i < txt.length ? '<span class="cursor"></span>' : '');
    if (i >= txt.length) clearInterval(digita);
  }, 28);
}
function ultima(txt) { $('#ultima').innerHTML = '<b>você</b>' + esc(txt); }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function xp() {
  const total = S.xp.xp || 0, nv = Math.floor(total / 300) + 1;
  $('#nivel').textContent = 'NV ' + nv;
  $('#xptxt').textContent = `${total} XP`;
}
function tempo(m) {
  const s = Math.max(0, Math.floor((m.fim || Date.now() / 1000) - m.inicio));
  return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
}

/* ---------- cotas ---------- */
function quando(ts) {   // "em 2h10", "sex 05:00"
  if (!ts) return '';
  const d = new Date(ts * 1000), falta = ts - Date.now() / 1000;
  if (falta <= 0) return 'renovando';
  if (falta < 86400) return `renova em ${Math.floor(falta / 3600)}h${String(Math.floor(falta % 3600 / 60)).padStart(2, '0')}`;
  return 'renova ' + d.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', '') + ' ' + d.toLocaleTimeString('pt-BR').slice(0, 5);
}
function cotas() {
  const el = $('#cotas'), cs = S.cotas || [];
  if (!cs.length) return;
  let h = '', curto = [], maisVelha = 0;
  cs.forEach(c => {
    if (!c.janelas.length) h += `<div class="cj"><div class="cj-topo"><b>${esc(c.nome)}</b><small>${esc(c.erro || 'sem leitura')}</small></div></div>`;
    c.janelas.forEach(j => {
      const u = j.usado ?? 0, nv = u >= 85 ? 'alto' : u >= 60 ? 'meio' : 'ok', on = Math.round(u / 100 * 24);
      h += `<div class="cj ${nv}"><div class="cj-topo"><b>${esc(c.nome)}</b><span>· ${esc(j.nome.toLowerCase())} · ${j.usado == null ? '—' : u + '% usado'}</span>
        <small>${esc(quando(j.renova))}${j.renova_estimada ? ' (estimado)' : ''}</small></div>
        <div class="cj-barra">${Array.from({ length: 24 }, (_, i) => `<i class="${i < on ? 'on' : ''}"></i>`).join('')}</div></div>`;
    });
    const pior = c.janelas.reduce((a, j) => Math.max(a, j.usado ?? 0), -1);
    if (pior >= 0) curto.push(`${esc(c.nome)} <b class="${pior >= 85 ? 'alto' : ''}">${pior}%</b>`);
    if (c.lido) maisVelha = Math.max(maisVelha, Date.now() / 1000 - c.lido);
  });
  el.innerHTML = h;
  $('#trilhoCotas').innerHTML = curto.join('<br>');
  $('#cotasLido').textContent = maisVelha > 1800 ? `leitura de ${Math.round(maisVelha / 3600 * 10) / 10} h atrás` : '';
}

/* ---------- mascotes (pixel) ---------- */
const SPRITES = {
  claude: ['..oooo..', '.oooooo.', 'oowoowoo', 'ookookoo', 'oooooooo', '.oommoo.', '.o.oo.o.', 'oo....oo'],
  codex: ['..gggg..', '.gwwwwg.', 'gwkwwkwg', 'gwwwwwwg', 'gwwmmwwg', '.gwwwwg.', '..g..g..', '.gg..gg.'],
};
const CORES = { o: '#ff6b1a', g: '#19c37d', w: '#ffffff', k: '#111318', m: '#111318' };
function mascote(agente) {
  const c = document.createElement('canvas'); c.width = c.height = 8; c.className = 'masc';
  const x = c.getContext('2d');
  (SPRITES[agente] || SPRITES.claude).forEach((l, j) => [...l].forEach((p, i) => { if (p !== '.') { x.fillStyle = CORES[p]; x.fillRect(i, j, 1, 1); } }));
  return c;
}

/* ---------- cartões ---------- */
const ROT = { trabalhando: 'TRABALHANDO', concluida: '✔ PRONTA', erro: '✖ NÃO DEU', parada: '■ PARADA' };
// resumo do agente sem marcação, emoji nem caminho de arquivo: só a primeira ideia
function limpaTxt(s) {
  s = String(s || '').replace(/[*_`#>]/g, '').replace(/^\s*RESULTADO:\s*(OK|PARCIAL|FALHOU)[\s.:-]*/i, '').replace(/[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}\u{FE0F}\u{2B00}-\u{2BFF}]/gu, '')
    .replace(/[A-Z]:\\(?:[^\\\n"']*\\)*/g, '').replace(/\b(?:entregas|trabalho|telas)\\/g, '').replace(/\s+/g, ' ').trim();
  const frases = s.split(/(?<=[.!?])\s+/);
  let out = frases[0] || '';
  if (out.length < 60 && frases[1]) out += ' ' + frases[1];
  return out.length > 170 ? out.slice(0, 167).replace(/\s+\S*$/, '') + '…' : out;
}
const TIPO = { site: 'Site', imagem: 'Imagem', video: 'Vídeo', audio: 'Áudio', texto: 'Texto', pdf: 'PDF', arquivo: 'Arquivo' };
const ICONE = { site: '🌐', audio: '♪', texto: '📄', pdf: '📄', arquivo: '▪' };
const urlM = (m, e) => `/m/${m.n}/${encodeURI(e.rel)}?v=${e.mod}`;
function principal(m) {   // a entrega que melhor representa a missão
  for (const t of ['video', 'imagem', 'site', 'pdf', 'audio', 'texto']) { const e = [...m.entregas].reverse().find(x => x.tipo === t && !/^antes\./i.test(x.nome)); if (e) return e; }
  return m.entregas[m.entregas.length - 1];
}
function miniTela(m, e) {   // miniatura de uma entrega: a própria imagem, o primeiro quadro do vídeo ou a captura do site
  const d = document.createElement('div'); d.className = 'mini-tela';
  if (!e) return d;
  const img = e.tipo === 'imagem' ? e : e.tipo === 'site' ? m.entregas.find(x => /^depois\./i.test(x.nome)) : null;
  if (img) d.style.backgroundImage = `url("${urlM(m, img)}")`;
  else if (e.tipo === 'video') { const v = document.createElement('video'); v.src = urlM(m, e) + '#t=1'; v.muted = true; v.preload = 'metadata'; d.append(v); }
  else d.textContent = ICONE[e.tipo] || '▪';
  return d;
}
function resumoTipos(m) {
  const t = [...new Set(m.entregas.map(e => TIPO[e.tipo] || 'Arquivo'))];
  if (m.entregas.some(e => /^antes\./i.test(e.nome)) && m.entregas.some(e => /^depois\./i.test(e.nome))) t.unshift('Antes e depois');
  return t.slice(0, 3).join(' · ');
}
function idade(ts) {
  const s = Math.max(0, Math.round(Date.now() / 1000 - ts));
  return s < 4 ? 'AGORA' : s < 60 ? `HÁ ${s} s` : s < 3600 ? `HÁ ${Math.floor(s / 60)} MIN` : `HÁ ${Math.floor(s / 3600)} H`;
}
function modo() {   // o arranjo da tela depende do momento
  const ativas = S.missoes.filter(m => m.estado === 'trabalhando').length, app = $('#app');
  const era = app.classList.contains('trabalho');
  app.classList.toggle('trabalho', ativas > 0); app.classList.toggle('parado', ativas === 0);
  app.classList.toggle('vendo', !!S.painel);
  $('#legenda').dataset.vazio = ativas === 1 ? 'Uma missão em andamento. Pode continuar falando comigo.' : `${ativas} missões em andamento. Pode continuar falando comigo.`;
  if (era !== (ativas > 0)) { tamanho(); setTimeout(tamanho, 60); }
}
function cartoes() {
  modo(); grade(); ultimas(); galeria();
}
function grade() {   // cada missão em andamento ganha uma coluna com a tela dela
  const g = $('#grade'), ativas = S.missoes.filter(m => m.estado === 'trabalhando').sort((a, b) => a.n - b.n);
  const mostra = ativas.slice(0, 3), vistos = new Set();
  mostra.forEach(m => {
    let el = g.querySelector(`[data-n="${m.n}"]`);
    if (!el) {
      el = document.createElement('div'); el.dataset.n = m.n; el.className = `missao trabalhando ${m.agente}`;
      el.innerHTML = `<div class="m-topo"></div><div class="m-titulo"></div>
        <div class="m-tela"><div class="m-tela-topo"><i></i><i></i><i></i><span></span></div><div class="m-img" hidden></div><div class="m-feed"></div></div>
        <div class="m-acao"><span></span></div><div class="m-passos"></div>
        <form class="m-recado"><input placeholder="Ajustar esta missão agora (ex.: é Valinhos, não Campinas)" autocomplete="off"><button title="Manda o ajuste: a missão é interrompida e segue já com ele">Ajustar</button></form>
        <div class="m-botoes"><button class="ampliar">⛶ Ampliar tela</button><button class="ativid">☰ Ver atividade</button><button class="parar">■ Parar</button></div>`;
      const topo = el.querySelector('.m-topo');
      // número grande: é por ele que se fala com a missão ("na 14, troca a cidade")
      topo.insertAdjacentHTML('beforeend', `<div class="m-num" title="Fale: na missão ${m.n}, ...">${m.n}</div>`);
      topo.append(mascote(m.agente));
      topo.insertAdjacentHTML('beforeend', `<div class="m-quem"><b></b><small>TRABALHANDO</small></div><div class="m-tempo"><small>TEMPO</small><b></b></div>`);
      el.querySelector('.m-recado').onsubmit = ev => {
        ev.preventDefault(); const c = el.querySelector('.m-recado input'), v = c.value.trim();
        if (v) { manda({ t: 'recado', missao: m.n, txt: v }); c.value = ''; SONS.missao(); }
      };
      el.querySelector('.m-tela').onclick = el.querySelector('.ampliar').onclick = () => { const mm = S.missoes.find(x => x.n === m.n) || m; manda({ t: 'abrir', missao: m.n, entrega: mm.telas.length ? '@telas' : 'atividade' }); };
      el.querySelector('.ativid').onclick = () => manda({ t: 'abrir', missao: m.n, entrega: 'atividade' });
      el.querySelector('.parar').onclick = () => { manda({ t: 'parar', v: m.n }); SONS.erro(); };
      g.append(el);
    }
    el.querySelector('.m-quem b').textContent = `${m.agente.toUpperCase()}${m.motor ? ' · ' + m.motor.toUpperCase() : ''}${m.projeto ? ' · ' + m.projeto.toUpperCase() : ''}${m.conversa ? ' · CONVERSA ' + m.conversa : ''}`;
    el.querySelector('.m-quem small').textContent = m.recados ? `AJUSTE NA FILA (${m.recados})` : 'TRABALHANDO';
    el.querySelector('.m-tempo b').textContent = tempo(m);
    el.querySelector('.m-tempo').classList.toggle('estourou', !!m.tempo_max && (Date.now() / 1000 - m.inicio) > m.tempo_max);
    el.querySelector('.m-titulo').textContent = m.titulo;
    const ult = m.telas[m.telas.length - 1], img = el.querySelector('.m-img'), feed = el.querySelector('.m-feed');
    img.hidden = !ult; feed.hidden = !!ult;
    el.querySelector('.m-tela-topo span').textContent = ult ? `CAPTURA · ${idade(ult.mod)}` : 'SEM CAPTURA · ATIVIDADE DO AGENTE';
    if (ult) { const u = `url("${urlM(m, ult)}")`; if (img.dataset.u !== u) { img.dataset.u = u; img.style.backgroundImage = u; } }
    else feed.innerHTML = m.log.slice(-9).map(l => `<div>${esc(limpaTxt(l.txt))}</div>`).join('') || '<div>Começando…</div>';
    el.querySelector('.m-acao span').textContent = limpaTxt(m.etapa);
    const feitos = m.log.filter(l => l.tipo === 'acao').slice(-4, -1);   // passos reais já dados, sem porcentagem inventada
    // os marcos que o agente avisou vêm antes (são o que importa para ele); depois, os últimos passos
    const marcos = (m.marcos || []).slice(-3), resto = Math.max(0, 3 - marcos.length);
    el.querySelector('.m-passos').innerHTML = marcos.map(t => `<span class="marco">${esc(t)}</span>`).join('') + (resto ? feitos.slice(-resto) : []).map(l => `<span>${esc(limpaTxt(l.txt))}</span>`).join('');
    vistos.add(String(m.n));
  });
  g.querySelectorAll('[data-n]').forEach(el => { if (!vistos.has(el.dataset.n)) el.remove(); });
  let mais = g.querySelector('.mais');
  if (ativas.length > 3) { if (!mais) { mais = document.createElement('div'); mais.className = 'mais'; mais.onclick = () => vista('entregas'); g.append(mais); } mais.textContent = `+${ativas.length - 3} em andamento`; }
  else if (mais) mais.remove();
}
setInterval(() => {   // relógios das missões e idade das capturas
  S.missoes.forEach(m => {
    const el = $(`#grade [data-n="${m.n}"]`); if (!el) return;
    el.querySelector('.m-tempo b').textContent = tempo(m);
    const ult = m.telas[m.telas.length - 1]; if (ult) el.querySelector('.m-tela-topo span').textContent = `CAPTURA · ${idade(ult.mod)}`;
  });
}, 1000);
function ultimas() {   // lista do lado (parado) e trilho de baixo (palco ocupado)
  const comEntrega = S.missoes.filter(m => m.entregas.length && m.estado !== 'trabalhando').sort((a, b) => (b.fim || 0) - (a.fim || 0));
  const chave = comEntrega.map(m => m.n + ':' + m.entregas.length + ':' + (m.fim || 0)).join('|') + '#' + S.missoes.filter(m => m.estado === 'trabalhando').map(m => m.n).join(',');
  const u = $('#ultimas');
  $('#qtdEntregas').textContent = S.missoes.length ? `(${S.missoes.length})` : '';
  if (u.dataset.k === chave) return;
  u.dataset.k = chave; u.innerHTML = '';
  $('#semEntregas').hidden = comEntrega.length > 0;
  comEntrega.slice(0, 4).forEach(m => {
    const d = document.createElement('div'); d.className = 'ult';
    d.append(miniTela(m, principal(m)));
    d.insertAdjacentHTML('beforeend', `<div><b>${esc(m.titulo)}</b><small>${esc(resumoTipos(m))}</small></div>`);
    d.onclick = () => manda({ t: 'abrir', missao: m.n });
    u.append(d);
  });
  const t = $('#trilhoItens'); t.innerHTML = '';
  S.missoes.filter(m => m.estado === 'trabalhando').forEach(m => {
    const d = document.createElement('div'); d.className = 'tri ativa'; d.append(mascote(m.agente));
    d.insertAdjacentHTML('beforeend', `<div><b>${esc(m.titulo)}</b><small>trabalhando</small></div>`);
    d.onclick = () => manda({ t: 'fechar' });
    t.append(d);
  });
  comEntrega.slice(0, 5).forEach(m => {
    const d = document.createElement('div'); d.className = 'tri';
    d.append(miniTela(m, principal(m)));
    d.insertAdjacentHTML('beforeend', `<div><b>${esc(m.titulo)}</b><small>${esc(resumoTipos(m))}</small></div>`);
    d.onclick = () => manda({ t: 'abrir', missao: m.n });
    t.append(d);
  });
}
const semAcento = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const GAL = { busca: '', tipo: '' };
function galeria() {   // aba ENTREGAS: todas as missões, da mais nova para a mais velha, com busca pelo assunto e filtro por tipo
  const sec = $('#galeria'); if (sec.hidden) return;
  const g = $('#galLista');
  const chave = S.missoes.map(m => `${m.n}${m.estado}${m.entregas.length}`).join('|') + '#' + GAL.busca + '#' + GAL.tipo;
  if (g.dataset.k === chave) return;
  g.dataset.k = chave; g.innerHTML = '';
  // filtros: só os tipos que existem de verdade, com a contagem
  const cont = {}; S.missoes.forEach(m => new Set(m.entregas.map(e => e.tipo)).forEach(t => { cont[t] = (cont[t] || 0) + 1; }));
  const f = $('#galFiltros'); f.innerHTML = '';
  [['', 'Tudo', S.missoes.length], ...Object.keys(TIPO).filter(t => cont[t]).map(t => [t, TIPO[t], cont[t]])].forEach(([t, nome, q]) => {
    const b = document.createElement('button'); b.textContent = `${nome} ${q}`; if (GAL.tipo === t) b.className = 'on';
    b.onclick = () => { GAL.tipo = t; galeria(); SONS.clique(); }; f.append(b);
  });
  const termos = semAcento(GAL.busca).split(/\s+/).filter(Boolean);
  const lista = [...S.missoes].sort((a, b) => b.n - a.n).filter(m => {
    if (GAL.tipo && !m.entregas.some(e => e.tipo === GAL.tipo)) return false;
    const alvo = semAcento(`${m.titulo} ${m.resumo} ${m.projeto || ''} ${m.processo || ''} ${m.agente} ${m.n} ${m.entregas.map(e => e.nome).join(' ')}`);
    return termos.every(t => alvo.includes(t));
  });
  if (!lista.length) { g.innerHTML = `<p class="gal-vazia">${S.missoes.length ? 'Nada com esse filtro.' : 'Nenhuma missão ainda.'}</p>`; return; }
  lista.forEach(m => {
    const d = document.createElement('div'); d.className = `hist ${m.estado} ${m.agente}`;
    const topo = document.createElement('div'); topo.className = 'hist-topo'; topo.append(mascote(m.agente));
    topo.insertAdjacentHTML('beforeend', `<small>#${m.n} · ${m.agente.toUpperCase()}${m.motor ? ' · ' + esc(m.motor.toUpperCase()) : ''} · ${tempo(m)}</small><span class="selo">${ROT[m.estado] || m.estado}</span>`);
    d.append(topo);
    d.insertAdjacentHTML('beforeend', `<b>${esc(m.titulo)}</b><p>${esc(limpaTxt(m.estado === 'trabalhando' ? m.etapa : (m.resumo || m.etapa)))}</p>`);
    const arqs = document.createElement('div'); arqs.className = 'hist-arqs';
    m.entregas.slice(-6).forEach(e => {
      const mt = miniTela(m, e); mt.insertAdjacentHTML('beforeend', `<span>${esc(e.nome)}</span>`);
      mt.onclick = ev => { ev.stopPropagation(); vista('painel'); manda({ t: 'abrir', missao: m.n, entrega: e.nome }); };
      arqs.append(mt);
    });
    d.append(arqs);
    d.onclick = () => { vista('painel'); manda({ t: 'abrir', missao: m.n, entrega: m.entregas.length ? '' : 'atividade' }); };
    g.append(d);
  });
}
function vista(qual) {
  S.vista = qual;
  for (const [id, v] of [['#vPainel', 'painel'], ['#vEntregas', 'entregas'], ['#vProcessos', 'processos'], ['#vConversas', 'conversas']]) $(id).classList.toggle('ativa', qual === v);
  $('#galeria').hidden = qual !== 'entregas'; $('#processos').hidden = qual !== 'processos'; $('#conversas').hidden = qual !== 'conversas';
  $('#procJanela').hidden = true;
  if (qual === 'entregas') { $('#galLista').dataset.k = ''; galeria(); }
  if (qual === 'processos') carregaProcessos();
  if (qual === 'conversas') carregaConversas();
}
function aviso(titulo, txt, aoClicar, erro) {
  const a = document.createElement('div');
  a.className = 'aviso' + (erro ? ' erro' : '');
  a.innerHTML = `<small>${esc(titulo)}</small>${esc(txt)}`;
  a.onclick = () => { if (aoClicar) aoClicar(); a.remove(); };
  $('#avisos').append(a); setTimeout(() => a.remove(), erro ? 15000 : 9000);
}
function avisar(velhas) {
  S.missoes.forEach(m => {
    const v = velhas.find(x => x.n === m.n);
    if (v && v.estado === 'trabalhando' && m.estado !== 'trabalhando')
      aviso(m.estado === 'concluida' ? 'MISSÃO TERMINADA' : 'MISSÃO ' + (ROT[m.estado] || ''), m.titulo, () => manda({ t: 'abrir', missao: m.n }), m.estado !== 'concluida');
  });
}

/* ---------- etiquetas do topo: o que está valendo, trocável com um clique ---------- */
function etiquetas() {
  const i = S.info || {};
  const modo = i.cerebro_modo || 'auto', quem = i.cerebro === 'local' ? 'Local' : 'Claude';
  $('#chCerebro').textContent = `🧠 ${quem}${modo === 'auto' ? ' · auto' : ''}`;
  $('#chCerebro').className = i.cerebro === 'local' ? 'on' : '';
  $('#chEscuta').textContent = i.escuta === 'nome' ? '👂 Só pelo nome' : '👂 Conversa aberta';
  $('#chEscuta').className = i.escuta === 'nome' ? 'on' : '';
  let pior = null;
  (S.cotas || []).forEach(c => c.janelas.forEach(j => { if (j.usado != null && (!pior || j.usado > pior.u)) pior = { u: j.usado, n: c.nome }; }));
  $('#chCota').textContent = pior ? `${pior.n} ${pior.u}%` : '';
  $('#chCota').className = pior && pior.u >= 85 ? 'alto' : pior && pior.u >= 60 ? 'meio' : '';
}
const ajuste = o => fetch('/api/ajuste', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(o) })
  .then(r => r.json()).then(r => { if (r && r.erro) aviso('AVISO', r.erro, null, true); }).catch(() => {});

/* ---------- aba PROCESSOS ---------- */
const api = (url, corpo) => fetch(url, corpo ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) } : undefined).then(r => r.json());
function carregaProcessos() {
  if (!(S.processos || []).length) $('#procLista').innerHTML = '<p class="gal-vazia">Carregando os processos…</p>';
  api('/api/processos').then(d => { S.processos = d.processos || []; S.agenda = d.agenda || []; S.projetos = d.projetos || []; telaProcessos(); })
    .catch(() => { $('#procLista').innerHTML = '<p class="gal-vazia">Não consegui ler os processos (o Jarvis precisa ser reaberto para esta aba funcionar).</p>'; });
}
function telaProcessos() {
  const g = $('#procLista'); g.innerHTML = '';
  (S.processos || []).forEach(p => {
    const d = document.createElement('div'); d.className = 'proc';
    const pars = p.parametros.map(x => `<i>${esc(x.nome)}${x.padrao ? ' = ' + esc(x.padrao) : ''}</i>`).join('');
    d.innerHTML = `<div class="proc-topo"><b>${esc(p.nome)}</b><small>${esc((p.agente || 'claude').toUpperCase())} · ${esc(p.nivel || 'medio')}${p.tempo_max_min ? ' · até ' + p.tempo_max_min + ' min' : ''}</small></div>
      <p>${esc(p.quando)}</p><div class="proc-pars">${pars}</div>
      <div class="proc-bt"><button class="rodar">▶ Rodar</button><button class="editar">✎ Editar</button><button class="dup">⧉ Duplicar</button></div>`;
    d.querySelector('.rodar').onclick = () => janelaRodar(p);
    d.querySelector('.editar').onclick = () => janelaEditar(p);
    d.querySelector('.dup').onclick = () => janelaEditar(Object.assign({}, p, { id: '', nome: p.nome + ' (cópia)' }));
    g.append(d);
  });
  if (!(S.processos || []).length) g.innerHTML = '<p class="gal-vazia">Nenhum processo ainda.</p>';
  const ag = $('#procAgenda');
  ag.innerHTML = (S.agenda || []).length ? '<h2 class="rot">AGENDADOS</h2>' + S.agenda.map(a => `<div class="linha-item"><b>${esc(a.hora)}</b><span>${esc(a.processo)} · ${esc(a.dias)}</span><small>${a.ultima ? 'rodou em ' + esc(a.ultima) : 'ainda não rodou'}</small></div>`).join('')
    : '<p class="gal-vazia">Nada agendado. Por voz: “todo dia às 8 faz o resumo do dia”.</p>';
}
function fechaJanela() { $('#procJanela').hidden = true; $('#procJanela').innerHTML = ''; }
function janelaRodar(p) {
  const j = $('#procJanela'); j.hidden = false;
  j.innerHTML = `<form class="pj"><div class="pj-topo"><b>▶ ${esc(p.nome)}</b><button type="button" class="x">Fechar ✕</button></div>
    <div class="pj-corpo">${p.parametros.map(x => `<label>${esc(x.nome.replace(/_/g, ' '))}${x.descricao ? ` <small>${esc(x.descricao)}</small>` : ''}<input name="${esc(x.nome)}" placeholder="${esc(x.padrao || '')}" autocomplete="off"></label>`).join('')}
      <label>projeto <small>só se a missão for trabalhar dentro de um projeto seu</small><select name="_projeto"><option value="">(nenhum)</option>${(S.projetos || []).filter(x => x.existe).map(x => `<option>${esc(x.nome)}</option>`).join('')}</select></label>
      <label>algo a mais para esta rodada <small>opcional</small><input name="_pedido" autocomplete="off"></label></div>
    <div class="pj-pe"><button class="forte">▶ Começar a missão</button></div></form>`;
  j.querySelector('.x').onclick = fechaJanela;
  j.querySelector('form').onsubmit = ev => {
    ev.preventDefault(); const f = new FormData(ev.target), pars = {};
    p.parametros.forEach(x => { const v = String(f.get(x.nome) || '').trim(); if (v) pars[x.nome] = v; });
    const bt = ev.target.querySelector('button.forte'); if (bt) { if (bt.disabled) return; bt.disabled = true; }
    api('/api/processos', { rodar: p.id, parametros: pars, pedido: f.get('_pedido') || '', projeto: f.get('_projeto') || '' }).then(r => {
      if (r.ok) { fechaJanela(); vista('painel'); SONS.missao(); } else aviso('NÃO COMEÇOU', r.erro || 'erro', null, true);
    }).catch(() => aviso('NÃO COMEÇOU', 'Sem ligação com o Jarvis.', null, true)).finally(() => { if (bt) bt.disabled = false; });
  };
  const prim = j.querySelector('input'); if (prim) prim.focus();
}
function janelaEditar(p) {
  const j = $('#procJanela'); j.hidden = false; const novo = !p.id;
  const campo = (rot, nome, val, dica) => `<label>${rot}${dica ? ` <small>${dica}</small>` : ''}<input name="${nome}" value="${esc(val || '')}" autocomplete="off"></label>`;
  j.innerHTML = `<form class="pj larga"><div class="pj-topo"><b>${novo ? '+ Novo processo' : '✎ ' + esc(p.nome)}</b><button type="button" class="x">Fechar ✕</button></div>
    <div class="pj-corpo duas">
      <div>${campo('nome', 'nome', p.nome)}${campo('quando usar', 'quando', p.quando, 'uma linha: é por ela que o Jarvis escolhe este processo')}
        ${campo('como você costuma pedir', 'gatilhos', p.gatilhos, 'palavras separadas por vírgula')}
        ${campo('parâmetros', 'parametros', p.parametros_txt, 'nicho (descrição); cidade; nota_minima = 4,5')}
        <div class="pj-linha"><label>agente<select name="agente"><option${p.agente !== 'codex' ? ' selected' : ''}>claude</option><option${p.agente === 'codex' ? ' selected' : ''}>codex</option></select></label>
          <label>nível<select name="nivel">${['leve', 'medio', 'pesado'].map(n => `<option${(p.nivel || 'medio') === n ? ' selected' : ''}>${n}</option>`).join('')}</select></label>
          <label>tempo máximo (min)<input name="tempo_max_min" value="${esc(p.tempo_max_min || '')}"></label></div>
        ${campo('entregas esperadas', 'entregas', p.entregas, 'nomes dos arquivos')}</div>
      <label class="rot-corpo">roteiro <small>o passo a passo que o agente segue; use {parametro} para os parâmetros</small><textarea name="corpo" spellcheck="false">${esc(p.corpo || 'Objetivo: \n\n1. ')}</textarea></label></div>
    <div class="pj-pe"><button class="forte">Salvar</button></div></form>`;
  j.querySelector('.x').onclick = fechaJanela;
  j.querySelector('form').onsubmit = ev => {
    ev.preventDefault(); const o = Object.fromEntries(new FormData(ev.target)); o.id = p.id || '';
    const bt = ev.target.querySelector('button.forte'); if (bt) { if (bt.disabled) return; bt.disabled = true; }
    api('/api/processos', o).then(r => { if (r.ok) { fechaJanela(); carregaProcessos(); SONS.pronto(); } else aviso('NÃO SALVOU', r.erro || 'erro', null, true); })
      .catch(() => aviso('NÃO SALVOU', 'Sem ligação com o Jarvis.', null, true)).finally(() => { if (bt) bt.disabled = false; });
  };
}

/* ---------- aba CONVERSAS: conversas numeradas do Claude Code, projetos e planilhas de leads ---------- */
function carregaConversas() {
  $('#convLista').innerHTML = '<p class="gal-vazia">Lendo…</p>';
  api('/api/conversas').then(d => {
    const g = $('#convLista'); g.innerHTML = '';
    (d.conversas || []).forEach(c => {
      const el = document.createElement('form'); el.className = 'conv';
      el.innerHTML = `<div class="m-num">${c.numero}</div><div class="conv-txt"><b>${esc(c.titulo)}</b><small>${esc(c.projeto)} · ${idade(c.mod).toLowerCase()}${c.missao ? ' · já virou a missão #' + c.missao : ''}</small></div>
        <input placeholder="O que pedir nesta conversa (ou diga: na conversa ${c.numero}, ...)" autocomplete="off"><button>Continuar</button>`;
      el.onsubmit = ev => {
        ev.preventDefault(); const v = el.querySelector('input').value.trim();
        api('/api/conversas', { numero: c.numero, instrucao: v }).then(r => { if (r.ok) { vista('painel'); SONS.missao(); } else aviso('NÃO DEU', r.erro || 'erro', null, true); });
      };
      g.append(el);
    });
    if (!(d.conversas || []).length) g.innerHTML = '<p class="gal-vazia">Nenhuma conversa recente do Claude Code neste computador.</p>';
    $('#projLista').innerHTML = (d.projetos || []).map(p => `<div class="linha-item${p.existe ? '' : ' falta'}"><b>${esc(p.nome)}</b><span>${esc(p.pasta)}</span><small>${p.existe ? 'diga: “no ' + esc(p.nome) + ', ...”' : 'pasta não encontrada'}</small></div>`).join('') || '<p class="gal-vazia">Nenhum projeto cadastrado.</p>';
    $('#leadsLista').innerHTML = (d.leads || []).map(l => `<div class="linha-item"><b>${esc(l.nicho)}</b><span>${esc(l.cidade)} · ${l.total} empresas</span><small>${Object.entries(l.por_situacao).map(([k, v]) => `${v} ${esc(k.replace(/_/g, ' '))}`).join(' · ')}</small></div>`).join('') || '<p class="gal-vazia">Nenhuma planilha ainda. Ela nasce na primeira prospecção.</p>';
  }).catch(() => { $('#convLista').innerHTML = '<p class="gal-vazia">Não consegui ler as conversas (o Jarvis precisa ser reaberto para esta aba funcionar).</p>'; });
}

/* ---------- painel ---------- */
let painelChave = '';
function painel(soAtualiza) {
  const p = $('#painel');
  modo();
  if (!S.painel) { p.hidden = true; painelChave = ''; return; }
  const m = S.missoes.find(x => x.n === S.painel.missao);
  if (!m) { p.hidden = true; return; }
  p.hidden = false;
  const selo = p.querySelector('.p-selo'); selo.className = 'p-selo ' + m.estado;
  selo.textContent = `MISSÃO #${String(m.n).padStart(2, '0')} ${{ trabalhando: 'EM ANDAMENTO', concluida: 'CONCLUÍDA', erro: 'NÃO DEU CERTO', parada: 'PARADA' }[m.estado] || ''}`;
  p.querySelector('.p-titulo').textContent = m.titulo;
  p.querySelector('.p-ajuste').onclick = () => { const c = $('#campo'); c.value = `Na missão ${m.n}, ajusta: `; c.focus(); };
  p.querySelector('.p-pasta').onclick = () => manda({ t: 'pasta', missao: m.n });
  const abas = [];
  const a = m.entregas.find(e => /^antes\./i.test(e.nome)), d = m.entregas.find(e => /^depois\./i.test(e.nome));
  if (a && d) abas.push({ id: '@antes_depois', nome: 'Antes e depois' });
  const ROTULO = { site: '🌐 ', imagem: '🖼 ', video: '▶ ', audio: '♪ ', texto: '📄 ', pdf: '📄 ' };
  m.entregas.forEach(e => { if (!(a && d && (e === a || e === d))) abas.push({ id: e.rel, nome: (ROTULO[e.tipo] || '') + e.nome.replace(/\.[^.]+$/, ''), e }); });
  if (m.telas.length) abas.push({ id: '@telas', nome: `Telas (${m.telas.length})` });
  abas.push({ id: '@atividade', nome: 'Atividade' });
  let atual = abas.find(x => x.id === S.painel.entrega) || abas.find(x => x.e && x.e === principal(m)) || abas[0];
  p.querySelector('.p-tipo').textContent = atual.e ? `${TIPO[atual.e.tipo] || 'Arquivo'} · ${atual.e.nome}` : atual.nome;
  const nav = p.querySelector('.p-abas'); nav.innerHTML = '';
  abas.forEach(x => {
    if (x.id === '@telas' || (x.id === '@atividade' && !m.telas.length)) nav.insertAdjacentHTML('beforeend', '<span class="sep"></span>');
    const b = document.createElement('button'); b.textContent = x.nome; if (x === atual) b.className = 'ativa';
    b.onclick = () => { S.painel.entrega = x.id; painel(); SONS.clique(); };
    nav.append(b);
  });
  const mod = atual.e ? atual.e.mod : atual.id === '@atividade' ? m.log.length + ':' + ((m.log[m.log.length - 1] || {}).t || 0) : atual.id === '@telas' ? m.telas.length + ':' + ((m.telas[m.telas.length - 1] || {}).mod || 0) : (a.mod + d.mod);
  const chave = `${m.n}|${atual.id}|${mod}`;
  if (chave === painelChave) return;
  painelChave = chave;
  const corpo = p.querySelector('.p-corpo'); corpo.innerHTML = '';
  const url = e => `/m/${m.n}/${encodeURI(e.rel)}?v=${e.mod}`;
  if (atual.id === '@atividade') {
    const div = document.createElement('div'); div.className = 'ativ';
    div.innerHTML = m.log.map(l => `<div class="${l.tipo}"><time>${new Date(l.t * 1000).toLocaleTimeString('pt-BR').slice(0, 5)}</time><span>${esc(l.txt)}</span></div>`).join('') || '<div><span>Ainda sem atividade.</span></div>';
    corpo.append(div); corpo.scrollTop = corpo.scrollHeight;
  } else if (atual.id === '@telas') {
    const g = document.createElement('div'); g.className = 'telas';
    [...m.telas].reverse().forEach(t => { const i = new Image(); i.src = url(t); i.onclick = () => window.open(i.src); g.append(i); });
    corpo.append(g);
  } else if (atual.id === '@antes_depois') {
    const et = document.createElement('div'); et.className = 'ad-et';
    et.innerHTML = '<span class="a">◀ ANTES</span><span class="d">DEPOIS ▶</span>';
    const w = document.createElement('div'); w.className = 'ad';
    w.innerHTML = `<img src="${url(a)}"><img class="depois" src="${url(d)}"><div class="linha"><span class="pega"></span></div>`;
    const move = ev => { const r = w.getBoundingClientRect(); w.style.setProperty('--x', Math.max(0, Math.min(100, (ev.clientX - r.left) / r.width * 100)) + '%'); };
    w.onpointerdown = ev => { move(ev); w.onpointermove = move; w.setPointerCapture(ev.pointerId); };
    w.onpointerup = () => { w.onpointermove = null; };
    // as duas capturas podem ter alturas diferentes: a moldura fica com a maior
    w.querySelectorAll('img').forEach(i => i.onload = () => { w.style.minHeight = Math.max(...[...w.querySelectorAll('img')].map(x => x.offsetHeight)) + 'px'; });
    corpo.append(et, w); corpo.scrollTop = 0;
  } else {
    const e = atual.e;
    if (e.tipo === 'site' || e.tipo === 'pdf') {
      const f = document.createElement('iframe');
      if (e.tipo === 'site') f.sandbox = 'allow-scripts allow-forms allow-popups allow-modals';   // sem acesso ao painel
      f.src = url(e); corpo.append(f);
    }
    else if (e.tipo === 'imagem') { const i = new Image(); i.className = 'cheia'; i.src = url(e); corpo.append(i); }
    else if (e.tipo === 'video') { const v = document.createElement('video'); v.src = url(e); v.controls = true; v.autoplay = true; corpo.append(v); }
    else if (e.tipo === 'audio') { const v = document.createElement('audio'); v.src = url(e); v.controls = true; v.style.margin = '30px'; corpo.append(v); }
    else fetch(url(e)).then(r => r.text()).then(t => { const pre = document.createElement('pre'); pre.textContent = t; corpo.append(pre); });
  }
}

/* ---------- esfera voxel ---------- */
const cv = $('#esfera'), g = cv.getContext('2d');
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
window.FORMAS = FORMAS;
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
const formaAtual = () => { const f = document.getElementById('app').dataset.forma; return PALETA_FORMA[f] ? f : 'orbe'; };
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
// enfeites desenhados por cima: olhos do fantasma, raios da entidade elétrica
function formaEnfeite(fm, cx, cy, R, t, e) {
  if (fm === 'fantasma') {
    const pisca = (t % 4.2) < 0.12, w = R * 0.15, h = pisca ? R * 0.03 : R * 0.22, oy = cy - R * 0.08 - h / 2;
    g.fillStyle = 'rgba(12,16,28,.92)';
    g.fillRect(cx - R * 0.32 - w / 2, oy, w, h); g.fillRect(cx + R * 0.32 - w / 2, oy, w, h);
    if (e === 'falando') { const b = R * (0.06 + V.nivel * 0.16); g.fillRect(cx - b / 2, cy + R * 0.22, b, b); }
  } else if (fm === 'eletrica') {
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
  dormindo: { vel: .12, amp: .03, raio: .72, espalha: 0 }, ouvindo: { vel: .35, amp: .05, raio: .92, espalha: .1 },
  pensando: { vel: 1.6, amp: .1, raio: .8, espalha: .02 }, falando: { vel: .5, amp: .06, raio: .95, espalha: 0 },
  trabalhando: { vel: .7, amp: .05, raio: .82, espalha: .04 }, mudo: { vel: .05, amp: .01, raio: .66, espalha: 0 },
};
function tamanho() {
  const r = devicePixelRatio || 1, b = cv.getBoundingClientRect();
  cv.width = b.width * r; cv.height = b.height * r;
}
addEventListener('resize', tamanho);
// o mouse mexe com a esfera: ela vira o rosto para ele e os cubos perto do cursor se afastam
const MOUSE = { x: -9999, y: -9999, nx: 0, ny: 0, dentro: false };
$('#palco').addEventListener('pointermove', ev => {
  const b = cv.getBoundingClientRect(), r = devicePixelRatio || 1;
  MOUSE.x = (ev.clientX - b.left) * r; MOUSE.y = (ev.clientY - b.top) * r; MOUSE.dentro = true;
  MOUSE.nx = (ev.clientX - b.left) / b.width - .5; MOUSE.ny = (ev.clientY - b.top) / b.height - .5;
});
$('#palco').addEventListener('pointerleave', () => { MOUSE.dentro = false; MOUSE.x = MOUSE.y = -9999; });
V.olhaX = 0; V.olhaY = 0;
let tAnt = performance.now();
function fpsAlvo() {
  if (!document.hasFocus()) return 15;
  const e = S.mudo ? 'mudo' : estadoVisual();
  return (e === 'dormindo' || e === 'mudo') && !MOUSE.dentro ? 30 : 60;
}
function quadro(agora) {
  if (agora - tAnt < 1000 / fpsAlvo() - 3) { requestAnimationFrame(quadro); return; }
  const dt = Math.min(.05, (agora - tAnt) / 1000); tAnt = agora;
  const fm = formaAtual(), e = S.mudo ? 'mudo' : estadoVisual(), alvo = ALVO[e], corJ = document.getElementById('app').dataset.corJarvis,
    pal = /^#[0-9a-f]{6}$/i.test(corJ || '') ? paletaDaCor(corJ, e) : (PALETA_FORMA[fm] || PALETA)[e], k = 1 - Math.pow(.02, dt);
  for (const c of ['vel', 'amp', 'raio', 'espalha']) V[c] += (alvo[c] - V[c]) * k;
  for (let i = 0; i < 3; i++) { V.cor1[i] += (pal[0][i] - V.cor1[i]) * k; V.cor2[i] += (pal[1][i] - V.cor2[i]) * k; }
  let nv = 0;
  if (e === 'falando' && analisador && tocando) {
    analisador.getByteFrequencyData(dadosAn);
    let s = 0; for (let i = 2; i < 40; i++) s += dadosAn[i]; nv = Math.min(1, s / 38 / 150);
  } else if (e === 'ouvindo') nv = S.nivelMic;
  else if (e === 'dormindo') nv = S.nivelMic * .25;
  V.nivel += (nv - V.nivel) * (nv > V.nivel ? .5 : .12);
  V.rot += dt * V.vel;

  const W = cv.width, H = cv.height, faixa = H < 260 * (devicePixelRatio || 1), coluna = !faixa && document.getElementById('app').classList.contains('trabalho');
  // coluna (com missões): a fala fica no alto e o mago no chão, então o orbe desce um pouco e cresce até a largura deixar
  const desvio = { fantasma: -.16, chama: .14 }[fm] || 0, flutua = (fm === 'fantasma' || fm === 'espirito') ? Math.sin(agora / 650) * .035 : 0;
  const cx = W / 2, cy0 = faixa ? H / 2 : coluna ? H * .54 : H * .4,
    R = (faixa ? Math.min(W, H) * .42 : coluna ? Math.min(W * .35, H * .27) : Math.min(W, H * .9) * .3) * V.raio;   // .35: o anel de nível (1,42 R) cabe dentro da coluna
  const cy = cy0 + R * (desvio + flutua);
  V.cx = cx; V.cy = cy; V.R = R;
  g.clearRect(0, 0, W, H);
  V.olhaX += ((MOUSE.dentro ? MOUSE.nx : 0) - V.olhaX) * .08; V.olhaY += ((MOUSE.dentro ? MOUSE.ny : 0) - V.olhaY) * .08;
  const t = agora / 1000, cs = Math.cos(V.rot + V.olhaX * 1.2), sn = Math.sin(V.rot + V.olhaX * 1.2), inc = .35 + V.olhaY * .9, ci = Math.cos(inc), si = Math.sin(inc);
  const lista = [];
  for (const p of pts) {
    let d = 1 + V.amp * Math.sin(t * 1.3 * p.s + p.f);
    if (e === 'falando') d += V.nivel * .34 * (.5 + .5 * Math.sin(p.y * 7 - t * 9));
    else if (e === 'ouvindo') d += V.nivel * .5 * p.s * (.4 + .6 * Math.abs(Math.sin(p.f * 3 + t * 5)));
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
  for (const [x, y, z, p] of lista) {
    const prof = (z + 1.4) / 2.8, esc2 = .55 + prof * .75, l = base * esc2 * (.75 + .5 * p.s * .6);
    let px = cx + x * R, py = cy + y * R;
    const mdx = px - MOUSE.x, mdy = py - MOUSE.y, md = Math.hypot(mdx, mdy), alc = R * .55;
    if (md < alc && md > .01) { const f = (1 - md / alc) ** 2 * R * .28; px += mdx / md * f; py += mdy / md * f; }
    const mix = .5 + .5 * Math.sin(p.f + t * .6), luz = .35 + prof * .75;
    const c = i => Math.min(255, (V.cor1[i] * (1 - mix) + V.cor2[i] * mix) * luz) | 0;
    const r = c(0), gg = c(1), b = c(2);
    g.fillStyle = `rgb(${r},${gg},${b})`; g.fillRect(px - l / 2, py - l / 2, l, l);               // frente
    g.fillStyle = `rgb(${Math.min(255, r * 1.35) | 0},${Math.min(255, gg * 1.35) | 0},${Math.min(255, b * 1.35) | 0})`;
    g.beginPath(); g.moveTo(px - l / 2, py - l / 2); g.lineTo(px - l / 2 + l * .3, py - l / 2 - l * .3);
    g.lineTo(px + l / 2 + l * .3, py - l / 2 - l * .3); g.lineTo(px + l / 2, py - l / 2); g.fill();  // topo
    g.fillStyle = `rgb(${r * .55 | 0},${gg * .55 | 0},${b * .55 | 0})`;
    g.beginPath(); g.moveTo(px + l / 2, py - l / 2); g.lineTo(px + l / 2 + l * .3, py - l / 2 - l * .3);
    g.lineTo(px + l / 2 + l * .3, py + l / 2 - l * .3); g.lineTo(px + l / 2, py + l / 2); g.fill();  // lado
  }
  if (!faixa) formaEnfeite(fm, cx, cy, R, t, e);
  // anel de nível, em blocos
  const blocos = faixa ? 0 : 48, on = Math.round(V.nivel * blocos);
  for (let i = 0; i < blocos; i++) {
    const a = -Math.PI / 2 + (i / blocos) * Math.PI * 2, rr = R * 1.42, lado = Math.max(3, R * .035);
    g.fillStyle = i < on ? `rgb(${V.cor1.map(v => v | 0)})` : '#ffffff10';
    g.fillRect(cx + Math.cos(a) * rr - lado / 2, cy + Math.sin(a) * rr * .98 - lado / 2, lado, lado);
  }
  requestAnimationFrame(quadro);
}

/* ---------- teclado e cliques ---------- */
$('#form').onsubmit = e => {
  e.preventDefault(); const c = $('#campo'); if (!c.value.trim()) return;
  if (!S.conectado) { aviso('SEM LIGAÇÃO', 'O Jarvis está reconectando. O texto ficou no campo: envie de novo em instantes.', null, true); return; }
  audio(); manda({ t: 'texto', v: c.value.trim() }); c.value = '';
};
addEventListener('keydown', e => {
  if (e.key === 'Escape') { if (!$('#procJanela').hidden) fechaJanela(); else if (S.painel) manda({ t: 'fechar' }); else vista('painel'); if (document.activeElement) document.activeElement.blur(); return; }
  if (e.code === 'Space' && !/^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName || '')) { e.preventDefault(); audio(); manda({ t: 'mudo', v: !S.mudo }); SONS.clique(); }
});
// onde o orbe está na tela (centro e raio de clique): clicar nele acorda ou cala; o resto do palco é chão do mago
function orbeTela() {
  if (!V.R) return null;
  const b = cv.getBoundingClientRect(), r = devicePixelRatio || 1;
  return b.width ? { x: b.left + V.cx / r, y: b.top + V.cy / r, r: Math.max(60, V.R * 1.5 / r) } : null;
}
$('#palco').onclick = ev => {
  const o = orbeTela();
  if (window.MAGO && o && Math.hypot(ev.clientX - o.x, ev.clientY - o.y) > o.r) return;   // fora do orbe: é o mago quem responde
  audio(); SONS.clique(); cv.classList.remove('pulso'); void cv.offsetWidth; cv.classList.add('pulso');
  if (S.mudo) { aviso('MICROFONE DESLIGADO', 'Aperte ESPAÇO ou o botão ● para ele ouvir.', null, true); return; }
  if (S.estado === 'falando') manda({ t: 'calar' }); else manda({ t: 'acordar' });
};
$('#btMini').onclick = () => manda({ t: 'janela', modo: 'mini' });
$('#vPainel').onclick = () => { vista('painel'); SONS.clique(); };
$('#vEntregas').onclick = () => { if (S.painel) manda({ t: 'fechar' }); vista('entregas'); SONS.clique(); };
$('#vProcessos').onclick = () => { if (S.painel) manda({ t: 'fechar' }); vista('processos'); SONS.clique(); };
$('#vConversas').onclick = () => { if (S.painel) manda({ t: 'fechar' }); vista('conversas'); SONS.clique(); };
$('#procNovo').onclick = () => janelaEditar({ id: '', nome: '', parametros: [], agente: 'claude', nivel: 'medio' });
let galEspera = 0;
$('#galBusca').oninput = ev => { GAL.busca = ev.target.value; clearTimeout(galEspera); galEspera = setTimeout(galeria, 180); };
$('#chCerebro').onclick = () => { const m = (S.info || {}).cerebro_modo || 'auto'; ajuste({ cerebro: m === 'auto' ? 'local' : m === 'local' ? 'claude' : 'auto' }); SONS.clique(); };
$('#chEscuta').onclick = () => { ajuste({ escuta: (S.info || {}).escuta === 'nome' ? 'aberta' : 'nome' }); SONS.clique(); };
$('#mic').onclick = () => { audio(); manda({ t: 'mudo', v: !S.mudo }); SONS.clique(); };
new ResizeObserver(() => tamanho()).observe(cv);
let pararArmado = 0;
$('#btParar').onclick = () => {
  const b = $('#btParar');
  if (Date.now() - pararArmado > 3000) {      // primeiro clique só arma: missão longa não morre por um clique perdido
    pararArmado = Date.now(); b.classList.add('armado'); b.textContent = 'Confirmar?'; SONS.clique();
    setTimeout(() => { if (Date.now() - pararArmado >= 3000) { b.classList.remove('armado'); b.textContent = 'Parar tudo'; } }, 3100);
    return;
  }
  pararArmado = 0; b.classList.remove('armado'); b.textContent = 'Parar tudo';
  manda({ t: 'parar', v: 'todas' }); manda({ t: 'calar' }); SONS.erro();
};
$('#btZerar').onclick = () => { manda({ t: 'zerar' }); legenda(''); $('#ultima').textContent = ''; };
$('#painel .p-fechar').onclick = () => manda({ t: 'fechar' });
$('#btEntrar').onclick = () => { audio(); $('#entrada').hidden = true; SONS.acordar(); tocarProxima(); };
addEventListener('pointerdown', () => audio(), { once: true });
addEventListener('pointerdown', () => manda({ t: 'aqui' }));   // esta é a tela em uso: a voz toca aqui
addEventListener('focus', () => manda({ t: 'aqui' }));

tamanho(); requestAnimationFrame(quadro); ligar();
