"""Turns Chiño's character sheets (assets/characters/source/*-full.jpg) into the layers the puppets animate.
Usage: python3 tools/prepare_characters.py      -> assets/characters/<id>/{head,body}.png + rig.json

Per character:
  - cuts the white background out (flood fill from the borders, so white shoes and teeth stay),
  - removes the brand-like logo of R's sneakers (originality rule of docs/biblia-personajes.md),
  - splits head / body at the chin so the head can turn, nod and tilt over the hood,
  - keeps the face exactly as it is in the drawing (Chiño's rule: the faces must be his illustrations), and makes
    two small layers from the drawing itself so the face can move without redrawing it:
      blink.png  the eyes closed: the eye area filled with the skin around it, plus a lash line,
      jaw.png    the drawing below the lip line, which src/puppets.js slides down while the character speaks
                 (the gap shows the inside of the mouth).
The coordinates below were measured on the 896x1200 sources; rig.json carries them to the browser."""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets/characters/source')

RIGS = {
    'e': {
        'src': 'e-full.jpg',
        'chin': 442, 'pivot': [458, 446], 'feet': 1150, 'center': 452,
        'eyes': [{'x': 402, 'y': 321, 'w': 80, 'h': 56}, {'x': 518, 'y': 321, 'w': 78, 'h': 56}],
        'brows': [{'x': 395, 'y': 270, 'w': 62, 'tilt': -6}, {'x': 520, 'y': 268, 'w': 60, 'tilt': 6}],
        'mouth': {'x': 458, 'y': 400, 'w': 112},
        'lids': [(354, 289, 450, 356), (472, 289, 566, 356)],
        # lip line: the top of the lower lip; the lower lip and the chin move from here. ox / ow: centre and half
        # width of the mouth opening on that line (measured on the drawing), where the inside of the mouth shows
        'jaw': {'x': 458, 'y': 406, 'w': 112, 'd': 8, 'ox': 456.5, 'ow': 29, 'inside': '#4A0E08'},
        'iris': ['#2B160B', '#6E3E1E', '#A8723F'], 'brow': '#7E4426', 'lip': '#7A3A2A',
    },
    'r': {
        'src': 'r-full.jpg',
        'chin': 410, 'pivot': [460, 414], 'feet': 1150, 'center': 446,
        'eyes': [{'x': 405, 'y': 289, 'w': 76, 'h': 54}, {'x': 516, 'y': 289, 'w': 74, 'h': 54}],
        'brows': [{'x': 397, 'y': 240, 'w': 62, 'tilt': -4}, {'x': 522, 'y': 238, 'w': 62, 'tilt': 4}],
        'mouth': {'x': 461, 'y': 360, 'w': 96},
        'lids': [(367, 262, 443, 318), (480, 262, 552, 318)],
        'jaw': {'x': 461, 'y': 363, 'w': 96, 'd': 7, 'ox': 454.5, 'ow': 27, 'inside': '#5A1A10'},
        'iris': ['#2E1A0C', '#734421', '#B07A45'], 'brow': '#A0642E', 'lip': '#8A4A36',
        # navy swoosh-like marks on both sneakers -> plain white leather
        'logo_boxes': [(318, 1072, 420, 1132), (470, 1072, 575, 1132)],
    },
}


def cutout(img, top=0):
    a = np.asarray(img).astype(int)
    mn, mx = a.min(axis=2), a.max(axis=2)
    H, W = mn.shape
    light = (mn > 222) & (mx - mn < 18)
    # the floor shadow under the sneakers is a little darker: accept it near the feet
    feet = np.zeros_like(light); feet[1085:, :] = True
    light |= feet & (mn > 196) & (mx - mn < 26)
    b = Image.new('L', (W, H)); b.putdata(list((light * 255).astype(np.uint8).ravel()))
    for seed in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1), (W // 2, 0), (W // 2, H - 1), (5, H // 2), (W - 6, H // 2)]:
        if b.getpixel(seed) == 255:
            ImageDraw.floodfill(b, seed, 128)
    bg = np.asarray(b) == 128
    # near-white pixels hugging the background are the light fringe of the hair: drop them too
    bgi = Image.new('L', (W, H)); bgi.putdata(list((bg * 255).astype(np.uint8).ravel()))
    near = np.asarray(bgi.filter(ImageFilter.MaxFilter(9))) > 0
    bg = bg | (near & (mn > 205) & (mx - mn < 40))
    # white pockets closed in between hair strands (above the eyes nothing is white)
    yy = np.arange(H)[:, None]
    bg = bg | ((yy < top) & (mn > 212) & (mx - mn < 34))
    al = Image.new('L', (W, H)); al.putdata(list(np.where(bg, 0, 255).astype(np.uint8).ravel()))
    # eat the 1-2 px white fringe of the hair, then soften the edge
    return al.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.9))


