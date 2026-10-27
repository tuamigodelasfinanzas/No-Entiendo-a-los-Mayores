"""The channel's intro Short (E and R), 1080x1920, ~29 s, built with tools/escena_rig.py.
Usage:
  python3 tools/presentacion.py out.mp4                 video (voices from content/especiales/presentacion/voces)
  TRAMO=3,7.2 python3 tools/presentacion.py out.mp4     only that stretch, to review
  python3 tools/presentacion.py out.png 12.5            one frame
  python3 tools/presentacion.py poses.png --poses       every pose of both kids, for checking hands and arms"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from escena_rig import *                        # noqa: F401,F403  (kid, POSES, mix_arm, label, background...)
from escena_rig import ROOT, W, H, FPS, K, POSES, MOVE, COLOR, HEIGHT, kid, mix_arm, settle, keyed, envelope, \
    background, label, pop, font, ease, pose_sheet

DIR = os.path.join(ROOT, 'content/especiales/presentacion')
# ---------------------------------------------------------------- the script
LINES = {l['id']: l for l in json.load(open(os.path.join(DIR, 'lineas.json')))['lineas']}
DUR = json.load(open(os.path.join(DIR, 'voces/duraciones.json')))
SAYS = {'01': 0.35, '02': 3.3, '03': 5.75, '04': 7.35, '05': 12.3, '06': 16.45, '07': 20.8, '08': 23.15}  # line -> start
TOTAL = 29.0
# world: E on the left, R on the right, both standing on the same floor
# R is taller than E (Chiño's photo of them: E is about 87 % of R's height); the drawings are almost the same height
WORLD = {'e': (300, 1620, 0.98 * HEIGHT['e']), 'r': (780, 1620, 0.98 * HEIGHT['r'])}
# shots: (start, camera centre x, y, zoom, push over the shot)
SHOTS = [
    (0.0, 790, 845, 1.75, 0.04),     # 1 R, close up: "E, ¿qué estamos haciendo aquí?"
    (3.0, 360, 1025, 1.35, 0.03),     # 2 E comes in pointing up
    (5.6, 540, 1040, 1.22, 0.02),    # 3 both: "¿Todo el mundo?"
    (7.2, 350, 1025, 1.38, 0.03),     # 4 E, hands on the hips: "Todo..."
    (9.4, 540, 1000, 1.12, 0.03),    # 5 E explains, the things he says pop up over them
    (12.1, 740, 885, 1.55, 0.04),    # 6 R, fist under the chin
    (14.6, 540, 1040, 1.22, 0.0),    # 7 both: an awkward silence (crickets)
    (16.2, 345, 965, 1.6, 0.03),     # 8 E scratches his head, then points up
    (18.3, 540, 990, 1.05, 0.03),    # 9 both: "...por eso vamos a investigarlo"
    (20.6, 545, 1070, 1.36, 0.03),    # 10 both to camera: "Esto puede salir muy bien..."
    (23.0, 430, 1040, 1.42, 0.03),   # 11 E: "¡O muy divertido!"
    (25.4, 540, 1000, 1.0, 0.02),    # 12 both wave and celebrate, end texts
]
ARMS = {  # kid -> [(time, pose)]; between keys the arm moves in 0.35 s
    'e': [(0, 'quieto'), (3.05, 'senala_arriba'), (7.1, 'cintura'), (9.3, 'explica'), (12.0, 'quieto'),
          (16.2, 'rasca'), (17.45, 'senala_arriba'), (20.4, 'quieto'), (23.05, 'celebra'), (24.6, 'quieto'),
          (25.45, 'celebra'), (27.4, 'saluda_izq')],
    'r': [(0, 'quieto'), (5.65, 'encoge_corto'), (7.0, 'quieto'), (12.1, 'barbilla'), (16.0, 'quieto'),
          (20.7, 'explica'), (22.9, 'quieto'), (25.5, 'saluda')],
}
LOOK = {'e': [(0, 0.04), (3.3, 0.0), (5.7, 0.05), (7.2, 0.0), (12.2, 0.05), (16.3, -0.03), (20.6, 0.0), (21.0, 0.04), (23.0, 0.0)],
        'r': [(0, 0.0), (3.2, -0.05), (5.7, 0.0), (7.1, -0.05), (12.1, 0.0), (14.6, -0.06), (20.6, 0.0), (23.0, -0.05), (25.4, 0.0)]}
BLINK = {'e': [1.2, 4.1, 6.9, 9.0, 11.6, 13.9, 15.6, 19.4, 22.1, 24.9, 27.8], 'r': [1.9, 4.7, 7.6, 10.4, 13.3, 15.1, 17.8, 20.2, 23.6, 26.6, 28.4]}
ICONS = [('wifi', 'Internet'), ('moneda', 'Dinero'), ('planeta', 'Espacio'), ('bombilla', 'Inventos')]
ICON_AT = [8.3, 9.15, 9.95, 10.8]


ENV = {}


def talk(c, t):
    for lid, at in SAYS.items():
        if LINES[lid]['who'] != c:
            continue
        if lid not in ENV:
            ENV[lid] = envelope(os.path.join(DIR, 'voces', lid + '.mp3'))
        i = (t - at) * FPS
        if 0 <= i < len(ENV[lid]) - 1:
            j = int(i)
            return float(ENV[lid][j] * (1 - (i - j)) + ENV[lid][j + 1] * (i - j))
    return 0.0


def speaking(c, t):
    return any(LINES[l]['who'] == c and at <= t <= at + DUR[l] for l, at in SAYS.items())


def state(c, t):
    """Pose of kid c at t."""
    a, b, x = keyed(ARMS[c], t)
    since = max([t - k_t - MOVE for k_t, _ in ARMS[c] if k_t <= t] + [0])
    prev = [n for k_t, n in ARMS[c] if k_t <= t - MOVE] or [ARMS[c][0][1]]
    before = prev[-2] if len(prev) > 1 else prev[-1]
    arms = {}
    for sd in ('l', 'r'):
        pa, pb = POSES[a][sd], POSES[b][sd]
        if x >= 1 or a == b:
            v = list(pb) + [None] * (5 - len(pb))
            du, df = settle(POSES[before][sd], pb, since)
            v[0] += du
            v[1] += df
        else:
            v = list(mix_arm(pa, pb, x))
            if pb[0] < 0 or pa[0] < 0 or (len(pb) > 4 and pb[4]) or (len(pa) > 4 and pa[4]):
                v[4] = (pb[4] if len(pb) > 4 else None) if x > 0.5 else (pa[4] if len(pa) > 4 else None)
        arms[sd] = v
    # gestures that keep moving
    if b == 'saluda' or b == 'saluda_izq':
        sd = 'r' if b == 'saluda' else 'l'
        w = math.sin((t - 25.5) * 2 * math.pi * 1.6) * min(x, 1)
        arms[sd][0] += 4 * w
        arms[sd][1] += 12 * w
    if b == 'rasca' and x >= 1:
        arms['r'][1] += 7 * math.sin(t * 2 * math.pi * 3.2)
    la, lb, lx = keyed(LOOK[c], t, 0.4)
    head = la + (lb - la) * ease(lx)
    ph = 0.0 if c == 'e' else 1.7
    head += 0.018 * math.sin(1.1 * t + ph)
    tk = talk(c, t)
    sp = speaking(c, t)
    if sp:
        head += 0.025 * math.sin(4.3 * t + ph)
    # the hips stay put (a few px down would bend the knees outwards): the life is in the head
    drop = 0.0
    head += 0.012 * tk * (1 if c == 'e' else -1)
    p = {'arms': arms, 'head': head, 'drop': drop, 'talk': tk,
         'blink': any(0 <= t - bt < 0.13 for bt in BLINK[c]), 'tilt': 0.006 * math.sin(0.8 * t + ph)}
    jump(c, t, p)
    return p


def jump(c, t, p):
    """E's little hop on "¡O muy divertido!" and his jump at the end."""
    if c != 'e':
        return
    for j0, high in ((23.0, 70), (25.55, 260)):
        u = t - j0
        crouch, push, air_t, land, rec = 0.22, 0.08, 0.3 + high / 600, 0.12, 0.22
        if u < 0:
            continue
        if u < crouch:
            k = ease(u / crouch)
            p['drop'] += 30 * k
            p['lift'] = 0.4 * k
        elif u < crouch + push:
            k = ease((u - crouch) / push)
            p['drop'] += 30 * (1 - k)
            p['lift'] = 0.4 * (1 - k)
        elif u < crouch + push + air_t:
            k = (u - crouch - push) / air_t
            h = 4 * k * (1 - k) * high
            p['drop'] -= h
            p['air'] = h
            p['lift'] = 0.5 * math.sin(math.pi * k)
        elif u < crouch + push + air_t + land + rec:
            k = u - crouch - push - air_t
            dip = ease(k / land) if k < land else 1 - ease((k - land) / rec)
            p['drop'] += 24 * dip
            p['lift'] = 0.3 * dip


