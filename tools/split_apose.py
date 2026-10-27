"""E's rig from Chiño's "pose A" drawing (arms hanging straight, away from the body), with his original head on top.
Usage: python3 tools/split_apose.py      -> assets/characters/e/rig/<piece>.png + rig.json

Sources (assets/characters/source):
  e-pose-a-x4.png   front panel of e-pose-a.png, 4x with Real-ESRGAN (x4plus), placed on the 896x1200 frame of
                    e-full.jpg (same chin and feet), so the head of the original drawing sits on it as it is;
  e-manos-x4.png    the hand sheet of e-pose-a.png, 4x: top row = the hand on the left of the screen (E's right),
                    bottom row = the other one.
The face is never redrawn: head.png / blink.png / jaw.png of assets/characters/e are used untouched.

Pieces, back to front: foot_l/r, shin_l/r, thigh_l/r, torso, arm + hand per side, head.
Every joint is a round end (see capsule()), so a segment can turn without opening a gap."""
import json, math, os
import numpy as np
from PIL import Image, ImageFilter

from split_parts import soft, flood, harmonic, polymask, grow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets/characters/source')
E = os.path.join(ROOT, 'assets/characters/e')
OUT = os.path.join(E, 'rig')
W, H = 896, 1200
SCALE, DX, DY = 0.31, 142, 87          # x4 image -> 896x1200 frame (chin ~444, soles 1166, centre 452)
HOODIE_LINE = np.array([110, 18, 22.0])
DENIM_LINE = np.array([22, 34, 58.0])

JOINTS = {
    'neck': [458, 446], 'pelvis': [452, 790],
    'shoulder_l': [338, 505], 'elbow_l': [292, 618], 'wrist_l': [255, 732],
    'shoulder_r': [566, 505], 'elbow_r': [612, 618], 'wrist_r': [655, 732],
    'hip_l': [395, 790], 'knee_l': [368, 925], 'ankle_l': [343, 1058],
    'hip_r': [510, 790], 'knee_r': [522, 925], 'ankle_r': [537, 1058],
}
# each sleeve, cuff included, up to the seam with the body (hand not included)
ARM = {
    'l': [(347, 440), (330, 470), (300, 530), (268, 600), (245, 660), (226, 705), (222, 740), (262, 746),
          (292, 738), (318, 705), (340, 662), (352, 630), (352, 560), (356, 500)],
    'r': [(555, 440), (575, 470), (604, 530), (636, 600), (660, 660), (680, 705), (686, 740), (645, 746),
          (612, 738), (586, 705), (563, 662), (552, 630), (552, 560), (548, 500)],
}
HAND_BOX = {'l': (205, 725, 285, 845), 'r': (620, 725, 700, 845)}
CROTCH = 452
ELBOW_R = 44                           # half the sleeve's width at the elbow
NECK_CUT = 440                         # the pose-A head goes, the original one goes on top

# hand sheet: cells in e-pose-a.png coordinates (the x4 sheet starts at (10, 920))
HAND_COLS = [(14, 170), (184, 343), (356, 505), (519, 663), (676, 853), (866, 1010)]
HAND_ROWS = {'l': (926, 1178), 'r': (1199, 1453)}
HAND_NAMES = ['abierta', 'dorso', 'puno', 'pulgar', 'senala', 'relajada']
# where each hand meets its cuff (as a fraction of the cell) and the direction wrist -> hand, in degrees (y down)
HAND_WRIST = {
    'l': {'abierta': (0.42, 0.74, -90), 'dorso': (0.47, 0.75, -90), 'puno': (0.45, 0.72, -90),
          'pulgar': (0.22, 0.68, -32), 'senala': (0.12, 0.62, -24), 'relajada': (0.5, 0.38, 90)},
    'r': {'abierta': (0.48, 0.74, -90), 'dorso': (0.47, 0.74, -90), 'puno': (0.55, 0.72, -90),
          'pulgar': (0.72, 0.70, -129), 'senala': (0.85, 0.55, -149), 'relajada': (0.5, 0.38, 90)},
}
HAND_SIZE = {'abierta': 1.15, 'dorso': 1.15, 'puno': 0.75, 'pulgar': 0.85, 'senala': 0.85}   # vs the relaxed hand
POSE_HAND_AREA = 0.0


