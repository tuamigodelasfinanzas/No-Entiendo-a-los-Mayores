// Renders one script: content/guiones/<lang>/<id>.json -> short.mp4 (1080x1920, 30 fps, H.264 + AAC), cover.jpg,
// timing.json and post.json (titles and texts for Instagram, Facebook and YouTube).
// Usage: node src/render.mjs <script.json> <out-dir>
// Env: CDM_VOICE=false renders without voice (durations estimated), CDM_FPS (default 30), CDM_STILLS=1 saves a
// still every second in <out>/work, CDM_FRAMES="0.4,50%,-0.4" saves start / middle / end as <out>/frame-inicio|centro|final.jpg.
// Same pipeline as zero-understands/src/render.mjs: voice -> frames (Chromium + stage.js) -> sfx + music -> mux.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync, spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { tts, voiceOn, estimate } from './voice.mjs';

const ENV_HZ = 50;   // values per second of the mouth envelope of each line (envelope / syllables below)
import { build } from './director.mjs';
import { post } from './post.mjs';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const [file, outDir = 'out'] = process.argv.slice(2);
const script = JSON.parse(fs.readFileSync(file, 'utf8'));
const ep = JSON.parse(JSON.stringify(build(script)));
const FPS = Number(process.env.CDM_FPS || 30);
const [W, H] = [1080, 1920];
const work = path.join(outDir, 'work');
fs.mkdirSync(work, { recursive: true });

// 1) voice: one clip per line ("ambos" = both voices at once); the beat lasts as long as its lines need
let useVoice = voiceOn();
const clips = [];
const beats = [];
let t = 0;
for (const [i, b] of ep.beats.entries()) {
  const beat = { i, start: t, lines: [] };
  let lt = b.pre ?? 0.3;
  for (const [j, ln] of (b.lines || []).entries()) {
    let d = estimate(ln.text);
    if (useVoice) {
      try {
        const who = ln.who === 'ambos' ? ['e', 'r'] : [ln.who];
        d = 0;
        for (const w of who) {
          const f = path.join(work, `v${i}-${j}-${w}.mp3`);
          d = Math.max(d, tts(ln.text, f, w, ep.lang));
          clips.push({ file: f, at: t + lt, gain: who.length > 1 ? 0.8 : 1 });
        }
      } catch (e) { console.warn('::warning::voice failed, continuing without voice: ' + e.message); useVoice = false; clips.length = 0; d = estimate(ln.text); }
    }
    const env = useVoice ? mergeEnv(clips.filter(c => c.at === t + lt).map(c => envelope(c.file))) : syllables(ln.text, d);
    beat.lines.push({ who: ln.who, text: ln.text, start: t + lt, dur: d, words: wordTimes(ln.text, d), env });
    if (useVoice) console.log(`  ${ln.who.padEnd(5)} ${d.toFixed(2)} s (est. ${estimate(ln.text).toFixed(2)})  ${ln.text}`);
    lt += d + (ln.gap ?? 0.3);
  }
  const need = beat.lines.length ? lt - 0.3 + (b.hold ?? 0.55) : 0;
  beat.dur = Math.max(b.min ?? 0, need, 0.5);
  t += beat.dur;
  beats.push(beat);
}
const total = t;
console.log(`${ep.id}: ${beats[0].lines.length} lines, ${total.toFixed(1)} s${useVoice ? '' : ' (no voice, estimated)'}`);

// word timings for the captions: spread over the clip by length (long words take longer)
// the mouth follows the voice: loudness of the clip, ENV_HZ values per second, 0..1 (fast to open, a little
// slower to close, like a jaw), so it shuts in the pauses and opens more on the stressed syllables
function envelope(file) {
  const raw = execFileSync('ffmpeg', ['-v', 'error', '-i', file, '-ac', '1', '-ar', '8000', '-f', 's16le', '-']);
  const x = new Int16Array(raw.buffer, raw.byteOffset, raw.length >> 1), n = 8000 / ENV_HZ, out = [];
  for (let i = 0; i + n <= x.length; i += n) {
    let e = 0;
    for (let j = i; j < i + n; j++) e += x[j] * x[j];
    out.push(Math.sqrt(e / n));
  }
  const sorted = [...out].sort((a, b) => a - b), top = sorted[Math.floor(sorted.length * 0.95)] || 1, floor = top * 0.08;
  let v = 0;
  return out.map(e => { const k = Math.min(1, Math.max(0, (e - floor) / (top - floor))); v += (k - v) * (k > v ? 0.7 : 0.35); return +v.toFixed(2); });
}
function mergeEnv(envs) {
  if (envs.length < 2) return envs[0] || [];
  return envs[0].map((v, i) => Math.max(...envs.map(e => e[i] ?? 0)));
}
// without voice (local previews): one bump per syllable (vowel group), closed between words
function syllables(text, d) {
  const out = new Array(Math.ceil(d * ENV_HZ)).fill(0);
  let t0 = 0;
  for (const { w, end } of wordTimes(text, d)) {
    const syl = Math.max(1, (w.toLowerCase().match(/[aeiouáéíóúü]+/g) || []).length), len = (end - t0) * 0.85;
    for (let k = 0; k < syl; k++) {
      const a = t0 + len * k / syl, b = t0 + len * (k + 1) / syl, h = 0.6 + 0.4 * ((w.length * 7 + k * 13) % 5) / 4;
      for (let i = Math.floor(a * ENV_HZ); i < Math.min(out.length, Math.ceil(b * ENV_HZ)); i++) out[i] = +(h * Math.sin(Math.PI * Math.min(1, Math.max(0, (i / ENV_HZ - a) / (b - a))))).toFixed(2);
    }
    t0 = end;
  }
  return out;
}

