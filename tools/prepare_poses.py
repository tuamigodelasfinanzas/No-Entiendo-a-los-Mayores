"""Turns Chiño's pose sheets (assets/characters/source/poses-*.png) into body layers for the puppets.
Usage: python3 tools/prepare_poses.py      (after tools/prepare_characters.py)
       -> assets/characters/<id>/poses/<pose>.png (+ <pose>-front.png) and the "poses" table of rig.json

The face is never taken from the sheets: the head stays the original drawing (head.png, blink.png, jaw.png) and
each pose only gives the body under it. Per pose:
  - the cell is cut out of the sheet (white background out, floor shadow out),
  - the original head is matched on the pose's head (masked least squares) to find where the pose's head is,
  - standing poses are scaled so that chin -> soles fits the original drawing (the head keeps the proportion of
    the drawing, Chiño's rule); poses with the feet elsewhere (jumping, running, sitting...) keep the head scale,
  - the pose's own head is removed, and the hands that go over the face are kept in a "front" layer that is
    drawn on top of the original head,
  - brand-like marks on the sneakers become plain white leather (originality rule of docs/biblia-personajes.md).
The sheets are small (each figure is about 300 px tall against 1100 px of the originals), so the poses are
upscaled: they look a little softer than the head."""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets/characters/source')
CH = os.path.join(ROOT, 'assets/characters')