def paint_out(a, box, iters=1500):
    """Fills the ellipse inscribed in box with the skin around it (harmonic inpainting: each pixel becomes the
    average of its neighbours until it settles), so the shading of the cheeks carries on without seams."""
    x0, y0, x1, y1 = box
    m = 6
    sub = a[y0 - m:y1 + m, x0 - m:x1 + m].copy()
    h, w = sub.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, rx, ry = (w - 1) / 2, (h - 1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    hole = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    f = sub.copy()
    f[hole] = sub[~hole].mean(axis=0)
    for _ in range(iters):
        avg = (np.roll(f, 1, 0) + np.roll(f, -1, 0) + np.roll(f, 1, 1) + np.roll(f, -1, 1)) / 4
        f[hole] = avg[hole]
    # a soft 2 px blend at the rim of the ellipse
    d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    k = np.clip((1.12 - d) / 0.12, 0, 1)[..., None]
    a[y0 - m:y1 + m, x0 - m:x1 + m] = sub * (1 - k) + f * k


def blink_layer(a, rig):
    """Closed eyes, from the drawing: each eye filled with the skin around it, and a soft lash arc where the lids meet."""
    H, W = a.shape[:2]
    f = a.copy()
    lay = np.zeros((H, W, 4))
    for box in rig['lids']:
        paint_out(f, box)
    m = Image.new('L', (W, H))
    d = ImageDraw.Draw(m)
    for (x0, y0, x1, y1) in rig['lids']:
        d.ellipse((x0 - 4, y0 - 4, x1 + 4, y1 + 4), fill=255)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(2.5))).astype(float)
    lay[..., :3] = f
    lay[..., 3] = m
    img = Image.fromarray(lay.astype(np.uint8), 'RGBA')
    # lash lines, drawn at 4x and scaled down so they are as smooth as the drawing
    S = 4
    big = Image.new('RGBA', (W * S, H * S))
    g = ImageDraw.Draw(big)
    for i, e in enumerate(rig['eyes']):
        x, y, w, h = e['x'], e['y'], e['w'], e['h']
        pts = []
        for k in range(41):
            t = k / 40
            px = x - w / 2 + w * t
            py = y + h * 0.05 + h * 0.24 * (1 - (2 * t - 1) ** 2)
            pts.append((px * S, py * S))
        g.line(pts, fill=(52, 28, 18, 255), width=int(4.5 * S), joint='curve')
        # the little flick at the outer corner, like in the drawing
        ox, sgn = (x - w / 2, -1) if i == 0 else (x + w / 2, 1)
        g.line([(ox * S, (y + h * 0.05) * S), ((ox + sgn * 8) * S, (y - h * 0.08) * S)], fill=(52, 28, 18, 255), width=int(3.5 * S))
    lash = big.resize((W, H), Image.LANCZOS)
    return Image.alpha_composite(img, lash)


def jaw_layer(a, alpha, rig):
    """The drawing just below the lip line (lower lip and chin around the mouth), feathered at the sides and at the
    bottom. Sliding it down a few pixels opens the mouth the drawing already has."""
    H, W = a.shape[:2]
    j = rig['jaw']
    yy, xx = np.mgrid[0:H, 0:W]
    dx = np.abs(xx - j['x']) / (j['w'] * 0.8)
    below = (yy - j['y']) / 28.0       # stays well above the chin, so the jaw line never moves
    m = np.clip((1 - dx) / 0.3, 0, 1) * np.clip((1 - below) / 0.5, 0, 1) * (yy >= j['y'])
    return Image.fromarray(np.dstack([a, (m * alpha).clip(0, 255)]).astype(np.uint8), 'RGBA')