function wordTimes(text, d) {
  const ws = String(text).split(/\s+/).filter(Boolean);
  const wt = ws.map(w => 1.2 + w.replace(/[^\p{L}\p{N}]/gu, '').length);
  const sum = wt.reduce((a, b) => a + b, 0);
  let acc = 0;
  return ws.map((w, i) => { acc += wt[i] / sum * d; return { w, end: acc }; });
}

// 2) sound effects at their times (t, u, l = line start, le = line end, end = before the end)
const SFX = path.join(ROOT, 'assets/sfx');
const sfx = [];
for (const [i, b] of ep.beats.entries()) for (const s of b.sfx || []) {
  const beat = beats[i];
  let at = beat.start + (s.t ?? 0) + (s.u != null ? s.u * beat.dur : 0);
  if (s.l != null && beat.lines[s.l]) at += beat.lines[s.l].start - beat.start;
  if (s.le != null && beat.lines[s.le]) at += beat.lines[s.le].start + beat.lines[s.le].dur - beat.start;
  if (s.end != null) at = beat.start + beat.dur - s.end;
  const f = path.join(SFX, s.s + '.wav');
  if (fs.existsSync(f)) sfx.push({ file: f, at, gain: s.g ?? 0.8 }); else console.warn('::warning::missing sfx ' + s.s);
}

