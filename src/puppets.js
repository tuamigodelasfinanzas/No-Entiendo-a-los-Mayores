// Runs inside the browser. Draws E and R (from the layers of tools/prepare_characters.py), the sets, the props and
// the overlay (hook, insert cards, caption bubble, end stamp). Same pattern as zero-understands/src/puppets.js:
// every function takes the actor's state at this frame and returns an SVG string.
(() => {
  const FONT = "Fredoka, 'Arial Rounded MT Bold', Arial, sans-serif";
  const INK = '#2A2320';
  const COLORS = { E: '#D7322E', R: '#1F6FE0', INK, CREAM: '#FFF7EA', YEL: '#FFC93C', GREEN: '#2E9E5B', GRAY: '#9A9A9A' };
  const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const RIG = window.KID_RIG;          // { e: rig.json, r: rig.json } set by render.mjs
  const IMG = window.KID_IMG;          // { e: { head, body }, r: ... } urls
  const f1 = v => (+v).toFixed(1);

  // ---------- expressions (docs/biblia-personajes.md §4) ----------
  // brows: [left, right] { up: px raised, tilt: inner end up (+) / down (-) }, lids: upper lid cover 0..1,
  // mouth: { w: width factor, curve: smile (+) / frown (-), open 0..1, round 0..1 (an "o"), asym: one corner up }
  const B = (up = 0, tilt = 0) => ({ up, tilt });
  const EXPR = {
    neutral: { brows: [B(), B()], lids: [0.12, 0.12], mouth: { w: 0.62, curve: 0.35 } },
    feliz: { brows: [B(4, 1), B(4, 1)], lids: [0.08, 0.08], mouth: { w: 0.85, curve: 1, open: 0.35 } },
    sonrisa: { brows: [B(2), B(2)], lids: [0.14, 0.14], mouth: { w: 0.7, curve: 0.8 } },
    convencido: { brows: [B(7, -1), B(7, -1)], lids: [0.06, 0.06], mouth: { w: 0.72, curve: 0.75, asym: 0.25 } },
    curioso: { brows: [B(8, 3), B(8, 3)], lids: [0.02, 0.02], mouth: { w: 0.42, curve: 0.15, open: 0.12 }, look: [0, -0.2] },
    sorprendido: { brows: [B(16, 2), B(16, 2)], lids: [0, 0], mouth: { w: 0.38, round: 1, open: 0.7 }, pupil: 0.85 },
    asombrado: { brows: [B(20, 4), B(20, 4)], lids: [0, 0], mouth: { w: 0.5, round: 0.8, open: 1 }, pupil: 0.8 },
    serio: { brows: [B(-1, -1), B(-1, -1)], lids: [0.26, 0.26], mouth: { w: 0.5, curve: 0 } },
    dudoso: { brows: [B(-3, -4), B(14, 3)], lids: [0.28, 0.08], mouth: { w: 0.5, curve: -0.1, asym: 0.5 } },
    pensativo: { brows: [B(6, 4), B(1, 0)], lids: [0.2, 0.2], mouth: { w: 0.36, curve: -0.05, asym: -0.4 }, look: [0.6, -0.7] },
    confundido: { brows: [B(10, 8), B(4, -3)], lids: [0.1, 0.18], mouth: { w: 0.46, curve: -0.35, asym: 0.35 } },
    resignado: { brows: [B(4, 8), B(4, 8)], lids: [0.4, 0.4], mouth: { w: 0.56, curve: -0.3 } },
    triste: { brows: [B(6, 10), B(6, 10)], lids: [0.3, 0.3], mouth: { w: 0.5, curve: -0.7 }, look: [0, 0.4] },
    picaro: { brows: [B(8, -2), B(2, -4)], lids: [0.18, 0.4], mouth: { w: 0.7, curve: 0.8, asym: 0.6 } },
    enfadado: { brows: [B(-4, -9), B(-4, -9)], lids: [0.3, 0.3], mouth: { w: 0.52, curve: -0.5 } },
    ilusionado: { brows: [B(12, 4), B(12, 4)], lids: [0, 0], mouth: { w: 0.9, curve: 1, open: 0.6 }, pupil: 1.1 },
  };
  const lerp = (a, b, k) => a + (b - a) * k;

  function eyes(rig, st, id) {
    const ex = EXPR[st.face] || EXPR.neutral;
    const look = st.look || ex.look || [0, 0];
    const blink = st.blink || 0;
    let out = '';
    rig.eyes.forEach((e, i) => {
      const { x, y, w, h } = e;
      const top = `M ${f1(x - w / 2)} ${f1(y + h * 0.06)} C ${f1(x - w * 0.36)} ${f1(y - h * 0.66)} ${f1(x + w * 0.36)} ${f1(y - h * 0.66)} ${f1(x + w / 2)} ${f1(y + h * 0.02)}`;
      const shape = `${top} C ${f1(x + w * 0.34)} ${f1(y + h * 0.62)} ${f1(x - w * 0.34)} ${f1(y + h * 0.62)} ${f1(x - w / 2)} ${f1(y + h * 0.06)} Z`;
      const ir = h * 0.5, pr = ir * 0.5 * (st.pupil ?? ex.pupil ?? 1);
      const ix = x + look[0] * w * 0.2, iy = y + h * 0.05 + look[1] * h * 0.14;
      const lid = Math.min(1, Math.max(ex.lids[i] ?? 0, st.lid ?? 0, blink));
      const ly = y - h * 0.58 + lid * h * 1.18;           // lower edge of the upper lid
      const cid = `${id}eye${i}`;
      out += `<clipPath id="${cid}"><path d="${shape}"/></clipPath>
        <path d="${shape}" fill="#FFFDF8"/>
        <g clip-path="url(#${cid})">
          <ellipse cx="${f1(x)}" cy="${f1(y - h * 0.34)}" rx="${f1(w * 0.6)}" ry="${f1(h * 0.3)}" fill="#E9D6CC" opacity="0.7"/>
          <circle cx="${f1(ix)}" cy="${f1(iy)}" r="${f1(ir)}" fill="url(#${id}iris)"/>
          <circle cx="${f1(ix)}" cy="${f1(iy)}" r="${f1(ir)}" fill="none" stroke="${rig.iris[0]}" stroke-width="2.2"/>
          <circle cx="${f1(ix)}" cy="${f1(iy)}" r="${f1(pr)}" fill="#120A06"/>
          <circle cx="${f1(ix + ir * 0.32)}" cy="${f1(iy - ir * 0.36)}" r="${f1(ir * 0.27)}" fill="#fff"/>
          <circle cx="${f1(ix - ir * 0.34)}" cy="${f1(iy + ir * 0.34)}" r="${f1(ir * 0.11)}" fill="#fff" opacity="0.85"/>
          ${lid > 0.01 ? `<path d="M ${f1(x - w)} ${f1(y - h * 1.2)} H ${f1(x + w)} V ${f1(ly)} Q ${f1(x)} ${f1(ly + h * 0.22 * (1 - lid * 0.6))} ${f1(x - w)} ${f1(ly)} Z" fill="${rig.lid || rig.skin}"/>` : ''}
        </g>`;
      // lash line: along the lid edge, or the top of the eye when the lid is up
      // the ends stay on the eye corners, so a closed eye reads as a soft arc, not a bar
      const le = Math.min(Math.max(ly, y - h * 0.3), y + h * 0.05);
      const lm = Math.min(Math.max(ly, y - h * 0.4) + h * 0.22 * (1 - lid * 0.6), y + h * 0.3);
      const lash = lid > 0.16
        ? `M ${f1(x - w / 2 - 2)} ${f1(le)} Q ${f1(x)} ${f1(2 * lm - le)} ${f1(x + w / 2 + 3)} ${f1(le)}`
        : top;
      const flick = i === 0 ? `M ${f1(x - w / 2)} ${f1(y + h * 0.02)} l -7 -6` : `M ${f1(x + w / 2)} ${f1(y)} l 7 -6`;
      out += `<path d="${lash}" fill="none" stroke="#2A1810" stroke-width="5" stroke-linecap="round"/>
        <path d="${flick}" fill="none" stroke="#2A1810" stroke-width="4" stroke-linecap="round"/>
        <path d="M ${f1(x - w * 0.4)} ${f1(y + h * 0.34)} Q ${f1(x)} ${f1(y + h * 0.58)} ${f1(x + w * 0.4)} ${f1(y + h * 0.34)}" fill="none" stroke="#B07A5E" stroke-width="1.8" opacity="0.6"/>`;
    });
    return out;
  }

  function brows(rig, st) {
    const ex = EXPR[st.face] || EXPR.neutral;
    return rig.brows.map((b, i) => {
      const d = i === 0 ? 1 : -1;                 // left brow: inner end to the right
      const p = ex.brows[i] || B();
      const up = p.up + (st.browUp ?? 0), t = p.tilt;
      const ix = b.x + d * b.w / 2, ox = b.x - d * b.w / 2;
      const iy = b.y - up - t * 1.4, oy = b.y - up + t * 0.6 + 3;
      const my = b.y - up - 8;
      const th = 10;
      return `<path d="M ${f1(ox)} ${f1(oy)} Q ${f1(b.x)} ${f1(my - th / 2)} ${f1(ix)} ${f1(iy)} Q ${f1(b.x)} ${f1(my + th)} ${f1(ox)} ${f1(oy)} Z" fill="${rig.brow}" stroke="${rig.brow}" stroke-width="3.5" stroke-linejoin="round"/>`;
    }).join('');
  }

  function mouth(rig, st, id) {
    const ex = EXPR[st.face] || EXPR.neutral;
    const m = Object.assign({ w: 0.6, curve: 0.3, open: 0, round: 0, asym: 0 }, ex.mouth);
    const talk = st.talk || 0;
    // talking opens the mouth from its resting shape
    const open = Math.min(1, m.open + talk * (0.55 - m.open * 0.3));
    const W = rig.mouth.w, cx = rig.mouth.x, cy = rig.mouth.y;
    const round = Math.max(m.round, talk * 0.25);
    const hw = W / 2 * lerp(m.w, 0.34, round * 0.8) * (1 - talk * 0.08);
    const cyL = -m.curve * W * 0.1 - m.asym * W * 0.06, cyR = -m.curve * W * 0.1 + m.asym * W * 0.06;
    const midClosed = m.curve * W * 0.1;
    if (open < 0.06) {
      return `<path d="M ${f1(cx - hw)} ${f1(cy + cyL)} Q ${f1(cx)} ${f1(cy + midClosed * 1.4)} ${f1(cx + hw)} ${f1(cy + cyR)}" fill="none" stroke="${rig.lip}" stroke-width="5.5" stroke-linecap="round"/>
        ${m.curve > 0.5 ? `<path d="M ${f1(cx - hw - 5)} ${f1(cy + cyL - 3)} q 4 3 6 8 M ${f1(cx + hw + 5)} ${f1(cy + cyR - 3)} q -4 3 -6 8" fill="none" stroke="${rig.lip}" stroke-width="2.6" stroke-linecap="round" opacity="0.6"/>` : ''}`;
    }
    if (round > 0.5) {
      // an "o": an oval that opens with the voice
      const rx = W * (0.11 + open * 0.05) * (m.w / 0.4), ry = W * (0.1 + open * 0.13);
      return `<ellipse cx="${f1(cx)}" cy="${f1(cy + ry * 0.35)}" rx="${f1(rx)}" ry="${f1(ry)}" fill="#5B1E18" stroke="${rig.lip}" stroke-width="3.6"/>
        <ellipse cx="${f1(cx)}" cy="${f1(cy + ry * 1.0)}" rx="${f1(rx * 0.6)}" ry="${f1(ry * 0.35)}" fill="#E0736E"/>`;
    }
    const topY = midClosed * 0.4 - open * W * 0.04 - round * open * W * 0.12;
    const botY = midClosed * 1.3 + open * W * (0.3 + round * 0.12);
    const shape = `M ${f1(cx - hw)} ${f1(cy + cyL)} Q ${f1(cx)} ${f1(cy + topY * 2 - (cyL + cyR) / 2)} ${f1(cx + hw)} ${f1(cy + cyR)} Q ${f1(cx)} ${f1(cy + botY * 2 - (cyL + cyR) / 2)} ${f1(cx - hw)} ${f1(cy + cyL)} Z`;
    const cid = `${id}mouth`;
    return `<clipPath id="${cid}"><path d="${shape}"/></clipPath>
      <path d="${shape}" fill="#5B1E18"/>
      <g clip-path="url(#${cid})">
        <rect x="${f1(cx - hw)}" y="${f1(cy + Math.min(cyL, cyR) - W * 0.2)}" width="${f1(hw * 2)}" height="${f1(W * 0.2 + (topY > 0 ? topY : 0) + W * 0.08 * Math.min(1, open * 2) * (1 - round))}" fill="#FFFFFF"/>
        <ellipse cx="${f1(cx)}" cy="${f1(cy + botY)}" rx="${f1(hw * 0.7)}" ry="${f1(W * 0.12)}" fill="#E0736E"/>
      </g>
      <path d="${shape}" fill="none" stroke="${rig.lip}" stroke-width="3.6" stroke-linejoin="round"/>`;
  }

  // emotes over the head: ? ! ... bulb, drop, hearts, swirl, sparkle
  function emote(kind, k, x, y) {
    if (!kind || k <= 0) return '';
    const s = k < 1 ? 0.2 + 0.8 * (1 - Math.pow(1 - k, 3)) * (1 + 0.18 * Math.sin(k * Math.PI)) : 1;
    const txt = (t, c, fs = 120) => `<text x="0" y="0" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="${fs}" fill="${c}" stroke="${INK}" stroke-width="6" paint-order="stroke">${t}</text>`;
    const g = {
      '?': txt('?', '#1F6FE0'), '!': txt('!', '#E63946'), '??': `<g transform="translate(-34 0) rotate(-14)">${txt('?', '#1F6FE0', 100)}</g><g transform="translate(40 -20) rotate(12)">${txt('?', '#7B5CD6', 120)}</g>`,
      '...': `<g fill="${INK}"><circle cx="-38" cy="0" r="13"/><circle cx="0" cy="0" r="13"/><circle cx="38" cy="0" r="13"/></g>`,
      bombilla: `<g stroke="${INK}" stroke-width="6" stroke-linejoin="round"><path d="M0 -62 a 46 46 0 0 1 28 82 v 18 h -56 v -18 a 46 46 0 0 1 28 -82 Z" fill="#FFC93C"/><path d="M-22 48 h44 M-18 62 h36" fill="none" stroke-linecap="round"/></g><g stroke="#FFC93C" stroke-width="7" stroke-linecap="round"><path d="M-70 -40 l-20 -10 M70 -40 l20 -10 M0 -84 v-22"/></g>`,
      gota: `<path d="M0 -50 Q 30 0 0 22 Q -30 0 0 -50 Z" fill="#7FC4FF" stroke="${INK}" stroke-width="5"/>`,
      corazon: `<path d="M0 34 C -60 -6 -40 -60 0 -30 C 40 -60 60 -6 0 34 Z" fill="#E63946" stroke="${INK}" stroke-width="6"/>`,
      lio: `<path d="M -50 0 c 0 -40 60 -40 60 0 c 0 30 -44 30 -44 0 c 0 -22 30 -22 30 0 M 14 0 c 10 -30 50 -30 50 0" fill="none" stroke="${INK}" stroke-width="7" stroke-linecap="round"/>`,
      brillo: `<path d="M0 -50 L12 -12 L50 0 L12 12 L0 50 L-12 12 L-50 0 L-12 -12 Z" fill="#FFC93C" stroke="${INK}" stroke-width="5" stroke-linejoin="round"/>`,
    }[kind] || txt(esc(kind), INK, 90);
    return `<g transform="translate(${f1(x)} ${f1(y)}) scale(${f1(s)}) rotate(${f1(Math.sin(k * 7) * 4)})">${g}</g>`;
  }

  // a kid: st = { who: 'e'|'r', x, y (floor), s, face, look, blink, talk, headR, headX, headY, lean, squash, flip, emote, emoteK, o }
  function kid(st) {
    const rig = RIG[st.who], img = IMG[st.who];
    const id = `k${st.who}`;
    const s = st.s ?? 1, sq = st.squash ?? 1;
    const [px, py] = rig.pivot;
    const sh = `<ellipse cx="${rig.center}" cy="${rig.feet + 4}" rx="${f1(200 * (1 - (st.jump ?? 0) * 0.002))}" ry="26" fill="url(#kshadow)"/>`;
    const head = `<g transform="translate(${f1(st.headX ?? 0)} ${f1(st.headY ?? 0)}) rotate(${f1(st.headR ?? 0)} ${px} ${py})">
        <image href="${img.head}" x="0" y="0" width="${rig.w}" height="${rig.h}"/>
        ${brows(rig, st)}${eyes(rig, st, id)}${mouth(rig, st, id)}
        ${st.blush ? `<g opacity="${f1(st.blush)}"><ellipse cx="${rig.eyes[0].x - 10}" cy="${rig.mouth.y - 22}" rx="34" ry="18" fill="#FF6B6B" opacity="0.35"/><ellipse cx="${rig.eyes[1].x + 10}" cy="${rig.mouth.y - 22}" rx="34" ry="18" fill="#FF6B6B" opacity="0.35"/></g>` : ''}
      </g>`;
    const defs = `<defs><radialGradient id="${id}iris" cx="50%" cy="58%" r="55%"><stop offset="0" stop-color="${rig.iris[2]}"/><stop offset="0.55" stop-color="${rig.iris[1]}"/><stop offset="1" stop-color="${rig.iris[0]}"/></radialGradient></defs>`;
    const em = emote(st.emote, st.emoteK ?? 1, rig.center + (st.who === 'e' ? 190 : -190), rig.bbox[1] + 40);
    const flip = st.flip ? -1 : 1;
    return `<g transform="translate(${f1(st.x)} ${f1(st.y)}) rotate(${f1(st.lean ?? 0)}) scale(${f1(s * flip / Math.sqrt(sq))} ${f1(s * sq)}) translate(${-rig.center} ${-rig.feet})" opacity="${st.o ?? 1}">
      ${defs}${sh}<image href="${img.body}" x="0" y="0" width="${rig.w}" height="${rig.h}"/>${head}${em}</g>`;
  }

  // ---------- icons for the insert cards (centered at 0,0, about 200 px) ----------
  const S = `stroke="${INK}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"`;
  const ICONS = {
    casa: `<path d="M-80 0 L0 -70 L80 0 V80 H-80 Z" fill="#FFD9A8" ${S}/><path d="M-96 6 L0 -82 L96 6" fill="none" ${S} stroke="#E63946" stroke-width="12"/><rect x="-22" y="20" width="44" height="60" fill="#8C5A3C" ${S}/><rect x="34" y="-10" width="30" height="28" fill="#BFE3FF" ${S}/>`,
    tarjeta: `<rect x="-95" y="-60" width="190" height="120" rx="16" fill="#1F6FE0" ${S}/><rect x="-95" y="-34" width="190" height="24" fill="${INK}"/><rect x="-70" y="6" width="40" height="30" rx="6" fill="#FFC93C" ${S} stroke-width="4"/><path d="M10 30 h60" ${S} stroke="#fff" stroke-width="8"/>`,
    moneda: `<circle r="80" fill="#FFC93C" ${S}/><circle r="58" fill="none" stroke="#E0A100" stroke-width="7"/><text y="4" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="90" fill="#B07A00">€</text>`,
    billetes: `<g transform="rotate(-10)"><rect x="-100" y="-50" width="200" height="100" rx="10" fill="#9ED27A" ${S}/><circle r="28" fill="#CFEFB8" ${S} stroke-width="5"/></g><g transform="translate(10 20) rotate(6)"><rect x="-100" y="-50" width="200" height="100" rx="10" fill="#7CC35A" ${S}/><text y="4" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="60" fill="#2E6B1F">€</text></g>`,
    movil: `<rect x="-55" y="-95" width="110" height="190" rx="20" fill="${INK}" ${S}/><rect x="-43" y="-75" width="86" height="140" rx="6" fill="#BFE3FF"/><circle cy="80" r="7" fill="#666"/><path d="M-25 -40 h50 M-25 -15 h35 M-25 10 h45" stroke="#1F6FE0" stroke-width="9" stroke-linecap="round"/>`,
    reloj: `<circle r="85" fill="#fff" ${S}/><path d="M0 0 V-55 M0 0 L38 22" ${S} stroke-width="10"/><circle r="9" fill="${INK}"/>`,
    calendario: `<rect x="-85" y="-75" width="170" height="160" rx="16" fill="#fff" ${S}/><rect x="-85" y="-75" width="170" height="45" rx="16" fill="#E63946" ${S}/><path d="M-50 -95 v35 M50 -95 v35" ${S} stroke-width="10"/><g fill="${INK}">${[0, 1, 2, 3].map(r => [0, 1, 2, 3].map(c => `<rect x="${-62 + c * 34}" y="${-15 + r * 24}" width="22" height="14" rx="3" opacity="${r * 4 + c === 9 ? 1 : 0.25}"/>`).join('')).join('')}</g>`,
    pesa: `<rect x="-70" y="-10" width="140" height="20" rx="8" fill="#9A9A9A" ${S}/><rect x="-100" y="-50" width="34" height="100" rx="10" fill="#555" ${S}/><rect x="66" y="-50" width="34" height="100" rx="10" fill="#555" ${S}/>`,
    cafe: `<path d="M-70 -40 H50 V30 a 50 50 0 0 1 -50 50 H-20 a 50 50 0 0 1 -50 -50 Z" fill="#fff" ${S}/><path d="M50 -20 h15 a 25 25 0 0 1 0 50 h-15" fill="none" ${S}/><path d="M-60 -40 H40 V-20 H-60 Z" fill="#8C5A3C"/><path d="M-30 -60 q 10 -15 0 -30 M10 -60 q 10 -15 0 -30" fill="none" ${S} stroke="#9A9A9A"/>`,
    nube: `<path d="M-80 40 a 40 40 0 0 1 10 -78 a 55 55 0 0 1 100 -10 a 45 45 0 0 1 50 88 Z" fill="#fff" ${S}/><path d="M0 30 v-50 m-22 22 l22 -22 l22 22" fill="none" ${S} stroke="#1F6FE0"/>`,
    candado: `<path d="M-45 -10 v-35 a 45 45 0 0 1 90 0 v35" fill="none" ${S} stroke-width="14"/><rect x="-70" y="-15" width="140" height="105" rx="16" fill="#FFC93C" ${S}/><circle cy="30" r="14" fill="${INK}"/><rect x="-5" y="34" width="10" height="28" fill="${INK}"/>`,
    grafica: `<path d="M-90 80 H90 M-90 80 V-80" fill="none" ${S}/><path d="M-70 50 L-20 10 L20 30 L80 -60" fill="none" ${S} stroke="#E63946" stroke-width="12"/><path d="M50 -62 L82 -64 L80 -32" fill="none" ${S} stroke="#E63946" stroke-width="10"/>`,
    carrito: `<path d="M-100 -60 h30 l25 100 h110 l20 -70 H-55" fill="none" ${S} stroke-width="9"/><circle cx="-30" cy="70" r="14" fill="${INK}"/><circle cx="60" cy="70" r="14" fill="${INK}"/><rect x="-40" y="-55" width="40" height="40" fill="#FF6B5B" ${S} stroke-width="5"/><rect x="10" y="-50" width="40" height="35" fill="#9ED27A" ${S} stroke-width="5"/>`,
    factura: `<path d="M-65 -90 H65 V90 l-22 -14 l-22 14 l-21 -14 l-22 14 l-21 -14 l-22 14 Z" fill="#fff" ${S}/><path d="M-40 -55 h80 M-40 -25 h60 M-40 5 h80" ${S} stroke="#9A9A9A"/><text x="0" y="52" text-anchor="middle" font-family="${FONT}" font-weight="700" font-size="44" fill="#E63946">€€€</text>`,
    coche: `<path d="M-100 30 V0 l25 -50 h110 l35 50 h25 v30 Z" fill="#FF6B5B" ${S}/><path d="M-65 -40 h45 v35 h-62 Z M-5 -40 h35 l25 35 h-60 Z" fill="#BFE3FF" ${S} stroke-width="5"/><circle cx="-55" cy="34" r="24" fill="${INK}"/><circle cx="55" cy="34" r="24" fill="${INK}"/><circle cx="-55" cy="34" r="9" fill="#ccc"/><circle cx="55" cy="34" r="9" fill="#ccc"/>`,
    galleta: `<circle r="80" fill="#E0A96B" ${S}/><g fill="#6B3A1E"><circle cx="-30" cy="-30" r="11"/><circle cx="25" cy="-20" r="9"/><circle cx="-10" cy="25" r="12"/><circle cx="35" cy="35" r="8"/><circle cx="-45" cy="20" r="7"/></g><path d="M50 -62 a 30 30 0 0 0 30 30 a 80 80 0 0 0 -30 -30 Z" fill="#fff"/>`,
    like: `<path d="M0 70 C -110 0 -70 -90 0 -40 C 70 -90 110 0 0 70 Z" fill="#E63946" ${S}/>`,
    maleta: `<rect x="-90" y="-50" width="180" height="130" rx="18" fill="#FF6B5B" ${S}/><path d="M-30 -50 v-25 h60 v25" fill="none" ${S}/><path d="M-50 -50 v130 M50 -50 v130" ${S} stroke="#B2402F"/>`,
    despertador: `<circle cy="10" r="75" fill="#fff" ${S}/><circle cx="-60" cy="-60" r="25" fill="#E63946" ${S}/><circle cx="60" cy="-60" r="25" fill="#E63946" ${S}/><path d="M0 10 V-35 M0 10 L30 30" ${S} stroke-width="9"/><path d="M-50 80 l-15 15 M50 80 l15 15" ${S}/>`,
    wifi: `<path d="M-90 -20 a 130 130 0 0 1 180 0 M-60 12 a 85 85 0 0 1 120 0 M-30 44 a 42 42 0 0 1 60 0" fill="none" ${S} stroke="#1F6FE0" stroke-width="14"/><circle cy="74" r="13" fill="#1F6FE0"/>`,
    banco: `<path d="M-100 -30 L0 -90 L100 -30 Z" fill="#E4EBF3" ${S}/><path d="M-70 -20 v80 M-25 -20 v80 M25 -20 v80 M70 -20 v80" ${S} stroke-width="14"/><rect x="-105" y="60" width="210" height="24" fill="#E4EBF3" ${S}/>`,
    oferta: `<path d="M-90 -40 L-40 -90 H80 V30 L30 80 Z" fill="#FFC93C" ${S} transform="rotate(45)"/><text y="10" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="74" fill="#E63946" stroke="${INK}" stroke-width="3" paint-order="stroke">-50%</text>`,
    tarta: `<rect x="-85" y="-10" width="170" height="80" rx="12" fill="#FFB7C5" ${S}/><path d="M-85 10 q 21 20 42 0 q 21 20 42 0 q 21 20 42 0 q 21 20 42 0" fill="none" ${S} stroke="#fff"/><path d="M0 -10 v-40" ${S}/><path d="M0 -72 q 12 12 0 22 q -12 -10 0 -22 Z" fill="#FFC93C" ${S} stroke-width="4"/>`,
    mensaje: `<path d="M-90 -60 H90 V40 H-20 L-60 80 V40 H-90 Z" fill="#9ED27A" ${S}/><g fill="${INK}"><circle cx="-40" cy="-10" r="10"/><circle cx="0" cy="-10" r="10"/><circle cx="40" cy="-10" r="10"/></g>`,
    robot: `<rect x="-70" y="-55" width="140" height="115" rx="26" fill="#E4EBF3" ${S}/><circle cx="-30" cy="0" r="16" fill="#1F6FE0"/><circle cx="30" cy="0" r="16" fill="#1F6FE0"/><path d="M-25 35 h50" ${S}/><path d="M0 -55 v-25" ${S}/><circle cy="-88" r="10" fill="#E63946" ${S} stroke-width="4"/>`,
    maletin: `<rect x="-95" y="-45" width="190" height="125" rx="14" fill="#8C5A3C" ${S}/><path d="M-35 -45 v-25 h70 v25" fill="none" ${S}/><path d="M-95 5 H95" ${S}/><rect x="-14" y="-6" width="28" height="22" rx="4" fill="#FFC93C" ${S} stroke-width="4"/>`,
    portatil: `<rect x="-80" y="-75" width="160" height="110" rx="10" fill="${INK}" ${S}/><rect x="-66" y="-62" width="132" height="84" fill="#BFE3FF"/><path d="M-105 45 H105 L90 65 H-90 Z" fill="#9A9A9A" ${S}/>`,
    tele: `<rect x="-100" y="-65" width="200" height="125" rx="14" fill="${INK}" ${S}/><rect x="-86" y="-52" width="172" height="99" fill="#7B5CD6"/><path d="M-30 60 l-20 25 M30 60 l20 25" ${S}/><path d="M-20 -20 v40 l35 -20 Z" fill="#fff"/>`,
    hucha: `<ellipse cx="0" cy="10" rx="90" ry="65" fill="#FFB7C5" ${S}/><circle cx="-90" cy="0" r="22" fill="#FF9AB0" ${S}/><path d="M-20 -55 h40" ${S} stroke-width="10"/><circle cx="40" cy="-10" r="8" fill="${INK}"/><path d="M-50 70 v20 M40 70 v20" ${S} stroke-width="14"/><path d="M-25 -80 a 18 18 0 1 1 36 0" fill="#FFC93C" ${S} stroke-width="5"/>`,
    escudo: `<path d="M0 -90 L80 -60 V0 C 80 50 40 80 0 95 C -40 80 -80 50 -80 0 V-60 Z" fill="#2E9E5B" ${S}/><path d="M-30 0 l22 24 l40 -46" fill="none" ${S} stroke="#fff" stroke-width="12"/>`,
    anillo: `<circle cy="25" r="62" fill="none" ${S} stroke="#FFC93C" stroke-width="18"/><circle cy="25" r="62" fill="none" stroke="${INK}" stroke-width="4"/><path d="M-28 -45 L0 -82 L28 -45 L0 -28 Z" fill="#BFE3FF" ${S} stroke-width="5"/>`,
    llave: `<circle cx="-50" r="38" fill="#FFC93C" ${S}/><circle cx="-50" r="12" fill="#fff" ${S} stroke-width="4"/><path d="M-12 0 H95 M60 0 v25 M80 0 v18" ${S} stroke-width="14"/>`,
    bocadillo: `<path d="M-90 -50 H90 V30 H-10 L-50 70 V30 H-90 Z" fill="#fff" ${S}/><text y="-10" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="70" fill="${INK}">...</text>`,
    lunes: `<rect x="-85" y="-75" width="170" height="160" rx="16" fill="#fff" ${S}/><rect x="-85" y="-75" width="170" height="45" rx="16" fill="#7B5CD6" ${S}/><text y="35" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="58" fill="${INK}">LUN</text>`,
    reunion: `<rect x="-100" y="20" width="200" height="22" rx="8" fill="#8C5A3C" ${S}/>${[-62, 0, 62].map(x => `<circle cx="${x}" cy="-35" r="22" fill="#FFD9A8" ${S} stroke-width="5"/><path d="M${x - 28} 18 a 28 28 0 0 1 56 0" fill="#9A9A9A" ${S} stroke-width="5"/>`).join('')}`,
    ticket: `<path d="M-95 -45 H95 V-15 a 15 15 0 0 0 0 30 V45 H-95 V15 a 15 15 0 0 0 0 -30 Z" fill="#FFC93C" ${S}/><text y="2" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="50" fill="${INK}">P</text>`,
  };

  // ---------- sets (1080 x 1920 world, floor line around y = 1640) ----------
  const SETS = {
    dormitorio: () => `<defs><linearGradient id="wd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFEBD2"/><stop offset="1" stop-color="#F7D9B8"/></linearGradient></defs>
      <rect x="-400" y="-200" width="1880" height="1860" fill="url(#wd)"/>
      ${[...Array(9)].map((_, i) => `<path d="M ${-260 + i * 190} 60 l 9 20 l 22 3 l -16 15 l 4 22 l -19 -11 l -19 11 l 4 -22 l -16 -15 l 22 -3 Z" fill="#FFF6E8" opacity="0.8"/><circle cx="${-170 + i * 190}" cy="${230 + (i % 2) * 90}" r="8" fill="#FFF6E8"/>`).join('')}
      <rect x="70" y="520" width="330" height="410" rx="18" fill="#BFE3FF" stroke="#E3B98E" stroke-width="22"/><path d="M235 520 V930 M70 725 H400" stroke="#E3B98E" stroke-width="14"/>
      <circle cx="320" cy="610" r="34" fill="#FFF3B0"/><path d="M110 860 q 40 -40 80 0 q 40 -40 80 0" fill="none" stroke="#fff" stroke-width="14" stroke-linecap="round"/>
      <rect x="620" y="560" width="260" height="20" rx="6" fill="#C98F5E"/><rect x="650" y="500" width="54" height="60" rx="8" fill="#FF6B5B"/><rect x="714" y="470" width="40" height="90" rx="6" fill="#7FC4FF"/><circle cx="810" cy="525" r="35" fill="#9ED27A"/>
      <rect x="690" y="700" width="200" height="270" rx="10" fill="#fff" stroke="#E3B98E" stroke-width="10"/><path d="M720 920 l 50 -90 l 40 60 l 25 -30 l 30 60 Z" fill="#7B5CD6" opacity="0.7"/><circle cx="840" cy="760" r="20" fill="#FFC93C"/>
      <rect x="-400" y="1600" width="1880" height="420" fill="#D9AE80"/>${[...Array(12)].map((_, i) => `<path d="M ${-400 + i * 160} 1600 L ${-560 + i * 200} 2020" stroke="#C99A6B" stroke-width="5"/>`).join('')}
      <rect x="-400" y="1592" width="1880" height="16" fill="#E8C49C"/>
      <ellipse cx="540" cy="1760" rx="520" ry="110" fill="#F2A65A" opacity="0.55"/>`,
    salon: () => `<rect x="-400" y="-200" width="1880" height="1860" fill="#DCEBEE"/>
      <path d="M-400 1080 H1480" stroke="#C6DCE0" stroke-width="10"/>
      <rect x="620" y="700" width="260" height="190" rx="10" fill="#FFF8EC" stroke="#B98A5E" stroke-width="14"/><path d="M645 870 q 50 -100 100 -34 q 42 -58 116 34 Z" fill="#9ED27A"/><circle cx="830" cy="760" r="22" fill="#FFC93C"/>
      <path d="M940 1440 V760 M890 760 h100 l-25 -110 h-50 Z" stroke="#555" stroke-width="10" fill="#FFE2A8"/>
      <ellipse cx="120" cy="1420" rx="60" ry="22" fill="#B2402F"/><path d="M120 1400 q -60 -160 -10 -260 M120 1400 q 50 -170 10 -280 M120 1400 q 10 -120 70 -200" fill="none" stroke="#2E9E5B" stroke-width="24" stroke-linecap="round"/>
      <rect x="-60" y="1160" width="1200" height="360" rx="70" fill="#7FA7C9"/><rect x="-60" y="1100" width="1200" height="200" rx="70" fill="#8DB4D4"/>
      <rect x="-400" y="1600" width="1880" height="420" fill="#CBB59A"/><rect x="-400" y="1592" width="1880" height="14" fill="#B79E80"/>
      <ellipse cx="540" cy="1770" rx="560" ry="120" fill="#E9D8C0"/>`,
    parque: () => `<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9FD4FF"/><stop offset="1" stop-color="#E6F5FF"/></linearGradient></defs>
      <rect x="-400" y="-200" width="1880" height="1860" fill="url(#sky)"/>
      <g fill="#fff" opacity="0.95"><ellipse cx="200" cy="420" rx="120" ry="44"/><ellipse cx="270" cy="390" rx="80" ry="50"/><ellipse cx="820" cy="300" rx="140" ry="46"/><ellipse cx="760" cy="270" rx="80" ry="50"/></g>
      <ellipse cx="80" cy="1240" rx="420" ry="200" fill="#A8D98A"/><ellipse cx="1000" cy="1260" rx="460" ry="220" fill="#B6E19A"/>
      <g><rect x="120" y="900" width="36" height="320" fill="#8C5A3C"/><circle cx="138" cy="850" r="150" fill="#5DB85B"/><circle cx="60" cy="930" r="90" fill="#4FA94E"/>
      <rect x="880" y="880" width="40" height="340" fill="#8C5A3C"/><circle cx="900" cy="820" r="160" fill="#6CC46A"/><circle cx="1000" cy="900" r="95" fill="#5DB85B"/></g>
      <rect x="-400" y="1240" width="1880" height="780" fill="#8FCB6B"/>
      <path d="M380 2020 Q 520 1500 560 1240 H 660 Q 700 1500 900 2020 Z" fill="#E9D3A6"/>
      <g fill="#7AB85A">${[...Array(16)].map((_, i) => `<path d="M ${-100 + i * 80} ${1300 + (i % 3) * 120} l 8 -26 l 8 26 Z"/>`).join('')}</g>`,
    cocina: () => `<rect x="-400" y="-200" width="1880" height="1860" fill="#EAF4F1"/>
      <g stroke="#D5E6E1" stroke-width="4">${[...Array(30)].map((_, i) => `<path d="M ${-400 + i * 80} 700 V 1300"/>`).join('')}${[...Array(8)].map((_, i) => `<path d="M -400 ${700 + i * 80} H 1480"/>`).join('')}</g>
      <rect x="420" y="330" width="300" height="300" rx="14" fill="#BFE3FF" stroke="#fff" stroke-width="20"/><path d="M570 330 V630" stroke="#fff" stroke-width="12"/>
      <rect x="-80" y="420" width="300" height="1220" rx="26" fill="#F4F7FA" stroke="#C9D6DE" stroke-width="8"/><path d="M-80 900 H220" stroke="#C9D6DE" stroke-width="8"/><rect x="170" y="600" width="16" height="120" rx="8" fill="#9AA7B0"/><rect x="170" y="980" width="16" height="160" rx="8" fill="#9AA7B0"/>
      <rect x="250" y="1240" width="1300" height="400" fill="#F2C38E"/><rect x="230" y="1210" width="1340" height="40" rx="10" fill="#FFFFFF" stroke="#D5E6E1" stroke-width="6"/>
      <circle cx="840" cy="1150" r="50" fill="#FF6B5B"/><rect x="900" y="1080" width="70" height="130" rx="14" fill="#fff" stroke="#9AA7B0" stroke-width="6"/>
      <rect x="-400" y="1600" width="1880" height="420" fill="#fff"/>${[...Array(26)].map((_, i) => [...Array(6)].map((_, j) => (i + j) % 2 ? `<rect x="${-400 + i * 80}" y="${1600 + j * 80}" width="80" height="80" fill="#F2B8A0"/>` : '').join('')).join('')}`,
    cole: () => `<rect x="-400" y="-200" width="1880" height="1860" fill="#F6EDD8"/>
      <rect x="-400" y="1180" width="1880" height="420" fill="#E8D7B5"/>
      <rect x="80" y="460" width="840" height="560" rx="16" fill="#2F5E4E" stroke="#B98A5E" stroke-width="24"/>
      <g fill="none" stroke="#F4F4EC" stroke-width="7" stroke-linecap="round" opacity="0.85"><path d="M160 560 h70 M195 525 v70"/><path d="M300 560 h70"/><text x="420" y="590" font-family="${FONT}" font-weight="700" font-size="76" fill="#F4F4EC" stroke="none">2 + 2 = ?</text><path d="M170 760 q 90 -90 180 0 t 180 0" /><path d="M640 860 l 60 -70 l 60 70 Z"/></g>
      <rect x="120" y="1000" width="200" height="14" fill="#fff" opacity="0.6"/>
      <circle cx="1000" cy="620" r="56" fill="#fff" stroke="${INK}" stroke-width="9"/><path d="M1000 620 V584 M1000 620 L1024 634" stroke="${INK}" stroke-width="8" stroke-linecap="round"/>
      <rect x="-400" y="1600" width="1880" height="420" fill="#C9A577"/><rect x="-400" y="1592" width="1880" height="14" fill="#B38E60"/>`,
    calle: () => `<defs><linearGradient id="sky2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFD9B8"/><stop offset="1" stop-color="#FFF1E2"/></linearGradient></defs>
      <rect x="-400" y="-200" width="1880" height="1860" fill="url(#sky2)"/>
      <rect x="-200" y="380" width="420" height="1240" fill="#F7A072"/><rect x="230" y="560" width="360" height="1060" fill="#9DC3E6"/><rect x="600" y="300" width="400" height="1320" fill="#F3D27A"/><rect x="1010" y="520" width="300" height="1100" fill="#B9A6E0"/>
      <g fill="#FFF7EA" opacity="0.9">${[...Array(4)].map((_, c) => [...Array(7)].map((_, r) => `<rect x="${-150 + c * 290}" y="${460 + r * 150}" width="70" height="90" rx="6"/>`).join('')).join('')}</g>
      <rect x="-400" y="1420" width="1880" height="200" fill="#CFC6BC"/><rect x="-400" y="1600" width="1880" height="420" fill="#B9B1A8"/>
      <path d="M960 1600 V900" stroke="#555" stroke-width="16"/><path d="M960 900 q 0 -50 -60 -50" fill="none" stroke="#555" stroke-width="16"/><ellipse cx="890" cy="860" rx="40" ry="18" fill="#FFE07A"/>`,
  };

  // ---------- props ----------
  const PROPS = {
    set: p => (SETS[p.name] || SETS.dormitorio)(p),
    rect: p => `<rect x="${-(p.w ?? 100) / 2}" y="${-(p.h ?? 100) / 2}" width="${p.w ?? 100}" height="${p.h ?? 100}" rx="${p.rx ?? 0}" fill="${p.fill ?? '#fff'}" opacity="${p.op ?? 1}"/>`,
    text: p => `<text x="0" y="0" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="${p.size ?? 84}" fill="${p.color ?? INK}" stroke="${p.strokeColor ?? INK}" stroke-width="${p.stroke ?? 0}" paint-order="stroke" stroke-linejoin="round">${esc(p.txt)}</text>`,
    icon: p => `<g transform="scale(${p.s ?? 1})">${ICONS[p.name] || ''}</g>`,
    // hook / header card: the question of the episode, big at the start and docked as a header after
    hook: p => {
      const lines = wrap(p.txt, p.max ?? 18), fs = p.size ?? 86, lh = fs * 1.12;
      const w = Math.min(1000, Math.max(...lines.map(l => l.length)) * fs * 0.56 + 90), h = lines.length * lh + 60;
      return `<g><rect x="${f1(-w / 2)}" y="${f1(-h / 2)}" width="${f1(w)}" height="${f1(h)}" rx="38" fill="#FFFFFF" stroke="${INK}" stroke-width="8"/>
        ${p.badge ? `<g transform="translate(${f1(-w / 2 + 30)} ${f1(-h / 2 - 8)}) rotate(-4)"><rect x="0" y="-34" width="${f1(p.badge.length * 24 + 50)}" height="56" rx="28" fill="${p.badgeColor ?? COLORS.YEL}" stroke="${INK}" stroke-width="6"/><text x="${f1((p.badge.length * 24 + 50) / 2)}" y="-5" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="34" fill="${INK}">${esc(p.badge)}</text></g>` : ''}
        ${lines.map((l, i) => `<text x="0" y="${f1(-h / 2 + 30 + lh * (i + 0.5))}" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="${fs}" fill="${INK}">${esc(l)}</text>`).join('')}</g>`;
    },
    // insert card: an icon and a short label ("30 AÑOS")
    card: p => {
      const fs = p.size ?? 78, label = p.txt ? wrap(p.txt, 14) : [];
      const w = Math.max(360, Math.max(0, ...label.map(l => l.length)) * fs * 0.58 + 80), h = (p.icon ? 250 : 40) + label.length * fs * 1.1 + 30;
      return `<g transform="rotate(${p.tilt ?? -3})"><rect x="${f1(-w / 2 + 10)}" y="${f1(-h / 2 + 12)}" width="${f1(w)}" height="${f1(h)}" rx="34" fill="${INK}" opacity="0.18"/>
        <rect x="${f1(-w / 2)}" y="${f1(-h / 2)}" width="${f1(w)}" height="${f1(h)}" rx="34" fill="${p.fill ?? '#FFF7EA'}" stroke="${INK}" stroke-width="8"/>
        ${p.icon ? `<g transform="translate(0 ${f1(-h / 2 + 140)})">${ICONS[p.icon] || ''}</g>` : ''}
        ${label.map((l, i) => `<text x="0" y="${f1(-h / 2 + (p.icon ? 270 : 40) + fs * 1.1 * (i + 0.5))}" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="${fs}" fill="${p.color ?? INK}">${esc(l)}</text>`).join('')}</g>`;
    },
    // end stamp: "Cosas de mayores."
    stamp: p => `<g transform="rotate(${p.tilt ?? -6})"><rect x="-470" y="-95" width="940" height="190" rx="30" fill="#FFF7EA" stroke="${p.color ?? '#D7322E'}" stroke-width="14"/><rect x="-450" y="-75" width="900" height="150" rx="20" fill="none" stroke="${p.color ?? '#D7322E'}" stroke-width="5"/>
      <text x="0" y="4" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="${p.size ?? 96}" fill="${p.color ?? '#D7322E'}">${esc(p.txt ?? 'Cosas de mayores.')}</text></g>`,
    handle: p => { const fs = p.size ?? 40, w = String(p.txt).length * fs * 0.55 + 50; return `<rect x="${f1(-w / 2)}" y="${f1(-fs * 0.75)}" width="${f1(w)}" height="${f1(fs * 1.5)}" rx="${f1(fs * 0.75)}" fill="#fff" stroke="${INK}" stroke-width="4"/><text x="0" y="0" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-weight="700" font-size="${fs}" fill="${INK}">${esc(p.txt)}</text>`; },
    vignette: p => `<defs><radialGradient id="vig" cx="50%" cy="55%" r="75%"><stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="${p.op ?? 0.35}"/></radialGradient></defs><rect x="-540" y="-960" width="1080" height="1920" fill="url(#vig)"/>`,
  };

  function wrap(text, max) {
    const words = String(text ?? '').split(/\s+/).filter(Boolean), lines = [];
    let cur = '';
    for (const w of words) { if ((cur + ' ' + w).trim().length > max && cur) { lines.push(cur); cur = w; } else cur = (cur + ' ' + w).trim(); }
    if (cur) lines.push(cur);
    return lines;
  }

  const SHARED_DEFS = `<radialGradient id="kshadow"><stop offset="0" stop-color="#000" stop-opacity="0.28"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>`;
  window.PUPPETS = { kid, PROPS, ICONS, SETS, EXPR, COLORS, FONT, INK, esc, wrap, SHARED_DEFS };
})();
