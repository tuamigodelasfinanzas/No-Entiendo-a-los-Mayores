"""Cuts E's body (assets/characters/e/body.png, made by tools/prepare_characters.py) into the pieces of a skeleton,
so he can walk and jump instead of only switching poses.
Usage: python3 tools/split_parts.py      -> assets/characters/e/parts/<piece>.png + parts.json

Pieces (draw order, back to front): foot_l, foot_r, shin_l, shin_r, thigh_l, thigh_r, torso, head (+ blink, jaw).
  - torso:  hoodie, arms with the hands in the pockets, and the jeans down to a V line through the crotch;
  - torso_libre: the same without the arms (the side of the hoodie gets its outline, the pockets are filled), for
            upperarm + forearm (the sleeves of the drawing, split at the elbow crease) and a hand;
  - hand_<kind>_<side>: the hands of the MANOS row of the character sheet (open, fist, thumb up, pointing, relaxed),
            the right side is the mirror of the left;
  - thigh:  hip to knee; its top goes on under the torso, so the hip never opens a gap;
  - shin:   knee to the cuff; its top is rounded and goes on under the thigh, and a knee disk of the same denim sits behind it so the
            joint stays closed when the knee bends;
  - foot:   the sneaker; the part hidden under the cuff is filled from the shoe around it.
  - head:   assets/characters/e/head.png untouched (Chiño's rule: the face is his drawing, never redrawn or stretched).
Every piece keeps the 896x1200 coordinates of the drawing; parts.json has each piece's crop offset and its joints."""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets/characters/e')
OUT = os.path.join(SRC, 'parts')

# joints measured on the 896x1200 drawing (x, y)
CROTCH = 450
JOINTS = {
    'neck': [458, 446],
    'pelvis': [450, 812],
    'hip_l': [385, 812], 'knee_l': [362, 946], 'ankle_l': [338, 1058],
    'hip_r': [512, 812], 'knee_r': [510, 946], 'ankle_r': [518, 1058],
    'shoulder_l': [320, 548], 'elbow_l': [302, 650], 'wrist_l': [338, 746],
    'shoulder_r': [588, 548], 'elbow_r': [597, 648], 'wrist_r': [564, 750],
}

# the arms in the drawing (hands in the pockets): outline of each sleeve, and the elbow crease that splits it
ARM = {
    'l': [(320, 492), (300, 535), (272, 600), (254, 645), (262, 700), (285, 738), (312, 756), (352, 748), (364, 712),
          (350, 655), (346, 600), (338, 555), (330, 512)],
    'r': [(566, 495), (598, 520), (616, 580), (638, 640), (636, 690), (618, 738), (586, 756), (548, 756), (545, 710),
          (550, 655), (554, 600), (558, 545)],
}
CREASE = {'l': ((254, 640), (350, 660)), 'r': ((552, 655), (640, 640))}
POCKET = {'l': (305, 735, 382, 798), 'r': (522, 735, 600, 798)}     # the hands in the pockets
SIDE = {'l': 364, 'r': 541}                                         # new side of the hoodie at the hem
HIP = {'l': [(364, 730), (364, 766), (352, 771), (342, 779), (334, 794), (331, 800), (382, 800), (382, 730)],
       'r': [(541, 730), (541, 766), (553, 771), (562, 779), (566, 794), (568, 800), (522, 800), (522, 730)]}
HEM = 766                                                           # bottom of the hoodie where the hands go in
HOODIE_LINE = np.array([92, 20, 22.0])

# hands from the MANOS row of the character sheet (E_data_sheet.jpg, 853x1280): box, wrist, and the direction
# wrist -> knuckles in degrees (image coords, y down). They are E's right hand (on the
# left of the screen); the other one is the mirror.
SHEET = 'source/e-sheet.jpg'
HANDS = {
    'abierta': {'box': (20, 701, 86, 775), 'wrist': (52, 768), 'dir': -90},
    'puno': {'box': (86, 711, 136, 765), 'wrist': (108, 761), 'dir': -90},
    'pulgar': {'box': (134, 703, 186, 766), 'wrist': (139, 752), 'dir': -20},
    'senala': {'box': (186, 709, 264, 765), 'wrist': (193, 752), 'dir': -22},
    'relajada': {'box': (260, 709, 324, 777), 'wrist': (306, 716), 'dir': 125},
}
HAND_SCALE = 1.55         # sheet hands -> the 896x1200 drawing


def soft(mask, r=1.0):
    m = Image.fromarray((mask * 255).astype(np.uint8))
    return np.asarray(m.filter(ImageFilter.GaussianBlur(r))) / 255.0