def cutout(rgb):
    mn, mx = rgb.min(axis=2), rgb.max(axis=2)
    light = (mn > 228) & (mx - mn < 20)
    h, w = mn.shape
    bg = flood(light, [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (5, h // 2), (w - 6, h // 2)])
    a = Image.fromarray(((~bg) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    return np.asarray(a) / 255.0


def capsule(rgb, alpha, core, ends, line, within=None):
    """A segment: the drawing inside core, plus a round end at each joint (ring = squared distance to the joint,
    radius). Inside the drawing the round end is the drawing itself (the neighbouring segment's pixels, which
    continue it); outside, it is filled from the segment and outlined, so a bent joint stays closed."""
    disks = np.zeros_like(core)
    if not ends:
        return rgb, soft(core, 0.7) * alpha
    for ring, rad in ends:
        disks |= ring <= rad ** 2
    if within is not None:
        disks &= within
    own = (core | disks) & (alpha > 0.5)
    hole = disks & ~own
    rim = hole & grow(~disks, 3)
    ys, xs = np.where(disks | core)
    sl = (slice(max(ys.min() - 3, 0), ys.max() + 4), slice(max(xs.min() - 3, 0), xs.max() + 4))
    fill = rgb.copy()
    fill[sl] = harmonic(rgb[sl], hole[sl], own[sl], iters=400)
    k = soft(rim, 0.7)[..., None] * 0.9
    fill = fill * (1 - k) + line * k
    oa = soft(core | disks, 0.7) * np.where(own, alpha, 1.0)
    return fill, oa


def hands(meta):
    """Each hand of the sheet without its cuff, about the size of the drawing's own hand, with its wrist point and
    direction (HAND_WRIST, measured on the sheet)."""
    sheet = np.asarray(Image.open(os.path.join(SRC, 'e-manos-x4.png')).convert('RGB')).astype(np.float64)
    meta['hands'] = {}
    target = POSE_HAND_AREA             # skin area of the drawing's own hand: every hand gets about that size
    for side, (y0, y1) in HAND_ROWS.items():
        for name, (x0, x1) in zip(HAND_NAMES, HAND_COLS):
            c = sheet[(y0 - 920) * 4 + 12:(y1 - 920) * 4 - 12, (x0 - 10) * 4 + 12:(x1 - 10) * 4 - 12]
            a = cutout(c)
            r, g, b = c[..., 0], c[..., 1], c[..., 2]
            skin = (a > 0.5) & (r > 170) & (g > 105) & (b > 60) & (r - b > 40) & (g - b > 10)
            skin = flood(skin, [tuple(np.argwhere(skin)[len(np.argwhere(skin)) // 2][::-1])]) if skin.any() else skin
            fx, fy, d = HAND_WRIST[side][name]
            wx, wy = fx * c.shape[1], fy * c.shape[0]
            k = math.sqrt(target * HAND_SIZE.get(name, 1.0) / skin.sum())
            # only the hand: the sheet's cuff goes, the hand slides into E's own cuff
            a = a * soft(grow(skin, 1), 0.6)
            img = Image.fromarray(np.dstack([c, a * 255]).astype(np.uint8), 'RGBA')
            img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
            n = f'hand_{name}_{side}'
            img.save(os.path.join(OUT, n + '.png'), optimize=True)
            meta['pieces'][n] = {'x': 0, 'y': 0}
            meta['hands'][f'{name}_{side}'] = {'wrist': [wx * k, wy * k], 'dir': d}


def main():
    big = Image.open(os.path.join(SRC, 'e-pose-a-x4.png')).convert('RGB')
    sm = big.resize((round(big.width * SCALE), round(big.height * SCALE)), Image.LANCZOS)
    frame = Image.new('RGB', (W, H), (255, 255, 255))
    frame.paste(sm, (DX, DY))
    rgb = np.asarray(frame).astype(np.float64)
    alpha = cutout(rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    alpha = alpha * soft(yy >= NECK_CUT, 1.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2)
    J = {k: np.array(v, float) for k, v in JOINTS.items()}
    os.makedirs(OUT, exist_ok=True)
    pieces = {}
    meta = {'w': W, 'h': H, 'joints': JOINTS, 'pieces': {}}

    def ring(j):
        return (xx - J[j][0]) ** 2 + (yy - J[j][1]) ** 2

    def along(a, bb):
        """0 at joint a, 1 at joint bb, measured along the bone."""
        v = J[bb] - J[a]
        return ((xx - J[a][0]) * v[0] + (yy - J[a][1]) * v[1]) / (v @ v)

    # arms
    armmask = {}
    for side in ('l', 'r'):
        poly = polymask(ARM[side], W, H)
        armmask[side] = poly
        # one piece from the shoulder to the cuff (the hoodie's sleeve is too wide and soft to split at the elbow
        # without the cut showing): the sleeve's pixels around the bone, as wide as the sleeve, so the wedge of the
        # body under the armpit stays with the torso. Its top is round and the torso keeps a round shoulder under it
        S0, W0 = J['shoulder_' + side], J['wrist_' + side]
        v = W0 - S0
        t = np.clip(((xx - S0[0]) * v[0] + (yy - S0[1]) * v[1]) / (v @ v), 0, 1)
        d = np.hypot(xx - (S0[0] + t * v[0]), yy - (S0[1] + t * v[1]))
        rad = 30 + 16 * np.sin(np.pi * np.clip(t * 1.4, 0, 1))      # 30 at the shoulder, 46 from mid arm down
        sleeve = poly & (alpha > 0.5) & (d <= rad)
        inner = sleeve & grow(poly & (alpha > 0.5) & ~sleeve, 2)     # the cut against the body gets the outline
        k = soft(inner, 0.6)[..., None] * 0.9
        pieces['arm_' + side] = (rgb * (1 - k) + HOODIE_LINE * k, soft(sleeve, 0.7) * alpha)

    # torso: no sleeves (but a round shoulder under the arm), down to a V through the crotch
    vline = 812 - np.abs(xx - CROTCH) * 0.30
    keep = (yy < vline) & ~HAND_ZONE(xx, yy) & ~((yy > 560) & ((xx < 342) | (xx > 562)))
    for side in ('l', 'r'):
        keep &= ~(armmask[side] & (ring('shoulder_' + side) > 34 ** 2))
    ta = alpha * soft(keep, 0.8)
    cut = grow(~keep, 2) & keep & (alpha > 0.5) & (yy < 760) & (yy > 470)
    k = soft(cut, 0.6)[..., None] * 0.85
    pieces['torso'] = (rgb * (1 - k) + HOODIE_LINE * k, ta)

    # legs
    denim = ((b > r + 8) & (mx < 170)) | ((mx < 80) & (b > r + 4))
    pants = flood(denim & (yy >= 1000) & (yy < 1095), [(345, 1020), (530, 1020), (330, 1040), (545, 1040)])
    pants |= (yy < 1000)
    for side in ('l', 'r'):
        sel = (xx < CROTCH) if side == 'l' else (xx >= CROTCH)
        leg = sel & (alpha > 0.5) & (yy >= 760) & ~HAND_ZONE(xx, yy) & ~grow(armmask['l'] | armmask['r'], 3)
        leg &= (xx > 280) & (xx < 625)
        t = along('hip_' + side, 'knee_' + side)
        s2 = along('knee_' + side, 'ankle_' + side)
        thigh = leg & (t < 1) & pants
        shin = leg & (t >= 1) & pants
        pieces['thigh_' + side] = capsule(rgb, alpha, thigh, [(ring('knee_' + side), 40)], DENIM_LINE)
        pieces['shin_' + side] = capsule(rgb, alpha, shin, [(ring('knee_' + side), 40)], DENIM_LINE)
        shoe = sel & (alpha > 0.5) & ~pants & (yy > 1030)
        # under the cuff: the top of the sneaker, filled from the leather around it
        under = sel & pants & (yy > 1040) & (yy < 1100) & grow(shoe, 14)
        ys, xs = np.where(shoe | under)
        sl = (slice(ys.min() - 2, ys.max() + 3), slice(xs.min() - 2, xs.max() + 3))
        fill = rgb.copy()
        fill[sl] = harmonic(rgb[sl], under[sl], (shoe & (mx > 190))[sl], iters=500)
        pieces['foot_' + side] = (fill, soft(shoe | under, 0.7) * np.where(under, 1.0, alpha))
        del s2

    # the hand of the drawing itself (relaxed, hanging)
    global POSE_HAND_AREA
    x0, y0, x1, y1 = HAND_BOX['l']
    POSE_HAND_AREA = float(((alpha[y0:y1, x0:x1] > 0.5) & ~armmask['l'][y0:y1, x0:x1]).sum())
    for side in ('l', 'r'):
        x0, y0, x1, y1 = HAND_BOX[side]
        box = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1) & ~armmask[side]
        pieces['hand_pose_' + side] = (rgb, alpha * soft(box & (alpha > 0.05), 0.6))

    for name, (prgb, pa) in pieces.items():
        a8 = (pa * 255).clip(0, 255).astype(np.uint8)
        img = np.dstack([prgb.clip(0, 255).astype(np.uint8), a8])
        img[a8 == 0] = 0
        ys, xs = np.where(a8 > 0)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        Image.fromarray(img[y0:y1, x0:x1], 'RGBA').save(os.path.join(OUT, name + '.png'), optimize=True)
        meta['pieces'][name] = {'x': int(x0), 'y': int(y0)}
    hands(meta)
    for side in ('l', 'r'):
        # the drawing's own hand works like the sheet ones: local wrist, and the forearm's direction
        p = meta['pieces']['hand_pose_' + side]
        wx, wy = JOINTS['wrist_' + side]
        ex, ey = JOINTS['elbow_' + side]
        meta['hands']['pose_' + side] = {'wrist': [wx - p['x'], wy - p['y']], 'dir': math.degrees(math.atan2(wy - ey, wx - ex))}
        meta['pieces']['hand_pose_' + side] = {'x': 0, 'y': 0}
    for name in ('head', 'blink', 'jaw'):
        im = Image.open(os.path.join(E, name + '.png'))
        x0, y0, x1, y1 = im.getbbox()
        im.crop((x0, y0, x1, y1)).save(os.path.join(OUT, name + '.png'), optimize=True)
        meta['pieces'][name] = {'x': x0, 'y': y0}
    json.dump(meta, open(os.path.join(OUT, 'rig.json'), 'w'), indent=1)
    print('pieces:', ', '.join(sorted(meta['pieces'])))


def HAND_ZONE(xx, yy):
    """The two hanging hands of the drawing (they are pieces of their own)."""
    z = np.zeros(xx.shape, bool)
    for x0, y0, x1, y1 in HAND_BOX.values():
        z |= (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    return z


if __name__ == '__main__':
    main()
