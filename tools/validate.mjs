// Checks every script and the calendar before anything is rendered or published (docs/guia-editorial.md §7).
// Usage: node tools/validate.mjs [content/guiones/es/001-x.json ...]   (no arguments = all scripts)
//        node tools/validate.mjs --timing out/*/timing.json          (real durations after a render with voice)
// Exit code 1 if there is any error; warnings are printed but do not fail.
import fs from 'node:fs';
import path from 'node:path';
import { estimate } from '../src/voice.mjs';
import { SERIES, PILLARS, speakerOf } from '../src/director.mjs';

const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const args = process.argv.slice(2);
const errors = [], warns = [];
const err = (id, m) => errors.push(`${id}: ${m}`), warn = (id, m) => warns.push(`${id}: ${m}`);

// what the renderer knows how to draw (read from the code, so this list never goes stale)
const puppets = fs.readFileSync(path.join(ROOT, 'src/puppets.js'), 'utf8');
const block = name => { const a = puppets.indexOf(`const ${name} = {`); const b = puppets.indexOf('\n  };', a); return puppets.slice(a, b); };
const keysOf = src => [...src.matchAll(/^ {4}([a-záéíóúñ]+): /gim)].map(m => m[1]);
const EXPR = keysOf(block('EXPR')), ICONS = keysOf(block('ICONS')), SETS = keysOf(block('SETS'));
const director = fs.readFileSync(path.join(ROOT, 'src/director.mjs'), 'utf8');
const POSES = Object.fromEntries(['e', 'r'].map(w => [w, Object.keys(JSON.parse(fs.readFileSync(path.join(ROOT, `assets/characters/${w}/rig.json`), 'utf8')).poses || {})]));
const GESTURES = [...director.slice(director.indexOf('const GESTURES'), director.indexOf('};', director.indexOf('const GESTURES'))).matchAll(/^ {2}([a-z]+): /gm)].map(m => m[1]);
const EMOTES = ['?', '!', '??', '...', 'bombilla', 'gota', 'corazon', 'lio', 'brillo'];
const REACTIONS = ['silencio', 'mirada', 'parpadeo', 'giro', 'arriba'];
const FORMATS = ['pregunta-respuesta', 'malentendido', 'definicion-absurda', 'comparacion', 'situacion-cotidiana', 'mini-historia', 'deduccion-logica', 'correccion', 'ambos-equivocados', 'ambos-descubren', 'nadie-sabe', 'instrucciones'];
const DURATION = { normal: [28, 35], corta: [20, 25], larga: [40, 50] };
// words that are too local for the rest of the Spanish-speaking world, or that a kids' show should not use
const AVOID = ['coger', 'guay', 'mola', 'molar', 'flipar', 'flipas', 'chaval', 'tío', 'tía', 'curro', 'currar', 'mogollón', 'chuches', 'zumo', 'ordenador', 'gilipollas', 'joder', 'hostia', 'coño', 'cabrón', 'idiota', 'tonto', 'estúpido', 'mierda', 'sexy', 'cerveza', 'alcohol', 'apostar', 'apuesta'];
const norm = s => String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

if (args[0] === '--timing') {
  for (const f of args.slice(1)) {
    const t = JSON.parse(fs.readFileSync(f, 'utf8'));
    const script = JSON.parse(fs.readFileSync(path.join(ROOT, 'content/guiones', 'es', `${t.id}.json`), 'utf8'));
    const [lo, hi] = DURATION[script.duracion || 'normal'];
    const msg = `${t.total.toFixed(1)} s${t.voice ? '' : ' (sin voz: estimado)'}`;
    if (t.total < 20 || t.total > 50) err(t.id, `dura ${msg}: fuera de 20-50 s`);
    else if (t.total < lo || t.total > hi) warn(t.id, `dura ${msg}, fuera de su rango ${lo}-${hi} s (${script.duracion || 'normal'})`);
    else console.log(`✓ ${t.id}: ${msg}`);
    if (t.lines[0].start + t.lines[0].dur > 3.2) warn(t.id, `el gancho termina en ${(t.lines[0].start + t.lines[0].dur).toFixed(1)} s (mejor antes de 2-3 s)`);
  }
  report();
}