def shot_at(t):
    i = max(k for k, sh in enumerate(SHOTS) if sh[0] <= t)
    t0, cx, cy, z, push = SHOTS[i]
    t1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else TOTAL
    return i, z * (1 + push * ease((t - t0) / (t1 - t0))), cx, cy


def overlays(img, t):
    # scene 1: what is going on?
    if 0.15 <= t < 3.0:
        label(img, '¿Qué está pasando?', W / 2, 250, 92, (40, 30, 40), (255, 214, 64), scale=pop(t - 0.15), rot=-3)
    # E's list
    if 8.0 <= t < 12.1:
        for i, ((kind, word), at) in enumerate(zip(ICONS, ICON_AT)):
            sc = pop(t - at)
            if sc <= 0:
                continue
            if kind not in ICON_IMG:
                ICON_IMG[kind] = icon(kind, 210)
            size = int(210 * sc)
            ic = ICON_IMG[kind].resize((size, size), Image.LANCZOS)
            x = 150 + i * 260
            y = 300 + (i % 2) * 70 + 10 * math.sin(2.4 * t + i)
            img.alpha_composite(ic, (int(x - size / 2), int(y - size / 2)))
            label(img, word, x, y + 145, 44, (40, 30, 40), (255, 255, 255), scale=sc, pad=(18, 8))
    # subtitles: what is being said, in big letters, with the colour of who says it (no names)
    starts = sorted(SAYS.values())
    for lid, at in SAYS.items():
        nxt = min([x for x in starts if x > at] + [TOTAL])
        if at - 0.05 <= t <= min(at + DUR[lid] + 0.3, nxt - 0.06):    # one at a time
            c = LINES[lid]['who']
            label(img, LINES[lid]['text'].replace('...', '…'), W / 2, 1600, 74, (30, 25, 35), (255, 255, 255),
                  border=COLOR[c], scale=min(1.0, 0.85 + (t - at + 0.05) * 3))
    # ending
    if t >= 25.7:
        label(img, 'Pequeñas preguntas.', W / 2, 250, 88, (40, 30, 40), (255, 214, 64), scale=pop(t - 25.7), rot=-2)
    if t >= 26.1:
        label(img, 'Grandes aventuras.', W / 2, 385, 88, (255, 255, 255), (215, 50, 46), scale=pop(t - 26.1), rot=2)
    if t >= 26.9:
        b = 1 + 0.04 * math.sin(2 * math.pi * (t - 26.9) * 1.2) if t > 27.3 else pop(t - 26.9)
        label(img, 'Síguenos para descubrirlo', W / 2, 1640, 70, (255, 255, 255), (31, 111, 224), scale=b)
        label(img, 'No Entiendo a los Mayores', W / 2, 1790, 48, (40, 30, 40), (255, 255, 255), scale=pop(t - 27.2), pad=(26, 12))


