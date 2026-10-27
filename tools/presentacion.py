"""The channel's intro Short (E and R), 1080x1920, ~29 s, put together with the pose A rigs of tools/rig_test.py.
Usage:
  python3 tools/presentacion.py out.mp4                 video (voices from content/especiales/presentacion/voces)
  python3 tools/presentacion.py out.png 12.5            one frame
  python3 tools/presentacion.py poses.png --poses       every pose of both kids, for checking hands and arms

The faces are Chiño's drawings, never redrawn: only the whole head moves (small turns), the eyes close (blink.png)
and, while a kid speaks, the part under the lip line slides down a few pixels (jaw.png) over the inside of the mouth,
as in src/puppets.js. Arms, hands and legs are the rig's pieces."""
import importlib.util, json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
DIR = os.path.join(ROOT, 'content/especiales/presentacion')
W, H, FPS = 1080, 1920, 30
FONT = os.environ.get('FREDOKA', os.path.join(ROOT, 'out/fredoka-700.ttf'))
if not os.path.exists(FONT):                    # the channel's font (@fontsource/fredoka) as a TTF for Pillow
    from fontTools.ttLib import TTFont
    os.makedirs(os.path.dirname(FONT), exist_ok=True)
    _f = TTFont(os.path.join(ROOT, 'node_modules/@fontsource/fredoka/files/fredoka-latin-700-normal.woff2'))
    _f.flavor = None
    _f.save(FONT)


