"""Layered sleeves for E's rig: upper arm + forearm per side, so the elbow can bend.
Usage: python3 tools/split_sleeves.py      (after tools/split_apose.py)
       -> assets/characters/e/rig/upperarm_{l,r}.png, forearm_{l,r}.png, added to rig.json

Source: assets/characters/source/e-mangas.png, four capsule-shaped sleeves on white, left to right: upper arm and
forearm of the arm on the left of the screen, then the same for the other one. Each piece is cut out, its red is
brought to the red of pose A, and it is fitted (width and length separately) between its two joints of rig.json,
already turned to the rest pose: the upper arm's round ends are centred on the shoulder and the elbow, the forearm's
round end on the elbow and its cuff ends just past the wrist, where the hand goes in.

It also joins both into one straight sleeve per side, sleeve_{l,r}.png (2x, axis down the middle, the shoulder's centre
at row CAP*2): tools/rig_test.py bends it along a curve through shoulder, elbow and wrist, so the elbow and the
shoulder bend round instead of turning two stiff pieces."""
import json, math, os
import numpy as np
from PIL import Image, ImageFilter

from split_parts import flood, soft

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets/characters/source/e-mangas.png')
OUT = os.path.join(ROOT, 'assets/characters/e/rig')
RED_POSE_A = np.array([210, 34, 35.0])
HOODIE_LINE = np.array([110, 18, 22.0])        # pose A's outline on the hoodie
UPPER_W, FORE_W = 80, 74               # sleeve width in the 896x1200 frame (pose A: ~75 across the elbow)
CUFF_PAST_WRIST = 14                   # the open cuff goes a bit past the wrist, the hand sits inside it
SHOULDER_CAP = 24                      # sleeve above the shoulder joint: stays under the torso's round shoulder


def pieces(rgb):
    """The four sleeves, left to right, as RGBA crops (white background flooded from the border)."""
    ink = rgb.min(2) < 235
    bg = flood(~ink, [(0, 0), (rgb.shape[1] - 1, 0), (0, rgb.shape[0] - 1), (rgb.shape[1] - 1, rgb.shape[0] - 1)])
    fg = ~bg
    cols = np.where(fg.any(0))[0]
    runs, start = [], cols[0]
    for a, b in zip(cols, cols[1:]):
        if b > a + 5:
            runs.append((start, a))
            start = b
    runs.append((start, cols[-1]))
    alpha = soft(fg, 1)
    out = []
    for x0, x1 in runs:
        rows = np.where(fg[:, x0:x1 + 1].any(1))[0]
        y0, y1 = rows[0], rows[-1]
        c = rgb[y0:y1 + 1, x0:x1 + 1].astype(float)
        a = alpha[y0:y1 + 1, x0:x1 + 1]
        out.append((c, a))
    return out


def recolour(c, ref_med):
    """Brings the generated red to pose A's red; the outline and the dark folds keep their relative shade."""
    k = RED_POSE_A / ref_med
    return np.clip(c * k, 0, 255)


def fit(c, a, width, top, bottom, pad_top, pad_bottom):
    """Piece crop (vertical, top end first) -> RGBA image in the rig frame plus its offset. top/bottom: frame points
    the piece's axis runs between; pad_top/pad_bottom: how much of the piece sticks out past them (frame px)."""
    h, w = a.shape
    d = bottom - top
    L = np.linalg.norm(d)
    total = L + pad_top + pad_bottom
    sx, sy = width / w, total / h
    th = math.atan2(d[1], d[0]) - math.pi / 2           # turn the vertical piece onto the bone
    c_, s_ = math.cos(th), math.sin(th)
    # piece (u, v) -> frame: centre column on the axis, v = pad_top on the top joint
    def to_frame(u, v):
        x, y = (u - w / 2) * sx, v * sy - pad_top
        return top + np.array([c_ * x - s_ * y, s_ * x + c_ * y])
    corners = np.array([to_frame(u, v) for u, v in ((0, 0), (w, 0), (0, h), (w, h))])
    x0, y0 = np.floor(corners.min(0)).astype(int) - 2
    x1, y1 = np.ceil(corners.max(0)).astype(int) + 2
    M = np.array([[c_ * sx, -s_ * sy, 0], [s_ * sx, c_ * sy, 0], [0, 0, 1.0]])
    o = to_frame(0, 0)
    M[0, 2], M[1, 2] = o[0] - x0, o[1] - y0
    inv = np.linalg.inv(M)
    rgba = np.dstack([c, a * 255]).astype(np.uint8)
    # premultiply so the white around the piece doesn't bleed into the edge when it is resampled
    pm = rgba.astype(float)
    pm[..., :3] *= pm[..., 3:] / 255
    im = Image.fromarray(pm.astype(np.uint8), 'RGBA')
    out = np.array(im.transform((x1 - x0, y1 - y0), Image.AFFINE, tuple(inv[:2].ravel()), resample=Image.BICUBIC),
                   float)
    al = out[..., 3:]
    out[..., :3] = np.where(al > 0, out[..., :3] * 255 / np.maximum(al, 1), 0)
    out = outline(out)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA'), (int(x0), int(y0))


