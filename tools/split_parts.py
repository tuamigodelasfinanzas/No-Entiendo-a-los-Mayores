"""Cuts E's body (assets/characters/e/body.png, made by tools/prepare_characters.py) into the pieces of a skeleton,
so he can walk and jump instead of only switching poses.
Usage: python3 tools/split_parts.py      -> assets/characters/e/parts/<piece>.png + parts.json

Pieces (draw order, back to front): foot_l, foot_r, shin_l, shin_r, thigh_l, thigh_r, torso, head (+ blink, jaw).
  - torso:  hoodie, arms with the hands in the pockets, and the jeans down to a V line through the crotch;
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
}


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
        filled = harmonic(rgb, hidden, shoe & (yy < 1110) & (mx > 200))
        fa = np.maximum(alpha * foot * (1 - hidden), soft(hidden, 0.6))
        pieces['foot_' + side] = (filled, fa)

    pieces['torso'] = (rgb, alpha * torso)

    os.makedirs(OUT, exist_ok=True)
    meta = {'w': W, 'h': H, 'joints': JOINTS, 'order': ['foot_l', 'foot_r', 'shin_l', 'shin_r', 'thigh_l', 'thigh_r',
                                                         'torso', 'head'], 'pieces': {}}
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
