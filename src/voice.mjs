// Voices with edge-tts (free), one per character and language, the same in every video (docs/biblia-personajes.md §5).
// Same approach as zero-understands/src/voice.mjs. A new language = a new block in VOICES (and its scripts).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

export const VOICES = {
  es: {
    // E: quick, bright, a little higher (impulsive, always has an idea)
    e: { voice: 'es-ES-XimenaNeural', rate: '+8%', pitch: '+28Hz' },
    // R: calmer, lower and a bit slower (he thinks before asking)
    r: { voice: 'es-ES-ElviraNeural', rate: '-3%', pitch: '+14Hz' },
  },
};
export const voiceOn = () => String(process.env.CDM_VOICE ?? 'true') !== 'false';
export const probe = f => Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).toString().trim());
// rough duration when there is no voice (local previews): kids speak ~2.7 words per second, plus the breath of the line
export const estimate = text => Math.max(0.7, String(text).split(/\s+/).filter(Boolean).length / 2.7 + 0.25);

const clean = t => String(t ?? '').replace(/\p{Extended_Pictographic}|\u{FE0F}|\u{200D}/gu, '').replace(/(\d)\s?%/g, '$1 por ciento').replace(/€/g, ' euros').replace(/\s+/g, ' ').trim();

export function tts(text, file, who, lang = 'es', overrides = {}) {
  const v = Object.assign({}, VOICES[lang]?.[who] || VOICES.es[who], overrides?.[who] || {});
  const tf = path.join(os.tmpdir(), `cdm-tts-${process.pid}-${Math.random().toString(36).slice(2)}.txt`);
  fs.writeFileSync(tf, clean(text));
  const proxy = process.env.HTTPS_PROXY ? ['--proxy', process.env.HTTPS_PROXY] : [];
  let err = '';
  for (let i = 0; i < 3; i++) {
    try {
      fs.rmSync(file, { force: true });
      execFileSync('edge-tts', [...proxy, '--voice', v.voice, `--rate=${v.rate}`, `--pitch=${v.pitch}`, '--file', tf, '--write-media', file], { stdio: 'pipe' });
      if (fs.existsSync(file) && fs.statSync(file).size > 1000) { fs.rmSync(tf, { force: true }); return probe(file); }
    } catch (e) { err = String(e.stderr || e.message).slice(-200); }
  }
  fs.rmSync(tf, { force: true });
  throw new Error('edge-tts failed: ' + err);
}