def outline(rgba, size=5):
    """Redraws the outline at pose A's weight: shrunk to the rig's size the generated line breaks into dots."""
    a = Image.fromarray(rgba[..., 3].astype(np.uint8))
    inner = np.asarray(a.filter(ImageFilter.MinFilter(size)), float) / 255
    band = np.clip(rgba[..., 3] / 255 - inner, 0, 1)[..., None]
    rgba[..., :3] = rgba[..., :3] * (1 - band) + HOODIE_LINE * band
    return rgba


STRIP_K = 2                            # straight sleeve: pixels per frame pixel
STRIP_HALF = 50                        # half its width, frame px


def sample(img, r, c):
    """Bilinear lookup of img (H x W x C) at float rows r / cols c (same shape); outside the image is 0."""
    h, w = img.shape[:2]
    r0, c0 = np.floor(r).astype(int), np.floor(c).astype(int)
    fr, fc = (r - r0)[..., None], (c - c0)[..., None]
    out = 0
    for dr, dc, wt in ((0, 0, (1 - fr) * (1 - fc)), (1, 0, fr * (1 - fc)), (0, 1, (1 - fr) * fc), (1, 1, fr * fc)):
        rr, cc = r0 + dr, c0 + dc
        ok = ((rr >= 0) & (rr < h) & (cc >= 0) & (cc < w))[..., None]
        out = out + img[np.clip(rr, 0, h - 1), np.clip(cc, 0, w - 1)] * ok * wt
    return out


def premul(c, a):
    return np.dstack([c * a[..., None], a * 255])


def straight(up, fore, lu, lf):
    """One straight sleeve: the upper arm down to the elbow, then the forearm, cross-faded over the elbow and with the
    width easing from one to the other, so nothing in it marks a joint."""
    (cu, au), (cf, af) = up, fore
    U, F = premul(cu, au), premul(cf, af)
    cap = UPPER_W / 2
    v = np.arange(-cap, lu + lf + CUFF_PAST_WRIST, 1 / STRIP_K)[:, None]
    d = np.arange(-STRIP_HALF, STRIP_HALF, 1 / STRIP_K)[None, :]
    width = UPPER_W + (FORE_W - UPPER_W) * np.clip((v - lu * 0.5) / (lu * 0.5 + lf * 0.5), 0, 1)
    hu, wu = au.shape
    hf, wf = af.shape
    rows_u = (v + cap) * hu / (lu + cap + UPPER_W / 2) + 0 * d
    cols_u = wu / 2 + d / width * wu
    rows_f = (v - lu + FORE_W / 2) * hf / (lf + FORE_W / 2 + CUFF_PAST_WRIST) + 0 * d
    cols_f = wf / 2 + d / width * wf
    k = np.clip((v - (lu - 14)) / 28, 0, 1)[..., None]
    out = sample(U, rows_u, cols_u) * (1 - k) + sample(F, rows_f, cols_f) * k
    al = out[..., 3:]
    out[..., :3] = np.where(al > 0, out[..., :3] * 255 / np.maximum(al, 1), 0)
    return outline(out, 2 * STRIP_K + 1)


def main():
    rgb = np.array(Image.open(SRC).convert('RGB'))
    got = pieces(rgb)
    assert len(got) == 4, f'expected 4 sleeves, found {len(got)}'
    red = rgb[(rgb[..., 0] > 150) & (rgb[..., 1] < 90)].astype(float)
    med = np.median(red, 0)
    meta = json.load(open(os.path.join(OUT, 'rig.json')))
    J = {k: np.array(v, float) for k, v in meta['joints'].items()}
    for side, (up, fore) in (('l', got[0:2]), ('r', got[2:4])):
        S, E, Wr = J['shoulder_' + side], J['elbow_' + side], J['wrist_' + side]
        cu, au = up
        im, off = fit(recolour(cu, med), au, UPPER_W, S, E, SHOULDER_CAP, UPPER_W / 2)
        im.save(os.path.join(OUT, f'upperarm_{side}.png'))
        meta['pieces'][f'upperarm_{side}'] = {'x': off[0], 'y': off[1]}
        cf, af = fore
        im, off = fit(recolour(cf, med), af, FORE_W, E, Wr, FORE_W / 2, CUFF_PAST_WRIST)
        im.save(os.path.join(OUT, f'forearm_{side}.png'))
        meta['pieces'][f'forearm_{side}'] = {'x': off[0], 'y': off[1]}
        lu, lf = float(np.linalg.norm(E - S)), float(np.linalg.norm(Wr - E))
        im = straight((recolour(cu, med), au), (recolour(cf, med), af), lu, lf)
        Image.fromarray(np.clip(im, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, f'sleeve_{side}.png'))
        meta.setdefault('sleeves', {})[side] = {'k': STRIP_K, 'half': STRIP_HALF, 'cap': UPPER_W / 2, 'upper': lu,
                                                'fore': lf, 'cuff': CUFF_PAST_WRIST}
    json.dump(meta, open(os.path.join(OUT, 'rig.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