def load(c):
    os.environ['CHAR'], os.environ['RIG'] = c, 'rig'
    spec = importlib.util.spec_from_file_location('rig_' + c, os.path.join(ROOT, 'tools/rig_test.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


K = {'e': load('e'), 'r': load('r')}
# mouth of the original drawings (tools/prepare_characters.py RIGS[...]['jaw']), in rig coordinates
MOUTH = {'e': {'y': 406, 'd': 8, 'ox': 456.5, 'ow': 29, 'inside': (74, 14, 8)},
         'r': {'y': 363, 'd': 7, 'ox': 454.5, 'ow': 27, 'inside': (90, 26, 16)}}
T, Rm, Sc, ap, ease = K['e'].T, K['e'].R, K['e'].Sc, K['e'].ap, K['e'].ease


def real_wrist(m, name):
    """The pointing hand of the rig has its wrist in the middle of the palm (so the index follows the forearm when
    pointing sideways); pointing up, that hides the palm in the sleeve and only a finger and the thumb show, like a
    claw. Here its wrist goes back to the real one, the back edge of the hand, and its axis to the fingertip."""
    a = np.asarray(m.IMG['hand_' + name])[..., 3] > 128
    ys, xs = np.nonzero(a)
    back = xs.max() if name.endswith('_r') else xs.min()
    band = np.abs(xs - back) < 8
    wx = back - 7 if name.endswith('_r') else back + 7
    wy = float(np.median(ys[band]))
    d2 = (xs - wx) ** 2 + (ys - wy) ** 2
    i = d2.argmax()
    m.HANDS[name] = {'wrist': [float(wx), wy], 'dir': math.degrees(math.atan2(ys[i] - wy, xs[i] - wx))}


for _c in K:
    for _sd in ('l', 'r'):
        real_wrist(K[_c], 'senala_' + _sd)

# ---------------------------------------------------------------- arm poses
# side -> (upper arm out, forearm out, hand, hand turn) in degrees away from hanging down, outwards (rig_test.arm).
# For E and R the 'r' side is the one on the right of the screen.
POSES = {
    'quieto': {'l': (12, 8, 'pose', 0), 'r': (12, 8, 'pose', 0)},
    # arm up with the hand open (Chiño: no pointing finger; arms up always with an open hand)
    'senala_arriba': {'l': (10, 6, 'pose', 0), 'r': (128, 165, 'abierta~', 0)},
    'cintura': {'l': (42, -38, 'puno', 0), 'r': (42, -38, 'puno', 0)},
    'explica': {'l': (10, 6, 'pose', 0), 'r': (40, 80, 'abierta~', 35)},
    'barbilla': {'l': (14, 10, 'pose', 0), 'r': (-8, -174, 'puno', 0, 'front')},     # fist under the chin
    'rasca': {'l': (10, 6, 'pose', 0), 'r': (128, -158, 'puno', 0, 'behind')},     # hand behind the head
    'saluda': {'l': (10, 6, 'pose', 0), 'r': (132, 150, 'abierta~', 0)},
    'saluda_izq': {'l': (132, 150, 'abierta~', 0), 'r': (10, 6, 'pose', 0)},
    'celebra': {'l': (145, 160, 'abierta~', 0), 'r': (145, 160, 'abierta~', 0)},
    'encoge': {'l': (40, 80, 'abierta~', 35), 'r': (40, 80, 'abierta~', 35)},
    'encoge_corto': {'l': (24, 62, 'abierta~', 30), 'r': (40, 80, 'abierta~', 35)},   # the hand towards E stays close
}


def sleeve(m, side, Sw, Ew, Ww, t_sh, S):
    """rig_test.draw_sleeve, computed once per frame and side (it is drawn twice: under the torso and over it), with
    the nearest point of the curve found by a k-d tree instead of brute force. Returns (tile rgba premultiplied, v
    rows, x0, y0) or None."""
    from scipy.spatial import cKDTree
    g, im = m.SLEEVES[side], m.STRIP[side]
    tf = m.unit(Ww - Ew)
    te = m.unit(m.unit(Ew - Sw) + tf)
    lu, lf = np.linalg.norm(Ew - Sw), np.linalg.norm(Ww - Ew)
    a = Sw - t_sh * g['cap'] * S * 1.2
    seg = [np.linspace(a, Sw, 12)[:-1],
           m.hermite(Sw, Ew, t_sh * lu, te * lu * 0.9, 50)[:-1],
           m.hermite(Ew, Ww, te * lf * 0.9, tf * lf, 50)[:-1],
           np.linspace(Ww, Ww + tf * (g['cuff'] + 6) * S, 8)]
    C = np.concatenate(seg)
    # densify, so the nearest sample is as good as the brute force one
    C = np.concatenate([np.linspace(C[i], C[i + 1], 4, endpoint=False) for i in range(len(C) - 1)] + [C[-1:]])
    marks = [0, 11 * 4, (11 + 49) * 4, (11 + 98) * 4]
    ds = np.linalg.norm(np.diff(C, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(ds)])
    Tn = np.gradient(C, axis=0)
    Tn /= np.maximum(np.linalg.norm(Tn, axis=1, keepdims=True), 1e-6)
    s_keys = [arc[0], arc[marks[1]], arc[marks[2]], arc[marks[3]], arc[-1]]
    v_keys = [-g['cap'] * 1.2, 0, g['upper'], g['upper'] + g['fore'], g['upper'] + g['fore'] + g['cuff'] + 6]
    pad = g['half'] * S + 3
    x0, y0 = np.floor(C.min(0) - pad).astype(int)
    x1, y1 = np.ceil(C.max(0) + pad).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return None
    yy, xx = np.mgrid[y0:y1, x0:x1]
    P = np.stack([xx.ravel(), yy.ravel()], 1).astype(float)
    dist, best = cKDTree(C).query(P, distance_upper_bound=pad + 2)
    far = ~np.isfinite(dist)
    best[far] = 0
    dv = P - C[best]
    t = Tn[best]
    along = arc[best] + (dv * t).sum(1)
    across = dv[:, 0] * t[:, 1] - dv[:, 1] * t[:, 0]
    v = np.interp(along, s_keys, v_keys, left=-1e4, right=1e4)
    v[far] = -1e4
    k = g['k']
    rows = ((v + g['cap']) * k).reshape(yy.shape)
    cols = ((across / S + g['half']) * k).reshape(yy.shape)
    px = sample_fast(im, rows, cols)
    return px, v.reshape(yy.shape), x0, y0


def sample_fast(img, r, c):
    h, w = img.shape[:2]
    ok = (r > -1) & (r < h) & (c > -1) & (c < w)
    out = np.zeros(r.shape + (img.shape[2],))
    if ok.any():
        out[ok] = _bilinear(img, r[ok], c[ok])
    return out


def _bilinear(img, r, c):
    h, w = img.shape[:2]
    r0, c0 = np.floor(r).astype(int), np.floor(c).astype(int)
    fr, fc = (r - r0)[:, None], (c - c0)[:, None]
    out = 0
    for dr, dc, wt in ((0, 0, (1 - fr) * (1 - fc)), (1, 0, fr * (1 - fc)), (0, 1, (1 - fr) * fc), (1, 1, fr * fc)):
        rr, cc = r0 + dr, c0 + dc
        okk = ((rr >= 0) & (rr < h) & (cc >= 0) & (cc < w))[:, None]
        out = out + img[np.clip(rr, 0, h - 1), np.clip(cc, 0, w - 1)] * okk * wt
    return out


def paste_sleeve(frame, sl, fade=None, mask=None):
    if sl is None:
        return
    px, v, x0, y0 = sl
    px = px.copy()
    if fade:
        px *= np.clip((v - fade[0]) / (fade[1] - fade[0]), 0, 1)[..., None]
    if mask is not None:
        px *= mask[y0:y0 + px.shape[0], x0:x0 + px.shape[1], None] / 255
    al = px[..., 3:]
    px[..., :3] = np.where(al > 0, px[..., :3] * 255 / np.maximum(al, 1), 0)
    frame.alpha_composite(Image.fromarray(np.clip(px, 0, 255).astype(np.uint8), 'RGBA'), (int(x0), int(y0)))


def mix_arm(a, b, x):
    """Angles from pose a to pose b (x 0..1), the way a child moves an arm. Raising it, the elbow bends first and
    brings the hand up in front of the shoulder, then the upper arm lifts and the forearm opens up (the hand never
    swings up on a straight arm). Lowering it, the upper arm drops first and the hand trails behind. The hand
    changes while it is close to the body."""
    if b[0] - a[0] > 50:                         # raising
        ku, kf = ease((x - 0.2) / 0.8), ease(x / 0.6)
        swap = kf > 0.35
    elif a[0] - b[0] > 50:                       # lowering
        ku, kf = ease(x / 0.8), ease((x - 0.15) / 0.85)
        swap = ku > 0.55
    else:
        ku = kf = ease(x)
        swap = ku > 0.4
    up = a[0] + (b[0] - a[0]) * ku
    df = b[1] - a[1]
    if abs(df) > 180:                            # over the head: the short way round, not down and back up
        df -= math.copysign(360, df)
    inward = b[0] - a[0] > 50 and a[1] < 40 and b[1] > 140 and b[2] != 'puno' and a[2] == 'pose' and not (b[0] > 140)
    if inward:                                   # from hanging to up: the hand rises in front of the chest
        df -= 360
    fore = a[1] + df * kf
    if not (inward or a[0] < 0 or b[0] < 0 or a[1] < 0 or b[1] < 0):
        fore = max(fore, up - 6)                 # the elbow never bends backwards
    src = b if swap else a
    where = 'front' if inward and x < 0.8 else (src[4] if len(src) > 4 else None)
    hand = src[2]
    return (up, fore, hand, a[3] + (b[3] - a[3]) * ease(x), where)


def settle(a, b, s):
    """After a big move the arm overshoots a little and settles (s: seconds since it arrived)."""
    if s > 0.6 or abs(b[0] - a[0]) < 50:
        return 0.0, 0.0
    sg = 1 if b[0] > a[0] else -1
    d = math.exp(-7 * s)
    return sg * 4 * d * math.sin(13 * s), sg * 7 * d * math.sin(13 * s - 0.7)


# ---------------------------------------------------------------- one kid
HAND_OUT = {}                                   # hand -> px of the drawing it comes further out of the sleeve
WRISTS = []                                     # where the hands went (for checking the joins)
WRIST_INFO = {}


def wrist_info(m, c, hand, side):
    """Skin colour, edge colour and wrist half width (px of the drawing) of a hand piece: measured on the piece
    itself, across its wrist->fingers axis where the hand is full."""
    key = (c, hand.rstrip('~'), side)
    if key in WRIST_INFO:
        return WRIST_INFO[key]
    h = m.HANDS[f'{key[1]}_{side}']
    a = np.asarray(m.IMG[f'hand_{key[1]}_{side}'], float)
    ax = np.array([math.cos(math.radians(h['dir'])), math.sin(math.radians(h['dir']))])
    nx = np.array([-ax[1], ax[0]])
    w0 = np.array(h['wrist'], float)
    widths, cols, depths = [], [], []
    for depth in range(-20, 70, 2):
        q = w0 + ax * depth
        ok = []
        for t in np.arange(-70, 70, 0.5):
            x, y = (q + nx * t).astype(int)
            if 0 <= y < a.shape[0] and 0 <= x < a.shape[1] and a[y, x, 3] > 128:
                ok.append(t)
                if 20 <= depth <= 44 and abs(t) < 14 and a[y, x, 3] > 250:
                    cols.append(a[y, x, :3])
        if ok:
            widths.append(max(ok) - min(ok))
            depths.append(depth)
    cols = np.array(cols) if len(cols) else np.array([[240, 190, 160.0]])
    lum = cols.sum(1)
    skin = np.median(cols[(lum >= np.percentile(lum, 25)) & (lum <= np.percentile(lum, 70))], 0)
    edge = skin * 0.8
    half = float(np.clip(0.42 * max(widths or [44]), 15, 24))
    # where the hand is really full (its cut edge is above this): the join must reach it before fading
    full = next((d for d, w_ in zip(depths, widths) if w_ >= 0.8 * max(widths)), 10)
    WRIST_INFO[key] = (skin, edge, half, full)
    return WRIST_INFO[key]


def wrist_join(img, Ww, Ph, ah, info, S):
    """Skin between the cuff and the hand, the colour of the hand, so the hand never looks detached: a tapered piece
    from inside the sleeve (Ww) down into the hand, fading out over the hand so it covers its cut edge."""
    skin, edge, half, full = info
    into = (max(full, 0) + 10) * S
    B = Ph + ah * into
    d = B - Ww
    L = np.linalg.norm(d)
    if L < 1:
        return
    u = d / L
    n = np.array([-u[1], u[0]])
    pad = half * S + 4
    pts = np.array([Ww + n * pad, Ww - n * pad, B + n * pad, B - n * pad])
    x0, y0 = np.floor(pts.min(0)).astype(int)
    x1, y1 = np.ceil(pts.max(0)).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
    dx, dy = xx - Ww[0], yy - Ww[1]
    along = dx * u[0] + dy * u[1]
    across = np.abs(dx * n[0] + dy * n[1])
    r = half * S * (1.0 - 0.06 * np.clip(along / L, 0, 1))
    al = np.clip(r - across + 0.5, 0, 1) * (along >= 0) * np.clip((L - along) / (12 * S), 0, 1)
    k = np.clip((across - (r - 2.4 * S)) / (2.4 * S), 0, 1)[..., None]     # thin darker edge, like the drawing's
    shade = 1 - 0.07 * (across / np.maximum(r, 1))[..., None] ** 2          # a little rounder in the middle
    rgb = (skin[None, None] * shade) * (1 - k) + edge[None, None] * k
    tile = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al * 255]).astype(np.uint8), 'RGBA')
    img.alpha_composite(tile, (int(x0), int(y0)))


