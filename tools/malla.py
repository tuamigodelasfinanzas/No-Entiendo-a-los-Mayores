"""Mesh animation (malla deformable) for E and R, all free and made here (no Spine): the hoodie and the trousers
are not stiff cut-outs any more but meshes of small triangles, each corner pulled by the bones near it, so the body
bends like rubber instead of turning in pieces. Built on tools/escena_rig.py (same pieces, sleeves, hands, wrists and
shoulders that Chiño approved) and moved by real human gestures (tools/gestos.py, retarget()).

What bends:
- Hoodie (torso.png): the chest leans and turns on the hips with a smooth bend at the waist, breathes, and each
  shoulder of the hoodie goes up with its arm (or both, shrugging).
- Trousers (thigh/shin): one continuous leg, bent smoothly at the knee and at the hip, no seam between the pieces.
- Never the face: the head is Chiño's drawing, moved and turned whole (docs/reglas-animacion.md). It follows the
  chest with a little delay (spring), like a real head.

Rules kept from escena_rig: hands come out of the sleeves (SINK, wrist_join, over_opening), arms up only with the
open hand, round shoulders (shoulder_fill), mouths that follow the syllables (mouth), R taller than E (HEIGHT)."""
import math, os, sys
import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escena_rig as er
from escena_rig import K, W, H, T, Rm, Sc, ap, sleeve, paste_sleeve, over_opening, wrist_join, wrist_info, \
    shoulder_fill, mouth, SINK


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- the mesh
class Malla:
    """A piece of the drawing cut into a grid of triangles. Each corner (vertex) has weights for a few bones; the
    piece is drawn by moving every vertex with its bones' matrices (linear blend skinning) and filling every triangle
    with the drawing, stretched by its own affine map (cv2.remap, bilinear)."""

    def __init__(self, img, off, step=12):
        a = np.asarray(img.convert('RGBA'), np.float32)
        a[..., :3] *= a[..., 3:] / 255                       # premultiplied, so stretching doesn't darken the edges
        self.tex = a
        h, w = a.shape[:2]
        xs = np.arange(-step, w + 2 * step, step, dtype=float)
        ys = np.arange(-step, h + 2 * step, step, dtype=float)
        gx, gy = np.meshgrid(xs, ys)
        self.P = np.stack([gx.ravel(), gy.ravel()], 1)       # vertex in piece pixels
        self.V0 = self.P + np.array(off, float)              # vertex in drawing coordinates
        nx = len(xs)
        alpha = a[..., 3] > 0
        tris = []
        for j in range(len(ys) - 1):
            for i in range(nx - 1):
                x0, y0 = int(max(xs[i] - step, 0)), int(max(ys[j] - step, 0))
                x1, y1 = int(min(xs[i + 1] + step, w)), int(min(ys[j + 1] + step, h))
                if x1 <= x0 or y1 <= y0 or not alpha[y0:y1, x0:x1].any():
                    continue
                v = j * nx + i
                tris += [(v, v + 1, v + nx + 1), (v, v + nx + 1, v + nx)]
        self.tri = np.array(tris)

    def skin(self, weights, mats):
        """weights: (n vertices, n bones), rows add up to 1; mats: one 3x3 matrix per bone (drawing -> frame)."""
        V = np.zeros((len(self.V0), 2))
        Vh = np.column_stack([self.V0, np.ones(len(self.V0))])
        for b, M in enumerate(mats):
            V += weights[:, b:b + 1] * (Vh @ M.T)[:, :2]
        return V

    def draw(self, frame, V):
        D = V[self.tri]                                      # (n tri, 3, 2) where each triangle lands
        x0, y0 = np.floor(D.reshape(-1, 2).min(0)).astype(int) - 1
        x1, y1 = np.ceil(D.reshape(-1, 2).max(0)).astype(int) + 2
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        if x1 <= x0 or y1 <= y0:
            return
        ids = np.full((y1 - y0, x1 - x0), -1, np.int32)
        sub = 4                                              # sub-pixel corners (cv2 shift)
        pts = np.round((D - [x0, y0]) * (1 << sub)).astype(np.int32)
        for k in range(len(pts)):
            cv2.fillConvexPoly(ids, pts[k], int(k), lineType=cv2.LINE_8, shift=sub)
        # each triangle's map from the frame back into the piece
        S = self.P[self.tri]
        Dh = np.concatenate([D - [x0, y0], np.ones(D.shape[:2] + (1,))], 2)       # (n, 3, 3) rows = corners
        Sh = S
        A = np.linalg.solve(np.where(np.abs(np.linalg.det(Dh))[:, None, None] < 1e-6, np.eye(3), Dh), Sh)  # (n, 3, 2)
        yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(np.float32)
        k = np.maximum(ids, 0)
        mx = (A[k, 0, 0] * xx + A[k, 1, 0] * yy + A[k, 2, 0]).astype(np.float32)
        my = (A[k, 0, 1] * xx + A[k, 1, 1] * yy + A[k, 2, 1]).astype(np.float32)
        mx[ids < 0] = -10
        my[ids < 0] = -10
        px = cv2.remap(self.tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        al = px[..., 3:]
        px[..., :3] = np.where(al > 0, px[..., :3] * 255 / np.maximum(al, 1e-3), 0)
        frame.alpha_composite(Image.fromarray(np.clip(px, 0, 255).astype(np.uint8), 'RGBA'), (int(x0), int(y0)))


# ---------------------------------------------------------------- each kid's meshes and weights
WAIST = (760, 560)          # drawing rows: below the first the hoodie follows the hips, above the second the chest
SPINE_Y = 640               # where the chest turns on the hips (the waist)
SHOULDER_R = 85             # px of the drawing around each shoulder that go up with it
HIP_BLEND = (-30, 30)       # rows around the hip joint where the thigh melts into the hips
KNEE_BLEND = 30             # rows above and below the knee where thigh and shin melt into each other
MESH = {}


def meshes(c):
    if c in MESH:
        return MESH[c]
    m = K[c]
    J = m.J
    out = {}
    t = Malla(m.IMG['torso'], m.OFF['torso'])
    y = t.V0[:, 1]
    chest = smoothstep((WAIST[0] - y) / (WAIST[0] - WAIST[1]))
    sh = {}
    for sd in ('l', 'r'):
        d = np.linalg.norm(t.V0 - J['shoulder_' + sd], axis=1)
        sh[sd] = chest * smoothstep((SHOULDER_R - d) / (SHOULDER_R * 0.6))
    # bones: hips, chest, left shoulder, right shoulder
    t.w = np.column_stack([1 - chest, chest - sh['l'] - sh['r'], sh['l'], sh['r']])
    out['torso'] = t
    for sd in ('l', 'r'):
        for part in ('thigh_', 'shin_'):
            g = Malla(m.IMG[part + sd], m.OFF[part + sd], step=10)
            y = g.V0[:, 1]
            hips = 1 - smoothstep((y - J['hip_' + sd][1] - HIP_BLEND[0]) / (HIP_BLEND[1] - HIP_BLEND[0]))
            shin = smoothstep((y - J['knee_' + sd][1] + KNEE_BLEND) / (2 * KNEE_BLEND))
            # bones: hips, thigh, shin
            g.w = np.column_stack([hips * (1 - shin), (1 - hips) * (1 - shin), shin])
            out[part + sd] = g
    MESH[c] = out
    return out


# ---------------------------------------------------------------- one kid
def kid(img, c, x, floor, S, p):
    """Like escena_rig.kid, with the meshes. p (all optional): tilt (hips, rad), bend (chest on the hips, rad),
    breath (-1..1), rise {'l','r'} (px of the drawing each shoulder goes up), head (rad, on the chest), dx, drop,
    lift, air, arms {'l'|'r': (up, fore, hand, turn, where, upper length, forearm length)}, blink, talk.
    where: None, 'front' (in front of the face) or 'pecho' (forearm in front of the body)."""
    m = K[c]
    J = m.J
    ms = meshes(c)
    tilt, bend = p.get('tilt', 0.0), p.get('bend', 0.0)
    ankle_y = floor - (m.SOLE - J['ankle_l'][1]) * S
    hip_y = ankle_y - (J['ankle_l'][1] - J['pelvis'][1]) * S + p.get('drop', 0) * S
    cx = x + p.get('dx', 0) * S
    Mt = T(cx, hip_y) @ Rm(tilt) @ Sc(S) @ T(*-J['pelvis'])
    br = p.get('breath', 0.0)
    sp = np.array([J['pelvis'][0], SPINE_Y])
    Mc = Mt @ T(*sp) @ Rm(bend) @ Sc(1 + 0.006 * br, 1 + 0.004 * br) @ T(*-sp)
    rise = p.get('rise', {'l': 0.0, 'r': 0.0})
    Msh = {sd: Mc @ T(0, -rise[sd]) for sd in ('l', 'r')}
    Mh = Mc @ T(*J['neck']) @ Rm(p.get('head', 0)) @ T(*-J['neck'])
    chest = tilt + bend
    # shadow
    sw, shh = 330 * S, 40 * S
    if 0 < floor < H + 200:
        from PIL import ImageDraw, ImageFilter
        box = (int(cx - sw), int(floor - shh), int(cx + sw), int(floor + shh))
        sm = Image.new('L', (box[2] - box[0], box[3] - box[1]))
        ImageDraw.Draw(sm).ellipse((sw / 2, shh / 2, sw * 1.5, shh * 1.5), fill=int(60 * (1 - p.get('air', 0) / 700)))
        sm = sm.filter(ImageFilter.GaussianBlur(10 * S))
        img.paste(Image.new('RGBA', sm.size, (120, 95, 70, 255)), box[:2], sm)
    air = p.get('air', 0)
    legs = {}
    for sd in ('l', 'r'):
        A0 = J['ankle_' + sd]
        A = np.array([x + (A0[0] - J['pelvis'][0]) * S, ankle_y - air * S])      # the feet stay where they are
        legs[sd] = m.leg(sd, Mt, A, S, p.get('lift', 0))
    for sd in ('l', 'r'):
        m.draw(img, 'foot_' + sd, legs[sd][2])
    for part in ('shin_', 'thigh_'):
        for sd in ('l', 'r'):
            g = ms[part + sd]
            g.draw(img, g.skin(g.w, [Mt, legs[sd][0], legs[sd][1]]))
    arms, joins = {}, {}
    for sd in ('l', 'r'):
        a = (list(p['arms'][sd]) + [None, None, 1.0, 1.0])[:7]
        up, fore, hand, rot, where, ru, rf = a
        rot = rot or 0.0
        sgn = 1 if sd == 'l' else -1
        th_u = math.radians(90 + sgn * up) + chest
        th_f = math.radians(90 + sgn * fore) + chest
        du = np.array([math.cos(th_u), math.sin(th_u)])
        df = np.array([math.cos(th_f), math.sin(th_f)])
        # the sleeve's top goes up half as much as the hoodie's shoulder, or its round cap shows above it
        Sw = ap(Mc @ T(0, -0.5 * rise[sd]), J['shoulder_' + sd]) - np.array([0, m.SHOULDER_RISE * S * min(max((up - 60) / 90, 0), 1)])
        Ew = Sw + du * np.linalg.norm(J['elbow_' + sd] - J['shoulder_' + sd]) * S * (ru or 1.0)
        Ww = Ew + df * np.linalg.norm(J['wrist_' + sd] - J['elbow_' + sd]) * S * (rf or 1.0)
        h = m.HANDS[f'{hand.rstrip("~")}_{sd}']
        into = m.SLEEVES['l']['cuff'] - 8
        Mhd = T(*(Ww + into * S * df)) @ Rm(th_f - math.radians(h['dir']) + sgn * math.radians(rot)) @ Sc(S)
        if hand.endswith('~'):
            Mhd = Mhd @ m.mirror(h['dir'])
        Mhd = Mhd @ T(*[-v for v in h['wrist']])
        first = wrist_info(m, c, hand, sd)[4]
        Mhd = T(*(df * min(14 - SINK - first, 0) * S)) @ Mhd
        th_s = th_u - m.SHOULDER_FOLLOW * (th_u - (math.pi / 2 + chest))
        t_sh = np.array([math.cos(th_s), math.sin(th_s)])
        arms[sd] = (hand, Mhd, sleeve(m, sd, Sw, Ew, Ww, t_sh, S), where)
        Ph = ap(Mhd, h['wrist'])
        tip = ap(Mhd, np.array(h['wrist']) + 10 * np.array([math.cos(math.radians(h['dir'])), math.sin(math.radians(h['dir']))]))
        joins[sd] = (Ww, Ph, (tip - Ph) / max(np.linalg.norm(tip - Ph), 1e-6), wrist_info(m, c, hand, sd))

    def hand_layer(sd):
        hand, Mhd, sl, where = arms[sd]
        hl = Image.new('RGBA', (W, H))
        wrist_join(hl, *joins[sd], S)
        m.draw(hl, f'hand_{hand.rstrip("~")}_{sd}', Mhd)
        return hl

    for sd, (hand, Mhd, sl, where) in arms.items():
        if where not in ('front', 'pecho'):
            hl = hand_layer(sd)
            img.alpha_composite(hl)
            paste_sleeve(img, sl)
            over_opening(img, hl, sl, m, sd)
        elif where == 'pecho':                  # the shoulder end of the sleeve still goes under the hoodie
            paste_sleeve(img, sl)
    torso = Image.new('RGBA', (W, H))
    t = ms['torso']
    t.draw(torso, t.skin(t.w, [Mt, Mc, Msh['l'], Msh['r']]))
    img.alpha_composite(torso)
    tmask = np.asarray(torso)[..., 3].astype(float)
    for sd, (hand, Mhd, sl, where) in arms.items():
        if where != 'front':
            paste_sleeve(img, sl, fade=m.SHOULDER_FADE, mask=tmask)
    shoulder_fill(img, c, tmask, [a[2] for a in arms.values()],
                  [ap(Msh[s], J['shoulder_' + s]) for s in ('l', 'r')], S)
    for sd, (hand, Mhd, sl, where) in arms.items():
        if where == 'pecho':                    # forearm and hand in front of the body, under the face
            g = m.SLEEVES[sd]
            hl = hand_layer(sd)
            img.alpha_composite(hl)
            paste_sleeve(img, sl, fade=(g['upper'] * 0.35, g['upper'] * 0.75))
            over_opening(img, hl, sl, m, sd)
    m.draw(img, 'head', Mh)
    mouth(img, c, Mh, p.get('talk', 0))
    if p.get('blink'):
        m.draw(img, 'blink', Mh)
    for sd, (hand, Mhd, sl, where) in arms.items():
        if where == 'front':
            img.alpha_composite(hand_layer(sd))
            paste_sleeve(img, sl)
            paste_sleeve(img, sl, fade=m.SHOULDER_FADE, mask=tmask)
    return Mh


# ---------------------------------------------------------------- real gestures -> the kid
def spring(x, fps=30, freq=2.2, damp=0.55):
    """The value follows x like a mass on a spring (a little late, a little overshoot): overlapping action."""
    w = 2 * math.pi * freq
    y, v, out = float(x[0]), 0.0, np.zeros(len(x))
    dt = 1 / fps
    for i, target in enumerate(x):
        for _ in range(4):
            a = w * w * (target - y) - 2 * damp * w * v
            v += a * dt / 4
            y += v * dt / 4
        out[i] = y
    return out


def _ang(v):
    """Angle in the frame (y down) of a body vector given with y up."""
    return math.atan2(-v[1], v[0])


def retarget(X, c='e', fps=30):
    """A gesto (frames x joints x 3, tools/gestos.py) -> the kid's p for every frame. Only angles are copied, so the
    adult of the recording becomes a kid with his own proportions. The person's left arm is the one on the right of
    the screen (the kids face the camera)."""
    from gestos import NAMES
    i = {n: k for k, n in enumerate(NAMES)}
    J = K[c].J
    n = len(X)
    q = lambda name: X[:, i[name]]
    pel = (q('hip_l') + q('hip_r')) / 2
    neck = q('neck')
    px_m = (J['ankle_l'][1] - J['neck'][1]) / np.median(neck[:, 1] - (q('ankle_l')[:, 1] + q('ankle_r')[:, 1]) / 2)
    spine = np.array([_ang(v) + math.pi / 2 for v in neck - pel])          # 0 = upright, + = top to the right
    shl = np.array([_ang(v) for v in q('shoulder_l') - q('shoulder_r')])
    hipl = np.array([_ang(v) for v in q('hip_l') - q('hip_r')])
    tilt = np.clip(hipl * 0.6, -0.12, 0.12)
    chest = np.clip(0.6 * spine + 0.4 * shl, -0.3, 0.3)
    bend = spring(chest - tilt, fps, 3.0, 0.6)
    headv = q('head') - neck
    head_abs = np.array([_ang(v) + math.pi / 2 for v in headv])
    head = spring(np.clip((head_abs - chest) * 0.8, -0.18, 0.18), fps, 2.4, 0.5)     # the head comes a bit late
    head += 0.25 * (bend - spring(bend, fps, 1.5, 0.7))                          # and swings a little with the chest
    rise = {}
    for sd, person in (('l', 'r'), ('r', 'l')):
        h = q('shoulder_' + person)[:, 1] - neck[:, 1]
        rise[sd] = np.clip((h - np.median(h)) * px_m * 1.2, -4, 16)
    dx = np.clip((pel[:, 0] - (q('ankle_l')[:, 0] + q('ankle_r')[:, 0]) / 2) * px_m * 0.5, -22, 22)
    dx -= np.median(dx)
    breath = np.sin(np.arange(n) / fps * 2 * math.pi / 3.2)
    arms = {}
    for sd, person in (('l', 'r'), ('r', 'l')):
        sgn = 1 if sd == 'l' else -1
        Sh, El, Wr = q('shoulder_' + person), q('elbow_' + person), q('wrist_' + person)
        u, v = El - Sh, Wr - El
        cdeg = np.degrees(tilt + bend)
        up = sgn * (np.degrees([_ang(x) for x in u]) - 90 - cdeg)
        fore = sgn * (np.degrees([_ang(x) for x in v]) - 90 - cdeg)
        # continuous in time (no jump of 360 degrees from one frame to the next), the elbow bend within half a turn
        up = np.degrees(np.unwrap(np.radians(up)))
        up -= 360 * np.round(np.median(up) / 360)
        ru = np.linalg.norm(u[:, :2], axis=1) / np.maximum(np.linalg.norm(u, axis=1), 1e-6)
        rf = np.linalg.norm(v[:, :2], axis=1) / np.maximum(np.linalg.norm(v, axis=1), 1e-6)
        # a forearm pointing at the camera looks very short and its direction on screen is noise: there it follows
        # the recording slowly, so the arm doesn't whip round
        # continuous in time, then followed slowly where the forearm looks short
        bendl = np.degrees(np.unwrap(np.radians(fore - up)))
        bendl -= 360 * np.round(np.median(bendl) / 360)
        b = np.zeros(n)
        b[0] = bendl[0]
        for f in range(1, n):
            g = float(np.clip((rf[f] - 0.25) / 0.35, 0.08, 1.0))
            b[f] = b[f - 1] + float(np.clip(g * (bendl[f] - b[f - 1]), -24, 24))     # never faster than 24 deg/frame
        from scipy.ndimage import gaussian_filter1d
        b = gaussian_filter1d(b, 1.5, mode='nearest')
        fore = up + b
        ru, rf = np.maximum(ru, 0.6), np.maximum(rf, 0.55)
        # the hand: open (palm to the camera) when the arm does something, relaxed when it hangs; and the forearm in
        # front of the body when the hand comes towards the camera. Both with a margin and a minimum time, so they
        # don't flicker
        busy = np.maximum(up, fore - 20) + 90 * (1 - rf)
        hand = _hold(busy, 48, 32)
        dz = Wr[:, 2] - Sh[:, 2]
        front = _hold(np.where(np.abs(fore) < 150, dz, -1), 0.18, 0.12)
        arms[sd] = [(float(up[f]), float(fore[f]), 'abierta~' if hand[f] else 'pose', 0.0,
                     'pecho' if front[f] else None, float(ru[f]), float(rf[f])) for f in range(n)]
    frames = []
    for f in range(n):
        frames.append({'arms': {sd: arms[sd][f] for sd in arms}, 'tilt': float(tilt[f]), 'bend': float(bend[f]),
                       'head': float(head[f]), 'rise': {'l': float(rise['l'][f]), 'r': float(rise['r'][f])},
                       'dx': float(dx[f]), 'breath': float(breath[f])})
    return frames


def _hold(x, on, off, frames=8):
    """True/False from x with a margin (on above `on`, off below `off`) and at least `frames` frames each time."""
    out, state, since = np.zeros(len(x), bool), False, frames
    for i, v in enumerate(x):
        since += 1
        if since >= frames and ((not state and v > on) or (state and v < off)):
            state, since = not state, 0
        out[i] = state
    return out


def blend(clips, fade=0.4, fps=30):
    """Joins gestos one after the other, each (X, start second): over fade seconds the body goes from one to the
    next (the positions are mixed, so the arms travel, they don't jump)."""
    end = max(s + len(X) / fps for X, s in clips)
    n = int(end * fps)
    out = None
    for X, s in clips:
        a = int(s * fps)
        Y = np.concatenate([X, np.repeat(X[-1:], max(n - a - len(X), 0), 0)])[:n - a]
        if out is None:
            out = np.concatenate([np.repeat(Y[:1], a, 0), Y])
            continue
        w = smoothstep((np.arange(n - a) / fps) / fade)[:, None, None]
        out[a:] = out[a:] * (1 - w) + Y * w
    return out
