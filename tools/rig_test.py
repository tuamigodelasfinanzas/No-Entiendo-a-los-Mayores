"""Rig test: E walks towards the camera and jumps twice, moved only by the skeleton of tools/split_parts.py.
Usage: python3 tools/rig_test.py out.mp4 [--debug]      (--debug draws the joints)

The legs use two-bone IK: the hip comes from the torso, the ankle from the floor (or the air), and the knee bends
outwards, like a child seen from the front. A leg that lifts towards the camera gets shorter on screen (the thigh
takes most of it) instead of bending sideways. The head is the original drawing, only moved and turned."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'assets/characters/e/parts')
W, H, FPS = 1080, 1920, 30
DUR = 9.0

meta = json.load(open(os.path.join(PARTS, 'parts.json')))
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


def pose(t):
    """Everything that moves, as numbers, at time t."""
    p = {'tilt': 0.0, 'head': 0.0, 'lift': [0.0, 0.0], 'air': [0.0, 0.0], 'drop': 0.0, 'dx': 0.0, 'blink': False,
         'spread': 0.0}
    # walk towards the camera: 0 .. 4.2 s, steps of 0.5 s
    walk_end = 4.2
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
    # two jumps
    for j0 in (4.9, 7.0):
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
    draw(img, 'torso', Mt)
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