# ---------------------------------------------------------------- frames
def frame_at(t):
    i, z, cx, cy = shot_at(t)
    img = background(z, cx, cy)
    for c in ('e', 'r'):
        x, floor, s = WORLD[c]
        if c == 'e' and t < 3.0:
            continue                           # E is not here yet
        if c == 'e' and t < 3.35:              # comes in from the left
            x -= 700 * (1 - ease((t - 3.0) / 0.35))
        sx = W / 2 + (x - cx) * z
        if sx < -500 or sx > W + 500:
            continue
        kid(img, c, sx, H / 2 + (floor - cy) * z, s * z, state(c, t))
    overlays(img, t)
    return img.convert('RGB')


def audio_plan(path):
    sfx = os.path.join(ROOT, 'assets/sfx')
    clips = [{'file': os.path.join(DIR, 'voces', l + '.mp3'), 'at': at, 'gain': 1.0} for l, at in SAYS.items()]
    fx = [(0.15, 'pop', 0.5), (2.95, 'whoosh', 0.5), (5.55, 'swipe', 0.3), (8.25, 'pop', 0.5), (9.1, 'pop', 0.5),
          (9.9, 'pop', 0.5), (10.75, 'pop', 0.5), (14.75, 'grillos', 0.55), (17.5, 'ding', 0.4), (23.25, 'boing', 0.4),
          (25.85, 'boing', 0.45), (26.2, 'cheer', 0.5), (25.7, 'pop', 0.5), (26.1, 'pop', 0.5), (26.9, 'pop', 0.5)]
    plan = {'total': TOTAL, 'clips': clips, 'sfx': [{'file': os.path.join(sfx, n + '.wav'), 'at': a, 'gain': g} for a, n, g in fx],
            'music': os.path.join(ROOT, 'assets/music/juguete.wav'), 'musicGain': 0.16}
    json.dump(plan, open(path, 'w'))


