"""Short test scene of the mesh animation (tools/malla.py) moved by real gestures (tools/gestos.py): E waves and
says "¡Vamos a explicar cómo funciona el mundo!" gesturing like a real person telling a story.
Usage:
  python3 tools/escena_malla.py out.mp4          the scene (~7 s, with voice and music)
  python3 tools/escena_malla.py out.png 3.2      one frame
Gestures: motion capture of the CMU Graphics Lab database (free, commercial use allowed): 141_16 "wave hello" and
138_11 "story" (assets/gestos/cmu_*.json, made with tools/gestos.py bvh)."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malla, gestos
from escena_rig import ROOT, W, H, FPS, HEIGHT, COLOR, envelope, background, label

C = 'e'
TOTAL = 7.0
VOICE = os.path.join(ROOT, 'content/especiales/presentacion/voces/02.mp3')
LINE = '¡Vamos a explicar cómo funciona el mundo!'
SAY = 3.05                                        # when E starts talking
CLIPS = [('cmu_141_16', 0.0, 0.0, 2.2),           # (gesto, at, from, to): waves
         ('cmu_138_11', 2.75, 0.0, 3.7)]          # tells, opening the arms on "el mundo"
BLINKS = [1.45, 4.85]
SHOT = (540, 1075, 1.4)                          # camera centre x, y and zoom
WORLD = (540, 1620, 0.98 * HEIGHT[C])             # where E stands (x, floor, size)



def slow_start(X, secs=0.45, k=0.5, hold=0.35, fps=FPS):
    """The adult of the recording lifts the arm very fast: the first secs go at k of the speed, after hold seconds
    standing still, so the arm comes up like a child's (elbow first, the hand in front of the chest)."""
    src = np.concatenate([np.zeros(int(hold * fps)), np.arange(0, secs * fps, k)])
    src = np.concatenate([src, np.arange(src[-1] + 1, len(X))])
    i = np.clip(src.astype(int), 0, len(X) - 2)
    f = (src - i)[:, None, None]
    return X[i] * (1 - f) + X[i + 1] * f


clips = []
for name, at, a, b in CLIPS:
    X, fps = gestos.load(name)
    X = X[int(a * fps):int(b * fps)]
    clips.append((slow_start(X) if at == 0 else X, at))
X = malla.blend(clips, fade=0.45)
X = np.concatenate([X, np.repeat(X[-1:], int(TOTAL * FPS) - len(X) + 1, 0)])
POSE = malla.retarget(X, C)
ENV = envelope(VOICE)


def state(t):
    f = min(int(round(t * FPS)), len(POSE) - 1)
    p = dict(POSE[f])
    i = (t - SAY) * FPS
    p['talk'] = float(np.interp(i, np.arange(len(ENV)), ENV, left=0, right=0))
    p['blink'] = any(0 <= t - bt < 0.13 for bt in BLINKS)
    return p


def frame_at(t):
    cx, cy, z = SHOT
    img = background(z, cx, cy)
    x, floor, s = WORLD
    malla.kid(img, C, W / 2 + (x - cx) * z, H / 2 + (floor - cy) * z, s * z, state(t))
    if SAY - 0.05 <= t <= SAY + 2.33 + 0.4:
        label(img, LINE, W / 2, 1640, 74, (30, 25, 35), (255, 255, 255), border=COLOR[C],
              scale=min(1.0, 0.85 + (t - SAY + 0.05) * 3))
    return img.convert('RGB')


def render_range(args):
    a, b, path = args
    with open(path, 'wb') as f:
        for n in range(a, b):
            f.write(frame_at(n / FPS).tobytes())


def video(out):
    from multiprocessing import Pool
    work = os.path.join(os.path.dirname(os.path.abspath(out)), 'malla-work')
    os.makedirs(work, exist_ok=True)
    n = int(TOTAL * FPS)
    jobs = os.cpu_count() or 2
    cuts = np.linspace(0, n, jobs * 3 + 1).astype(int)
    parts = [(int(cuts[k]), int(cuts[k + 1]), os.path.join(work, f'part{k:02d}.raw')) for k in range(len(cuts) - 1)]
    with Pool(jobs) as pool:
        pool.map(render_range, parts, chunksize=1)
    plan = {'total': TOTAL, 'clips': [{'file': VOICE, 'at': SAY, 'gain': 1.0}], 'sfx': [],
            'music': os.path.join(ROOT, 'assets/music/juguete.wav'), 'musicGain': 0.14}
    json.dump(plan, open(os.path.join(work, 'mix.json'), 'w'))
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools/mix.py'), os.path.join(work, 'mix.json'),
                    os.path.join(work, 'mix.wav')], check=True)
    cat = subprocess.Popen(['cat'] + [p[2] for p in parts], stdout=subprocess.PIPE)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                    '-i', '-', '-i', os.path.join(work, 'mix.wav'), '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out],
                   stdin=cat.stdout, check=True)
    for p in parts:
        os.remove(p[2])


if __name__ == '__main__':
    if sys.argv[1].endswith(('.png', '.jpg')):
        frame_at(float(sys.argv[2])).save(sys.argv[1])
    else:
        video(sys.argv[1])
