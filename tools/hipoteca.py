"""Episode 001 "¿Qué es una hipoteca?" made with the rig of E and R (tools/escena_rig.py), like the intro Short:
same arms, hands, wrists, shoulders, mouths, voices and subtitles that Chiño approved. 1080x1920.
Usage:
  python3 tools/hipoteca.py out.mp4                 video (voices from content/especiales/hipoteca/voces)
  TRAMO=3,7.2 python3 tools/hipoteca.py out.mp4     only that stretch, to review
  python3 tools/hipoteca.py out.png 12.5            one frame
The times come from the voices: each line starts when the one before ends (plus a short breath)."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from escena_rig import ROOT, W, H, FPS, POSES, MOVE, COLOR, HEIGHT, kid, mix_arm, settle, keyed, envelope, \
    background, label, pop, ease, icon
import fondos

DIR = os.path.join(ROOT, 'content/especiales/hipoteca')
# the set of the mortgage (tools/fondos.py), from its script; FONDO=liso keeps the old plain wall
FONDO = None if os.environ.get('FONDO') == 'liso' else fondos.Fondo(
    json.load(open(os.path.join(ROOT, 'content/guiones/es/001-hipoteca.json'))), theme=os.environ.get('FONDO') or None)
# R gestures with the hand on E's side (the left of the screen), E with the one on R's side; shrugging next to each
# other, the hand towards the other kid stays close to the body
POSES = dict(POSES)
POSES['explica_izq'] = {'l': (26, 66, 'abierta~', 32), 'r': (10, 6, 'pose', 0)}
POSES['encoge_corto_der'] = {'l': (40, 80, 'abierta~', 35), 'r': (24, 62, 'abierta~', 30)}
LINES = {l['id']: l for l in json.load(open(os.path.join(DIR, 'lineas.json')))['lineas']}
DUR = json.load(open(os.path.join(DIR, 'voces/duraciones.json')))

# ---------------------------------------------------------------- the script
# line -> (shot, poses {kid: pose}, card, emote). shot: 'e', 'r' (close on who speaks) or 'dos'
SCRIPT = {
    '01': ('dos', {'e': 'quieto', 'r': 'explica_izq'}, None, None),
    '02': ('e', {'e': 'explica'}, ('casa', 'HIPOTECA'), None),
    '03': ('e', {'e': 'cintura'}, ('calendario', '30 AÑOS'), None),
    '04': ('dos', {'r': 'encoge_corto', 'e': 'quieto'}, None, ('r', '!')),
    '05': ('r', {'r': 'barbilla'}, None, None),
    '06': ('e', {'e': 'senala_arriba', 'r': 'quieto'}, ('grafica', 'INTERESES'), None),
    '07': ('r', {'r': 'explica_izq', 'e': 'quieto'}, None, None),
    '08': ('dos', {'e': 'celebra', 'r': 'quieto'}, ('casa', 'TUYA'), None),
    '09': ('r', {'r': 'encoge_corto', 'e': 'quieto'}, None, None),
    '10': ('e', {'e': 'rasca'}, ('banco', 'DEL BANCO'), ('r', '?')),
}
GAP = 0.32                  # breath between lines
PAUSE = 1.4                 # the silence before the closing line: they look at each other
START = 0.5
SAYS = {}
t = START
for lid in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']:
    SAYS[lid] = t
    t += DUR[lid] + GAP
QUIET = t                   # the awkward silence
SAYS['11'] = SAYS['11b'] = t + PAUSE
TOTAL = SAYS['11'] + max(DUR['11'], DUR['11b']) + 2.2

WORLD = {'e': (300, 1620, 0.98 * HEIGHT['e']), 'r': (790, 1620, 0.98 * HEIGHT['r'])}
SHOT = {'dos': (545, 1040, 1.15), 'e': (345, 1000, 1.5), 'r': (750, 900, 1.55)}


def shots():
    out = [(0.0, 'dos')]
    for lid, at in sorted(SAYS.items(), key=lambda x: x[1]):
        s = SCRIPT[lid][0] if lid in SCRIPT else 'dos'
        if s != out[-1][1]:
            out.append((at - 0.12, s))
    out.insert(len(out) - 1, (QUIET + 0.1, 'dos'))           # the silence: both of them
    return sorted(set(out))


SHOTS = shots()


def arms_keys(c):
    keys = [(0.0, 'quieto')]
    for lid, at in sorted(SAYS.items(), key=lambda x: x[1]):
        if lid not in SCRIPT:
            continue
        poses = SCRIPT[lid][1]
        if c in poses and poses[c] != keys[-1][1]:
            keys.append((at - 0.15, poses[c]))
        elif c not in poses and keys[-1][1] != 'quieto' and LINES[lid]['who'] != c:
            keys.append((at, 'quieto'))
    keys.append((QUIET, 'quieto'))
    keys.append((SAYS['11'] - 0.1, 'encoge_corto_der' if c == 'e' else 'encoge_corto'))   # "Cosas de mayores": palms up
    return sorted(keys)


ARMS = {c: arms_keys(c) for c in ('e', 'r')}
BLINK = {'e': list(np.arange(1.3, TOTAL, 2.9)), 'r': list(np.arange(2.1, TOTAL, 3.3))}
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


def speaker(t):
    for lid, at in SAYS.items():
        if at <= t <= at + DUR[lid]:
            return LINES[lid]['who']
    return None


def state(c, t):
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
    if b == 'rasca' and x >= 1:
        arms['r'][1] += 7 * math.sin(t * 2 * math.pi * 3.2)
    # where they look: at whoever speaks, at each other in the silence, to the camera at the end
    other = 0.045 if c == 'e' else -0.05
    sp = speaker(t)
    if QUIET <= t < SAYS['11']:
        look = other * 1.6 * ease((t - QUIET) / 0.3)
    elif t >= SAYS['11']:
        look = other * 1.6 * (1 - ease((t - SAYS['11']) / 0.3))
    else:
        look = other if sp and sp != c else 0.0
    ph = 0.0 if c == 'e' else 1.7
    head = look + 0.018 * math.sin(1.1 * t + ph)
    tk = talk(c, t)
    if sp == c:
        head += 0.025 * math.sin(4.3 * t + ph)
    head += 0.012 * tk * (1 if c == 'e' else -1)
    p = {'arms': arms, 'head': head, 'drop': 0.0, 'talk': tk,
         'blink': any(0 <= t - bt < 0.13 for bt in BLINK[c]), 'tilt': 0.006 * math.sin(0.8 * t + ph)}
    if c == 'r':
        hop(t - SAYS['04'], p, 40)                          # "¿Treinta años?": a little jump of surprise
    if c == 'e':
        hop(t - SAYS['08'], p, 50)                          # "la casa es tuya": happy
    return p


def hop(u, p, high):
    crouch, push, air_t, land, rec = 0.16, 0.07, 0.3 + high / 600, 0.1, 0.2
    if u < 0:
        return
    if u < crouch:
        k = ease(u / crouch)
        p['drop'] += 22 * k
        p['lift'] = 0.35 * k
    elif u < crouch + push:
        k = ease((u - crouch) / push)
        p['drop'] += 22 * (1 - k)
        p['lift'] = 0.35 * (1 - k)
    elif u < crouch + push + air_t:
        k = (u - crouch - push) / air_t
        h = 4 * k * (1 - k) * high
        p['drop'] -= h
        p['air'] = h
        p['lift'] = 0.4 * math.sin(math.pi * k)
    elif u < crouch + push + air_t + land + rec:
        k = u - crouch - push - air_t
        dip = ease(k / land) if k < land else 1 - ease((k - land) / rec)
        p['drop'] += 18 * dip
        p['lift'] = 0.25 * dip


def camera(t):
    """Camera centre and zoom at t: it glides to the next shot in 0.35 s and pushes in a little during each."""
    i = max(k for k, sh in enumerate(SHOTS) if sh[0] <= t)
    t0, name = SHOTS[i]
    t1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else TOTAL
    cx, cy, z = SHOT[name]
    z *= 1 + 0.03 * ease((t - t0) / max(t1 - t0, 0.1))
    if i > 0 and t - t0 < 0.35:
        px, py, pz = SHOT[SHOTS[i - 1][1]]
        k = ease((t - t0) / 0.35)
        cx, cy, z = px + (cx - px) * k, py + (cy - py) * k, pz + (z - pz) * k
    return cx, cy, z


# ---------------------------------------------------------------- texts
CARD = {}


def card(img, kind, text, u, x, y):
    sc = pop(u)
    if sc <= 0:
        return
    if kind not in CARD:
        CARD[kind] = icon(kind, 230)
    size = int(230 * sc)
    ic = CARD[kind].resize((size, size), Image.LANCZOS)
    y += 8 * math.sin(2.2 * u)
    img.alpha_composite(ic, (int(x - size / 2), int(y - size / 2)))
    label(img, text, x, y + 160 * sc, 56, (40, 30, 40), (255, 214, 64), scale=sc, pad=(24, 10))


def overlays(img, t):
    # the series and the question, always at the top
    big = t < 2.6
    if big:
        label(img, 'DICCIONARIO DE MAYORES', W / 2, 150, 40, (255, 255, 255), (60, 160, 90), scale=pop(t), rot=-2,
              pad=(26, 10))
        label(img, '¿Qué es una hipoteca?', W / 2, 300, 92, (40, 30, 40), (255, 255, 255), border=(40, 30, 40),
              scale=pop(t - 0.1), rot=-2)
    else:
        label(img, '¿Qué es una hipoteca?', W / 2, 150, 52, (40, 30, 40), (255, 255, 255), border=(40, 30, 40),
              scale=min(1.0, pop(t - 2.6) + 0.6), pad=(26, 12))
    # cards over who explains
    for lid, (shot, poses, cd, emote) in SCRIPT.items():
        at = SAYS[lid]
        if cd and at + 0.25 <= t <= at + DUR[lid] + 0.25:
            card(img, cd[0], cd[1], t - at - 0.25, W / 2 if shot == 'dos' else W / 2, 470)
    # subtitles: one at a time, the border is who speaks (no names)
    starts = sorted(set(SAYS.values()))
    for lid, at in SAYS.items():
        if lid == '11b':
            continue
        nxt = min([x for x in starts if x > at] + [TOTAL])
        if at - 0.05 <= t <= min(at + DUR[lid] + 0.3, nxt - 0.06):
            c = LINES[lid]['who']
            text = LINES[lid]['text'].replace('...', '…')
            border = (130, 60, 170) if lid == '11' else COLOR[c]
            label(img, text, W / 2, 1600, 74, (30, 25, 35), (255, 255, 255), border=border,
                  scale=min(1.0, 0.85 + (t - at + 0.05) * 3))
    if t >= SAYS['11'] + max(DUR['11'], DUR['11b']) + 0.3:
        u = t - SAYS['11'] - max(DUR['11'], DUR['11b']) - 0.3
        label(img, 'No Entiendo a los Mayores', W / 2, 1790, 48, (40, 30, 40), (255, 255, 255), scale=pop(u),
              pad=(26, 12))


def emotes(img, t, pos):
    """A '!' or '?' popping over a kid's head (pos: kid -> head top on screen)."""
    for lid, (shot, poses, cd, emote) in SCRIPT.items():
        if not emote:
            continue
        at = SAYS[lid] + 0.1
        if at <= t <= SAYS[lid] + DUR[lid] + 0.4 and emote[0] in pos:
            x, y = pos[emote[0]]
            col = COLOR[emote[0]]
            label(img, emote[1], x + 90, y - 30, 96, (255, 255, 255), col, scale=pop(t - at),
                  rot=-8 * math.sin(6 * (t - at)) * math.exp(-2 * (t - at)), pad=(28, 4))