def flood(mask, seeds):
    """Pixels of mask connected to any seed (4-neighbour)."""
    m = Image.fromarray((mask * 255).astype(np.uint8)).copy()     # copy: floodfill ignores array-backed images
    for s in seeds:
        if m.getpixel(s) == 255:
            ImageDraw.floodfill(m, s, 128)
    return np.asarray(m) == 128


def harmonic(rgb, hole, known, iters=800):
    """Fills hole with the colours of known around it (each pixel the average of its neighbours until it settles)."""
    f = rgb.copy()
    f[hole] = rgb[known].mean(axis=0) if known.any() else 230
    for _ in range(iters):
        avg = (np.roll(f, 1, 0) + np.roll(f, -1, 0) + np.roll(f, 1, 1) + np.roll(f, -1, 1)) / 4
        f[hole] = avg[hole]
    return f


def polymask(pts, W, H):
    m = Image.new('L', (W, H))
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return np.asarray(m) > 0


def grow(mask, px):
    m = Image.fromarray((mask * 255).astype(np.uint8))
    return np.asarray(m.filter(ImageFilter.MaxFilter(2 * px + 1))) > 0


def cut_hands(out, meta):
    """Each hand of the sheet on its own, background out, plus its mirror for the other side."""
    sheet = Image.open(os.path.join(SRC, '..', SHEET)).convert('RGB')
    meta['hands'] = {}
    for name, h in HANDS.items():
        x0, y0, x1, y1 = h['box']
        crop = np.asarray(sheet.crop(h['box'])).astype(np.float64)
        mn, mx = crop.min(axis=2), crop.max(axis=2)
        light = (mn > 232) & (mx - mn < 14)
        bg = flood(light, [(0, 0), (crop.shape[1] - 1, 0), (0, crop.shape[0] - 1), (crop.shape[1] - 1, crop.shape[0] - 1)])
        al = np.asarray(Image.fromarray(((~bg) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
                        .filter(ImageFilter.GaussianBlur(0.7))).astype(np.float64)
        # only the hand: the biggest blob (drops bits of the neighbours that fall inside the box)
        img = Image.fromarray(np.dstack([crop, al]).astype(np.uint8), 'RGBA')
        img = img.resize((round(img.width * HAND_SCALE), round(img.height * HAND_SCALE)), Image.LANCZOS)
        wx, wy = (h['wrist'][0] - x0) * HAND_SCALE, (h['wrist'][1] - y0) * HAND_SCALE
        for side in ('l', 'r'):
            piece = img if side == 'l' else img.transpose(Image.FLIP_LEFT_RIGHT)
            px = wx if side == 'l' else piece.width - wx
            d = h['dir'] if side == 'l' else 180 - h['dir']
            piece.save(os.path.join(out, f'hand_{name}_{side}.png'), optimize=True)
            meta['pieces'][f'hand_{name}_{side}'] = {'x': 0, 'y': 0}
            meta['hands'][f'{name}_{side}'] = {'wrist': [px, wy], 'dir': d}


def capsule(rgb, core, ends):
    """A segment of sleeve: its pixels (core) plus a round end at each joint (ring: squared distance to the joint,
    radius). The round ends are filled from the sleeve around them and get the hoodie's outline on their rim."""
    disks = np.zeros_like(core)
    rims = np.zeros_like(core)
    for ring, rad in ends:
        disks |= ring <= rad ** 2
        rims |= (ring <= rad ** 2) & (ring >= (rad - 3) ** 2)
    ys, xs = np.where(disks | core)
    sl = (slice(ys.min() - 2, ys.max() + 3), slice(xs.min() - 2, xs.max() + 3))
    fill = rgb.copy()
    hole = disks & ~core
    fill[sl] = harmonic(rgb[sl], hole[sl], core[sl], iters=500)
    fill[rims & ~core] = HOODIE_LINE
    ca = soft(core, 0.7)
    out_rgb = rgb * ca[..., None] + fill * (1 - ca[..., None])
    return out_rgb, np.maximum(ca, soft(disks, 0.7))


def arms(rgb, alpha, torso_a, xx, yy):
    """Upper arm, forearm (with a shoulder and an elbow disk behind) and a torso without the arms."""
    H, W = alpha.shape
    pieces = {}
    trgb = rgb.copy()
    ta = torso_a.copy()
    sleeve = np.median(rgb[polymask(ARM['l'], W, H) & (alpha > 0.9) & (rgb[..., 0] > 150)], axis=0)
    jeans = np.median(rgb[(yy > 790) & (yy < 830) & (xx > 380) & (xx < 520) & (alpha > 0.9)], axis=0)
    for side in ('l', 'r'):
        poly = polymask(ARM[side], W, H)
        (cx0, cy0), (cx1, cy1) = CREASE[side]
        crease = cy0 + (xx - cx0) * (cy1 - cy0) / (cx1 - cx0)
        ex, ey = JOINTS['elbow_' + side]
        sx, sy = JOINTS['shoulder_' + side]
        polys = soft(poly, 0.8)
        sring = (xx - sx) ** 2 + (yy - sy) ** 2
        ering = (xx - ex) ** 2 + (yy - ey) ** 2
        # the cut side of the sleeve (inside the drawing) gets the hoodie's outline, like the outer side has
        inner = grow(~poly, 2) & poly & (alpha > 0.5) & ~grow(alpha < 0.3, 4)
        k = soft(inner, 0.6)[..., None] * 0.9
        lined = rgb * (1 - k) + HOODIE_LINE * k
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        skin_all = (r > 190) & (g > 120) & (b > 80) & (r - b > 50) & (g - b > 15) & (yy > 720)
        # each segment ends round at its joints (a disk as wide as the sleeve there), so nothing opens or pokes
        # out when the arm bends: the disk is filled from the sleeve itself and outlined where it shows
        up_core = poly & (alpha > 0.5) & (yy < crease)
        fa_core = poly & (alpha > 0.5) & (yy >= crease) & ~grow(skin_all, 1)
        pieces['upperarm_' + side] = capsule(lined, up_core, [(sring, 24), (ering, 42)])
        pieces['forearm_' + side] = capsule(lined, fa_core, [(ering, 42)])
        # torso: the sleeve out but a round shoulder (it stays, under the arm); the new side gets the outline.
        # 3 px more than the sleeve, so no light rim of the old arm is left around the hoodie
        removed = grow(poly, 3) & (sring > 50 ** 2) & (yy > JOINTS['shoulder_' + side][1] - 10)
        ta = ta * (1 - soft(removed, 0.8))
        edge = grow(removed, 3) & ~removed & (ta > 0.5)
        ek = soft(edge, 0.7)[..., None] * 0.85
        trgb = trgb * (1 - ek) + HOODIE_LINE * ek
        # the hand in the pocket: hoodie above the hem, denim below
        x0, y0, x1, y1 = POCKET[side]
        box = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        skin = box & (r > 190) & (g > 120) & (b > 80) & (r - b > 50) & (g - b > 15)
        hole = grow(skin, 3) & box & (alpha > 0.1)
        above = yy < HEM
        # above the hem only what is inside the hoodie's new side; below it the jeans of the hip
        inside = (xx >= SIDE[side]) if side == 'l' else (xx <= SIDE[side])
        jeans_in = (xx >= 331) if side == 'l' else (xx <= 568)
        hole = hole & ((above & inside) | (~above & jeans_in))
        # the cuff and the hand outside the hoodie and the jeans: nothing there now
        gone = box & ((above & ~inside) | (~above & ~jeans_in))
        ta = ta * (1 - soft(gone, 0.6))
        for part, base in ((above, sleeve), (~above, jeans)):
            src = trgb.copy()
            src[~part & box] = base
            sl = (slice(y0 - 4, y1 + 4), slice(x0 - 4, x1 + 4))
            filled = harmonic(src[sl], (hole & part)[sl], (~hole & part & box & (alpha > 0.9))[sl], iters=600)
            trgb[sl][(hole & part)[sl]] = filled[(hole & part)[sl]]
        # hem line and pocket line where the hand was
        ta = np.maximum(ta, soft(hole, 0.6))
        # the new hip: the hoodie side runs into the jeans, which widen to the hip; outlined like the drawing
        keep = polymask(HIP[side], W, H) | ~box
        ta = ta * soft(keep, 0.7)
        rim = box & keep & grow(~keep, 2) & (yy < y1 - 2)
        k = soft(rim, 0.6)[..., None] * 0.9
        line = np.where((yy < HEM)[..., None], HOODIE_LINE, np.array([27, 42, 61.0]))
        trgb = trgb * (1 - k) + line * k
    pieces['torso_libre'] = (trgb, ta)
    return pieces


def main():
    body = np.asarray(Image.open(os.path.join(SRC, 'body.png'))).astype(np.float64)
    rgb, alpha = body[..., :3], body[..., 3] / 255.0
    H, W = alpha.shape
    yy, xx = np.mgrid[0:H, 0:W]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2)

    # V line through the crotch: the torso ends here, following the creases of the jeans
    vline = 842 - np.abs(xx - CROTCH) * 0.30
    torso = soft(yy < vline, 1.2)

    # denim below the knees: navy fabric and its navy outline, connected to the leg (shoe lines are grey, not navy)
    denim = ((b > r + 8) & (mx < 165)) | ((mx < 80) & (b > r + 4))
    pants = flood(denim & (yy >= 1000), [(340, 1020), (515, 1020), (350, 1030), (510, 1030)])
    pants |= (yy < 1035)
    pants_s = soft(pants, 0.8)

    pieces = {}
    for side, sel in (('l', xx < CROTCH), ('r', xx >= CROTCH)):
        side_m = soft(sel, 0.8)
        kx, ky = JOINTS['knee_' + side]
        # thigh: from under the torso to a knee crease that bows down a little in the middle
        knee_cut = ky + 6 - 6 * ((xx - kx) / 50.0) ** 2
        thigh = soft((yy >= 790) & (yy < knee_cut), 1.0) * side_m
        # shin: from under the thigh down to the cuff
        foot_sel = (yy >= 1035) & sel
        foot = soft(foot_sel, 0.8) * (1 - pants_s)
        pieces['thigh_' + side] = (rgb, alpha * thigh)
        # knee disk behind the shin: denim colour of the knee, with the navy outline, half a leg wide
        span = np.where((alpha[ky] > 0.5) & sel[ky])[0]
        rad = (span.max() - span.min()) / 2 - 2
        ring = (xx - kx) ** 2 + (yy - ky) ** 2
        disk = ring <= rad ** 2
        # shin: from the knee down to the cuff; above the knee only the round of the disk, so no corner pokes out
        shin = soft((yy >= ky) | (ring <= (rad - 2) ** 2), 1.0) * side_m * pants_s
        jeans = np.median(rgb[(yy > ky - 30) & (yy < ky + 30) & sel & (alpha > 0.9) & denim & (mx > 70)], axis=0)
        line = np.array([27, 42, 61.0])
        disk_rgb = np.where((ring >= (rad - 3) ** 2)[..., None], line, jeans)
        sa = alpha * shin
        shin_rgb = rgb * sa[..., None] + disk_rgb * (1 - sa[..., None])
        shin_a = np.maximum(sa, soft(disk, 0.8))
        pieces['shin_' + side] = (shin_rgb, shin_a)
        # foot: the sneaker, plus the part under the cuff filled from the leather around it
        shoe = (alpha > 0.5) & foot_sel & ~pants
        shoe_rows = np.where(shoe.any(axis=1))[0]
        hidden = np.zeros_like(shoe)
        cols = np.where(shoe.any(axis=0))[0]
        for x in cols:
            ys = np.where(shoe[:, x])[0]
            # under the cuff: from the top of the shoe at the sides up to the cuff line
            hidden[ys.min() - 1::-1, x] = False
        # region inside the shoe outline that the cuff covers: between the shoe's left and right edges, below 1045
        for y in range(1045, shoe_rows.max()):
            xs = np.where(shoe[y])[0]
            if len(xs):
                hidden[y, xs.min():xs.max() + 1] |= pants[y, xs.min():xs.max() + 1] & sel[y, xs.min():xs.max() + 1]
        hidden &= ~shoe
        sl = (slice(1000, H), slice(None))
        filled = rgb.copy()
        filled[sl] = harmonic(rgb[sl], hidden[sl], (shoe & (yy < 1110) & (mx > 200))[sl])
        fa = np.maximum(alpha * foot * (1 - hidden), soft(hidden, 0.6))
        pieces['foot_' + side] = (filled, fa)

    pieces['torso'] = (rgb, alpha * torso)
    pieces.update(arms(rgb, alpha, alpha * torso, xx, yy))

    os.makedirs(OUT, exist_ok=True)
    meta = {'w': W, 'h': H, 'joints': JOINTS, 'order': ['foot_l', 'foot_r', 'shin_l', 'shin_r', 'thigh_l', 'thigh_r',
                                                         'torso', 'head'], 'pieces': {}}
    os.makedirs(OUT, exist_ok=True)
    cut_hands(OUT, meta)
    for name, (prgb, pa) in pieces.items():
        a8 = (pa * 255).clip(0, 255).astype(np.uint8)
        img = np.dstack([prgb.clip(0, 255).astype(np.uint8), a8])
        img[a8 == 0] = 0
        ys, xs = np.where(a8 > 0)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        Image.fromarray(img[y0:y1, x0:x1], 'RGBA').save(os.path.join(OUT, name + '.png'), optimize=True)
        meta['pieces'][name] = {'x': int(x0), 'y': int(y0)}
        print(name, (x0, y0, x1, y1))
    for name in ('head', 'blink', 'jaw'):
        im = Image.open(os.path.join(SRC, name + '.png'))
        x0, y0, x1, y1 = im.getbbox()
        im.crop((x0, y0, x1, y1)).save(os.path.join(OUT, name + '.png'), optimize=True)
        meta['pieces'][name] = {'x': x0, 'y': y0}
    json.dump(meta, open(os.path.join(OUT, 'parts.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