# cells on the sheets (x0, y0, x1, y1), measured by hand. fit: 'stand' (chin -> soles like the drawing) or
# 'head' (keep the head scale). front: boxes (in the 896 px frame) of the hands that go over the original head.
POSES = {
    'poses-1.png': {
        'e-explica': ((13, 53, 332, 354), 'stand', []),
        'e-senala': ((353, 53, 672, 354), 'stand', [('keep', 620, 220, 780, 460)]),
        'e-brazos-cruzados': ((692, 53, 1011, 354), 'stand', []),
        'e-encoge': ((13, 408, 332, 717), 'stand', []),
        'e-rasca': ((353, 408, 672, 717), 'stand', [('keep', 180, 250, 310, 480)]),
        'e-manos-cadera': ((692, 408, 1011, 717), 'stand', []),
        'r-mano-barbilla': ((13, 785, 332, 1114), 'stand', [(370, 360, 560, 520)]),
        'r-levanta-mano': ((353, 785, 672, 1114), 'stand', [('keep', 150, 50, 335, 430)]),
        'r-senala-a-e': ((692, 785, 1011, 1114), 'stand', []),
        'r-brazos-cruzados': ((13, 1171, 332, 1516), 'stand', []),
        'r-palmas-arriba': ((353, 1171, 672, 1516), 'stand', []),
        'r-mano-frente': ((692, 1171, 1011, 1516), 'stand', [(270, 105, 435, 268), ('keep', 195, 190, 320, 430)]),
    },
    'poses-2.png': {
        'e-salta': ((35, 123, 266, 516), 'head', [('keep', 100, 40, 310, 470), ('keep', 570, 40, 800, 470)]),
        'e-corre': ((266, 131, 490, 516), 'head', []),
        'e-susurra': ((45, 575, 235, 1000), 'stand', [('keep', 540, 260, 720, 480)]),
        'e-pulgar-arriba': ((285, 568, 470, 998), 'stand', []),
        'e-idea': ((35, 1049, 252, 1457), 'stand', [('keep', 620, 140, 820, 470)]),
        'e-corazon': ((282, 1050, 469, 1456), 'stand', []),
        'r-con-balon': ((525, 122, 747, 553), 'stand', []),
        'r-caminando': ((771, 122, 990, 557), 'stand', []),
        'r-sentado': ((531, 656, 754, 981), 'head', []),
        'r-senala-arriba': ((759, 594, 997, 1021), 'stand', [('keep', 590, 40, 896, 470)]),
        'r-atandose': ((539, 1094, 736, 1435), 'head', []),
        'r-leyendo': ((798, 1059, 993, 1460), 'stand', []),
    },
    'poses-3.png': {
        'e-celebrando': ((5, 68, 128, 279), 'head', []),
        'e-saltando': ((134, 68, 254, 279), 'head', []),
        'e-corriendo': ((260, 68, 378, 279), 'head', []),
        'e-senalando-lejos': ((384, 68, 503, 279), 'stand', []),
        'e-empujando': ((5, 308, 128, 528), 'head', []),
        'e-tirando': ((134, 308, 254, 528), 'head', []),
        'e-agachado': ((260, 308, 378, 528), 'head', []),
        'e-mirando-arriba': ((384, 308, 503, 528), 'stand', []),
        'e-mirando-lejos': ((5, 558, 128, 792), 'stand', []),
        'e-escuchando': ((134, 558, 254, 792), 'stand', []),
        'e-sorpresa': ((260, 558, 378, 792), 'stand', []),
        'e-riendo': ((384, 558, 503, 792), 'stand', []),
        'e-miedo': ((5, 820, 128, 1041), 'stand', []),
        'e-sentado': ((260, 820, 378, 1041), 'head', []),
        'e-ensenando': ((5, 1071, 128, 1278), 'stand', []),
        'e-con-idea': ((134, 1071, 254, 1278), 'stand', []),
        'e-usando-tablet': ((260, 1071, 378, 1278), 'head', []),
        'e-con-mochila': ((384, 1071, 503, 1278), 'stand', []),
        'e-mirando-reloj': ((5, 1307, 128, 1503), 'stand', []),
        'e-pensativo': ((134, 1307, 254, 1503), 'head', []),
        'e-hablando': ((260, 1307, 378, 1503), 'stand', []),
        'e-despidiendose': ((384, 1307, 503, 1503), 'stand', []),
        'r-saludando': ((517, 68, 636, 279), 'stand', []),
        'r-senalando': ((642, 68, 767, 279), 'stand', []),
        'r-pulgar-arriba': ((773, 68, 896, 279), 'stand', []),
        'r-ok': ((902, 68, 1016, 279), 'stand', []),
        'r-pensativo': ((517, 308, 636, 528), 'stand', []),
        'r-escuchando': ((642, 308, 767, 528), 'stand', []),
        'r-sorprendido': ((773, 308, 896, 528), 'stand', []),
        'r-riendo': ((902, 308, 1016, 528), 'stand', []),
        'r-cruzado-serio': ((517, 558, 636, 792), 'stand', []),
        'r-explicando': ((642, 558, 767, 792), 'stand', []),
        'r-mostrando': ((773, 558, 896, 792), 'stand', []),
        'r-mirando-arriba': ((902, 558, 1016, 792), 'stand', []),
        'r-corriendo': ((773, 820, 896, 1041), 'head', []),
        'r-saltando': ((902, 820, 1016, 1041), 'head', []),
        'r-usando-tablet': ((773, 1071, 896, 1278), 'head', []),
        'r-con-mochila': ((517, 1307, 636, 1503), 'stand', []),
        'r-despidiendose': ((902, 1307, 1016, 1503), 'stand', []),
    },
}
# poses-3.png: its figures are ~200 px tall and many heads are turned or tilted, so the cut-out leaves bits of the
# sheet's own face and hair around the original head. Left out until Chiño sends them as big single files.
SKIP = {'poses-3.png'}
SOLES = 1167     # bottom of the sneakers in the original drawings (896 x 1200)