def main():
    for cid, rig in RIGS.items():
        img = Image.open(os.path.join(SRC, rig['src'])).convert('RGB')
        alpha = np.asarray(cutout(img, rig['eyes'][0]['y'] - 45)).astype(np.float64)
        a = np.asarray(img).astype(np.float64).copy()
        H, W = alpha.shape
        for (x0, y0, x1, y1) in rig.get('logo_boxes', []):
            sub = a[y0:y1, x0:x1]
            r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
            navy = (b > r + 25) & (b > 90) & (r < 170)
            m = Image.new('L', (x1 - x0, y1 - y0)); m.putdata(list((navy * 255).astype(np.uint8).ravel()))
            m = np.asarray(m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))) / 255.0
            shoe = np.array([236, 233, 238.0])
            a[y0:y1, x0:x1] = sub * (1 - m[..., None]) + shoe * m[..., None]
        yy = np.arange(H)[:, None].repeat(W, axis=1)
        head = (yy < rig['chin']) & (alpha > 0)
        # soften the cut line between head and body (2 px)
        hm = Image.new('L', (W, H)); hm.putdata(list((head * 255).astype(np.uint8).ravel()))
        hm = np.asarray(hm.filter(ImageFilter.GaussianBlur(1.0))) / 255.0
        head_rgb = a.copy()          # the face as drawn
        out = os.path.join(ROOT, 'assets/characters', cid)
        os.makedirs(out, exist_ok=True)
        ys, xs = np.where(alpha > 8)
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        # head layer
        ha = (alpha * hm).clip(0, 255)
        Image.fromarray(np.dstack([head_rgb, ha]).astype(np.uint8), 'RGBA').save(os.path.join(out, 'head.png'), optimize=True)
        # body layer: everything else, plus a patch of neck skin that shows when the head turns
        # the body starts 5 px above the cut, under the head: no see-through seam when the head moves
        bm = Image.new('L', (W, H)); bm.putdata(list((((yy < rig['chin'] - 5) & (alpha > 0)) * 255).astype(np.uint8).ravel()))
        bm = np.asarray(bm.filter(ImageFilter.GaussianBlur(1.0))) / 255.0
        ba = (alpha * (1 - bm)).clip(0, 255)
        body = Image.fromarray(np.dstack([a, ba]).astype(np.uint8), 'RGBA')
        px, py = rig['pivot']
        skin = tuple(int(v) for v in a[py - 12, px])
        # skin behind the lower face, inside its silhouette: what shows when the head turns
        nm = (yy > py - 130) & (yy < rig['chin'] + 4) & (alpha > 0)
        nmi = Image.new('L', (W, H)); nmi.putdata(list((nm * 255).astype(np.uint8).ravel()))
        nmi = nmi.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(2))
        neck = Image.new('RGBA', (W, H), skin + (255,)); neck.putalpha(nmi)
        body = Image.alpha_composite(neck, body)
        body.save(os.path.join(out, 'body.png'), optimize=True)
        for name, layer in (('blink', blink_layer(a, rig)), ('jaw', jaw_layer(a, alpha * hm, rig))):
            la = np.asarray(layer).copy()
            la[la[..., 3] == 0] = 0                      # empty pixels compress to nothing
            Image.fromarray(la, 'RGBA').save(os.path.join(out, f'{name}.png'), optimize=True)
        meta = {k: v for k, v in rig.items() if k not in ('src', 'lids', 'logo_boxes')}
        lid = np.array(skin) * 0.8 + np.array([232, 150, 112]) * 0.2   # lids: the skin, a touch warmer
        meta.update({'w': W, 'h': H, 'bbox': bbox, 'skin': '#%02X%02X%02X' % skin, 'lid': '#%02X%02X%02X' % tuple(int(v) for v in lid)})
        json.dump(meta, open(os.path.join(out, 'rig.json'), 'w'), indent=1)
        print(cid, 'bbox', bbox, 'skin', meta['skin'])


if __name__ == '__main__':
    main()