def render_range(args):
    a, b, path = args
    with open(path, 'wb') as f:
        for n in range(a, b):
            f.write(frame_at(n / FPS).tobytes())


def video(out):
    from multiprocessing import Pool
    work = os.path.join(os.path.dirname(os.path.abspath(out)), 'presentacion-work')
    os.makedirs(work, exist_ok=True)
    t0, t1 = (float(v) for v in os.environ.get('TRAMO', f'0,{TOTAL}').split(','))   # TRAMO=3,7.2: only that bit
    n0, n = int(t0 * FPS), int(t1 * FPS)
    jobs = int(os.environ.get('JOBS', os.cpu_count() or 2))
    cuts = np.linspace(n0, n, jobs * 4 + 1).astype(int)
    parts = [(int(cuts[k]), int(cuts[k + 1]), os.path.join(work, f'part{k:02d}.raw')) for k in range(len(cuts) - 1)]
    with Pool(jobs) as pool:
        pool.map(render_range, parts, chunksize=1)
    audio_plan(os.path.join(work, 'mix.json'))
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools/mix.py'), os.path.join(work, 'mix.json'),
                    os.path.join(work, 'mix.wav')], check=True)
    cat = subprocess.Popen(['cat'] + [p[2] for p in parts], stdout=subprocess.PIPE)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                    '-i', '-', '-ss', str(t0), '-i', os.path.join(work, 'mix.wav'), '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out],
                   stdin=cat.stdout, check=True)
    for p in parts:
        os.remove(p[2])


if __name__ == '__main__':
    if '--poses' in sys.argv:
        pose_sheet(sys.argv[1])
    elif sys.argv[1].endswith(('.png', '.jpg')):
        frame_at(float(sys.argv[2])).save(sys.argv[1])
    else:
        video(sys.argv[1])
