"""Any episode of content/guiones/es made with the rig of E and R (tools/escena_rig.py), the model of the intro
Short v7 that Chiño approved: same arms, hands, wrists, shoulders, mouths, voices and subtitles. 1080x1920.
Usage:
  python3 tools/episodio.py lineas 002-no-tengo-tiempo           the lines to voice -> content/voces/<id>/lineas.json
                                                                  (push it: GitHub Actions makes the voices,
                                                                  .github/workflows/presentacion-voces.yml)
  python3 tools/episodio.py 002-no-tengo-tiempo out.mp4          the video
  TRAMO=3,7.2 python3 tools/episodio.py 002-... out.mp4          only that stretch, to review
  python3 tools/episodio.py 002-no-tengo-tiempo out.png 12.5     one frame

The direction comes from the script (direct()): what each line's face, gesture, card and emote say becomes a pose
of the arms (POSES), a close shot or a wide one, a little hop, an icon over the head. The times come from the voices:
each line starts when the one before ends, plus a short breath."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from escena_rig import ROOT, W, H, FPS, POSES, MOVE, COLOR, HEIGHT, kid, mix_arm, settle, keyed, envelope, \
    background, label, pop, ease, icon

# each kid gestures with the hand on the other's side (E is on the left of the screen, R on the right); shrugging
# next to each other, the hand towards the other kid stays close to the body
POSES = dict(POSES)
POSES['explica_izq'] = {'l': (26, 66, 'abierta~', 32), 'r': (10, 6, 'pose', 0)}
POSES['encoge_corto_der'] = {'l': (40, 80, 'abierta~', 35), 'r': (24, 62, 'abierta~', 30)}
TOWARD = {'e': 'explica', 'r': 'explica_izq'}
SHRUG = {'e': 'encoge_corto_der', 'r': 'encoge_corto'}
ICONS = {'casa', 'calendario', 'grafica', 'banco', 'movil', 'reloj', 'moneda', 'bombilla', 'wifi', 'planeta'}
EMOTE_TEXT = {'!': '!', '?': '?', '??': '??', '...': '...', 'lio': '?!', 'gota': '...', 'brillo': '!'}
SERIES = {'diccionario': 'DICCIONARIO DE MAYORES', 'por-que': '¿POR QUÉ LOS MAYORES...?',
          'cuando-sea-mayor': 'CUANDO SEA MAYOR...', 'quien-invento': '¿QUIÉN INVENTÓ ESTO?',
          'explicamelo': 'EXPLÍCAMELO COMO SI TUVIERA 8 AÑOS', 'manual': 'MANUAL PARA SER ADULTO'}
CLOSING = 'Cosas de mayores.'
GAP = 0.32                  # breath between lines
START = 0.5
WORLD = {'e': (300, 1620, 0.98 * HEIGHT['e']), 'r': (790, 1620, 0.98 * HEIGHT['r'])}
SHOT = {'dos': (545, 1040, 1.15), 'e': (345, 1000, 1.5), 'r': (750, 900, 1.55)}


# ---------------------------------------------------------------- script -> lines to voice
def script_lines(g):
    """The spoken lines of a script, with ids: 01, 02... ('ambos': one voice each, 07 and 07b)."""
    out, k = [], 0
    for ln in g['lineas']:
        if 'pausa' in ln:
            continue
        k += 1
        if 'ambos' in ln:
            out.append({'id': f'{k:02d}', 'who': 'e', 'text': ln['ambos'], 'src': ln, 'ambos': True})
            out.append({'id': f'{k:02d}b', 'who': 'r', 'text': ln['ambos'], 'src': ln, 'ambos': True})
        else:
            w = 'e' if 'e' in ln else 'r'
            out.append({'id': f'{k:02d}', 'who': w, 'text': ln[w], 'src': ln})
    return out


def write_lines(eid):
    g = json.load(open(os.path.join(ROOT, 'content/guiones/es', eid + '.json')))
    d = os.path.join(ROOT, 'content/voces', eid)
    os.makedirs(d, exist_ok=True)
    lines = [{k: v for k, v in l.items() if k in ('id', 'who', 'text')} for l in script_lines(g)]
    json.dump({'_doc': f'Líneas de {eid} para las voces (tools/episodio.py lineas). Nunca se llaman por su nombre.',
               'lineas': lines}, open(os.path.join(d, 'lineas.json'), 'w'), ensure_ascii=False, indent=1)
    return os.path.join(d, 'lineas.json')


# ---------------------------------------------------------------- direction
def direct(lines, roles):
    """line id -> {shot, poses, card, emote, hop, nod}, from the face, gesture, card and emote of each line."""
    out, alt = {}, 0
    for i, ln in enumerate(lines):
        if ln.get('ambos'):
            continue
        src, c = ln['src'], ln['who']
        o = 'r' if c == 'e' else 'e'
        cara, gesto = src.get('cara'), src.get('gesto')
        d = {'shot': c, 'poses': {c: 'quieto'}, 'card': None, 'emote': None, 'hop': 0, 'shake': gesto == 'niega'}
        if cara in ('pensativo',):
            d['poses'][c] = 'barbilla'
        elif cara in ('dudoso', 'resignado', 'triste') or gesto == 'encoge':
            d['poses'][c] = SHRUG[c]
        elif cara in ('confundido',):
            d['poses'][c] = 'rasca'
        elif cara in ('convencido', 'picaro', 'enfadado'):
            d['poses'][c] = 'cintura'
        elif cara in ('ilusionado', 'feliz') or gesto in ('salto', 'bota'):
            d['poses'][c] = 'celebra'
        elif cara in ('sorprendido', 'asombrado'):
            d['poses'][c] = SHRUG[c]
            d['hop'] = 40
            d['emote'] = (c, '!')
        elif cara == 'serio':
            d['poses'][c] = 'quieto'
        elif src.get('tarjeta') or cara == 'curioso' or '?' in ln['text']:
            d['poses'][c] = TOWARD[c]
        elif c == roles.get('explica'):
            d['poses'][c] = (TOWARD[c], 'senala_arriba')[alt % 2]
            alt += 1
        if gesto in ('salto', 'bota'):
            d['hop'] = 60
        if src.get('tarjeta'):
            d['card'] = (src['tarjeta'].get('icono'), src['tarjeta'].get('texto', ''))
        if src.get('emote'):
            d['emote'] = (c, src['emote'])
        if src.get('emote_otro'):
            d['emote'] = (o, src['emote_otro'])
        # wide when both react or when it's the first line; otherwise close on who speaks
        if i == 0 or d['hop'] or src.get('emote_otro') or d['poses'][c] == 'celebra':
            d['shot'] = 'dos'
        out[ln['id']] = d
    return out


# ---------------------------------------------------------------- the episode
class Ep:
    pass


EP = Ep()


def load(eid):
    g = json.load(open(os.path.join(ROOT, 'content/guiones/es', eid + '.json')))
    EP.g, EP.id = g, eid
    EP.dir = os.path.join(ROOT, 'content/voces', eid)
    EP.lines = script_lines(g)
    EP.L = {l['id']: l for l in EP.lines}
    EP.dur = json.load(open(os.path.join(EP.dir, 'voces/duraciones.json')))
    EP.d = direct(EP.lines, g.get('roles', {}))
    # times
    says, t, k, quiet, react = {}, START, 0, None, None
    entries = g['lineas']
    ids = iter([l['id'] for l in EP.lines])
    for ln in entries:
        if 'pausa' in ln:
            quiet, react = t, ln.get('reaccion', 'mirada')
            t += ln['pausa']
            continue
        lid = next(ids)
        says[lid] = t
        if 'ambos' in ln:
            lid2 = next(ids)
            says[lid2] = t
            t += max(EP.dur[lid], EP.dur[lid2]) + GAP
        else:
            t += EP.dur[lid] + GAP
    EP.says = says
    EP.quiet, EP.react = quiet, react
    EP.end_text = None
    if g['cierre']['tipo'] != 'hablado' or not any(l.get('ambos') for l in EP.lines):
        EP.end_text = t + (0.1 if quiet is not None and quiet + 2 > t else 0.4)
        t = EP.end_text + 2.4
    else:
        t += 1.9
    EP.total = t
    EP.shots = shots()
    EP.arms = {c: arms_keys(c) for c in ('e', 'r')}
    EP.blink = {'e': list(np.arange(1.3, t, 2.9)), 'r': list(np.arange(2.1, t, 3.3))}
    EP.env = {}


def shots():
    out = [(0.0, 'dos')]
    for lid, at in sorted(EP.says.items(), key=lambda x: x[1]):
        s = EP.d[lid]['shot'] if lid in EP.d else 'dos'
        if s != out[-1][1]:
            out.append((at - 0.12, s))
    if EP.quiet is not None and out[-1][1] != 'dos':
        out.append((EP.quiet + 0.1, 'dos'))
    if EP.end_text is not None and out[-1][1] != 'dos':
        out.append((EP.end_text - 0.2, 'dos'))
    return sorted(set(out))


def arms_keys(c):
    keys = [(0.0, 'quieto')]
    for lid, at in sorted(EP.says.items(), key=lambda x: x[1]):
        if lid not in EP.d:
            continue
        poses = EP.d[lid]['poses']
        if c in poses and poses[c] != keys[-1][1]:
            keys.append((at - 0.15, poses[c]))
        elif c not in poses and keys[-1][1] != 'quieto':
            keys.append((at, 'quieto'))
    if EP.quiet is not None:
        keys.append((EP.quiet, 'quieto'))
    both = [EP.says[l['id']] for l in EP.lines if l.get('ambos')]
    if both:
        keys.append((both[0] - 0.1, SHRUG[c]))            # "Cosas de mayores": palms up, the two of them
    elif EP.end_text is not None:
        keys.append((EP.end_text, SHRUG[c]))
    keys = sorted(keys)
    return [k for i, k in enumerate(keys) if i == 0 or k[1] != keys[i - 1][1]]


def talk(c, t):
    for lid, at in EP.says.items():
        if EP.L[lid]['who'] != c:
            continue
        if lid not in EP.env:
            EP.env[lid] = envelope(os.path.join(EP.dir, 'voces', lid + '.mp3'))
        i = (t - at) * FPS
        if 0 <= i < len(EP.env[lid]) - 1:
            j = int(i)
            return float(EP.env[lid][j] * (1 - (i - j)) + EP.env[lid][j + 1] * (i - j))
    return 0.0


def speaking(t):
    """(line id, kid) speaking at t."""
    for lid, at in EP.says.items():
        if at <= t <= at + EP.dur[lid]:
            return lid, EP.L[lid]['who']
    return None, None


def state(c, t):
    ARMS = EP.arms
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
    lid, sp = speaking(t)
    q0 = EP.quiet
    q1 = q0 + next(l['pausa'] for l in EP.g['lineas'] if 'pausa' in l) if q0 is not None else None
    if q0 is not None and q0 <= t < q1 and EP.react in ('mirada', 'giro', 'silencio'):
        look = other * 1.6 * ease((t - q0) / 0.3)
    elif q1 is not None and q1 <= t < q1 + 0.3 and EP.react in ('mirada', 'giro', 'silencio'):
        look = other * 1.6 * (1 - ease((t - q1) / 0.3))
    else:
        look = other if sp and sp != c else 0.0
    ph = 0.0 if c == 'e' else 1.7
    head = look + 0.018 * math.sin(1.1 * t + ph)
    tk = talk(c, t)
    if sp == c:
        head += 0.025 * math.sin(4.3 * t + ph)
        d = EP.d.get(lid, {})
        if d.get('shake'):                              # "no": the head goes from side to side
            u = t - EP.says[lid]
            head += 0.05 * math.sin(2 * math.pi * 2.6 * u) * math.exp(-1.2 * u)
    head += 0.012 * tk * (1 if c == 'e' else -1)
    blink = any(0 <= t - bt < 0.13 for bt in EP.blink[c])
    if q0 is not None and EP.react == 'parpadeo':          # both blink slowly, twice, in the silence
        blink = blink or any(0 <= t - (q0 + k) < 0.2 for k in (0.35, 0.95))
    p = {'arms': arms, 'head': head, 'drop': 0.0, 'talk': tk, 'blink': blink,
         'tilt': 0.006 * math.sin(0.8 * t + ph)}
    for l2, d in EP.d.items():
        if d['hop'] and EP.L[l2]['who'] == c:
            hop(t - EP.says[l2], p, d['hop'])
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
    S = EP.shots
    i = max(k for k, sh in enumerate(S) if sh[0] <= t)
    t0, name = S[i]
    t1 = S[i + 1][0] if i + 1 < len(S) else EP.total
    cx, cy, z = SHOT[name]
    z *= 1 + 0.03 * ease((t - t0) / max(t1 - t0, 0.1))
    if i > 0 and t - t0 < 0.35:
        px, py, pz = SHOT[S[i - 1][1]]
        k = ease((t - t0) / 0.35)
        cx, cy, z = px + (cx - px) * k, py + (cy - py) * k, pz + (z - pz) * k
    return cx, cy, z


# ---------------------------------------------------------------- texts
CARD = {}


def card(img, kind, text, u, x, y):
    sc = pop(u)
    if sc <= 0:
        return
    y += 8 * math.sin(2.2 * u)
    if kind in ICONS:
        if kind not in CARD:
            CARD[kind] = icon(kind, 230)
        size = int(230 * sc)
        ic = CARD[kind].resize((size, size), Image.LANCZOS)
        img.alpha_composite(ic, (int(x - size / 2), int(y - size / 2)))
        label(img, text, x, y + 160 * sc, 56, (40, 30, 40), (255, 214, 64), scale=sc, pad=(24, 10))
    else:
        label(img, text, x, y + 60, 76, (40, 30, 40), (255, 214, 64), scale=sc, rot=-3, pad=(30, 14))


def overlays(img, t):
    g = EP.g
    title = g['titulo']
    series = SERIES.get(g.get('serie'), '')
    if t < 2.6:
        if series:
            label(img, series, W / 2, 115, 40, (255, 255, 255), (60, 160, 90), scale=pop(t), rot=-2, pad=(26, 10))
        label(img, title, W / 2, 330, 84, (40, 30, 40), (255, 255, 255), border=(40, 30, 40),
              scale=pop(t - 0.1), rot=-2, maxw=980)
    else:
        label(img, title, W / 2, 150, 48, (40, 30, 40), (255, 255, 255), border=(40, 30, 40),
              scale=min(1.0, pop(t - 2.6) + 0.6), pad=(26, 12), maxw=1000)
    for lid, d in EP.d.items():
        at = EP.says[lid]
        if d['card'] and at + 0.25 <= t <= at + EP.dur[lid] + 0.25:
            card(img, d['card'][0], d['card'][1], t - at - 0.25, W / 2, 500)
    # subtitles: one at a time, the border is who speaks (no names)
    starts = sorted(set(EP.says.values()))
    for lid, at in EP.says.items():
        if lid.endswith('b'):
            continue
        nxt = min([x for x in starts if x > at] + [EP.total])
        if at - 0.05 <= t <= min(at + EP.dur[lid] + 0.3, nxt - 0.06):
            c = EP.L[lid]['who']
            border = (130, 60, 170) if EP.L[lid].get('ambos') else COLOR[c]
            label(img, EP.L[lid]['text'].replace('...', '…'), W / 2, 1600, 74, (30, 25, 35), (255, 255, 255),
                  border=border, scale=min(1.0, 0.85 + (t - at + 0.05) * 3))
    if EP.end_text is not None and t >= EP.end_text:
        u = t - EP.end_text
        label(img, CLOSING, W / 2, 1560, 96, (255, 255, 255), (215, 50, 46), border=(255, 255, 255),
              scale=pop(u), maxw=1040, rot=-3 + 1.5 * math.sin(2 * u))
    end = EP.end_text if EP.end_text is not None else max(EP.says.values()) + 1.0
    if t >= end + 0.4:
        label(img, 'No Entiendo a los Mayores', W / 2, 1790, 48, (40, 30, 40), (255, 255, 255), scale=pop(t - end - 0.4),
              pad=(26, 12))


def emotes(img, t, pos):
    """A '!' or '?' (or a light bulb) popping over a kid's head (pos: kid -> head top on screen)."""
    for lid, d in EP.d.items():
        if not d['emote']:
            continue
        who, kind = d['emote']
        at = EP.says[lid] + 0.1
        if at <= t <= EP.says[lid] + EP.dur[lid] + 0.4 and who in pos:
            x, y = pos[who]
            u = t - at
            if kind == 'bombilla':
                if 'bombilla' not in CARD:
                    CARD['bombilla'] = icon('bombilla', 200)
                sc = pop(u)
                if sc > 0:
                    ic = CARD['bombilla'].resize((int(200 * sc), int(200 * sc)), Image.LANCZOS)
                    img.alpha_composite(ic, (int(x + 90 - ic.width / 2), int(y - 60 - ic.height / 2)))
                continue
            label(img, EMOTE_TEXT.get(kind, '!'), x + 90, y - 30, 96, (255, 255, 255), COLOR[who], scale=pop(u),
                  rot=-8 * math.sin(6 * u) * math.exp(-2 * u), pad=(28, 4))


