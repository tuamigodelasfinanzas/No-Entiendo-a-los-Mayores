// Voices with edge-tts (free), one per character and language, the same in every video (docs/biblia-personajes.md §5).
// Same approach as zero-understands/src/voice.mjs. A new language = a new block in VOICES (and its scripts).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

export const VOICES = {
  es: {
    // Natural voices, as the service speaks them: only its own pitch and rate, a little. Any pitch / formant
    // processing afterwards (asetrate, Rubber Band) sounds metallic to Chiño (27-10-2026): don't add one.
    // E: quick, bright, a little higher (impulsive, always has an idea)
    e: { voice: 'es-ES-XimenaNeural', rate: '+4%', pitch: '+12Hz' },
    // R: calmer, lower and a bit slower (he thinks before asking)
    r: { voice: 'es-ES-ElviraNeural', rate: '-2%', pitch: '+6Hz' },
  },
};
export const voiceOn = () => String(process.env.CDM_VOICE ?? 'true') !== 'false';
export const probe = f => Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).toString().trim());
// rough duration when there is no voice (local previews): kids speak ~2.7 words per second, plus the breath of the line
export const estimate = text => Math.max(0.7, String(text).split(/\s+/).filter(Boolean).length / 2.7 + 0.25);

const clean = t => String(t ?? '').replace(/\p{Extended_Pictographic}|\u{FE0F}|\u{200D}/gu, '').replace(/(\d)\s?%/g, '$1 por ciento').replace(/€/g, ' euros').replace(/\s+/g, ' ').trim();

// edge-tts leaves ~0.1 s of silence before and ~0.6 s after every clip: over 10-12 lines that is several seconds
// of dead air. Trim both ends (keeping a short tail so the last word is not clipped).
export function trim(file) {
  const tmp = file.replace(/\.mp3$/, '') + '.trim.mp3';
  const sr = 'silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.04';
  try {
    execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', file, '-af', `${sr},areverse,${sr.replace('0.04', '0.12')},areverse`, '-c:a', 'libmp3lame', '-q:a', '2', tmp], { stdio: 'pipe' });
    if (probe(tmp) > 0.3) fs.renameSync(tmp, file); else fs.rmSync(tmp, { force: true });
  } catch { fs.rmSync(tmp, { force: true }); }
}

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
      if (fs.existsSync(file) && fs.statSync(file).size > 1000) { fs.rmSync(tf, { force: true }); trim(file); return probe(file); }
    } catch (e) { err = String(e.stderr || e.message).slice(-200); }
  }
  fs.rmSync(tf, { force: true });
  throw new Error('edge-tts failed: ' + err);
}