def alpha_of(cell):
    a = np.asarray(cell).astype(int)
    mn, mx = a.min(2), a.max(2)
    light = (mn > 228) & (mx - mn < 20)
    h, w = mn.shape
    b = Image.fromarray((light * 255).astype(np.uint8)).copy()
    for s in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, h - 1), (w // 2, 0), (1, h // 2), (w - 2, h // 2)]:
        if b.getpixel(s) == 255:
            ImageDraw.floodfill(b, s, 128)
    bg = np.asarray(b) == 128
    # the soft grey floor shadow under the shoes
    sh = Image.fromarray((bg * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))
    bg |= (np.asarray(sh) > 0) & (mn > 196) & (mx - mn < 24)
    return bg


def dilate(m, r):
    """Grows a mask (PIL 'L') by about r px, fast: max filter on a 4x smaller copy."""
    w, h = m.size
    small = m.resize((max(1, w // 4), max(1, h // 4)), Image.BOX)
    k = max(3, (r // 4) * 2 + 1)
    return small.filter(ImageFilter.MaxFilter(k)).resize((w, h), Image.BILINEAR)


def fcorr(I, T):
    H, W = I.shape
    h, w = T.shape
    F = np.fft.rfft2(I, (H + h, W + w))
    G = np.fft.rfft2(T[::-1, ::-1], (H + h, W + w))
    return np.fft.irfft2(F * G, (H + h, W + w))[h - 1:H, w - 1:W]


def find_head(cell_l, head, s):
    """Where the original head (scaled by s) sits best on the cell: offset of its bbox corner."""
    t = head.resize((max(1, round(head.width * s)), max(1, round(head.height * s))), Image.LANCZOS)
    ta = np.asarray(t).astype(float) / 255
    T = np.asarray(t.convert('LA'))[..., 0].astype(float) / 255
    w = (ta[..., 3] > 0.9).astype(float)
    Tw = T * w
    ssd = ((Tw * T).sum() - 2 * fcorr(cell_l, Tw) + fcorr(cell_l ** 2, w)) / w.sum()
    y, x = np.unravel_index(np.argmin(ssd), ssd.shape)
    return x, y, ssd[y, x]


def head_scale(cell_l, head, s0):
    best = None
    for s in np.arange(s0 * 0.9, s0 * 1.1, s0 * 0.01):
        x, y, e = find_head(cell_l, head, s)
        if best is None or e < best[0]:
            best = (e, s, x, y)
    return best[1:]


def unbrand(rgb, alpha, soles_y, top_y):
    """Navy marks on the white sneakers -> white leather. A mark is navy with leather on its left, right and below
    (the hem of the jeans has leather only below), in the bottom of the figure."""
    a = rgb.astype(float)
    H, W = alpha.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    navy = (b > r + 15) & (a.max(2) < 170) & alpha
    leather = (a.min(2) > 190) & alpha
    k = max(4, round((soles_y - top_y) * 0.035))

    def seen(dy, dx):
        acc = np.zeros_like(leather)
        for i in range(1, k + 1):
            acc |= np.roll(leather, (dy * i, dx * i), (0, 1))
        return acc
    yy = np.arange(H)[:, None]
    zone = (yy > soles_y - (soles_y - top_y) * 0.09) & (yy <= soles_y)
    m = navy & zone & seen(0, 1) & seen(0, -1) & seen(-1, 0)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))) / 255.0
    shoe = np.array([238, 236, 240.0])
    return a * (1 - m[..., None]) + shoe * m[..., None]


def main():
    for cid in ('e', 'r'):
        os.makedirs(os.path.join(CH, cid, 'poses'), exist_ok=True)
    rigs = {cid: json.load(open(os.path.join(CH, cid, 'rig.json'))) for cid in ('e', 'r')}
    heads = {}
    for cid in ('e', 'r'):
        h = Image.open(os.path.join(CH, cid, 'head.png'))
        heads[cid] = (h, h.getbbox())
    # the head scale of a character is the same in all its standing poses of a sheet: take the median
    table = {cid: {} for cid in ('e', 'r')}
    for sheet, poses in POSES.items():
        if sheet in SKIP:
            continue
        im = Image.open(os.path.join(SRC, sheet)).convert('RGB')
        # first guess of the sheet scale: figure height (hair -> soles) against the drawing, median of the
        # standing poses (a raised hand makes one of them too tall, the median ignores it)
        guess = {}
        for name, (box, fit, front) in poses.items():
            if fit == 'stand':
                ys = np.where((~alpha_of(im.crop(box))).any(1))[0]
                guess.setdefault(name[0], []).append((ys.max() - ys.min()) / (SOLES - rigs[name[0]]['bbox'][1]))
        guess = {k: sorted(v)[len(v) // 2] for k, v in guess.items()}
        found = {}
        for name, (box, fit, front) in poses.items():
            cid = name[0]
            cell = im.crop(box)
            cl = np.asarray(cell.convert('L')).astype(float) / 255
            h, hb = heads[cid]
            s, x, y = head_scale(cl, h.crop(hb), guess[cid])
            found[name] = s
        for name, (box, fit, front) in poses.items():
            cid = name[0]
            rig = rigs[cid]
            same = sorted(v for k, v in found.items() if k[0] == cid and poses[k][1] == 'stand')
            # standing: the sheet's head scale (one bad match does not move it); other poses: their own
            s_h = same[len(same) // 2] if fit == 'stand' else found[name]
            cell = im.crop(box)
            rgb = np.asarray(cell).astype(float)
            cl = np.asarray(cell.convert('L')).astype(float) / 255
            h, hb = heads[cid]
            hx, hy, err = find_head(cl, h.crop(hb), s_h)
            # frame -> cell for the head: cell = frame * s_h + (hx - hb0 * s_h, hy - hb1 * s_h)
            ox_h, oy_h = hx - hb[0] * s_h, hy - hb[1] * s_h
            bg = alpha_of(cell)
            ys = np.where((~bg).any(1))[0]
            soles_c = ys.max()
            chin_c = oy_h + rig['chin'] * s_h
            px_c = ox_h + rig['pivot'][0] * s_h
            if fit == 'stand':
                s = (soles_c - chin_c) / (SOLES - rig['chin'])
            else:
                s = s_h
            # body transform: cell = frame * s + (tx, ty), with the chin and the neck on the original ones
            tx, ty = px_c - rig['pivot'][0] * s, chin_c - rig['chin'] * s
            soles_f = (soles_c - ty) / s
            Hf = max(rig['h'], int(np.ceil(soles_f + 40)))
            W = rig['w']
            up = (round(cell.width / s), round(cell.height / s))
            at = (round(-tx / s), round(-ty / s))

            def place(img, mode):
                c = Image.new(mode, (W, Hf))
                c.paste(img.resize(up, Image.LANCZOS), at)
                return c
            rgb_u = unbrand(rgb, ~bg, soles_c, ys.min())
            big = place(Image.fromarray(rgb_u.clip(0, 255).astype(np.uint8)), 'RGB')
            big = big.filter(ImageFilter.UnsharpMask(radius=2.5, percent=60, threshold=2))
            al = Image.fromarray(np.where(bg, 0, 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
            al = np.asarray(place(al, 'L').filter(ImageFilter.GaussianBlur(1.1))).astype(float)
            # the pose's own head: the original head silhouette put where it was found, a bit bigger, above the chin
            hs = Image.new('L', cell.size)
            hsil = h.getchannel('A').crop(hb).resize((round(h.crop(hb).width * s_h), round(h.crop(hb).height * s_h)), Image.LANCZOS)
            hs.paste(hsil, (hx, hy))
            hs = np.asarray(dilate(place(hs.point(lambda v: 255 if v > 40 else 0), 'L'), 24)).astype(float) / 255
            pose_head = hs.copy()
            # and a wide ring around the original head: the hair of the sheets is messier than the drawing
            oh = np.zeros((Hf, W), np.uint8)
            oh[:rig['h']] = (np.asarray(h.getchannel('A')) > 40) * 255
            oh = dilate(Image.fromarray(oh), 60)
            hs = np.maximum(hs, np.asarray(oh.filter(ImageFilter.GaussianBlur(4))).astype(float) / 255)
            # sleeve colour (for the hands drawn in front of the head)
            bf = np.asarray(big).astype(float)
            r_, g_, b_ = bf[..., 0], bf[..., 1], bf[..., 2]
            sleeve = ((r_ > 140) & (r_ > g_ + 100) & (r_ > b_ + 100) & (g_ < 90) & (b_ < 90)) if cid == 'e' else ((b_ > 150) & (b_ > r_ + 70) & (b_ > g_ + 20))
            sleeve = np.asarray(Image.fromarray((sleeve * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))).astype(float) / 255
            if cid == 'e':
                hair = (bf.max(2) < 200) & (r_ > b_ + 25) & (r_ - g_ < 75) & (g_ > b_)
            else:
                hair = (r_ > 120) & (b_ < 0.5 * r_) & (g_ > 0.55 * r_) & (g_ < 0.85 * r_)
            hair = np.asarray(Image.fromarray((hair * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5))) > 127
            skin = (r_ > 200) & (g_ > 130) & (b_ > 0.52 * r_) & (r_ > g_ + 15) & (g_ > b_ + 10)
            # arms that pass next to the head (a raised hand, a finger): boxes where the ring does not cut the
            # hand and the sleeve (the hair of the sheet in the box still goes)
            for b in front:
                if b[0] == 'keep':
                    x0, y0, x1, y1 = b[1:]
                    arm = ~hair[y0:y1, x0:x1]
                    hs[y0:y1, x0:x1] *= 1 - arm
            # the hood never goes (shoulders of a jumping kid come up near the chin)
            hs = hs * (1 - sleeve)
            yy = np.arange(Hf)[:, None]
            # under the chin the pose's neck and hood stay; the original head covers the joint
            hs = hs * np.clip((rig['chin'] - 5 - yy) / 6, 0, 1)
            body_a = al * (1 - hs)
            # the sheets draw the chin a little lower than the original: under the original chin, what is left of
            # the sheet's chin and jaw line becomes neck in the shade of the head (the hood and the collar stay)
            band = (yy >= rig['chin'] - 6) & (yy < rig['chin'] + 60)
            shirt = (b_ > r_ + 10) | (bf.min(2) > 200)
            line = (bf.max(2) < 120) & (r_ - g_ < 45) & (r_ - b_ < 60)        # the jaw line, not the hood's shadows
            chin = band & (pose_head > 0.5) & (skin | line) & ~shirt & (al > 0)
            cm = np.asarray(Image.fromarray((chin * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))).astype(float)[..., None] / 255
            # the skin of the drawing, in the shade of the head
            neck = np.array([int(rig['skin'][i:i + 2], 16) for i in (1, 3, 5)], float)
            shade = np.clip((yy - rig['chin']) / 30, 0, 1)[..., None]          # darker right under the chin
            neck_px = neck * (0.84 + 0.1 * shade)
            bf = bf * (1 - cm) + np.broadcast_to(neck_px, bf.shape) * cm
            big = Image.fromarray(bf.clip(0, 255).astype(np.uint8))
            # the original head's own silhouette is covered by the head layer: keep the body there (no holes)
            out = os.path.join(CH, cid, 'poses', name[2:])
            if os.environ.get('POSES_DEBUG'):
                Image.fromarray(np.dstack([np.asarray(big), al]).clip(0, 255).astype(np.uint8), 'RGBA').save(os.path.join(os.environ['POSES_DEBUG'], name + '.png'))
            rgba = np.dstack([np.asarray(big).astype(float), body_a]).clip(0, 255).astype(np.uint8)
            rgba[rgba[..., 3] == 0] = 0
            Image.fromarray(rgba, 'RGBA').save(out + '.png', optimize=True)
            entry = {'h': Hf, 'feet': round(soles_f - (SOLES - rig['feet']))}
            if any(b[0] != 'keep' for b in front):
                fm = Image.new('L', (W, Hf))
                d = ImageDraw.Draw(fm)
                for b in front:
                    if b[0] != 'keep':
                        d.rectangle(b, fill=255)
                fm = np.asarray(fm.filter(ImageFilter.GaussianBlur(4))).astype(float) / 255
                # only the hand and the sleeve (and their outline), not the hair of the sheet
                keep = np.asarray(Image.fromarray(((~hair & (skin | (sleeve > 0.5) | (bf.max(2) < 140))) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1))).astype(float) / 255
                fa = al * fm * keep
                fr = np.dstack([np.asarray(big).astype(float), fa]).clip(0, 255).astype(np.uint8)
                fr[fr[..., 3] == 0] = 0
                Image.fromarray(fr, 'RGBA').save(out + '-front.png', optimize=True)
                entry['front'] = True
            table[cid][name[2:]] = entry
            print(name, f's={s:.3f} head s={s_h:.3f} err={err:.3f} soles={soles_f:.0f} h={Hf}', 'front' if entry.get('front') else '')
    for cid in ('e', 'r'):
        p = os.path.join(CH, cid, 'rig.json')
        rig = json.load(open(p))
        rig['poses'] = table[cid]
        json.dump(rig, open(p, 'w'), indent=1)


if __name__ == '__main__':
    main()