const dir = path.join(ROOT, 'content/guiones');
const files = args.length ? args : fs.readdirSync(dir).flatMap(l => fs.readdirSync(path.join(dir, l)).filter(f => f.endsWith('.json')).map(f => path.join(dir, l, f))).sort();
const all = [];
for (const f of files) {
  let s;
  try { s = JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { err(path.basename(f), `JSON no válido: ${e.message}`); continue; }
  const id = s.id || path.basename(f);
  all.push({ s, f });
  if (s.id !== path.basename(f, '.json')) err(id, `el id no coincide con el nombre del archivo (${path.basename(f)})`);
  if (path.basename(path.dirname(f)) !== (s.idioma || 'es')) err(id, `está en la carpeta ${path.basename(path.dirname(f))} pero su idioma es ${s.idioma}`);
  for (const k of ['serie', 'pilar', 'tema', 'formato', 'escenario', 'titulo', 'lineas', 'cierre', 'aprendizaje']) if (s[k] == null || s[k] === '') err(id, `falta "${k}"`);
  if (s.serie && !SERIES[s.serie]) err(id, `serie desconocida "${s.serie}" (ver content/series.json)`);
  if (s.pilar && !PILLARS[s.pilar]) err(id, `pilar desconocido "${s.pilar}" (ver content/pilares.json)`);
  else if (s.pilar && !PILLARS[s.pilar].temas.includes(s.tema)) err(id, `el tema "${s.tema}" no está en la lista del pilar ${s.pilar} (añádelo a content/pilares.json)`);
  if (s.formato && !FORMATS.includes(s.formato)) err(id, `formato desconocido "${s.formato}" (${FORMATS.join(', ')})`);
  if (s.escenario && !SETS.includes(s.escenario)) err(id, `escenario desconocido "${s.escenario}" (${SETS.join(', ')})`);
  if (s.duracion && !DURATION[s.duracion]) err(id, `duracion debe ser ${Object.keys(DURATION).join(', ')}`);
  if (String(s.titulo).length > 70) warn(id, 'título de más de 70 caracteres (se corta en YouTube con #Shorts)');
  if (String(s.aprendizaje || '').length < 40) err(id, 'el "aprendizaje" es demasiado corto: cada episodio deja algo útil');
  if (!Array.isArray(s.lineas) || !s.lineas.length) continue;

  // lines
  const speech = [];
  let pauses = 0, cards = 0;
  s.lineas.forEach((ln, i) => {
    const who = speakerOf(ln);
    const where = `línea ${i + 1}`;
    if (!who && ln.pausa == null) return err(id, `${where}: ni habla nadie ni es una pausa`);
    if (who && ['e', 'r', 'ambos'].filter(k => ln[k] != null).length > 1) err(id, `${where}: dos personajes en la misma línea (una línea, una voz)`);
    if (who) {
      const t = ln[who];
      if (!t.trim()) err(id, `${where}: texto vacío`);
      if (t.length > 90) err(id, `${where}: ${t.length} caracteres (máx. 90: los niños hablan corto)`);
      for (const w of norm(t).split(/[^a-zñ]+/)) if (AVOID.map(norm).includes(w)) err(id, `${where}: evita "${w}" (muy local o impropio; docs/guia-editorial.md §5)`);
      if (ln.cara && !EXPR.includes(ln.cara)) err(id, `${where}: cara "${ln.cara}" no existe (${EXPR.join(', ')})`);
      if (ln.otro && !EXPR.includes(ln.otro)) err(id, `${where}: cara del otro "${ln.otro}" no existe`);
      for (const g of [ln.gesto, ln.gesto_otro]) if (g && !GESTURES.includes(g)) err(id, `${where}: gesto "${g}" no existe (${GESTURES.join(', ')})`);
      {
        const sp = speakerOf(ln), oth = sp === 'e' ? 'r' : 'e';
        if (ln.pose && (sp === 'ambos' || !POSES[sp].includes(ln.pose))) err(id, `${where}: pose "${ln.pose}" no existe para ${sp} (${sp === 'ambos' ? 'no se usa con ambos' : POSES[sp].join(', ')})`);
        if (ln.pose_otro && (sp === 'ambos' || !POSES[oth].includes(ln.pose_otro))) err(id, `${where}: pose_otro "${ln.pose_otro}" no existe para ${oth}`);
      }
      for (const e of [ln.emote, ln.emote_otro]) if (e && !EMOTES.includes(e)) err(id, `${where}: emote "${e}" no existe (${EMOTES.join(', ')})`);
      if (ln.tarjeta) {
        cards++;
        if (ln.tarjeta.icono && !ICONS.includes(ln.tarjeta.icono)) err(id, `${where}: icono "${ln.tarjeta.icono}" no existe (${ICONS.join(', ')})`);
        if (ln.tarjeta.texto && ln.tarjeta.texto.length > 16) err(id, `${where}: texto de tarjeta de más de 16 caracteres`);
      }
      speech.push({ who, text: t, pause: 0 });
    } else {
      if (!speech.length) err(id, `${where}: no se puede empezar con una pausa: el gancho va primero`);
      if (ln.pausa > 2) err(id, `${where}: pausa de ${ln.pausa} s (máx. 2 s: una pausa es un gesto, no relleno)`);
      if (ln.reaccion && !REACTIONS.includes(ln.reaccion)) err(id, `${where}: reacción "${ln.reaccion}" no existe (${REACTIONS.join(', ')})`);
      for (const c of Object.values(ln.caras || {})) if (!EXPR.includes(c)) err(id, `${where}: cara "${c}" no existe`);
      pauses += ln.pausa;
      if (speech.length) speech[speech.length - 1].pause += ln.pausa;
    }
  });
  if (!speech.some(l => l.who === 'e' || l.who === 'ambos') || !speech.some(l => l.who === 'r' || l.who === 'ambos')) err(id, 'tienen que hablar los dos');
  if (pauses > 3.5) err(id, `${pauses} s de pausas en total (máx. 3,5 s: no se alarga un vídeo artificialmente)`);
  if (cards > 3) warn(id, `${cards} tarjetas: con más de 3 la idea se dispersa (una idea por vídeo)`);
  if (speech.length > 16) warn(id, `${speech.length} líneas: ¿sigue siendo una sola idea?`);
  if (speech[0] && speech[0].text.length > 70) warn(id, 'la primera línea (el gancho) tiene más de 70 caracteres: tiene que entrar en 2-3 s');
  // closing: the brand device
  const tipo = s.cierre?.tipo;
  if (!['hablado', 'texto', 'reaccion'].includes(tipo)) err(id, 'cierre.tipo debe ser hablado, texto o reaccion');
  const lastItem = s.lineas[s.lineas.length - 1];
  if (tipo === 'hablado' && speech.length && !norm(speech[speech.length - 1].text).includes('cosas de mayores')) err(id, 'cierre hablado: la última línea tiene que decir «Cosas de mayores»');
  if ((tipo === 'texto' || tipo === 'reaccion') && lastItem?.pausa == null) err(id, `cierre ${tipo}: termina con una pausa (la reacción) y el sello aparece después`);

  // estimated duration, the same way src/render.mjs counts it without voice
  let t = 0.25;
  speech.forEach((l, i) => { t += estimate(l.text) + 0.28 + l.pause; });
  t += -0.3 + 1.35;
  s._dur = t;
  const [lo, hi] = DURATION[s.duracion || 'normal'];
  if (t < 20 || t > 50) err(id, `duración estimada ${t.toFixed(1)} s: fuera de 20-50 s`);
  else if (t < lo - 2 || t > hi + 2) warn(id, `duración estimada ${t.toFixed(1)} s, lejos de ${lo}-${hi} s (${s.duracion || 'normal'}); si el guion lo pide, declara "duracion"`);
  s._speech = speech;
}

// the whole catalogue: no repeated topics, variety of series, formats and roles
const ids = new Set(), temas = new Map();
for (const { s } of all) {
  if (ids.has(s.id)) err(s.id, 'id repetido'); ids.add(s.id);
  const k = `${s.idioma || 'es'}|${norm(s.tema)}`;
  if (temas.has(k)) err(s.id, `tema repetido: "${s.tema}" ya está en ${temas.get(k)}`); else temas.set(k, s.id);
}
const byLang = all.filter(x => (x.s.idioma || 'es') === 'es').map(x => x.s).sort((a, b) => a.id.localeCompare(b.id));
for (let i = 1; i < byLang.length; i++) {
  if (byLang[i].serie === byLang[i - 1].serie) warn(byLang[i].id, `misma serie que el anterior (${byLang[i].serie}): se publican seguidos`);
  if (byLang[i].pilar === byLang[i - 1].pilar && byLang[i].pilar === byLang[i - 2]?.pilar) warn(byLang[i].id, `tercer ${byLang[i].pilar} seguido`);
}
if (!args.length && byLang.length >= 12) {
  const count = k => byLang.reduce((m, s) => (m[s[k]] = (m[s[k]] || 0) + 1, m), {});
  const series = count('serie'), formats = count('formato'), pillars = count('pilar');
  for (const k of Object.keys(SERIES).filter(k => !k.startsWith('_'))) if (!series[k]) warn('catálogo', `la serie ${k} no tiene ningún guion`);
  for (const k of Object.keys(PILLARS).filter(k => !k.startsWith('_'))) if (!pillars[k]) warn('catálogo', `el pilar ${k} no tiene ningún guion`);
  if (Object.keys(formats).length < 6) warn('catálogo', `solo ${Object.keys(formats).length} estructuras distintas: los vídeos se volverán previsibles`);
  const swaps = byLang.filter(s => s.roles?.pregunta === 'e').length;
  if (swaps / byLang.length < 0.15) warn('catálogo', `R pregunta en el ${Math.round(100 - swaps / byLang.length * 100)} % de los guiones: intercambia los papeles más a menudo`);
  console.log(`Catálogo: ${byLang.length} guiones · series ${JSON.stringify(series)} · pilares ${JSON.stringify(pillars)} · ${Object.keys(formats).length} estructuras · E pregunta en ${swaps}`);
}

// calendar
const cal = JSON.parse(fs.readFileSync(path.join(ROOT, 'content/calendario.json'), 'utf8'));
for (const [k, v] of Object.entries(cal.franjas || {})) if (!/^\d\d:\d\d$/.test(v)) err('calendario', `franja ${k}: hora "${v}" no es HH:MM`);
if (Object.keys(cal.franjas || {}).length !== 2) warn('calendario', 'el plan es de 2 vídeos al día');
if (cal.inicio && !/^\d{4}-\d\d-\d\d$/.test(cal.inicio)) err('calendario', `inicio "${cal.inicio}" no es YYYY-MM-DD`);

for (const { s } of all) if (s._dur) console.log(`${errors.some(e => e.startsWith(s.id + ':')) ? '✗' : '✓'} ${s.id}  ${s._dur.toFixed(1)} s  ${s.serie} · ${s.pilar} · ${s.formato}`);
report();

function report() {
  for (const w of warns) console.log('⚠️  ' + w);
  for (const e of errors) console.log('❌ ' + e);
  console.log(errors.length ? `\n${errors.length} errores, ${warns.length} avisos` : `\nOK (${warns.length} avisos)`);
  process.exit(errors.length ? 1 : 0);
}