def HANDS_OF(m, hand, side):
    return m.HANDS[f'{hand.rstrip("~")}_{side}']['wrist']


def kid(img, c, x, floor, S, p):
    """Draws kid c with the feet centred at (x, floor) on the frame, S times the size of the drawing.
    p: tilt, head (rad), drop (px of the drawing), arms {'l': (...), 'r': (...)}, blink, talk 0..1."""
    m = K[c]
    J = m.J
    tilt = p.get('tilt', 0.0)
    ankle_y = floor - (m.SOLE - J['ankle_l'][1]) * S
    hip_y = ankle_y - (J['ankle_l'][1] - J['pelvis'][1]) * S + p.get('drop', 0) * S
    cx = x + p.get('dx', 0) * S
    Mt = T(cx, hip_y) @ Rm(tilt) @ Sc(S) @ T(*-J['pelvis'])
    Mh = Mt @ T(*J['neck']) @ Rm(p.get('head', 0) - tilt * 0.6) @ T(*-J['neck'])
    # shadow
    sw, sh = 330 * S, 40 * S
    if 0 < floor < H + 200:
        box = (int(cx - sw), int(floor - sh), int(cx + sw), int(floor + sh))
        sm = Image.new('L', (box[2] - box[0], box[3] - box[1]))
        ImageDraw.Draw(sm).ellipse((sw / 2, sh / 2, sw * 1.5, sh * 1.5), fill=int(60 * (1 - p.get('air', 0) / 700)))
        sm = sm.filter(ImageFilter.GaussianBlur(10 * S))
        img.paste(Image.new('RGBA', sm.size, (120, 95, 70, 255)), box[:2], sm)
    air = p.get('air', 0)
    legs = {}
    for side in ('l', 'r'):
        A0 = J['ankle_' + side]
        A = np.array([cx + (A0[0] - J['pelvis'][0]) * S, ankle_y - air * S])
        legs[side] = m.leg(side, Mt, A, S, p.get('lift', 0))
    for part, i in (('foot_', 2), ('shin_', 1), ('thigh_', 0)):
        for side in ('l', 'r'):
            m.draw(img, part + side, legs[side][i])
    arms, joins = {}, {}
    for side in ('l', 'r'):
        up, fore, hand, rot, where = (list(p['arms'][side]) + [None])[:5]
        Mu, Mf, Mhd = m.arm(side, Mt, S, tilt, up, fore, hand, rot)
        th_f = math.radians(90 + (1 if side == 'l' else -1) * fore) + tilt
        out = HAND_OUT.get(hand.rstrip('~'), 0)
        if out:                                 # this hand sits further out of the cuff (its palm was swallowed)
            Mhd = T(*(np.array([math.cos(th_f), math.sin(th_f)]) * out * S)) @ Mhd
        Sw, Ew, Ww = ap(Mu, J['shoulder_' + side]), ap(Mu, J['elbow_' + side]), ap(Mf, J['wrist_' + side])
        sgn = 1 if side == 'l' else -1
        th_u = math.radians(90 + sgn * up) + tilt
        th_s = th_u - m.SHOULDER_FOLLOW * (th_u - (math.pi / 2 + tilt))
        t_sh = np.array([math.cos(th_s), math.sin(th_s)])
        arms[side] = (hand, Mhd, sleeve(m, side, Sw, Ew, Ww, t_sh, S), where)
        hp = m.HANDS[f'{hand.rstrip("~")}_{side}']
        Ph = ap(Mhd, hp['wrist'])
        tip = ap(Mhd, np.array(hp['wrist']) + 10 * np.array([math.cos(math.radians(hp['dir'])), math.sin(math.radians(hp['dir']))]))
        joins[side] = (Ww, Ph, (tip - Ph) / max(np.linalg.norm(tip - Ph), 1e-6), wrist_info(m, c, hand, side))
        WRISTS.append(Ph)
    for side, (hand, Mhd, sl, where) in arms.items():
        if where != 'front':
            m.draw(img, f'hand_{hand.rstrip("~")}_{side}', Mhd)
            wrist_join(img, *joins[side], S)
            paste_sleeve(img, sl)
    torso = Image.new('RGBA', (W, H))
    m.draw(torso, 'torso', Mt)
    img.alpha_composite(torso)
    tmask = np.asarray(torso)[..., 3].astype(float)
    for side, (hand, Mhd, sl, where) in arms.items():
        if where != 'front':
            paste_sleeve(img, sl, fade=m.SHOULDER_FADE, mask=tmask)
    m.draw(img, 'head', Mh)
    mouth(img, c, Mh, p.get('talk', 0))
    if p.get('blink'):
        m.draw(img, 'blink', Mh)
    for side, (hand, Mhd, sl, where) in arms.items():
        if where == 'front':                    # a hand in front of the face (on the chin)
            m.draw(img, f'hand_{hand.rstrip("~")}_{side}', Mhd)
            wrist_join(img, *joins[side], S)
            paste_sleeve(img, sl)
            paste_sleeve(img, sl, fade=m.SHOULDER_FADE, mask=tmask)
    return Mh