# ---------------------------------------------------------------- frames
def frame_at(t):
    cx, cy, z = camera(t)
    img = background(z, cx, cy)
    heads = {}
    for c in ('e', 'r'):
        x, floor, s = WORLD[c]
        sx = W / 2 + (x - cx) * z
        if sx < -500 or sx > W + 500:
            continue
        p = state(c, t)
        fy = H / 2 + (floor - cy) * z
        kid(img, c, sx, fy, s * z, p)
        heads[c] = (sx, H / 2 + (floor - 1150 * s - cy) * z + 40 * z - p['drop'] * s * z)
    emotes(img, t, heads)
    overlays(img, t)
    return img.convert('RGB')


def audio_plan(path):
    sfx = os.path.join(ROOT, 'assets/sfx')
    clips = [{'file': os.path.join(EP.dir, 'voces', l + '.mp3'), 'at': at,
              'gain': 0.85 if EP.L[l].get('ambos') else 1.0} for l, at in EP.says.items()]
    fx = [(0.0, 'pop', 0.45), (0.1, 'pop', 0.4)]
    for lid, d in EP.d.items():
        if d['card']:
            fx.append((EP.says[lid] + 0.25, 'pop', 0.4))
        if d['hop']:
            fx.append((EP.says[lid] + 0.2, 'boing', 0.35))
        if d['emote'] and d['emote'][1] == 'bombilla':
            fx.append((EP.says[lid] + 0.1, 'ding', 0.4))
    if EP.quiet is not None:
        fx.append((EP.quiet + 0.15, 'grillos' if EP.react in ('silencio', 'mirada') else 'tick', 0.5))
    if EP.end_text is not None:
        fx.append((EP.end_text, 'pop', 0.5))
    plan = {'total': EP.total, 'clips': clips,
            'sfx': [{'file': os.path.join(sfx, n + '.wav'), 'at': a, 'gain': g_} for a, n, g_ in fx],
            'music': os.path.join(ROOT, 'assets/music/pensar.wav'), 'musicGain': 0.14}
    json.dump(plan, open(path, 'w'))


def render_range(args):
    a, b, path = args
    with open(path, 'wb') as f:
        for n in range(a, b):
            f.write(frame_at(n / FPS).tobytes())


def video(out):
    from multiprocessing import Pool
    work = os.path.join(os.path.dirname(os.path.abspath(out)), EP.id + '-work')
    os.makedirs(work, exist_ok=True)
    t0, t1 = (float(v) for v in os.environ.get('TRAMO', f'0,{EP.total}').split(','))
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
    os.rmdir(work) if not os.listdir(work) else None


if __name__ == '__main__':
    if sys.argv[1] == 'lineas':
        print(write_lines(sys.argv[2]))
        sys.exit()
    load(sys.argv[1])
    if sys.argv[2].endswith(('.png', '.jpg')):
        frame_at(float(sys.argv[3])).save(sys.argv[2])
    else:
        video(sys.argv[2])
