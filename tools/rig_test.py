"""Rig test: E walks towards the camera, waves, points away and up, shrugs and jumps, moved only by the
skeleton of tools/split_parts.py.
Usage: python3 tools/rig_test.py out.mp4 [--debug]      (--debug draws the joints)

The legs use two-bone IK: the hip comes from the torso, the ankle from the floor (or the air), and the knee bends
outwards, like a child seen from the front. A leg that lifts towards the camera gets shorter on screen (the thigh
takes most of it) instead of bending sideways. The head is the original drawing, only moved and turned."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIG = os.environ.get('RIG', 'parts')            # parts: first cut (hands in the pockets); rig: from pose A
PARTS = os.path.join(ROOT, 'assets/characters/e', RIG)
W, H, FPS = 1080, 1920, 30
DUR = 14.0

meta = json.load(open(os.path.join(PARTS, 'parts.json' if RIG == 'parts' else 'rig.json')))
TORSO_FREE = 'torso_libre' if RIG == 'parts' else 'torso'
REST_HAND = 'relajada' if RIG == 'parts' else 'pose'
J = {k: np.array(v, float) for k, v in meta['joints'].items()}
IMG = {n: Image.open(os.path.join(PARTS, n + '.png')).convert('RGBA') for n in meta['pieces']}
OFF = {n: np.array([p['x'], p['y']], float) for n, p in meta['pieces'].items()}


def T(x, y):
    return np.array([[1, 0, x], [0, 1, y], [0, 0, 1.0]])


def R(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def Sc(sx, sy=None):
    return np.array([[sx, 0, 0], [0, sx if sy is None else sy, 0], [0, 0, 1.0]])


def ap(M, p):
    return (M @ np.array([p[0], p[1], 1.0]))[:2]


def ang(v):
    return math.atan2(v[1], v[0])


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def draw(frame, name, M):
    """Pastes piece name with the matrix M (drawing coords -> frame coords)."""
    im = IMG[name]
    M = M @ T(*OFF[name])
    # only transform into the box the piece lands in
    corners = [ap(M, c) for c in ((0, 0), (im.width, 0), (0, im.height), (im.width, im.height))]
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    x0, y0 = int(max(math.floor(min(xs)) - 2, 0)), int(max(math.floor(min(ys)) - 2, 0))
    x1, y1 = int(min(math.ceil(max(xs)) + 2, W)), int(min(math.ceil(max(ys)) + 2, H))
    if x1 <= x0 or y1 <= y0:
        return
    inv = np.linalg.inv(M) @ T(x0, y0)
    tile = im.transform((x1 - x0, y1 - y0), Image.AFFINE, tuple(inv[:2].ravel()), resample=Image.BICUBIC)
    frame.alpha_composite(tile, (x0, y0))


HANDS = meta['hands']
REST = {}
for _sd in ('l', 'r'):
    REST['up_' + _sd] = math.degrees(ang(J['elbow_' + _sd] - J['shoulder_' + _sd]))
    REST['arm_' + _sd] = math.degrees(ang(J['wrist_' + _sd] - J['shoulder_' + _sd]))
    REST['fore_' + _sd] = math.degrees(ang(J['wrist_' + _sd] - J['elbow_' + _sd]))
SLEEVES = meta.get('sleeves')                   # one straight sleeve per side, bent along a curve (split_sleeves.py)
if SLEEVES:
    from split_sleeves import sample
    STRIP = {sd: np.asarray(Image.open(os.path.join(PARTS, f'sleeve_{sd}.png')).convert('RGBA'), float)
             for sd in SLEEVES}
    for _sd in STRIP:                           # premultiplied, so resampling doesn't darken the edge
        STRIP[_sd][..., :3] *= STRIP[_sd][..., 3:] / 255
ONE_PIECE = 'upperarm_l' not in meta['pieces']   # pose A rig without layered sleeves: a straight arm in one piece


def arm(side, Mt, S, tilt, up_out, fore_out, hand, hand_rot=0.0):
    """Upper arm, forearm and hand matrices. up_out / fore_out: degrees away from hanging straight down, outwards
    (90 = sideways, 180 = straight up), for the upper arm and the forearm; hand: kind of hand (abierta, puno...)."""
    sgn = 1 if side == 'l' else -1
    th_u = math.radians(90 + sgn * up_out) + tilt
    th_f = math.radians(90 + sgn * fore_out) + tilt
    S0, E0 = J['shoulder_' + side], J['elbow_' + side]
    Sw = ap(Mt, S0)
    if ONE_PIECE:
        Ma = T(*Sw) @ R(th_u - math.radians(REST['arm_' + side])) @ Sc(S) @ T(*-S0)
        Ww = ap(Ma, J['wrist_' + side]) - 6 * S * np.array([math.cos(th_u), math.sin(th_u)])
        h = HANDS[f'{hand}_{side}']
        Mh = T(*Ww) @ R(th_u - math.radians(h['dir']) + sgn * math.radians(hand_rot)) @ Sc(S) @ T(*[-v for v in h['wrist']])
        return Ma, None, Mh
    Mu = T(*Sw) @ R(th_u - math.radians(REST['up_' + side])) @ Sc(S) @ T(*-S0)
    Ew = ap(Mu, E0)
    Mf = T(*Ew) @ R(th_f - math.radians(REST['fore_' + side])) @ Sc(S) @ T(*-E0)
    Ww = ap(Mf, J['wrist_' + side]) - 9 * S * np.array([math.cos(th_f), math.sin(th_f)])   # into the cuff
    h = HANDS[f'{hand}_{side}']
    Mh = T(*Ww) @ R(th_f - math.radians(h['dir']) + sgn * math.radians(hand_rot)) @ Sc(S) @ T(*[-v for v in h['wrist']])
    return Mu, Mf, Mh


def hermite(p0, p1, m0, m1, n):
    u = np.linspace(0, 1, n)[:, None]
    return ((2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * m0 + (-2 * u ** 3 + 3 * u ** 2) * p1
            + (u ** 3 - u ** 2) * m1)


def unit(v):
    return v / max(np.linalg.norm(v), 1e-6)


def draw_sleeve(frame, side, Sw, Ew, Ww, t_sh, S, fade=None, mask=None):
    """Bends the straight sleeve along a smooth curve: it leaves the shoulder along t_sh (between hanging and the upper
    arm, so the shoulder rounds off like a real one), goes round the elbow and comes out along the forearm."""
    g, im = SLEEVES[side], STRIP[side]
    tf = unit(Ww - Ew)
    te = unit(unit(Ew - Sw) + tf)
    lu, lf = np.linalg.norm(Ew - Sw), np.linalg.norm(Ww - Ew)
    a = Sw - t_sh * g['cap'] * S * 1.2
    seg = [np.linspace(a, Sw, 12)[:-1],
           hermite(Sw, Ew, t_sh * lu, te * lu * 0.9, 50)[:-1],
           hermite(Ew, Ww, te * lf * 0.9, tf * lf, 50)[:-1],
           np.linspace(Ww, Ww + tf * (g['cuff'] + 6) * S, 8)]
    C = np.concatenate(seg)
    marks = np.cumsum([0] + [len(x) for x in seg[:-1]])           # sample index of shoulder, elbow, wrist
    ds = np.linalg.norm(np.diff(C, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(ds)])
    Tn = np.gradient(C, axis=0)
    Tn /= np.maximum(np.linalg.norm(Tn, axis=1, keepdims=True), 1e-6)
    # arc length -> row of the straight sleeve, joint by joint
    s_keys = [arc[0], arc[marks[1]], arc[marks[2]], arc[marks[3]], arc[-1]]
    v_keys = [-g['cap'] * 1.2, 0, g['upper'], g['upper'] + g['fore'], g['upper'] + g['fore'] + g['cuff'] + 6]
    pad = g['half'] * S + 3
    x0, y0 = np.floor(C.min(0) - pad).astype(int)
    x1, y1 = np.ceil(C.max(0) + pad).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    P = np.stack([xx.ravel(), yy.ravel()], 1).astype(float)
    best = np.zeros(len(P), int)
    bd = np.full(len(P), np.inf)
    for i in range(0, len(C), 32):                               # nearest curve sample, in chunks
        dd = ((P[:, None, :] - C[None, i:i + 32]) ** 2).sum(2)
        k = dd.argmin(1)
        m = dd[np.arange(len(P)), k] < bd
        bd[m], best[m] = dd[np.arange(len(P)), k][m], k[m] + i
    dv = P - C[best]
    t = Tn[best]
    along = arc[best] + (dv * t).sum(1)
    across = dv[:, 0] * t[:, 1] - dv[:, 1] * t[:, 0]
    v = np.interp(along, s_keys, v_keys, left=-1e4, right=1e4)
    k = g['k']
    rows = ((v + g['cap']) * k).reshape(yy.shape)
    cols = ((across / S + g['half']) * k).reshape(yy.shape)
    px = sample(im, rows, cols)
    if fade:                                    # over the torso: the top of the sleeve melts into the shoulder
        px *= np.clip((v.reshape(yy.shape) - fade[0]) / (fade[1] - fade[0]), 0, 1)[..., None]
    if mask is not None:                        # only where mask (the torso) is: elsewhere the sleeve below shows
        px *= mask[y0:y1, x0:x1, None] / 255
    al = px[..., 3:]
    px[..., :3] = np.where(al > 0, px[..., :3] * 255 / np.maximum(al, 1), 0)
    tile = Image.fromarray(np.clip(px, 0, 255).astype(np.uint8), 'RGBA')
    frame.alpha_composite(tile, (int(x0), int(y0)))


def leg(side, Mt, A, S, lift):
    """Thigh, shin and foot matrices: hip from the torso matrix Mt, ankle at A (frame coords).
    lift 0..1: how much the leg comes towards the camera (shortens on screen instead of bending sideways)."""
    H0, K0, A0 = J['hip_' + side], J['knee_' + side], J['ankle_' + side]
    Hp = ap(Mt, H0)
    L1, L2 = np.linalg.norm(K0 - H0) * S, np.linalg.norm(A0 - K0) * S
    d = max(np.linalg.norm(A - Hp), 1e-3)
    # towards the camera: the leg gets shorter, the thigh most; what is left bends the knee a little outwards
    short = max(L1 + L2 - d * (1.015 + 0.04 * lift), 0) * (0.25 + 0.75 * lift)
    l1, l2 = L1 - short * 0.75, L2 - short * 0.25
    if d >= l1 + l2:
        K = Hp + (A - Hp) * (l1 / (l1 + l2))
        l1, l2 = np.linalg.norm(K - Hp), np.linalg.norm(A - K)
    else:
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - a * a, 0))
        u = (A - Hp) / d
        n = np.array([-u[1], u[0]])
        K = Hp + u * a + n * h
        if (side == 'l' and K[0] > Hp[0] + u[0] * a + 1e-6) or (side == 'r' and K[0] < Hp[0] + u[0] * a - 1e-6):
            K = Hp + u * a - n * h
    phi1, phi2 = ang(K0 - H0), ang(A0 - K0)
    f1, f2 = l1 / L1, l2 / L2
    Mth = T(*Hp) @ R(ang(K - Hp)) @ Sc(f1, 1) @ R(-phi1) @ Sc(S) @ T(*-H0)
    Msh = T(*K) @ R(ang(A - K)) @ Sc(f2, 1) @ R(-phi2) @ Sc(S) @ T(*-K0)
    Mft = T(*A) @ Sc(S * (1 + 0.04 * lift)) @ T(*-A0)
    return Mth, Msh, Mft, Hp, K


# arm poses: side -> (upper arm out, forearm out, hand, hand turn); None = hands in the pockets (the drawing as is)
SHOULDER_FOLLOW = 0.35      # how much the sleeve leaves the shoulder still pointing down (round shoulder)
FOREARM_LAG = 0.08          # s
SHOULDER_FADE = (-6, 34)    # sleeve rows (from the shoulder joint) over which it fades into the torso
DOWN = {'l': (12, 8, REST_HAND, 0), 'r': (12, 8, REST_HAND, 0)}
ARM_KEYS = [  # (time, pose); between keys the angles ease, the hand changes half way
    (0.0, DOWN), (3.4, DOWN),
    (3.9, {'l': (6, 4, REST_HAND, 0), 'r': (135, 170, 'abierta', 0)}),          # waves
    (5.3, {'l': (6, 4, REST_HAND, 0), 'r': (135, 170, 'abierta', 0)}),
    (5.8, {'l': (84, 88, 'senala', 0), 'r': (6, 4, REST_HAND, 0)}),             # points away
    (7.0, {'l': (84, 88, 'senala', 0), 'r': (6, 4, REST_HAND, 0)}),
    (7.5, {'l': (6, 4, REST_HAND, 0), 'r': (160, 160, 'senala', 0)}),            # points up: an idea
    (8.7, {'l': (6, 4, REST_HAND, 0), 'r': (160, 160, 'senala', 0)}),
    (9.1, {'l': (40, 80, 'abierta', 0), 'r': (40, 80, 'abierta', 0)}),           # shrug
    (10.1, {'l': (40, 80, 'abierta', 0), 'r': (40, 80, 'abierta', 0)}),
    (10.5, {'l': (14, 30, 'puno', 0), 'r': (14, 30, 'puno', 0)}),                # gets ready to jump
    (10.9, {'l': (150, 168, 'puno', 0), 'r': (150, 168, 'puno', 0)}),            # celebrates in the air
    (11.6, {'l': (150, 168, 'puno', 0), 'r': (150, 168, 'puno', 0)}),
    (12.3, DOWN), (14.0, DOWN),
]


def arms_at(t):
    for (t0, a), (t1, b) in zip(ARM_KEYS, ARM_KEYS[1:]):
        if t0 <= t <= t1:
            k = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1
            out = {}
            for side in ('l', 'r'):
                pa, pb = a[side], b[side]
                out[side] = (pa[0] + (pb[0] - pa[0]) * k, pa[1] + (pb[1] - pa[1]) * k, pa[2] if k < 0.5 else pb[2],
                             pa[3] + (pb[3] - pa[3]) * k)
            return out
    return ARM_KEYS[-1][1]


def pose(t):
    """Everything that moves, as numbers, at time t."""
    p = {'tilt': 0.0, 'head': 0.0, 'lift': [0.0, 0.0], 'air': [0.0, 0.0], 'drop': 0.0, 'dx': 0.0, 'blink': False,
         'spread': 0.0}
    p['arms'] = {k: list(v) for k, v in arms_at(t).items()}
    late = arms_at(max(t - FOREARM_LAG, 0))          # the forearm and the hand trail the upper arm a little
    for sd in ('l', 'r'):
        p['arms'][sd][1] = late[sd][1]
        p['arms'][sd][2] = late[sd][2]
    # walk towards the camera: 0 .. 3.4 s, steps of 0.5 s; the arms swing a little
    walk_end = 3.4
    k = ease(min(t / walk_end, 1))
    p['S'] = 0.62 + 0.36 * k
    if t < walk_end:
        ph = t / 1.0 * 2 * math.pi
        amp = min(t / 0.4, 1) * min((walk_end - t) / 0.4, 1)
        s = math.sin(ph)
        p['lift'] = [max(s, 0) ** 1.4 * amp, max(-s, 0) ** 1.4 * amp]
        p['drop'] = -abs(s) * 9 * amp          # up at mid-stance, down when both feet are on the floor
        p['dx'] = -s * 7 * amp                 # the weight goes over the foot on the floor
        p['tilt'] = math.radians(2.2) * s * amp
        p['head'] = -math.radians(1.6) * math.sin(ph - 0.5) * amp
        # the arm opposite to the lifted leg comes forward: in a front view the forearm bends up a little
        p['arms']['l'][0] += 4 * amp * max(-s, 0)
        p['arms']['l'][1] += 26 * amp * max(-s, 0)
        p['arms']['r'][0] += 4 * amp * max(s, 0)
        p['arms']['r'][1] += 26 * amp * max(s, 0)
    # waving: the forearm goes from side to side
    if 3.9 <= t <= 5.3:
        p['arms']['r'][1] += 16 * math.sin((t - 3.9) * 2 * math.pi * 1.6)
        p['head'] += math.radians(3)
    if 5.8 <= t <= 7.0:
        p['head'] -= math.radians(3)
    if 9.1 <= t <= 10.1:                          # shrug: the shoulders go up with the head tilted
        c = math.sin(math.pi * (t - 9.1) / 1.0)
        p['head'] += math.radians(5) * c
        p['drop'] -= 6 * c
    # the jump
    for j0 in (10.3,):
        u = t - j0
        crouch, launch, air_t, land, rec = 0.38, 0.12, 0.62, 0.16, 0.3
        if 0 <= u < crouch:                            # get ready: knees out, body down
            c = ease(u / crouch)
            p['drop'] += 60 * c
            p['lift'] = [0.55 * c, 0.55 * c]           # knees come forward, not only out
            p['head'] += math.radians(3) * c
        elif crouch <= u < crouch + launch:            # push: legs straight, body up
            c = ease((u - crouch) / launch)
            p['drop'] += 60 * (1 - c) - 18 * c
            p['lift'] = [0.55 * (1 - c), 0.55 * (1 - c)]
        elif crouch + launch <= u < crouch + launch + air_t:   # in the air
            c = (u - crouch - launch) / air_t
            hgt = 4 * c * (1 - c)
            p['drop'] += -18 - 300 * hgt
            tuck = math.sin(math.pi * min(c * 1.25, 1))
            p['air'] = [70 * tuck + 300 * hgt, 70 * tuck + 300 * hgt]
            p['lift'] = [0.9 * tuck, 0.9 * tuck]
            p['spread'] = 14 * tuck
            p['head'] += -math.radians(4) * tuck
        elif crouch + launch + air_t <= u < crouch + launch + air_t + land + rec:   # land and come back up
            c = u - crouch - launch - air_t
            dip = ease(c / land) if c < land else 1 - ease((c - land) / rec)
            p['drop'] += 44 * dip
            p['lift'] = [0.5 * dip, 0.5 * dip]
            p['head'] += math.radians(2.5) * dip
    # blink every ~2.6 s
    p['blink'] = (t % 2.6) > 2.45
    return p


def background():
    yy = np.linspace(0, 1, H)[:, None, None]
    bg = np.array([250, 244, 232.0]) * (1 - yy) + np.array([236, 226, 210.0]) * yy
    bg = np.broadcast_to(bg, (H, W, 3)).copy()
    bg[1200:] = [226, 214, 196]
    return Image.fromarray(bg.astype(np.uint8)).convert('RGBA')


BG = background()


def frame_at(t, debug=False):
    p = pose(t)
    S = p['S']
    floor = 760 + S * 1050                          # further away = higher on screen
    cx = W / 2 + p['dx'] * S
    ankle_y = floor - (1150 - 1058) * S             # ankle above the sole
    hip_y = ankle_y - (J['ankle_l'][1] - J['pelvis'][1]) * S + p['drop'] * S
    Mt = T(cx, hip_y) @ R(p['tilt']) @ Sc(S) @ T(*-J['pelvis'])
    Mh = Mt @ T(*J['neck']) @ R(p['head'] - p['tilt'] * 0.6) @ T(*-J['neck'])

    img = BG.copy()
    # shadow, smaller when he is in the air
    air = max(p['air'][0], 0)
    sw, sh = 330 * S * (1 - air / 900), 40 * S * (1 - air / 900)
    sh_img = Image.new('L', (W, H))
    ImageDraw.Draw(sh_img).ellipse((cx - sw / 2, floor - sh / 2, cx + sw / 2, floor + sh / 2), fill=int(70 * (1 - air / 700)))
    sh_img = sh_img.filter(ImageFilter.GaussianBlur(10))
    img = Image.composite(Image.new('RGBA', (W, H), (120, 95, 70, 255)), img, sh_img)

    legs = {}
    for i, side in enumerate(('l', 'r')):
        A0 = J['ankle_' + side]
        spread = (-1 if side == 'l' else 1) * p['spread']
        A = np.array([cx + (A0[0] - J['pelvis'][0] + spread) * S, ankle_y - (p['lift'][i] * 34 + p['air'][i]) * S])
        legs[side] = leg(side, Mt, A, S, p['lift'][i])
    for side in ('l', 'r'):
        draw(img, 'foot_' + side, legs[side][2])
    for side in ('l', 'r'):
        draw(img, 'shin_' + side, legs[side][1])
    for side in ('l', 'r'):
        draw(img, 'thigh_' + side, legs[side][0])
    sleeves_later = []
    if not ONE_PIECE:                               # layered sleeves go behind the torso's round shoulder
        for side in ('l', 'r'):
            up, fore, hand, rot = p['arms'][side]
            Mu, Mf, Mhd = arm(side, Mt, S, p['tilt'], up, fore, hand, rot)
            draw(img, f'hand_{hand}_{side}', Mhd)
            if SLEEVES:
                Sw, Ew = ap(Mu, J['shoulder_' + side]), ap(Mu, J['elbow_' + side])
                Ww = ap(Mf, J['wrist_' + side])
                sgn = 1 if side == 'l' else -1
                th_u = math.radians(90 + sgn * up) + p['tilt']
                th_s = th_u - SHOULDER_FOLLOW * (th_u - (math.pi / 2 + p['tilt']))
                t_sh = np.array([math.cos(th_s), math.sin(th_s)])
                draw_sleeve(img, side, Sw, Ew, Ww, t_sh, S)
                sleeves_later.append((side, Sw, Ew, Ww, t_sh))
                continue
            draw(img, 'forearm_' + side, Mf)
            draw(img, 'upperarm_' + side, Mu)
    torso = Image.new('RGBA', (W, H))
    draw(torso, TORSO_FREE if p['arms'] else 'torso', Mt)
    img.alpha_composite(torso)
    if sleeves_later:                               # then over the torso, fading into its round shoulder
        tmask = np.asarray(torso)[..., 3].astype(float)
        for side, Sw, Ew, Ww, t_sh in sleeves_later:
            draw_sleeve(img, side, Sw, Ew, Ww, t_sh, S, fade=SHOULDER_FADE, mask=tmask)
    if p['arms'] and ONE_PIECE:
        for side in ('l', 'r'):
            up, fore, hand, rot = p['arms'][side]
            Mu, Mf, Mhd = arm(side, Mt, S, p['tilt'], up, fore, hand, rot)
            draw(img, f'hand_{hand}_{side}', Mhd)
            if ONE_PIECE:
                draw(img, 'arm_' + side, Mu)
                continue
            draw(img, 'forearm_' + side, Mf)
            draw(img, 'upperarm_' + side, Mu)
    draw(img, 'head', Mh)
    if p['blink']:
        draw(img, 'blink', Mh)
    if debug:
        d = ImageDraw.Draw(img)
        for side in ('l', 'r'):
            for q in (legs[side][3], legs[side][4]):
                d.ellipse((q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6), outline=(0, 160, 255), width=3)
    return img.convert('RGB')


def main():
    out = sys.argv[1]
    debug = '--debug' in sys.argv
    if out.endswith('.png'):
        t = float(sys.argv[2])
        frame_at(t, debug).save(out)
        return
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out],
                          stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        ff.stdin.write(frame_at(i / FPS, debug).tobytes())
    ff.stdin.close()
    ff.wait()


if __name__ == '__main__':
    main()
