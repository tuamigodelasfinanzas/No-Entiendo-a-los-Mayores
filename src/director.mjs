// Turns a script (content/guiones/<lang>/<id>.json, format in docs/guia-editorial.md §6) into an episode for
// src/stage.js: one beat with every line, the two kids keyed line by line (who speaks, who listens, faces, looks,
// gestures, emotes), the camera plan, the hook card, the insert cards, the pauses and the closing stamp.
// The writer only decides WHAT happens; the director decides HOW it is shot, always the same way, so all episodes
// feel like one show.
import fs from 'node:fs';

const read = f => JSON.parse(fs.readFileSync(new URL(`../content/${f}`, import.meta.url)));
export const CHARS = read('personajes.json');
export const SERIES = read('series.json');
export const PILLARS = read('pilares.json');
export const I18N = read('i18n.json');

const KIDS = ['e', 'r'];
const other = w => (w === 'e' ? 'r' : 'e');
export const speakerOf = ln => ['e', 'r', 'ambos'].find(k => typeof ln[k] === 'string');

// camera shots (docs/direccion.md §2): two-shot, medium on one kid, close-up on one face
function shot(name, who) {
  const Y = CHARS.suelo, S = CHARS.escala;
  const head = Y - 830 * S;                       // world y of the faces
  if (name === 'dos') return { z: 1, x: 540, y: 960 };
  const k = CHARS[who];
  // medium: the speaker centred, his face a little under the middle (the bubble goes below it, the cards above)
  if (name === 'medio') { const z = 1.5; return { z, x: k.x, y: head - 80 / z }; }
  if (name === 'cerca') { const z = 2.0; return { z, x: k.x, y: head - 40 / z }; }
  return { z: 1, x: 540, y: 960 };
}

const GESTURES = {
  // each returns keys for the kid that makes it, starting at key time `at`
  salto: (at, b) => [{ ...at, y: b.y }, { ...tplus(at, 0.16), y: b.y - 70, e: 'out' }, { ...tplus(at, 0.34), y: b.y, e: 'in' }, { ...tplus(at, 0.42), squash: 0.94 }, { ...tplus(at, 0.55), squash: 1 }],
  asiente: (at) => [{ ...at, headY: 0 }, { ...tplus(at, 0.14), headY: 12, headR: -2 }, { ...tplus(at, 0.3), headY: 0, headR: 0 }, { ...tplus(at, 0.44), headY: 10 }, { ...tplus(at, 0.6), headY: 0 }],
  niega: (at) => [{ ...at, headR: 0 }, { ...tplus(at, 0.15), headR: -7 }, { ...tplus(at, 0.32), headR: 7 }, { ...tplus(at, 0.48), headR: -5 }, { ...tplus(at, 0.62), headR: 0 }],
  inclina: (at, b, w) => [{ ...at, headR: 0 }, { ...tplus(at, 0.35), headR: w === 'e' ? 9 : -9, e: 'out' }],
  endereza: (at) => [{ ...at }, { ...tplus(at, 0.3), headR: 0, lean: 0 }],
  acerca: (at, b, w) => [{ ...at, x: b.x }, { ...tplus(at, 0.4), x: b.x + (w === 'e' ? 45 : -45), lean: w === 'e' ? 3 : -3, e: 'io' }],
  aparta: (at, b, w) => [{ ...at, x: b.x }, { ...tplus(at, 0.3), x: b.x + (w === 'e' ? -45 : 45), lean: w === 'e' ? -4 : 4, e: 'out' }],
  vuelve: (at, b) => [{ ...at }, { ...tplus(at, 0.4), x: b.x, lean: 0, e: 'io' }],
  encoge: (at) => [{ ...at, squash: 1, headY: 0 }, { ...tplus(at, 0.18), squash: 0.95, headY: 10, headR: -4, e: 'out' }, { ...tplus(at, 0.7), squash: 1, headY: 0, headR: 0 }],
  bota: (at, b) => [{ ...at, y: b.y }, { ...tplus(at, 0.12), y: b.y - 30, e: 'out' }, { ...tplus(at, 0.24), y: b.y, e: 'in' }, { ...tplus(at, 0.36), y: b.y - 26, e: 'out' }, { ...tplus(at, 0.48), y: b.y, e: 'in' }],
};
// Chiño's poses (assets/characters/<id>/poses, tools/prepare_poses.py): what the body does while a kid speaks or
// listens. A line can name one ("pose" for the speaker, "pose_otro" for the listener); otherwise the director picks
// from what the line is (its face, a question, an exclamation, an explanation). Only calm, standing poses here:
// jumping, running, sitting, the ball... are for scripts that ask for them.
// (rasca and susurra exist but are left out of the automatic choice: their hand goes behind the original hair /
// cheek and reads as a cut arm; a script can still ask for them)
const POSES = {
  e: {
    sorpresa: ['encoge', 'idea'], duda: ['encoge', 'brazos-cruzados'], piensa: ['idea', 'brazos-cruzados'], feliz: ['pulgar-arriba', 'corazon'],
    pregunta: ['encoge', 'explica'], exclama: ['senala', 'idea'], explica: ['explica', 'senala', 'idea', 'pulgar-arriba'],
    secreto: ['explica'], escucha: ['manos-cadera', 'brazos-cruzados', null], cierre: ['encoge'],
  },
  r: {
    sorpresa: ['palmas-arriba', 'levanta-mano'], duda: ['palmas-arriba', 'brazos-cruzados'], piensa: ['brazos-cruzados'], feliz: ['senala-arriba', 'levanta-mano'],
    pregunta: ['palmas-arriba', 'levanta-mano'], exclama: ['senala-a-e', 'senala-arriba'], explica: ['senala-a-e', 'senala-arriba', 'palmas-arriba'],
    secreto: ['brazos-cruzados'], escucha: ['brazos-cruzados', null], cierre: ['palmas-arriba'],
  },
};
const FACE_KIND = { sorprendido: 'sorpresa', asustado: 'sorpresa', dudoso: 'duda', confundido: 'duda', pensativo: 'piensa', feliz: 'feliz', orgulloso: 'feliz', sonrisa: 'feliz' };
function lineKind(it, text) {
  if (it.cara && FACE_KIND[it.cara]) return FACE_KIND[it.cara];
  if (it.emote === '!') return 'sorpresa';
  if (/\?\s*$/.test(text)) return 'pregunta';
  if (/!\s*$/.test(text)) return 'exclama';
  return 'explica';
}
// a small stable hash, so the same script always gets the same poses
const hash = str => [...str].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);