// 3) frames: a local origin serves the repo files (character layers, font) to the page
function font() {
  for (const b of [path.join(ROOT, 'node_modules/@fontsource/fredoka/files'), path.join(ROOT, 'assets/fonts')]) {
    const css = [];
    for (const wgt of ['700', '500']) {
      const f = path.join(b, `fredoka-latin-${wgt}-normal.woff2`);
      if (fs.existsSync(f)) css.push(`@font-face{font-family:'Fredoka';font-weight:${wgt};src:url(data:font/woff2;base64,${fs.readFileSync(f).toString('base64')}) format('woff2')}`);
    }
    if (css.length) return css.join('');
  }
  console.warn('::warning::Fredoka not found, fallback font');
  return '';
}
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const browser = await chromium.launch({ executablePath: process.env.CDM_CHROME || undefined, args: ['--font-render-hinting=none'] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on('pageerror', e => console.error('page error: ' + e.message));
const ORIGIN = 'http://cdm.local';
await page.route(`${ORIGIN}/**`, r => {
  const u = new URL(r.request().url());
  if (u.pathname === '/') return r.fulfill({ contentType: 'text/html', body: `<!doctype html><html><head><meta charset="utf-8"><style>${font()}*{margin:0;padding:0}html,body{width:${W}px;height:${H}px;overflow:hidden;background:#fff}</style></head><body><div id="stage"></div></body></html>` });
  const f = path.join(ROOT, decodeURIComponent(u.pathname));
  if (!f.startsWith(path.join(ROOT, 'assets')) || !fs.existsSync(f)) return r.fulfill({ status: 404, body: '' });
  r.fulfill({ contentType: f.endsWith('.png') ? 'image/png' : 'application/octet-stream', body: fs.readFileSync(f) });
});
await page.goto(`${ORIGIN}/`);
const rigs = Object.fromEntries(['e', 'r'].map(w => [w, JSON.parse(fs.readFileSync(path.join(ROOT, `assets/characters/${w}/rig.json`), 'utf8'))]));
const imgs = Object.fromEntries(['e', 'r'].map(w => [w, Object.fromEntries(['head', 'body', 'blink', 'jaw'].map(k => [k, `${ORIGIN}/assets/characters/${w}/${k}.png`]))]));
// Chiño's poses (tools/prepare_poses.py): only the ones this episode uses, so the page loads fast
const used = Object.fromEntries(['e', 'r'].map(w => [w, new Set(ep.beats.flatMap(b => (b.actors || []).filter(a => a.type === 'kid' && a.id === w).flatMap(a => a.k.flatMap(k => [k.pose, k.pose0]))).filter(n => n && rigs[w].poses?.[n]))]));
for (const w of ['e', 'r']) {
  imgs[w].poses = Object.fromEntries([...used[w]].map(n => [n, `${ORIGIN}/assets/characters/${w}/poses/${n}.png`]));
  imgs[w].fronts = Object.fromEntries([...used[w]].filter(n => rigs[w].poses[n].front).map(n => [n, `${ORIGIN}/assets/characters/${w}/poses/${n}-front.png`]));
}
await page.evaluate(d => { window.DATA = d.data; window.KID_RIG = d.rigs; window.KID_IMG = d.imgs; }, { data: { ep, beats, w: W, h: H, fps: FPS, life: process.env.CDM_LIFE !== '0' }, rigs, imgs });
for (const f of ['puppets.js', 'stage.js']) await page.addScriptTag({ path: path.join(ROOT, 'src', f) });
await page.waitForFunction('window.ready === true');
await page.evaluate('document.fonts.ready');
// decode the character layers before the first frame
await page.evaluate(async urls => { await Promise.all(urls.map(u => new Promise(res => { const i = new Image(); i.onload = i.onerror = res; i.src = u; }))); }, Object.values(imgs).flatMap(o => Object.values(o).flatMap(v => (typeof v === 'string' ? [v] : Object.values(v)))));

const video = path.join(work, 'video.mp4');
const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-tune', 'animation', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-g', String(FPS * 2), video], { stdio: ['pipe', 'inherit', 'inherit'] });
const N = Math.ceil(total * FPS);
const stills = process.env.CDM_STILLS ? Number(process.env.CDM_STILLS) : 0;
// CDM_FRAMES: seconds, negative = from the end, or a percentage. Three values ("0.4,50%,-0.4") are saved as
// frame-inicio / frame-centro / frame-final.jpg (start, middle, end); otherwise as frame-<second>.jpg.
const frameAt = (process.env.CDM_FRAMES || '').split(',').filter(Boolean)
  .map(v => (v.endsWith('%') ? total * parseFloat(v) / 100 : Number(v)))
  .map(x => Math.min(N - 1, Math.max(0, Math.round((x < 0 ? total + x : x) * FPS)))).sort((a, b) => a - b);
const frameName = k => (frameAt.length === 3 ? ['inicio', 'centro', 'final'][frameAt.indexOf(k)] : (k / FPS).toFixed(2));
// the cover: the hook on screen, both kids, before anyone moves much
const coverFrame = Math.min(N - 1, Math.round(0.6 * FPS));
for (let k = 0; k < N; k++) {
  await page.evaluate(x => window.frame(x), k / FPS);
  const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (stills && k % Math.round(FPS * stills) === 0) fs.writeFileSync(path.join(work, `still-${String(k).padStart(5, '0')}.jpg`), buf);
  if (frameAt.includes(k)) fs.writeFileSync(path.join(outDir, `frame-${frameName(k)}.jpg`), buf);
  if (k === coverFrame) fs.writeFileSync(path.join(outDir, 'cover.jpg'), buf);
  if (k % (FPS * 10) === 0 || process.env.CDM_DEBUG) console.log(`frame ${k}/${N}`);
}
ff.stdin.end();
await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
await browser.close();

// 4) audio: voices + sfx + music bed ducked under the voices (tools/mix.py, the same mixer as ZERO), then mux
const plan = { total, clips, sfx, music: ep.music ? path.join(ROOT, 'assets/music', ep.music + '.wav') : null, musicGain: ep.musicGain ?? 0.08 };
fs.writeFileSync(path.join(work, 'mix.json'), JSON.stringify(plan));
const wav = path.join(work, 'audio.wav');
execFileSync('python3', [path.join(ROOT, 'tools/mix.py'), path.join(work, 'mix.json'), wav], { stdio: 'inherit' });
const out = path.join(outDir, 'short.mp4');
execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', video, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]);
fs.writeFileSync(path.join(outDir, 'timing.json'), JSON.stringify({ id: ep.id, total: +total.toFixed(2), voice: useVoice, lines: beats[0].lines.map(l => ({ who: l.who, start: +l.start.toFixed(2), dur: +l.dur.toFixed(2), text: l.text })) }, null, 1));
fs.writeFileSync(path.join(outDir, 'post.json'), JSON.stringify({ ...post(script), duration: +total.toFixed(2), cover_ms: Math.round(coverFrame / FPS * 1000) }, null, 1));
console.log('OK', out, total.toFixed(1) + ' s');