def mouth(img, c, Mh, talk):
    """While speaking: the inside of the mouth under the lip line, and the drawing under it (jaw.png) slid down."""
    j = MOUTH[c]
    d = max(0.0, min(1.0, talk)) * j['d'] * 1.3
    if d < 0.25:
        return
    ox, ow, y = j['ox'], j['ow'], j['y']
    top = [(ox - ow + 2 * ow * u, y - 1 - 1.0 * math.sin(math.pi * u)) for u in np.linspace(0, 1, 16)]
    bot = [(ox + ow - 2 * ow * u, y - 1 + d * 1.1 * math.sin(math.pi * u)) for u in np.linspace(0, 1, 16)]
    pts = [tuple(ap(Mh, q)) for q in top + bot]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    ss = 4                                       # supersampled, so the edge is smooth
    lay = Image.new('RGBA', ((int(max(xs)) + 3 - x0) * ss, (int(max(ys)) + 3 - y0) * ss))
    dr = ImageDraw.Draw(lay)
    dr.polygon([((q[0] - x0) * ss, (q[1] - y0) * ss) for q in pts], fill=j['inside'] + (255,))
    tongue = [tuple(ap(Mh, (ox + ow * 0.45 * math.cos(a), y - 1 + d * 0.95 + d * 0.32 * math.sin(a)))) for a in
              np.linspace(0, 2 * math.pi, 24)]
    dr.polygon([((q[0] - x0) * ss, (q[1] - y0) * ss) for q in tongue], fill=(180, 80, 74, 205))
    lay = lay.resize((lay.width // ss, lay.height // ss), Image.LANCZOS)
    img.alpha_composite(lay, (max(x0, 0), max(y0, 0)) if x0 >= 0 and y0 >= 0 else (0, 0))
    K[c].draw(img, 'jaw', Mh @ T(0, d))


# ---------------------------------------------------------------- pose sheet
def pose_sheet(out):
    tiles = []
    for c in ('e', 'r'):
        for name, arms in POSES.items():
            im = Image.new('RGBA', (W, H), (246, 240, 228, 255))
            kid(im, c, W / 2, 1700, 1.15, {'arms': arms})
            ImageDraw.Draw(im).text((30, 30), f'{c} {name}', fill=(0, 0, 0), font=ImageFont.truetype(FONT, 60))
            tiles.append(im.crop((90, 250, 990, 1750)).resize((300, 500)))
    cols = len(POSES)
    sheet = Image.new('RGB', (300 * cols, 1000), 'white')
    for i, t in enumerate(tiles):
        sheet.paste(t, (300 * (i % cols), 500 * (i // cols)))
    sheet.save(out)


# ---------------------------------------------------------------- the script
LINES = {l['id']: l for l in json.load(open(os.path.join(DIR, 'lineas.json')))['lineas']}
DUR = json.load(open(os.path.join(DIR, 'voces/duraciones.json')))
SAYS = {'01': 0.35, '02': 3.3, '03': 5.75, '04': 7.35, '05': 12.3, '06': 16.45, '07': 20.8, '08': 23.15}  # line -> start
TOTAL = 29.0
# world: E on the left, R on the right, both standing on the same floor
# R is taller than E (Chiño's photo of them: E is about 87 % of R's height); the drawings are almost the same height
WORLD = {'e': (300, 1620, 0.86), 'r': (780, 1620, 0.98)}
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
MOVE = 0.6
LOOK = {'e': [(0, 0.04), (3.3, 0.0), (5.7, 0.05), (7.2, 0.0), (12.2, 0.05), (16.3, -0.03), (20.6, 0.0), (21.0, 0.04), (23.0, 0.0)],
        'r': [(0, 0.0), (3.2, -0.05), (5.7, 0.0), (7.1, -0.05), (12.1, 0.0), (14.6, -0.06), (20.6, 0.0), (23.0, -0.05), (25.4, 0.0)]}
BLINK = {'e': [1.2, 4.1, 6.9, 9.0, 11.6, 13.9, 15.6, 19.4, 22.1, 24.9, 27.8], 'r': [1.9, 4.7, 7.6, 10.4, 13.3, 15.1, 17.8, 20.2, 23.6, 26.6, 28.4]}
ICONS = [('wifi', 'Internet'), ('moneda', 'Dinero'), ('planeta', 'Espacio'), ('bombilla', 'Inventos')]
ICON_AT = [8.3, 9.15, 9.95, 10.8]
COLOR = {'e': (215, 50, 46), 'r': (31, 111, 224)}


def keyed(keys, t, dur=MOVE):
    """Value of a keyed list at t: holds each key, eases to the next over dur seconds."""
    cur = keys[0][1]
    for k_t, v in keys[1:]:
        if t < k_t:
            break
        prev, cur = cur, v
        x = (t - k_t) / dur
        if x < 1:
            return prev, cur, x
    return cur, cur, 1.0


def envelope(path, fps=FPS):
    """How open the mouth is, frame by frame, from the loudness of the voice. Smoothed like a real jaw (opens in
    ~40 ms, closes in ~65 ms) and compressed, so it doesn't flap fully open and shut from one frame to the next."""
    sr = 24000
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(sr), '-'],
                         check=True, capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    hop = sr // 200                                    # 5 ms
    rms = np.array([np.sqrt(np.mean(a[i:i + hop * 2] ** 2)) for i in range(0, len(a), hop)])
    rms = np.clip(rms / (np.percentile(rms, 95) or 1), 0, 1.2)
    att, rel = 1 - math.exp(-1 / (0.040 * 200)), 1 - math.exp(-1 / (0.065 * 200))
    env, y = np.zeros_like(rms), 0.0
    for i, v in enumerate(rms):
        y += (v - y) * (att if v > y else rel)
        env[i] = y
    env = np.clip((env - 0.16) / 0.84, 0, 1) ** 0.8 * 0.85
    idx = (np.arange(int(len(env) / 200 * fps) + 1) * 200 / fps).astype(int)
    return env[np.clip(idx, 0, len(env) - 1)]


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


# ---------------------------------------------------------------- background, texts, icons
def make_background():
    """The wall and the floor, in world coordinates at twice the size (so close ups stay sharp)."""
    k, M = 2, MARGIN
    w, h = (W + 2 * M) * k, (H + 2 * M) * k
    yy = np.linspace(0, 1, h)[:, None, None]
    bg = np.array([255, 236, 200.0]) * (1 - yy) + np.array([255, 214, 186.0]) * yy
    bg = np.broadcast_to(bg, (h, w, 3)).copy()
    img = Image.fromarray(bg.astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(img, 'RGBA')
    # soft confetti dots on the wall
    rng = np.random.default_rng(7)
    cols = [(255, 190, 90, 70), (120, 190, 255, 60), (255, 140, 140, 60), (140, 220, 160, 60)]
    for _ in range(70):
        x, y, r = rng.uniform(0, w), rng.uniform(0, (1450 + M) * k), rng.uniform(8, 26) * k
        d.ellipse((x - r, y - r, x + r, y + r), fill=cols[rng.integers(len(cols))])
    floor = (1560 + M) * k
    d.rectangle((0, floor, w, h), fill=(236, 196, 150, 255))
    d.rectangle((0, floor - 18 * k, w, floor), fill=(255, 250, 240, 255))      # skirting board
    d.line((0, floor, w, floor), fill=(210, 170, 128, 255), width=3 * k)
    for x in range(-200, w + 400, 260 * k):                                     # floor boards
        d.line((x, floor, x - 260 * k, h), fill=(222, 182, 138, 255), width=3 * k)
    return img


BG = None
MARGIN = 500                                    # world drawn around the 1080x1920 of the wide shot


def background(z, cx, cy):
    global BG
    if BG is None:
        BG = make_background()
    k = 2
    x0, y0 = (cx - W / 2 / z + MARGIN) * k, (cy - H / 2 / z + MARGIN) * k
    return BG.transform((W, H), Image.AFFINE, (k / z, 0, x0, 0, k / z, y0), resample=Image.BILINEAR)


def font(size):
    return ImageFont.truetype(FONT, size)


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        test = (cur + ' ' + w_).strip()
        if f.getlength(test) <= maxw or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w_
    return lines + [cur]


def pop(u):
    """0..1 scale for something popping in: overshoots a little and settles."""
    if u <= 0:
        return 0.0
    if u >= 0.35:
        return 1.0
    x = u / 0.35
    return 1 + 0.18 * math.sin(math.pi * x) - (1 - x) ** 3


def label(img, text, cx, cy, size, fg, bg, border=None, scale=1.0, maxw=940, rot=0.0, pad=(36, 22)):
    """Rounded box with text, centred at (cx, cy); scale pops it in."""
    if scale <= 0.01:
        return
    f = font(size)
    lines = wrap(text, f, maxw - 2 * pad[0])
    lh = int(size * 1.15)
    tw = max(f.getlength(l) for l in lines)
    bw, bh = int(tw + 2 * pad[0]), int(lh * len(lines) + 2 * pad[1])
    ss = 2
    lay = Image.new('RGBA', ((bw + 20) * ss, (bh + 20) * ss))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((10 * ss, 16 * ss, (bw + 10) * ss, (bh + 16) * ss), radius=34 * ss, fill=(0, 0, 0, 50))
    d.rounded_rectangle((10 * ss, 10 * ss, (bw + 10) * ss, (bh + 10) * ss), radius=34 * ss, fill=bg,
                        outline=border, width=(7 * ss if border else 0))
    fs = font(size * ss)
    for i, l in enumerate(lines):
        d.text(((bw / 2 + 10) * ss, (10 + pad[1] + lh * (i + 0.5)) * ss), l, font=fs, fill=fg, anchor='mm')
    lay = lay.resize((int(lay.width / ss * scale), int(lay.height / ss * scale)), Image.LANCZOS)
    if rot:
        lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


def icon(kind, size):
    """Simple round icons for the things E lists, drawn at 4x and shrunk."""
    k = 4
    s = size * k
    im = Image.new('RGBA', (s, s))
    d = ImageDraw.Draw(im)
    ink, lw = (40, 30, 40, 255), 6 * k
    d.ellipse((lw, lw, s - lw, s - lw), fill=(255, 255, 255, 255), outline=ink, width=lw)
    c = s / 2
    if kind == 'wifi':
        for i, r in enumerate((0.34, 0.24, 0.14)):
            rr = s * r
            d.arc((c - rr, c - rr + s * 0.12, c + rr, c + rr + s * 0.12), 225, 315, fill=(31, 111, 224, 255), width=int(s * 0.055))
        d.ellipse((c - s * 0.045, c + s * 0.1, c + s * 0.045, c + s * 0.19), fill=(31, 111, 224, 255))
    elif kind == 'moneda':
        r = s * 0.3
        d.ellipse((c - r, c - r, c + r, c + r), fill=(255, 201, 60, 255), outline=(176, 122, 0, 255), width=int(s * 0.03))
        d.text((c, c + s * 0.01), '€', font=font(int(s * 0.38)), fill=(176, 122, 0, 255), anchor='mm')
    elif kind == 'planeta':
        r = s * 0.2
        d.ellipse((c - r, c - r, c + r, c + r), fill=(140, 110, 230, 255), outline=ink, width=int(s * 0.02))
        d.arc((c - s * 0.33, c - s * 0.09, c + s * 0.33, c + s * 0.09), 0, 180, fill=(255, 170, 60, 255), width=int(s * 0.035))
        for (x, y) in ((0.24, 0.24), (0.76, 0.3), (0.7, 0.75)):
            d.ellipse((s * x - 6 * k, s * y - 6 * k, s * x + 6 * k, s * y + 6 * k), fill=(255, 201, 60, 255))
    elif kind == 'bombilla':
        r = s * 0.19
        d.ellipse((c - r, c - r * 1.35, c + r, c + r * 0.65), fill=(255, 225, 90, 255), outline=ink, width=int(s * 0.02))
        d.rectangle((c - s * 0.08, c + s * 0.1, c + s * 0.08, c + s * 0.22), fill=(150, 150, 160, 255), outline=ink, width=int(s * 0.015))
        for a in range(-150, -20, 32):
            x1, y1 = c + math.cos(math.radians(a)) * s * 0.27, c - s * 0.06 + math.sin(math.radians(a)) * s * 0.27
            x2, y2 = c + math.cos(math.radians(a)) * s * 0.36, c - s * 0.06 + math.sin(math.radians(a)) * s * 0.36
            d.line((x1, y1, x2, y2), fill=(255, 170, 40, 255), width=int(s * 0.025))
    return im.resize((size, size), Image.LANCZOS)


ICON_IMG = {}


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