const tplus = (at, d) => ({ ...at, t: (at.t ?? 0) + d });
const SFX_GESTURE = { salto: 'boing', bota: 'boing', aparta: 'swipe', encoge: 'tick' };

export function build(script, o = {}) {
  const lang = script.idioma || o.lang || 'es';
  const tr = v => (v && typeof v === 'object' ? v[lang] ?? v.es : v);
  const Y = CHARS.suelo, S = CHARS.escala;
  const base = w => ({ who: w, x: CHARS[w].x, y: Y, s: S, face: CHARS[w].cara_escucha, look: CHARS[w].mira_al_otro, headR: 0, headY: 0, lean: 0, squash: 1, emoteK: 0, lid: 0, pose: null, pose0: null, poseK: 1 });
  const keys = { e: [base('e')], r: [base('r')] };
  const cam = [{ t: 0, ...shot('dos'), e: 'step' }];
  const lines = [], cards = [], sfx = [];
  const items = script.lineas;

  // voice lines, with each pause attached to the line before it
  const speech = [];
  items.forEach(it => {
    const who = speakerOf(it);
    if (who) speech.push({ it, who, pause: 0, react: [] });
    else if (it.pausa != null) {
      if (!speech.length) throw new Error(`${script.id}: a script cannot start with a pause (the hook goes first)`);
      speech[speech.length - 1].pause += it.pausa; speech[speech.length - 1].react.push(it);
    }
  });
  const last = speech.length - 1;
  const closing = script.cierre?.tipo || 'hablado';

  // shot plan: the hook in two-shot; then the speaker in medium shot, a close-up for short punch lines,
  // and back to the two-shot for reactions and the ending
  let prevShot = 'dos';
  const poseNow = { e: null, r: null }, lastKind = { e: null, r: null }, changed = { e: -9, r: -9 };
  speech.forEach((sp, i) => {
    const { it, who } = sp;
    lines.push({ who, text: it[who], gap: 0.28 + sp.pause });
    const at = { l: i };
    const words = it[who].split(/\s+/).length;
    let s = it.plano;
    if (!s) {
      if (i === 0 || who === 'ambos' || (i === last && closing === 'hablado')) s = 'dos';
      else if (words <= 4 && (sp.pause > 0 || i === last - 1)) s = 'cerca';
      else s = prevShot === 'medio' && i % 4 === 3 ? 'dos' : 'medio';
    }
    const target = who === 'ambos' ? 'e' : who;
    cam.push({ ...at, t: -0.04, ...shot(s, target), e: 'step' });
    // slow push while the line plays, so a held shot never feels frozen
    const sh = shot(s, target);
    cam.push({ le: i, ...sh, z: sh.z * 1.025, e: 'lin' });
    prevShot = s;

    // faces and looks
    const speakers = who === 'ambos' ? KIDS : [who];
    for (const w of KIDS) {
      const talking = speakers.includes(w);
      const k = { ...at, t: -0.06 };
      const face = talking ? (it.cara && who !== 'ambos' ? it.cara : who === 'ambos' ? it.cara ?? 'serio' : CHARS[w].cara_habla) : (it.otro ?? null);
      if (face) k.face = face;
      const look = who === 'ambos' || it.mira === 'camara' && talking ? [0, 0.05] : it.mira === 'arriba' && talking ? [0.3, -0.8] : CHARS[w].mira_al_otro;
      keys[w].push({ ...k, look });
      if (talking && it.gesto && GESTURES[it.gesto]) { keys[w].push(...GESTURES[it.gesto]({ ...at, t: 0.05 }, base(w), w)); if (SFX_GESTURE[it.gesto]) sfx.push({ s: SFX_GESTURE[it.gesto], l: i, t: 0.1, g: 0.5 }); }
      if (!talking && it.gesto_otro && GESTURES[it.gesto_otro]) keys[w].push(...GESTURES[it.gesto_otro]({ ...at, t: 0.35 }, base(w), w));
      const em = talking ? it.emote : it.emote_otro;
      if (em) {
        keys[w].push({ ...at, t: 0.1, emote: em, emoteK: 0, e: 'step' }, { ...at, t: 0.45, emoteK: 1, e: 'out' }, { le: i, t: 0.5, emoteK: 1 }, { le: i, t: 0.75, emoteK: 0, e: 'in' });
        sfx.push({ s: em === 'bombilla' ? 'ding' : 'pop', l: i, t: 0.1, g: 0.45 });
      }
    }
    // poses: the speaker's body says what the line is, on the first syllable (half a second: a dissolve with a lean and a head tilt, no bounce); the
    // listener answers a moment later, and only now and then. Two lines of the same kind in a row by the same kid
    // keep the pose, and a kid who has just changed keeps it for one more line: few, calm changes
    for (const w of KIDS) {
      const talking = speakers.includes(w);
      const kind = talking ? (who === 'ambos' ? 'cierre' : lineKind(it, it[who])) : 'escucha';
      let next;
      if (talking) next = it.pose && who !== 'ambos' ? it.pose : (lastKind[w] === kind || i - changed[w] < 2) && poseNow[w] ? poseNow[w] : POSES[w][kind];
      else next = it.pose_otro ?? (i % 3 === 0 || poseNow[w] === null || !POSES[w].escucha.includes(poseNow[w]) ? POSES[w].escucha : [poseNow[w]]);
      lastKind[w] = talking ? kind : null;
      if (Array.isArray(next)) {
        const opts = next.filter(n => n !== poseNow[w]);
        next = opts.length ? opts[hash(`${script.id}${i}${w}`) % opts.length] : next[0];
      }
      if (next !== poseNow[w]) {
        const t0 = talking ? -0.25 : 0.35;
        keys[w].push({ ...at, t: t0, pose0: poseNow[w], pose: next, poseK: 0, e: 'step' }, { ...at, t: t0 + 0.5, poseK: 1, e: 'io' });
        poseNow[w] = next;
        changed[w] = i;
      }
    }
    if (it.tarjeta) cards.push({ i, ...it.tarjeta });

    // pauses: silence, looks, a slow blink... the reaction is part of the joke
    let t0 = 0.12;
    for (const p of sp.react) {
      const r = p.reaccion || 'silencio';
      const pk = { le: i, t: t0 };
      cam.push({ ...pk, ...shot(p.plano || 'dos'), e: 'step' }, { le: i, t: t0 + p.pausa, ...shot(p.plano || 'dos'), z: 1.06, e: 'io' });
      for (const w of KIDS) {
        const face = p.caras?.[w];
        const k = { ...pk };
        if (face) k.face = face;
        if (r === 'mirada') k.look = [0, 0.05];
        else if (r === 'giro' || r === 'silencio') k.look = CHARS[w].mira_al_otro;
        else if (r === 'arriba') k.look = [0.35, -0.8];
        keys[w].push(k);
        if (r === 'parpadeo') keys[w].push({ ...pk, t: t0 + 0.35, lid: 0 }, { ...pk, t: t0 + 0.55, lid: 1, e: 'in' }, { ...pk, t: t0 + 0.8, lid: 1 }, { ...pk, t: t0 + 1.0, lid: 0, e: 'out' });
        if (r === 'giro') keys[w].push({ ...pk, t: t0 + 0.4, look: [0, 0.05], e: 'io' });
        const em = p.emote?.[w];
        if (em) keys[w].push({ ...pk, t: 0.1 + t0, emote: em, emoteK: 0, e: 'step' }, { ...pk, t: t0 + 0.45, emoteK: 1, e: 'out' }, { ...pk, t: t0 + p.pausa - 0.1, emoteK: 1 }, { ...pk, t: t0 + p.pausa + 0.1, emoteK: 0, e: 'in' });
      }
      if (r === 'mirada' || r === 'silencio') sfx.push({ s: 'grillos', le: i, t: t0 + 0.1, g: 0.35 });
      if (r === 'parpadeo') sfx.push({ s: 'tick', le: i, t: t0 + 0.55, g: 0.4 }, { s: 'tick', le: i, t: t0 + 1.0, g: 0.4 });
      t0 += p.pausa;
    }
  });

  // overlay: hook card with the series badge, docked as a header once the question has been asked
  const serie = SERIES[script.serie] || {};
  const hookTxt = tr(script.gancho) || tr(script.titulo);
  const hook = {
    id: 'hook', type: 'hook', z: 20, k: [
      { t: 0, x: 540, y: 400, sc: 1, txt: hookTxt, badge: tr(serie.etiqueta), badgeColor: serie.color, ui: true, size: 84, max: 17 },
      { le: 0, t: 0.35, y: 400, sc: 1 },
      { le: 0, t: 0.8, y: 262, sc: 0.62, e: 'io' },
    ],
  };
  // insert cards: pop in over the kids' heads while their line plays
  const cardActors = cards.map((c, j) => ({
    id: `card${j}`, type: 'card', z: 18, k: [
      { t: 0, x: 540, y: 600, sc: 0, o: 0, icon: c.icono, txt: tr(c.texto), tilt: j % 2 ? 3 : -3, ui: true },
      { l: c.i, t: 0.15, sc: 0.2, o: 1, e: 'step' }, { l: c.i, t: 0.45, sc: 0.72, e: 'pop' },
      { le: c.i, t: c.hasta ?? 0.35, sc: 0.72 }, { le: c.i, t: (c.hasta ?? 0.35) + 0.2, sc: 0, o: 0, e: 'in' },
    ],
  }));
  cards.forEach(c => sfx.push({ s: 'pop', l: c.i, t: 0.15, g: 0.55 }));

  // closing stamp: said aloud (it pops as the line starts) or written after the last reaction
  const stampTxt = tr(script.cierre?.texto) || tr(I18N.cierre);
  const stampAt = closing === 'hablado' ? { l: last, t: 0.25 } : { le: last, t: speech[last].pause + 0.05 };
  const stamp = {
    id: 'stamp', type: 'stamp', z: 22, k: [
      { t: 0, x: 540, y: 560, sc: 0, o: 0, txt: stampTxt, tilt: -6, ui: true },
      { ...stampAt, sc: 1.6, o: 1, e: 'step' }, { ...tplus(stampAt, 0.22), sc: 1, e: 'in' },
    ],
  };
  const handle = { id: 'handle', type: 'handle', z: 22, k: [{ t: 0, x: 540, y: 705, o: 0, txt: tr(I18N.handle), ui: true, size: 42 }, { ...tplus(stampAt, 0.3), o: 0, e: 'step' }, { ...tplus(stampAt, 0.6), o: 1 }] };
  sfx.push({ s: 'sello', ...stampAt, g: 0.8 });
  // at the end both look at the viewer
  if (closing !== 'hablado') for (const w of KIDS) keys[w].push({ ...stampAt, look: [0, 0.05], face: script.cierre?.caras?.[w] ?? 'serio' });

  const set = { id: 'set', type: 'set', z: -10, depth: 0.9, k: [{ t: 0, x: 0, y: 0, name: script.escenario || 'dormitorio' }] };
  const kidsActors = KIDS.map(w => ({ id: w, type: 'kid', z: w === 'e' ? 5 : 6, k: keys[w] }));

  const names = { e: tr(CHARS.e.nombre), r: tr(CHARS.r.nombre) };
  return {
    id: script.id, lang, format: 'short', captions: true, names,
    music: script.musica ?? 'juguete', musicGain: script.volumen_musica ?? 0.07,
    title: tr(script.titulo), script,
    beats: [{ pre: 0.25, hold: 1.35, lines, cam, sfx, bg: '#FFFFFF', actors: [set, ...kidsActors, hook, ...cardActors, stamp, handle] }],
  };
}
