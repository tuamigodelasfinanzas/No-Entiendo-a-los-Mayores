// Runs inside the browser. window.DATA = { ep, beats: [{start, dur, lines: [{start, dur, who, text}]}], w, h, fps }.
// window.frame(t) draws the whole video at second t. Every visual comes from the episode built by src/director.mjs,
// so the same script renders in another language by translating its strings.
// Adapted from zero-understands/src/stage.js: same keyframes, easing, camera and transitions; the actors are E and R.
(() => {
  const { kid, PROPS, COLORS, FONT, INK, esc, wrap, SHARED_DEFS } = window.PUPPETS;
  const D = window.DATA, ep = D.ep, W = D.w, H = D.h;
  const root = document.getElementById('stage');
  // the life layer (see alive() below) is on unless the episode sets life: false or the render runs with CDM_LIFE=0
  const LIFE = D.ep.life ?? D.life ?? true;

  const EASE = {
    lin: x => x, step: () => 0,
    in: x => x * x * x, out: x => 1 - Math.pow(1 - x, 3),
    io: x => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2,
    back: x => { const c = 1.9; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
    pop: x => { const c = 3.2; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
  };
  const META = new Set(['t', 'u', 'l', 'le', 'e', 'end']);
  const isNum = v => typeof v === 'number';
  const isNumArr = v => Array.isArray(v) && v.every(isNum);

  // key time in seconds from the beat start: t (s), u (fraction of beat), l (line index: starts at that line),
  // le (line index: when that line ends), end (s before beat end)
  function keyTime(k, beat) {
    if (k.end != null) return beat.dur - k.end;
    let t = 0;
    if (k.l != null) { const ln = beat.lines[k.l]; t = ln ? ln.start - beat.start : 0; }
    if (k.le != null) { const ln = beat.lines[k.le]; t = ln ? ln.start + ln.dur - beat.start : 0; }
    if (k.u != null) t += k.u * beat.dur;
    if (k.t != null) t += k.t;
    return t;
  }

  // resolve actor state at local time lt from its keys (values persist; numbers ease to the next key)
  function stateAt(keys, lt, beat) {
    const ks = keys.map(k => ({ k, at: keyTime(k, beat) })).sort((a, b) => a.at - b.at);
    const st = {};
    // before its first key an actor holds that key's values
    if (ks.length) for (const p in ks[0].k) if (!META.has(p)) st[p] = ks[0].k[p];
    for (let i = 0; i < ks.length; i++) {
      const { k, at } = ks[i];
      if (at <= lt) { for (const p in k) if (!META.has(p)) st[p] = k[p]; continue; }
      // k is the next key: ease numeric props from current state towards it
      const prev = i > 0 ? ks[i - 1].at : 0;
      const span = Math.max(1e-6, at - prev);
      const x = Math.min(1, Math.max(0, (lt - prev) / span));
      const e = (EASE[k.e] || EASE.io)(x);
      for (const p in k) {
        if (META.has(p) || !(p in st)) continue;
        const a = st[p], b = k[p];
        if (isNum(a) && isNum(b)) st[p] = a + (b - a) * e;
        else if (isNumArr(a) && isNumArr(b) && a.length === b.length) st[p] = a.map((v, j) => v + (b[j] - v) * e);
      }
      break;
    }
    return st;
  }

  // final state of every actor of a beat, so the next beat can continue from it (inherit: true)
  const finals = [];
  D.beats.forEach((b, i) => {
    const spec = ep.beats[i];
    const prev = spec.inherit && i > 0 ? finals[i - 1] : {};
    b.actors = (spec.actors || []).map((a, j) => {
      const id = a.id || `${a.type}-${j}`;
      const base = prev[id] ? Object.assign({}, prev[id]) : null;
      const keys = base ? [Object.assign({ t: 0 }, base), ...a.k.map(k => Object.assign({}, k))] : a.k;
      // a key with no time sits at t=0
      keys.forEach(k => { if (k.t == null && k.u == null && k.l == null && k.le == null && k.end == null) k.t = 0; });
      return { id, type: a.type, keys, z: a.z ?? 0, depth: a.depth };
    });
    finals[i] = {};
    for (const a of b.actors) finals[i][a.id] = stateAt(a.keys, b.dur + 1, b);
  });

  // ---------- life: principles of animation applied on top of the keyframes ----------
  // The keys say where a kid must be; this layer decides how he gets there. Sampling the keyed motion a moment
  // before and after "now" gives anticipation and overshoot (second difference of x / y), leaning into the motion,
  // the head dragging behind the body, squash on vertical impulses, and an idle layer (breathing, weight shift,
  // small head drift) so nobody is ever frozen. Talking adds small nods and a little bounce.
  const clamp = (v, a) => Math.max(-a, Math.min(a, v));
  function alive(a, st, beat, lt, gt, sp) {
    const at = t => stateAt(a.keys, Math.min(beat.dur, Math.max(0, t)), beat);
    const h = 0.14;
    const P = at(lt - h), N = at(lt + h);
    const s = st.s ?? 1;
    const seed = (a.id.charCodeAt(0) || 0) * 0.37;
    const d2 = (k) => { const p0 = P[k] ?? st[k] ?? 0, p1 = st[k] ?? 0, p2 = N[k] ?? st[k] ?? 0; const a2 = p2 - 2 * p1 + p0; return Math.abs(a2) > 260 || Math.abs(p2 - p0) > 900 ? [0, 0] : [a2, (p2 - p0) / (2 * h)]; };
    const [ax, vx] = d2('x'), [ay, vy] = d2('y');
    st.x = (st.x ?? 0) - clamp(ax * 0.3, 8 * s);
    st.y = (st.y ?? 0) - clamp(ay * 0.18, 6 * s);
    st.lean = (st.lean ?? 0) + clamp(vx / s * 0.01, 5) - clamp(ax / s * 0.08, 4);
    st.headR = (st.headR ?? 0) + clamp(-vx / s * 0.006, 4) + clamp(ax / s * 0.05, 3);
    st.squash = (st.squash ?? 1) * (1 - Math.min(0.06, Math.abs(ay) / s * 0.0016) + Math.min(0.04, Math.abs(vy) / s * 0.00005));
    // eyes lead: look where the keys will be looking a moment from now
    const ahead = at(lt + 0.12);
    if (isNumArr(ahead.look)) st.look = ahead.look;
    // idle: breathing (3.4 s), weight shift (5.3 s), head drift
    const br = Math.sin(gt * 2 * Math.PI / 3.4 + seed);
    st.squash = (st.squash ?? 1) * (1 + 0.006 * br);
    st.lean = (st.lean ?? 0) + 0.8 * Math.sin(gt * 2 * Math.PI / 5.3 + seed * 0.7);
    st.headR = (st.headR ?? 0) + 1.2 * Math.sin(gt * 2 * Math.PI / 4.1 + seed) + 0.5 * Math.sin(gt * 1.3 + seed * 2);
    // talking: small nods and a light bounce instead of a rigid head
    if (sp >= 0) {
      const k = Math.min(1, sp * 4);
      st.headR += 2.2 * Math.sin(sp * 5.5) * k;
      st.headY = (st.headY ?? 0) + 2.5 * Math.sin(sp * 9) * k;
      st.squash *= 1 + 0.008 * Math.sin(sp * 11) * k;
    }
    return st;
  }

  // tout / tin: { type: 'zoom' | 'iris' | 'wipe' | 'fall', x, y (world point for zoom/iris), dur, color }
  //   zoom: the camera dives into a point (a screen, a head, a door) and the next beat opens from it
  //   iris: a circle closes on a point; wipe: a band of colour crosses the frame; fall: the world drops away upwards
  function transition(spec, beat, lt) {
    const out = {};
    const one = (t, k, dir) => { // k: 0 → 1 progress into the cut (dir 'out') or out of it ('in')
      const x = t.x ?? W / 2, y = t.y ?? H / 2, col = t.color ?? '#111111';
      const e = dir === 'out' ? EASE.in(k) : EASE.out(1 - k);    // e = 1 at the cut
      if (t.type === 'zoom') { out.zoom = 1 + e * (t.z ?? 9); out.zx = x; out.zy = y; out.pull = Math.min(1, e * 1.6); if (e > 0.75) out.over = `<rect width="${W}" height="${H}" fill="${col}" opacity="${((e - 0.75) / 0.25).toFixed(3)}"/>`; }
      if (t.type === 'iris') { const r = Math.hypot(W, H) * (1 - e); out.over = `<path fill-rule="evenodd" fill="${col}" d="M0 0H${W}V${H}H0Z M${x - r} ${y} a${r} ${r} 0 1 0 ${2 * r} 0 a${r} ${r} 0 1 0 ${-2 * r} 0Z"/>`; }
      if (t.type === 'wipe') { const p = dir === 'out' ? EASE.io(k) : 1 + EASE.io(k); const X = -W * 1.3 + p * W * 1.3; out.over = `<path fill="${t.color ?? '#FFC93C'}" d="M${X} 0 H${X + W * 1.15} L${X + W * 1.3} ${H} H${X + W * 0.15} Z"/>`; }
      if (t.type === 'fall') out.dy = (dir === 'out' ? 1 : -1) * e * H * 1.2;
    };
    if (spec.tout) { const d = spec.tout.dur ?? 0.5, k = (lt - (beat.dur - d)) / d; if (k > 0) one(spec.tout, Math.min(1, k), 'out'); }
    if (spec.tin) { const d = spec.tin.dur ?? 0.5, k = lt / d; if (k < 1) one(spec.tin, Math.max(0, k), 'in'); }
    return out;
  }

  function speaking(beat, who, gt) {
    for (const ln of beat.lines) if ((ln.who === who || ln.who === 'ambos') && gt >= ln.start && gt <= ln.start + ln.dur) return gt - ln.start;
    return -1;
  }

  function draw(beat, gt) {
    const lt = gt - beat.start;
    const spec = ep.beats[beat.i];
    const cam = spec.cam ? stateAt(spec.cam.map(k => Object.assign({}, k, (k.t == null && k.u == null && k.l == null && k.le == null && k.end == null) ? { t: 0 } : {})), lt, beat) : {};
    let cz = cam.z ?? 1, cx = cam.x ?? W / 2, cy = cam.y ?? H / 2;
    // integrated transitions (docs/direccion-visual.md §14): tout ends a beat, tin opens the next one
    const tr = transition(spec, beat, lt);
    if (tr.zoom) { cz *= tr.zoom; cx += (tr.zx - cx) * tr.pull; cy += (tr.zy - cy) * tr.pull; }
    if (tr.dy) cy += tr.dy;
    const shake = cam.shake ? `translate(${(Math.sin(gt * 61) * cam.shake).toFixed(1)} ${(Math.cos(gt * 47) * cam.shake).toFixed(1)})` : '';
    let world = '', overlay = '';
    const mouths = {};
    const actors = beat.actors.slice().sort((a, b) => a.z - b.z);
    for (const a of actors) {
      const st = stateAt(a.keys, lt, beat);
      if (st.o === 0 || st.hide) continue;
      let svg = '';
      if (a.type === 'kid') {
        // blink every ~3.9 s (each kid on his own phase) unless the key fixes it with blink: false
        if (st.blink === false) st.blink = 0;
        else if (st.blink == null) { const ph = (gt + (st.who === 'e' ? 0.9 : 2.4)) % 3.9; st.blink = ph < 0.14 ? Math.sin(ph / 0.14 * Math.PI) : 0; }
        const sp = speaking(beat, st.who, gt);
        // mouth: a fast, uneven open/close while the line plays (sum of two sines, never perfectly regular)
        st.talk = sp >= 0 && st.mute !== true ? Math.max(0, 0.55 + 0.35 * Math.sin(sp * 17.3) + 0.25 * Math.sin(sp * 29.1 + 1.3)) * Math.min(1, sp * 8) : 0;
        const ln = sp >= 0 ? beat.lines.find(l => (l.who === st.who || l.who === 'ambos') && gt >= l.start && gt <= l.start + l.dur) : null;
        if (ln && gt > ln.start + ln.dur - 0.08) st.talk = 0;
        const ks = LIFE && st.life !== false ? alive(a, st, beat, lt, gt, sp) : { ...st };
        svg = kid(ks);
        // where the mouth is on screen, so the caption bubble can point at whoever speaks
        const rig = window.KID_RIG[ks.who], m = rig.jaw || rig.mouth, ksc = ks.s ?? 1;
        let wx = ks.x + (m.x - rig.center) * ksc * (ks.flip ? -1 : 1) + (ks.headX ?? 0) * ksc, wy = ks.y + (m.y - rig.feet) * ksc + ((ks.headY ?? 0) + window.PUPPETS.poseDy(ks)) * ksc;
        if (a.depth != null && a.depth !== 1) { const k = (1 + (cz - 1) * a.depth) / cz; wx = cx + (wx - cx) * k + (cx - W / 2) * (1 - a.depth); wy = cy + (wy - cy) * k + (cy - H / 2) * (1 - a.depth); }
        mouths[ks.who] = { x: W / 2 + (wx - cx) * cz, y: H / 2 + (wy - cy) * cz };
      } else if (PROPS[a.type]) {
        const inner = PROPS[a.type](st);
        svg = `<g transform="translate(${st.x ?? 0} ${st.y ?? 0}) rotate(${st.r ?? 0}) scale(${(st.sc ?? 1) * (st.fx ? -1 : 1)} ${st.sc ?? 1})" opacity="${st.o ?? 1}">${inner}</g>`;
      }
      // parallax: depth < 1 sits behind (moves and zooms less with the camera), > 1 is foreground
      if (a.depth != null && a.depth !== 1 && svg) {
        const k = (1 + (cz - 1) * a.depth) / cz, dx = (cx - W / 2) * (1 - a.depth), dy = (cy - H / 2) * (1 - a.depth);
        svg = `<g transform="translate(${cx} ${cy}) scale(${k.toFixed(4)}) translate(${-cx} ${-cy}) translate(${dx.toFixed(1)} ${dy.toFixed(1)})">${svg}</g>`;
      }
      if (st.ui) overlay += svg; else world += svg;
    }
    const bg = spec.bg ?? '#FFFFFF';
    const gray = cam.gray ? `filter="url(#gray)"` : '';
    let html = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
      <defs>${SHARED_DEFS}
      <filter id="gray"><feColorMatrix type="saturate" values="${1 - (cam.gray ?? 0)}"/></filter></defs>
      <rect width="${W}" height="${H}" fill="${bg}"/>
      <g ${gray}><g transform="${shake} translate(${W / 2} ${H / 2}) scale(${cz}) translate(${-cx} ${-cy})">${world}</g>${overlay}</g>`;
    if (cam.flash) html += `<rect width="${W}" height="${H}" fill="#fff" opacity="${cam.flash}"/>`;
    if (cam.black) html += `<rect width="${W}" height="${H}" fill="#111" opacity="${cam.black}"/>`;
    html += tr.over || '';
    html += captions(beat, gt, mouths) + '</svg>';
    root.innerHTML = html;
  }

  // burned-in captions as a speech bubble over the speaker's side: the line in chunks of up to ~6 words, timed by
  // the word boundaries of the voice, the word being said in the speaker's colour. Inside the safe area of
  // Reels / Shorts / Facebook (clear of the top bar, the bottom caption and the right-hand buttons).
  function captions(beat, gt, mouths = {}) {
    if (ep.captions === false) return '';
    for (const ln of beat.lines) {
      if (gt < ln.start || gt > ln.start + ln.dur + 0.12 || !ln.text) continue;
      const words = ln.words?.length ? ln.words : evenWords(ln);
      const lt = gt - ln.start;
      let idx = words.findIndex(w => lt < w.end); if (idx < 0) idx = words.length - 1;
      // chunks: the whole line if it is short, otherwise groups that break at punctuation or after 5-6 words
      const chunks = []; let cur = [];
      words.forEach((w, i) => { cur.push(i); const n = cur.length; if (words.length > 7 && (n >= 7 || (n >= 2 && /[,.;:?!…]$/.test(w.w)))) { chunks.push(cur); cur = []; } });
      if (cur.length) chunks.push(cur);
      const ch = chunks.find(c => c.includes(idx)) || chunks[chunks.length - 1];
      const chStart = ch[0] === 0 ? 0 : words[ch[0] - 1].end;
      const pop = Math.min(1, (lt - chStart) / 0.14);
      const who = ln.who, col = who === 'e' ? COLORS.E : who === 'r' ? COLORS.R : INK;
      const fs = ep.capSize ?? 66, lh = fs * 1.16;
      const text = ch.map(i => words[i].w).join(' ');
      const lines = wrap(text, 17);
      let k = 0;
      const tsp = lines.map(l => l.split(' ').map(wd => { const i = ch[k++]; return `<tspan fill="${i === idx ? col : INK}">${esc(wd)}</tspan>`; }).join(' '));
      const w = Math.min(980, Math.max(...lines.map(l => l.length)) * fs * 0.55 + 80), h = lines.length * lh + 44;
      const side = who === 'e' ? -1 : who === 'r' ? 1 : 0;
      const cy = ep.capY ?? 1470, ty = cy - h / 2;
      // the bubble sits under the speaker and its tail points at the speaker's mouth (both kids for "ambos")
      const targets = (who === 'ambos' ? ['e', 'r'] : [who]).map(k => mouths[k]).filter(Boolean);
      const fallback = { x: W / 2 + side * 260, y: ty - 400 };
      const aim = targets.length ? targets : [fallback];
      const mx = who === 'ambos' ? W / 2 : aim[0].x;
      const cx = Math.max(w / 2 + 50, Math.min(W - w / 2 - 50, mx));
      const tail = aim.map(p => {
        const bx = Math.max(cx - w / 2 + 60, Math.min(cx + w / 2 - 60, p.x));        // base on the top edge, under the mouth
        const dx = p.x - bx, dy = Math.min(-40, p.y + 50 - ty), L = Math.hypot(dx, dy) || 1;
        const len = Math.min(95, Math.max(48, L - 40));                               // stops short of the face
        const tx = bx + dx / L * len, tyy = ty + dy / L * len;
        return `M ${(bx - 32).toFixed(1)} ${(ty + 4).toFixed(1)} L ${tx.toFixed(1)} ${tyy.toFixed(1)} L ${(bx + 32).toFixed(1)} ${(ty + 4).toFixed(1)} Z`;
      }).join(' ');
      const sc = 0.85 + 0.15 * (1 - Math.pow(1 - pop, 3));
      return `<g transform="translate(${cx.toFixed(1)} ${cy.toFixed(1)}) scale(${sc.toFixed(3)}) translate(${(-cx).toFixed(1)} ${(-cy).toFixed(1)})">
        <path d="${tail}" fill="#fff" stroke="${INK}" stroke-width="7" stroke-linejoin="round"/>
        <rect x="${(cx - w / 2).toFixed(1)}" y="${(cy - h / 2).toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" rx="40" fill="#fff" stroke="${INK}" stroke-width="7"/>
        <path d="${tail}" fill="#fff" stroke="none" transform="translate(0 9)"/>
        ${tsp.map((t, i) => `<text x="${cx.toFixed(1)}" y="${(cy - h / 2 + 22 + lh * (i + 0.5)).toFixed(1)}" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="${fs}">${t}</text>`).join('')}</g>`;
    }
    return '';
  }
  function evenWords(ln) {
    const ws = ln.text.split(/\s+/).filter(Boolean); const d = ln.dur / Math.max(1, ws.length);
    return ws.map((w, i) => ({ w, end: (i + 1) * d }));
  }

  window.frame = t => {
    let b = D.beats[D.beats.length - 1];
    for (const x of D.beats) if (t < x.start + x.dur) { b = x; break; }
    draw(b, t);
  };
  window.ready = true;
})();