# ---------------------------------------------------------------- frames
def frame_at(t):
    cx, cy, z = camera(t)
    img = FONDO.frame(z, cx, cy, t) if FONDO else background(z, cx, cy)
    heads = {}
    for c in ('e', 'r'):
        x, floor, s = WORLD[c]
        sx = W / 2 + (x - cx) * z
        if sx < -500 or sx > W + 500:
            continue
        kid(img, c, sx, H / 2 + (floor - cy) * z, s * z, state(c, t))
        heads[c] = (sx, H / 2 + (floor - 1150 * s - cy) * z + 40 * z)
    emotes(img, t, heads)
    overlays(img, t)
    return img.convert('RGB')


def audio_plan(path):
    sfx = os.path.join(ROOT, 'assets/sfx')
    clips = [{'file': os.path.join(DIR, 'voces', l + '.mp3'), 'at': at, 'gain': 0.85 if l.startswith('11') else 1.0}
             for l, at in SAYS.items()]
    fx = [(0.0, 'pop', 0.45), (0.1, 'pop', 0.4), (SAYS['04'] + 0.1, 'boing', 0.35), (QUIET + 0.15, 'grillos', 0.5),
          (SAYS['11'] + max(DUR['11'], DUR['11b']) + 0.3, 'pop', 0.4)]
    for lid, (shot, poses, cd, emote) in SCRIPT.items():
        if cd:
            fx.append((SAYS[lid] + 0.25, 'pop', 0.4))
    plan = {'total': TOTAL, 'clips': clips, 'sfx': [{'file': os.path.join(sfx, n + '.wav'), 'at': a, 'gain': g} for a, n, g in fx],
            'music': os.path.join(ROOT, 'assets/music/pensar.wav'), 'musicGain': 0.14}
    json.dump(plan, open(path, 'w'))


def render_range(args):
    a, b, path = args
    with open(path, 'wb') as f:
        for n in range(a, b):
            f.write(frame_at(n / FPS).tobytes())


def video(out):
    from multiprocessing import Pool
    work = os.path.join(os.path.dirname(os.path.abspath(out)), 'hipoteca-work')
    os.makedirs(work, exist_ok=True)
    t0, t1 = (float(v) for v in os.environ.get('TRAMO', f'0,{TOTAL}').split(','))
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
    if sys.argv[1].endswith(('.png', '.jpg')):
        frame_at(float(sys.argv[2])).save(sys.argv[1])
    else:
        video(sys.argv[1])
