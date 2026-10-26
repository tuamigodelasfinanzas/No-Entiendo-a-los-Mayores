"""Mixes voices, sound effects and the music bed into one WAV.
Usage: python3 tools/mix.py mix.json out.wav
The music is looped, faded in and out, and ducked while anyone speaks."""
import json, subprocess, sys, wave
import numpy as np

SR = 48000


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def main(plan_file, out):
    plan = json.load(open(plan_file))
    n = int((plan['total'] + 0.5) * SR)
    voice = np.zeros(n, dtype=np.float32)
    fx = np.zeros(n, dtype=np.float32)
    cache = {}
    for kind, bus in (('clips', voice), ('sfx', fx)):
        for c in plan[kind]:
            if c['file'] not in cache:
                cache[c['file']] = load(c['file'])
            s = cache[c['file']] * c.get('gain', 1.0)
            i = max(0, int(c['at'] * SR))
            m = min(len(s), n - i)
            if m > 0:
                bus[i:i + m] += s[:m]
    mix = voice + fx * 0.9
    if plan.get('music'):
        try:
            mu = load(plan['music'])
            reps = int(np.ceil(n / len(mu)))
            bed = np.tile(mu, reps)[:n] * plan.get('musicGain', 0.12)
            # duck under the voice: envelope of the voice, smoothed
            env = np.abs(voice)
            k = int(0.25 * SR)
            # moving average with a running sum: O(n) (np.convolve with a 12000-sample kernel is O(n*k))
            c = np.concatenate([[0.0], np.cumsum(env, dtype=np.float64)])
            idx = np.arange(n)
            lo, hi = np.clip(idx - k // 2, 0, n), np.clip(idx + k - k // 2, 0, n)
            env = ((c[hi] - c[lo]) / k).astype(np.float32)
            duck = 1.0 - 0.6 * np.clip(env / 0.03, 0, 1)
            fade = np.ones(n)
            f = int(1.0 * SR)
            fade[:f] = np.linspace(0, 1, f)
            fade[-f:] = np.linspace(1, 0, f)
            mix += bed * duck * fade
        except Exception as e:  # music is optional
            print('::warning::music skipped:', e)
    peak = np.max(np.abs(mix)) or 1
    if peak > 0.97:
        mix *= 0.97 / peak
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == '__main__':
    main(*sys.argv[1:3])
