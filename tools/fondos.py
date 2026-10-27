"""Theme backgrounds for the E and R videos: every episode gets its own colourful, lively set that matches what it is
about (a house and coins for the mortgage, clocks for "no tengo tiempo"...). Drawn here with Pillow, so it is free and
runs anywhere (GitHub Actions too); nothing touches the kids, who are drawn on top.

  elegir(g)                 the theme of a script: its "fondo" if it has one, otherwise from its tema, title,
                            hashtags and card icons (TEMAS, PALABRAS)
  Fondo(g)                  the set of that script: .frame(z, cx, cy, t) is the background of a frame, with the
                            camera of the scene (zoom z centred on world point cx, cy) and the things that move
                            (floating motifs, sparkles, the hands of a wall clock)
  python3 tools/fondos.py 002-no-tengo-tiempo out.png        a preview of a script's set (wide shot)
  python3 tools/fondos.py tiempo salon out.png               a preview of a theme in a place

The set is built in world coordinates (the 1080x1920 of the wide shot plus MARGIN around it, at K times the size so
close ups stay sharp), like escena_rig.background(). The kids stand on the floor at y 1620 with their heads between
y ~530 and ~1000: the busy things go around them, with a soft light behind them so they stand out."""
import math, os, sys, unicodedata
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1920
MARGIN = 500
K = 2
FLOOR = 1560
INK = (62, 42, 72, 255)
FONT = os.environ.get('FREDOKA', os.path.join(ROOT, 'out/fredoka-700.ttf'))


def font(size):
    try:
        return ImageFont.truetype(FONT, int(size))
    except OSError:
        return ImageFont.load_default(int(size))


def P(x, y):
    """World point -> pixel of the set."""
    return (x + MARGIN) * K, (y + MARGIN) * K


def box(x0, y0, x1, y1):
    return (*P(x0, y0), *P(x1, y1))


def rgba(c, a=255):
    return tuple(c[:3]) + (a,)


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# ---------------------------------------------------------------- motifs
# Each one draws itself in an s x s square (d: ImageDraw, s: side in px, cols: the theme's accents).
def _w(s, k=0.035):
    return max(2, int(s * k))


def m_casa(d, s, cols):
    w = _w(s)
    d.rectangle((s * .2, s * .45, s * .8, s * .9), fill=(255, 244, 222, 255), outline=INK, width=w)
    d.polygon([(s * .1, s * .5), (s * .5, s * .12), (s * .9, s * .5)], fill=rgba(cols[0]), outline=INK, width=w)
    d.rectangle((s * .62, s * .18, s * .72, s * .36), fill=(200, 110, 90, 255), outline=INK, width=w)
    d.rectangle((s * .42, s * .64, s * .58, s * .9), fill=(150, 95, 60, 255), outline=INK, width=w)
    d.rectangle((s * .26, s * .55, s * .38, s * .67), fill=(150, 215, 255, 255), outline=INK, width=w)
    d.rectangle((s * .64, s * .55, s * .76, s * .67), fill=(150, 215, 255, 255), outline=INK, width=w)


def m_llave(d, s, cols):
    w = _w(s)
    d.ellipse((s * .1, s * .3, s * .48, s * .68), fill=(255, 205, 70, 255), outline=INK, width=w)
    d.ellipse((s * .22, s * .42, s * .36, s * .56), fill=(0, 0, 0, 0), outline=INK, width=w)
    d.rectangle((s * .46, s * .44, s * .92, s * .54), fill=(255, 205, 70, 255), outline=INK, width=w)
    for x in (.7, .82):
        d.rectangle((s * x, s * .54, s * (x + .07), s * .66), fill=(255, 205, 70, 255), outline=INK, width=w)


def m_moneda(d, s, cols):
    w = _w(s)
    d.ellipse((s * .1, s * .1, s * .9, s * .9), fill=(255, 200, 50, 255), outline=(176, 118, 0, 255), width=w * 2)
    d.ellipse((s * .2, s * .2, s * .8, s * .8), outline=(230, 160, 20, 255), width=w)
    d.text((s * .5, s * .52), '€', font=font(s * .5), fill=(176, 118, 0, 255), anchor='mm')
    d.arc((s * .22, s * .18, s * .6, s * .5), 200, 260, fill=(255, 240, 180, 255), width=w * 2)


def m_hucha(d, s, cols):
    w = _w(s)
    pink = (255, 150, 185, 255)
    for x in (.3, .62):
        d.rectangle((s * x, s * .72, s * (x + .1), s * .88), fill=pink, outline=INK, width=w)
    d.polygon([(s * .3, s * .38), (s * .36, s * .16), (s * .48, s * .34)], fill=pink, outline=INK, width=w)
    d.ellipse((s * .12, s * .3, s * .84, s * .8), fill=pink, outline=INK, width=w)
    d.ellipse((s * .76, s * .46, s * .96, s * .64), fill=(255, 175, 200, 255), outline=INK, width=w)
    for x in (.83, .89):
        d.ellipse((s * x - w, s * .55 - w, s * x + w, s * .55 + w), fill=INK)
    d.ellipse((s * .6, s * .42, s * .66, s * .48), fill=INK)
    d.rounded_rectangle((s * .4, s * .32, s * .56, s * .36), radius=w, fill=INK)
    d.ellipse((s * .38, s * .02, s * .58, s * .22), fill=(255, 200, 50, 255), outline=(176, 118, 0, 255), width=w)


def m_billete(d, s, cols):
    w = _w(s)
    d.rounded_rectangle((s * .06, s * .26, s * .94, s * .74), radius=s * .05, fill=(150, 220, 160, 255), outline=INK, width=w)
    d.ellipse((s * .36, s * .34, s * .64, s * .66), fill=(110, 190, 125, 255), outline=INK, width=w)
    d.text((s * .5, s * .5), '€', font=font(s * .22), fill=INK, anchor='mm')
    for x in (.16, .84):
        d.ellipse((s * x - s * .04, s * .46, s * x + s * .04, s * .54), fill=(110, 190, 125, 255))


def m_euro(d, s, cols):
    f = font(s * .9)
    d.text((s * .54, s * .56), '€', font=f, fill=INK, anchor='mm')
    d.text((s * .5, s * .52), '€', font=f, fill=rgba(cols[1]), anchor='mm', stroke_width=_w(s), stroke_fill=INK)


def m_grafica(d, s, cols):
    w = _w(s, .05)
    for i, (h, c) in enumerate(((.3, cols[0]), (.5, cols[1]), (.75, cols[2]))):
        x = .14 + i * .26
        d.rectangle((s * x, s * (.9 - h), s * (x + .2), s * .9), fill=rgba(c), outline=INK, width=_w(s))
    d.line((s * .1, s * .62, s * .4, s * .42, s * .6, s * .5, s * .88, s * .16), fill=(40, 170, 90, 255), width=w, joint='curve')
    d.polygon([(s * .94, s * .08), (s * .76, s * .12), (s * .9, s * .26)], fill=(40, 170, 90, 255))


def m_tarjeta(d, s, cols):
    w = _w(s)
    d.rounded_rectangle((s * .06, s * .22, s * .94, s * .78), radius=s * .07, fill=rgba(cols[0]), outline=INK, width=w)
    d.rectangle((s * .06, s * .34, s * .94, s * .44), fill=INK)
    d.rounded_rectangle((s * .14, s * .52, s * .3, s * .64), radius=s * .02, fill=(255, 210, 80, 255), outline=INK, width=w // 2)
    for x in (.62, .72):
        d.ellipse((s * x, s * .58, s * (x + .14), s * .72), fill=(255, 255, 255, 170))


def m_reloj(d, s, cols, hands=True):
    w = _w(s, .045)
    d.ellipse((s * .06, s * .06, s * .94, s * .94), fill=rgba(cols[0]), outline=INK, width=w)
    d.ellipse((s * .15, s * .15, s * .85, s * .85), fill=(255, 252, 240, 255), outline=INK, width=_w(s, .02))
    for i in range(12):
        a = i * math.pi / 6
        r0, r1 = (.27, .33) if i % 3 else (.24, .33)
        d.line((s * (.5 + r0 * math.sin(a)), s * (.5 - r0 * math.cos(a)), s * (.5 + r1 * math.sin(a)),
                s * (.5 - r1 * math.cos(a))), fill=INK, width=_w(s, .03 if i % 3 == 0 else .018))
    if hands:
        d.line((s * .5, s * .5, s * .5, s * .26), fill=INK, width=_w(s, .045))
        d.line((s * .5, s * .5, s * .66, s * .58), fill=rgba(cols[1]), width=_w(s, .045))
        d.ellipse((s * .46, s * .46, s * .54, s * .54), fill=INK)


def m_reloj_arena(d, s, cols):
    w = _w(s)
    sand = (255, 200, 90, 255)
    d.rectangle((s * .2, s * .06, s * .8, s * .14), fill=(170, 110, 70, 255), outline=INK, width=w)
    d.rectangle((s * .2, s * .86, s * .8, s * .94), fill=(170, 110, 70, 255), outline=INK, width=w)
    d.polygon([(s * .28, s * .14), (s * .72, s * .14), (s * .53, s * .5), (s * .72, s * .86), (s * .28, s * .86),
               (s * .47, s * .5)], fill=(220, 245, 255, 255), outline=INK, width=w)
    d.polygon([(s * .38, s * .3), (s * .62, s * .3), (s * .5, s * .48)], fill=sand)
    d.polygon([(s * .32, s * .84), (s * .68, s * .84), (s * .5, s * .66)], fill=sand)
    d.line((s * .5, s * .5, s * .5, s * .7), fill=sand, width=w)


def m_calendario(d, s, cols):
    w = _w(s)
    d.rounded_rectangle((s * .1, s * .16, s * .9, s * .9), radius=s * .06, fill=(255, 255, 255, 255), outline=INK, width=w)
    d.rounded_rectangle((s * .1, s * .16, s * .9, s * .36), radius=s * .06, fill=rgba(cols[0]), outline=INK, width=w)
    for x in (.3, .7):
        d.rounded_rectangle((s * (x - .03), s * .08, s * (x + .03), s * .24), radius=w, fill=INK)
    for i in range(3):
        for j in range(4):
            x, y = .2 + j * .18, .46 + i * .14
            c = rgba(cols[1]) if (i, j) == (1, 2) else (225, 220, 230, 255)
            d.rounded_rectangle((s * x, s * y, s * (x + .12), s * (y + .09)), radius=w, fill=c)


def m_movil(d, s, cols):
    w = _w(s)
    d.rounded_rectangle((s * .26, s * .06, s * .74, s * .94), radius=s * .08, fill=(55, 55, 70, 255), outline=INK, width=w)
    d.rounded_rectangle((s * .31, s * .14, s * .69, s * .82), radius=s * .03, fill=(130, 200, 255, 255))
    for i, c in enumerate(((255, 120, 120), (255, 210, 90), (120, 220, 150), (200, 150, 255), (255, 160, 90), (120, 200, 255))):
        x, y = .36 + (i % 2) * .16, .22 + (i // 2) * .17
        d.rounded_rectangle((s * x, s * y, s * (x + .12), s * (y + .12)), radius=s * .03, fill=c + (255,))
    d.ellipse((s * .46, s * .85, s * .54, s * .91), fill=(200, 200, 210, 255))


def m_wifi(d, s, cols):
    for i, r in enumerate((.42, .3, .18)):
        d.arc((s * (.5 - r), s * (.66 - r), s * (.5 + r), s * (.66 + r)), 222, 318, fill=rgba(cols[i % len(cols)]),
              width=_w(s, .08))
    d.ellipse((s * .43, s * .62, s * .57, s * .76), fill=rgba(cols[0]))


def m_nube(d, s, cols):
    c = (255, 255, 255, 255)
    for (x, y, r) in ((.3, .58, .2), (.5, .44, .26), (.72, .58, .19)):
        d.ellipse((s * (x - r) - 4, s * (y - r) - 4, s * (x + r) + 4, s * (y + r) + 4), fill=INK)
    d.rounded_rectangle((s * .1 - 4, s * .56 - 4, s * .9 + 4, s * .8 + 4), radius=s * .12, fill=INK)
    for (x, y, r) in ((.3, .58, .2), (.5, .44, .26), (.72, .58, .19)):
        d.ellipse((s * (x - r), s * (y - r), s * (x + r), s * (y + r)), fill=c)
    d.rounded_rectangle((s * .1, s * .56, s * .9, s * .8), radius=s * .12, fill=c)


def m_candado(d, s, cols):
    w = _w(s, .05)
    d.arc((s * .28, s * .1, s * .72, s * .6), 180, 360, fill=(160, 165, 180, 255), width=_w(s, .1))
    d.line((s * .28 + w, s * .35, s * .28 + w, s * .45), fill=(160, 165, 180, 255), width=_w(s, .1))
    d.line((s * .72 - w, s * .35, s * .72 - w, s * .45), fill=(160, 165, 180, 255), width=_w(s, .1))
    d.rounded_rectangle((s * .18, s * .42, s * .82, s * .9), radius=s * .08, fill=rgba(cols[1]), outline=INK, width=_w(s))
    d.ellipse((s * .44, s * .55, s * .56, s * .67), fill=INK)
    d.rectangle((s * .48, s * .62, s * .52, s * .76), fill=INK)


def m_corazon(d, s, cols):
    c = rgba(cols[0])
    d.ellipse((s * .1, s * .18, s * .52, s * .6), fill=c)
    d.ellipse((s * .48, s * .18, s * .9, s * .6), fill=c)
    d.polygon([(s * .13, s * .5), (s * .87, s * .5), (s * .5, s * .9)], fill=c)
    d.ellipse((s * .22, s * .28, s * .34, s * .4), fill=(255, 255, 255, 150))


def m_estrella(d, s, cols):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = .44 if i % 2 == 0 else .2
        pts.append((s * (.5 + r * math.cos(a)), s * (.52 + r * math.sin(a))))
    d.polygon(pts, fill=rgba(cols[1]), outline=INK, width=_w(s))


def m_bombilla(d, s, cols):
    w = _w(s)
    d.ellipse((s * .22, s * .06, s * .78, s * .62), fill=(255, 228, 90, 255), outline=INK, width=w)
    d.rectangle((s * .38, s * .6, s * .62, s * .82), fill=(170, 170, 185, 255), outline=INK, width=w)
    d.arc((s * .36, s * .22, s * .64, s * .5), 200, 340, fill=(255, 160, 40, 255), width=w)


def m_cafe(d, s, cols):
    w = _w(s)
    d.arc((s * .56, s * .4, s * .86, s * .7), 270, 90, fill=INK, width=_w(s, .07))
    d.rounded_rectangle((s * .16, s * .34, s * .7, s * .86), radius=s * .1, fill=rgba(cols[0]), outline=INK, width=w)
    d.rectangle((s * .22, s * .34, s * .64, s * .42), fill=(120, 70, 40, 255))
    for x in (.32, .5):
        d.arc((s * (x - .06), s * .06, s * (x + .06), s * .3), 90, 270, fill=(255, 255, 255, 200), width=w)


def m_galleta(d, s, cols):
    d.ellipse((s * .08, s * .08, s * .92, s * .92), fill=(225, 170, 95, 255), outline=(160, 100, 45, 255), width=_w(s))
    for (x, y) in ((.3, .3), (.6, .28), (.45, .55), (.7, .6), (.3, .68)):
        d.ellipse((s * (x - .06), s * (y - .05), s * (x + .06), s * (y + .05)), fill=(95, 55, 30, 255))


def m_maleta(d, s, cols):
    w = _w(s)
    d.rounded_rectangle((s * .36, s * .1, s * .64, s * .3), radius=s * .05, outline=INK, width=_w(s, .06))
    d.rounded_rectangle((s * .1, s * .24, s * .9, s * .86), radius=s * .08, fill=rgba(cols[0]), outline=INK, width=w)
    for x in (.3, .7):
        d.rectangle((s * (x - .03), s * .24, s * (x + .03), s * .86), fill=rgba(cols[2]))
    d.ellipse((s * .2, s * .4, s * .36, s * .56), fill=(255, 255, 255, 220))


def m_sol(d, s, cols):
    c = (255, 205, 60, 255)
    for i in range(12):
        a = i * math.pi / 6
        d.line((s * (.5 + .34 * math.cos(a)), s * (.5 + .34 * math.sin(a)), s * (.5 + .47 * math.cos(a)),
                s * (.5 + .47 * math.sin(a))), fill=(255, 170, 40, 255), width=_w(s, .06))
    d.ellipse((s * .2, s * .2, s * .8, s * .8), fill=c, outline=(240, 150, 30, 255), width=_w(s))


def m_pesa(d, s, cols):
    w = _w(s)
    d.rectangle((s * .2, s * .46, s * .8, s * .54), fill=(150, 150, 165, 255), outline=INK, width=w)
    for x in (.1, .74):
        d.rounded_rectangle((s * x, s * .26, s * (x + .16), s * .74), radius=s * .04, fill=rgba(cols[0]), outline=INK, width=w)


def m_coche(d, s, cols):
    w = _w(s)
    d.polygon([(s * .26, s * .46), (s * .36, s * .26), (s * .66, s * .26), (s * .78, s * .46)], fill=(200, 235, 255, 255),
              outline=INK, width=w)
    d.rounded_rectangle((s * .06, s * .44, s * .94, s * .72), radius=s * .1, fill=rgba(cols[0]), outline=INK, width=w)
    for x in (.26, .74):
        d.ellipse((s * (x - .12), s * .6, s * (x + .12), s * .84), fill=(60, 60, 70, 255), outline=INK, width=w)
        d.ellipse((s * (x - .05), s * .67, s * (x + .05), s * .77), fill=(200, 200, 210, 255))
    d.ellipse((s * .84, s * .5, s * .92, s * .58), fill=(255, 230, 120, 255))


def m_mensaje(d, s, cols):
    w = _w(s)
    d.rounded_rectangle((s * .08, s * .14, s * .92, s * .7), radius=s * .14, fill=rgba(cols[1]), outline=INK, width=w)
    d.polygon([(s * .24, s * .66), (s * .44, s * .68), (s * .18, s * .88)], fill=rgba(cols[1]), outline=INK)
    for x in (.3, .5, .7):
        d.ellipse((s * (x - .06), s * .36, s * (x + .06), s * .48), fill=(255, 255, 255, 255))


def m_globo(d, s, cols, i=0):
    c = rgba(cols[i % len(cols)])
    d.line((s * .5, s * .74, s * .46, s * .98), fill=INK, width=_w(s, .02))
    d.ellipse((s * .2, s * .04, s * .8, s * .74), fill=c, outline=INK, width=_w(s))
    d.polygon([(s * .45, s * .78), (s * .55, s * .78), (s * .5, s * .72)], fill=c)
    d.ellipse((s * .32, s * .14, s * .44, s * .3), fill=(255, 255, 255, 140))


def m_regalo(d, s, cols):
    w = _w(s)
    d.rectangle((s * .14, s * .4, s * .86, s * .9), fill=rgba(cols[0]), outline=INK, width=w)
    d.rectangle((s * .08, s * .3, s * .92, s * .44), fill=rgba(cols[0]), outline=INK, width=w)
    d.rectangle((s * .44, s * .3, s * .56, s * .9), fill=rgba(cols[1]))
    d.ellipse((s * .26, s * .12, s * .5, s * .32), outline=rgba(cols[1]), width=_w(s, .06))
    d.ellipse((s * .5, s * .12, s * .74, s * .32), outline=rgba(cols[1]), width=_w(s, .06))


def m_factura(d, s, cols):
    w = _w(s)
    pts = [(s * .2, s * .06), (s * .8, s * .06), (s * .8, s * .9)]
    for i in range(6):
        pts.append((s * (.8 - (i + .5) * .1), s * (.94 if i % 2 == 0 else .88)))
    pts += [(s * .2, s * .9)]
    d.polygon(pts, fill=(255, 255, 255, 255), outline=INK, width=w)
    for i, y in enumerate((.2, .32, .44, .56)):
        d.line((s * .3, s * y, s * (.7 if i % 2 else .6), s * y), fill=(190, 185, 200, 255), width=w)
    d.text((s * .62, s * .74), '€', font=font(s * .2), fill=rgba(cols[0]), anchor='mm')


def m_tele(d, s, cols):
    w = _w(s)
    d.line((s * .4, s * .06, s * .5, s * .2, s * .62, s * .04), fill=INK, width=w)
    d.rounded_rectangle((s * .08, s * .2, s * .92, s * .8), radius=s * .08, fill=(60, 60, 75, 255), outline=INK, width=w)
    d.rounded_rectangle((s * .14, s * .26, s * .86, s * .74), radius=s * .04, fill=rgba(cols[1]))
    d.polygon([(s * .44, s * .38), (s * .44, s * .62), (s * .62, s * .5)], fill=(255, 255, 255, 255))
    d.rectangle((s * .3, s * .8, s * .7, s * .86), fill=INK)


def m_like(d, s, cols):
    d.ellipse((s * .06, s * .06, s * .94, s * .94), fill=rgba(cols[1]), outline=INK, width=_w(s))
    d.rounded_rectangle((s * .26, s * .44, s * .38, s * .74), radius=s * .02, fill=(255, 255, 255, 255))
    d.rounded_rectangle((s * .4, s * .42, s * .72, s * .74), radius=s * .06, fill=(255, 255, 255, 255))
    d.rounded_rectangle((s * .44, s * .2, s * .56, s * .5), radius=s * .05, fill=(255, 255, 255, 255))


def m_planta(d, s, cols):
    w = _w(s)
    g1, g2 = (70, 175, 95, 255), (110, 205, 120, 255)
    for a, c in ((-60, g1), (-20, g2), (20, g1), (60, g2), (0, g1)):
        r = math.radians(a)
        x, y = .5 + .3 * math.sin(r), .44 - .28 * math.cos(r)
        d.ellipse((s * (x - .12), s * (y - .2), s * (x + .12), s * (y + .2)), fill=c, outline=INK, width=w)
    d.polygon([(s * .28, s * .6), (s * .72, s * .6), (s * .66, s * .96), (s * .34, s * .96)], fill=rgba(cols[0]),
              outline=INK, width=w)
    d.rectangle((s * .26, s * .58, s * .74, s * .66), fill=rgba(cols[0]), outline=INK, width=w)


MOTIVOS = {'casa': m_casa, 'llave': m_llave, 'moneda': m_moneda, 'hucha': m_hucha, 'billete': m_billete,
           'euro': m_euro, 'grafica': m_grafica, 'tarjeta': m_tarjeta, 'reloj': m_reloj, 'reloj_arena': m_reloj_arena,
           'calendario': m_calendario, 'movil': m_movil, 'wifi': m_wifi, 'nube': m_nube, 'candado': m_candado,
           'corazon': m_corazon, 'estrella': m_estrella, 'bombilla': m_bombilla, 'cafe': m_cafe,
           'galleta': m_galleta, 'maleta': m_maleta, 'sol': m_sol, 'pesa': m_pesa, 'coche': m_coche,
           'mensaje': m_mensaje, 'globo': m_globo, 'regalo': m_regalo, 'factura': m_factura, 'tele': m_tele,
           'like': m_like, 'planta': m_planta}
# card icons of the scripts that have no motif of their own
ALIAS = {'banco': 'moneda', 'despertador': 'reloj', 'lunes': 'calendario', 'reunion': 'calendario',
         'maletin': 'maleta', 'oferta': 'regalo', 'ticket': 'factura', 'escudo': 'corazon', 'planeta': 'estrella'}


def sprite(name, size, cols, alpha=255, **kw):
    """A motif as an RGBA image of size x size px, drawn at 4x and shrunk (smooth edges)."""
    name = ALIAS.get(name, name)
    s = int(size * 4)
    im = Image.new('RGBA', (s, s))
    MOTIVOS.get(name, m_estrella)(ImageDraw.Draw(im), s, cols, **kw)
    im = im.resize((max(1, int(size)), max(1, int(size))), Image.LANCZOS)
    if alpha < 255:
        im.putalpha(im.getchannel('A').point(lambda v: v * alpha // 255))
    return im


# ---------------------------------------------------------------- themes
# pared: wall colour at the top and bottom; papel: the little motif of the wallpaper; acentos: bunting, rug, frames;
# ventana: what is seen through the window; cuadros: framed pictures; estante: things on the shelf; flotan: what
# drifts in the air; reloj: a big wall clock whose hands go round
TEMAS = {
    'casa': {'sofa': (170, 120, 225), 'pared': ((140, 220, 190), (196, 240, 214)), 'papel': 'casa', 'acentos': [(255, 120, 90), (255, 200, 60), (120, 170, 255), (190, 120, 230)],
             'ventana': 'ciudad', 'cuadros': ['casa', 'llave'], 'estante': ['hucha', 'casa', 'moneda'],
             'flotan': ['moneda', 'casa', 'llave', 'moneda', 'euro']},
    'dinero': {'sofa': (90, 190, 140), 'pared': ((255, 214, 110), (255, 236, 170)), 'papel': 'euro', 'acentos': [(60, 190, 120), (255, 140, 60), (150, 110, 230), (255, 90, 130)],
               'ventana': 'cielo', 'cuadros': ['grafica', 'billete'], 'estante': ['hucha', 'moneda', 'factura'],
               'flotan': ['moneda', 'billete', 'euro', 'moneda', 'estrella']},
    'tiempo': {'sofa': (120, 95, 215), 'pared': ((255, 196, 120), (255, 226, 170)), 'papel': 'reloj', 'acentos': [(40, 190, 180), (150, 100, 230), (255, 100, 120), (255, 210, 60)],
               'ventana': 'torre', 'cuadros': ['calendario', 'reloj_arena'], 'estante': ['reloj_arena', 'movil', 'calendario'],
               'flotan': ['reloj', 'reloj_arena', 'movil', 'reloj', 'calendario'], 'reloj': True},
    'tecnologia': {'sofa': (255, 150, 90), 'pared': ((180, 160, 255), (214, 204, 255)), 'papel': 'wifi', 'acentos': [(40, 200, 220), (255, 120, 200), (255, 200, 60), (110, 220, 140)],
                   'ventana': 'cielo', 'cuadros': ['wifi', 'like'], 'estante': ['movil', 'tele', 'candado'],
                   'flotan': ['nube', 'like', 'wifi', 'mensaje', 'movil']},
    'trabajo': {'sofa': (255, 180, 60), 'pared': ((120, 200, 240), (180, 228, 250)), 'papel': 'estrella', 'acentos': [(255, 150, 60), (255, 210, 60), (240, 90, 120), (120, 210, 120)],
                'ventana': 'ciudad', 'cuadros': ['calendario', 'grafica'], 'estante': ['maleta', 'cafe', 'reloj'],
                'flotan': ['cafe', 'calendario', 'mensaje', 'estrella', 'reloj'], 'reloj': True},
    'comida': {'sofa': (110, 200, 160), 'pared': ((255, 180, 170), (255, 214, 200)), 'papel': 'galleta', 'acentos': [(255, 200, 60), (90, 200, 150), (255, 120, 90), (150, 120, 230)],
               'ventana': 'cielo', 'cuadros': ['cafe', 'galleta'], 'estante': ['cafe', 'galleta', 'planta'],
               'flotan': ['galleta', 'cafe', 'corazon', 'estrella', 'galleta']},
    'deporte': {'sofa': (255, 150, 70), 'pared': ((150, 230, 140), (200, 245, 190)), 'papel': 'estrella', 'acentos': [(255, 120, 60), (60, 160, 240), (255, 210, 60), (230, 80, 150)],
                'ventana': 'cielo', 'cuadros': ['pesa', 'estrella'], 'estante': ['pesa', 'reloj', 'planta'],
                'flotan': ['pesa', 'estrella', 'corazon', 'pesa', 'estrella']},
    'viaje': {'sofa': (255, 175, 80), 'pared': ((120, 220, 235), (190, 240, 245)), 'papel': 'sol', 'acentos': [(255, 140, 60), (255, 210, 60), (240, 90, 150), (90, 200, 120)],
              'ventana': 'cielo', 'cuadros': ['sol', 'maleta'], 'estante': ['maleta', 'calendario', 'planta'],
              'flotan': ['sol', 'nube', 'maleta', 'estrella', 'globo']},
    'coche': {'sofa': (150, 110, 225), 'pared': ((255, 200, 120), (255, 230, 180)), 'papel': 'coche', 'acentos': [(80, 170, 240), (255, 100, 90), (120, 210, 120), (190, 120, 230)],
              'ventana': 'ciudad', 'cuadros': ['coche', 'factura'], 'estante': ['coche', 'moneda', 'llave'],
              'flotan': ['coche', 'moneda', 'llave', 'factura', 'estrella']},
    'amigos': {'sofa': (255, 190, 80), 'pared': ((255, 170, 210), (255, 210, 230)), 'papel': 'corazon', 'acentos': [(255, 200, 60), (90, 200, 220), (150, 110, 230), (110, 210, 120)],
               'ventana': 'cielo', 'cuadros': ['corazon', 'mensaje'], 'estante': ['regalo', 'movil', 'planta'],
               'flotan': ['mensaje', 'corazon', 'globo', 'estrella', 'mensaje']},
    'fiesta': {'sofa': (110, 200, 150), 'pared': ((255, 210, 120), (255, 232, 180)), 'papel': 'estrella', 'acentos': [(255, 110, 130), (80, 180, 240), (110, 210, 120), (190, 120, 230)],
               'ventana': 'cielo', 'cuadros': ['estrella', 'corazon'], 'estante': ['regalo', 'planta', 'bombilla'],
               'flotan': ['estrella', 'globo', 'corazon', 'estrella', 'bombilla']},
}
# words of a script -> theme (the tema counts three times, the title twice; the first theme wins a tie)
PALABRAS = {
    'casa': ['hipoteca', 'casa', 'vivienda', 'piso', 'alquiler', 'hogar', 'mudanza'],
    'tiempo': ['tiempo', 'reloj', 'lunes', 'prisa', 'hora', 'horas', 'tarde', 'despertador', 'calendario'],
    'dinero': ['dinero', 'salario', 'sueldo', 'bruto', 'neto', 'inflacion', 'comision', 'banco', 'oferta', 'ofertas',
               'descuento', 'impuesto', 'impuestos', 'pension', 'jubilacion', 'tarjeta', 'credito', 'bizum', 'seguro',
               'ahorro', 'hucha', 'factura', 'moneda', 'billetes', 'finanzas', 'precio'],
    'tecnologia': ['movil', 'cookies', 'contrasena', 'contrasenas', 'nube', 'actualizacion', 'actualizaciones',
                   'plataformas', 'suscripciones', 'suscripcion', 'whatsapp', 'wifi', 'internet', 'app', 'digitales'],
    'trabajo': ['trabajo', 'reunion', 'reuniones', 'entrevista', 'networking', 'oficina', 'jefe', 'vidaadulta'],
    'comida': ['cafe', 'galleta', 'cocina', 'comida', 'cena', 'desayuno'],
    'deporte': ['gimnasio', 'deporte', 'pesa', 'correr'],
    'viaje': ['vacaciones', 'viaje', 'maleta', 'playa'],
    'coche': ['coche', 'parking', 'gasolina', 'aparcar'],
    'amigos': ['quedar', 'amigos', 'grupo', 'padres', 'mensaje'],
}


def _norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(ch if ch.isalnum() else ' ' for ch in s if unicodedata.category(ch) != 'Mn')


def elegir(g):
    """Theme name of a script (dict of content/guiones): its "fondo" if set, else the best match of its words."""
    if g.get('fondo') in TEMAS:
        return g['fondo']
    icons = ' '.join(l['tarjeta'].get('icono', '') for l in g.get('lineas', []) if 'tarjeta' in l)
    parts = [(g.get('tema', ''), 3), (g.get('titulo', ''), 2), (' '.join(g.get('hashtags', [])), 1), (icons, 1)]
    score = {t: 0 for t in PALABRAS}
    for text, wgt in parts:
        words = _norm(text).split()
        for t, keys in PALABRAS.items():
            score[t] += wgt * sum(w in keys for w in words)
    best = max(score, key=lambda t: score[t])     # dicts keep their order: the first one wins a tie
    return best if score[best] > 0 else 'fiesta'


# ---------------------------------------------------------------- the set
def paste(img, sp, x, y, rot=0):
    """Paste a sprite centred on world point (x, y), its size already in set pixels."""
    if rot:
        sp = sp.rotate(rot, resample=Image.BICUBIC, expand=True)
    px, py = P(x, y)
    img.alpha_composite(sp, (int(px - sp.width / 2), int(py - sp.height / 2)))


def wall(img, d, th, w, h, rng):
    top, bot = th['pared']
    yy = np.linspace(0, 1, h)[:, None, None]
    bg = np.array(top, float) * (1 - yy) + np.array(bot, float) * yy
    img.paste(Image.fromarray(np.broadcast_to(bg, (h, w, 3)).astype(np.uint8)).convert('RGBA'))
    # wallpaper: the theme's motif, small and pale, in a staggered grid
    tile = sprite(th['papel'], 46 * K, [mix(c, (255, 255, 255), .3) for c in th['acentos']], alpha=70)
    step = 150
    for j, y in enumerate(range(-MARGIN, FLOOR - 380, step)):
        for x in range(-MARGIN + (step // 2) * (j % 2), W + MARGIN, step):
            paste(img, tile, x, y, rot=rng.uniform(-14, 14))
    # wainscot: a lighter band with panels and a rail
    dado = FLOOR - 400
    light = mix(bot, (255, 255, 255), .45)
    d.rectangle(box(-MARGIN, dado, W + MARGIN, FLOOR), fill=rgba(light))
    for x in range(-MARGIN + 40, W + MARGIN, 230):
        d.rounded_rectangle(box(x, dado + 60, x + 190, FLOOR - 50), radius=14 * K, outline=rgba(mix(light, top, .35)),
                            width=4 * K)
    d.rectangle(box(-MARGIN, dado - 16, W + MARGIN, dado + 10), fill=(255, 255, 255, 255))
    d.line((*P(-MARGIN, dado + 10), *P(W + MARGIN, dado + 10)), fill=rgba(mix(top, (0, 0, 0), .2)), width=3 * K)


def floor(img, d, th, w, h):
    wood_a, wood_b = (232, 176, 120), (214, 156, 102)
    d.rectangle(box(-MARGIN, FLOOR, W + MARGIN, H + MARGIN), fill=rgba(wood_a))
    for i, y in enumerate(range(FLOOR, H + MARGIN, 70)):
        d.rectangle(box(-MARGIN, y, W + MARGIN, y + 35), fill=rgba(wood_b if i % 2 else wood_a))
        off = 140 * (i % 3)
        for x in range(-MARGIN + off, W + MARGIN, 420):
            d.line((*P(x, y), *P(x, y + 70)), fill=(190, 135, 90, 255), width=2 * K)
    d.rectangle(box(-MARGIN, FLOOR - 26, W + MARGIN, FLOOR), fill=(255, 255, 255, 255))      # skirting board
    d.line((*P(-MARGIN, FLOOR), *P(W + MARGIN, FLOOR)), fill=(170, 120, 80, 255), width=3 * K)
    # a round rug under the kids, in stripes of the theme's colours
    a = th['acentos']
    for i, (rx, ry) in enumerate(((520, 120), (470, 100), (410, 82), (340, 64))):
        d.ellipse(box(545 - rx, 1640 - ry, 545 + rx, 1640 + ry), fill=rgba(a[i % len(a)]),
                  outline=INK if i == 0 else None, width=3 * K if i == 0 else 0)


def window(img, d, th, rng):
    x0, y0, x1, y1 = 385, 300, 705, 860
    sky_t, sky_b = (110, 190, 255), (200, 236, 255)
    view = Image.new('RGBA', (int((x1 - x0) * K), int((y1 - y0) * K)))
    vh, vw = view.height, view.width
    yy = np.linspace(0, 1, vh)[:, None, None]
    view.paste(Image.fromarray((np.array(sky_t, float) * (1 - yy) + np.array(sky_b, float) * yy)
                               .repeat(vw, 1).astype(np.uint8)).convert('RGBA'))
    v = ImageDraw.Draw(view)
    sun = sprite('sol', 170 * K, th['acentos'])
    view.alpha_composite(sun, (int(vw * .68), int(vh * .04)))
    for (cx, cy, sz) in ((.18, .2, 150), (.55, .34, 120)):
        cl = sprite('nube', sz * K, th['acentos'])
        view.alpha_composite(cl, (int(vw * cx), int(vh * cy)))
    kind = th['ventana']
    if kind in ('ciudad', 'torre'):
        # a row of colourful little houses and blocks
        x = -20
        i = 0
        while x < vw:
            bw = int(rng.uniform(70, 120) * K)
            bh = int(rng.uniform(.18, .38) * vh)
            c = th['acentos'][i % len(th['acentos'])]
            c = mix(c, (255, 255, 255), .25)
            v.rectangle((x, vh - bh, x + bw, vh), fill=rgba(c), outline=INK, width=2 * K)
            v.polygon([(x - 6, vh - bh), (x + bw / 2, vh - bh - bw * .45), (x + bw + 6, vh - bh)],
                      fill=rgba(mix(c, (120, 40, 40), .35)), outline=INK)
            for wy in range(vh - bh + 16 * K, vh - 20 * K, 34 * K):
                for wx in (x + bw * .22, x + bw * .58):
                    v.rectangle((wx, wy, wx + bw * .2, wy + 16 * K), fill=(255, 240, 160, 255))
            x += bw + int(8 * K)
            i += 1
        if kind == 'torre':
            # a clock tower in the middle of the town (it gives the time... that nobody has)
            tx, tw = vw * .38, vw * .24
            v.rectangle((tx, vh * .3, tx + tw, vh), fill=(250, 226, 190, 255), outline=INK, width=3 * K)
            v.polygon([(tx - 10, vh * .3), (tx + tw / 2, vh * .1), (tx + tw + 10, vh * .3)], fill=rgba(th['acentos'][0]),
                      outline=INK, width=3 * K)
            ck = sprite('reloj', tw * .8, th['acentos'])
            view.alpha_composite(ck, (int(tx + tw * .1), int(vh * .34)))
    else:
        # green hills and balloons
        for k_, (c, hgt) in enumerate((((140, 215, 120), .3), ((100, 190, 100), .2))):
            v.ellipse((-vw * .3 + k_ * vw * .4, vh * (1 - hgt), vw * (.9 + k_ * .4), vh * (1 + hgt)), fill=rgba(c))
        for k_, (bx, by) in enumerate(((.12, .45), (.3, .55), (.82, .5))):
            b = sprite('globo', 90 * K, th['acentos'], i=k_)
            view.alpha_composite(b, (int(vw * bx), int(vh * by)))
    # frame, cross bars and the sill
    d.rounded_rectangle(box(x0 - 26, y0 - 26, x1 + 26, y1 + 26), radius=18 * K, fill=(255, 255, 255, 255), outline=INK,
                        width=4 * K)
    img.alpha_composite(view, P(x0, y0))
    d.rectangle(box((x0 + x1) / 2 - 9, y0, (x0 + x1) / 2 + 9, y1), fill=(255, 255, 255, 255))
    d.rectangle(box(x0, (y0 + y1) / 2 - 9, x1, (y0 + y1) / 2 + 9), fill=(255, 255, 255, 255))
    d.rounded_rectangle(box(x0 - 50, y1 + 14, x1 + 50, y1 + 44), radius=10 * K, fill=(255, 255, 255, 255), outline=INK,
                        width=3 * K)
    # curtains in the first accent, with ties
    c = th['acentos'][0]
    for side in (-1, 1):
        xa = x0 - 90 if side < 0 else x1 + 10
        pts = [(xa, y0 - 50), (xa + 80, y0 - 50), (xa + 80 - side * 40, y1 - 60), (xa + 60, y1 + 90), (xa + 20, y1 + 90),
               (xa - side * 20 + (0 if side < 0 else 20), (y0 + y1) / 2 + 60)]
        d.polygon([P(*p) for p in pts], fill=rgba(c), outline=INK, width=3 * K)
        for k_ in range(1, 3):
            d.line((*P(xa + 26 * k_, y0 - 40), *P(xa + 26 * k_ - side * 12, y1 + 60)), fill=rgba(mix(c, (0, 0, 0), .2)),
                   width=2 * K)
    d.rounded_rectangle(box(x0 - 120, y0 - 70, x1 + 120, y0 - 44), radius=12 * K, fill=(170, 110, 70, 255), outline=INK,
                        width=3 * K)


def blackboard(img, d, th, rng):
    x0, y0, x1, y1 = 260, 300, 830, 840
    d.rounded_rectangle(box(x0 - 30, y0 - 30, x1 + 30, y1 + 30), radius=16 * K, fill=(185, 125, 75, 255), outline=INK,
                        width=4 * K)
    d.rectangle(box(x0, y0, x1, y1), fill=(52, 110, 84, 255))
    chalk = [(255, 255, 255), (255, 235, 140), (255, 180, 200), (170, 225, 255)]
    for i, name in enumerate(th['flotan'][:4]):
        sp = sprite(name, 120 * K, chalk[i:] + chalk[:i], alpha=200)
        paste(img, sp, x0 + 90 + i * 150, y0 + 120 + (i % 2) * 220, rot=rng.uniform(-10, 10))
    d.rectangle(box(x0 - 40, y1 + 20, x1 + 40, y1 + 44), fill=(160, 105, 60, 255), outline=INK, width=3 * K)


def bunting(img, d, th):
    """A garland of little flags across the top of the wall, in the theme's colours."""
    a = th['acentos']
    for row, (y, sag) in enumerate(((235, 45), (205, 30))):
        xs = list(range(-MARGIN + 40 * row, W + MARGIN, 70))
        pts = [(x, y + sag * math.sin(math.pi * ((x + MARGIN) % 700) / 700)) for x in xs]
        d.line([P(*p) for p in pts], fill=INK, width=2 * K)
        for i, (x, yy) in enumerate(pts[:-1]):
            if row == 1 and i % 2:
                continue
            nx, ny = pts[i + 1]
            d.polygon([P(x + 4, yy), P(nx - 4, ny), P((x + nx) / 2, (yy + ny) / 2 + 58)], fill=rgba(a[(i + row) % len(a)]),
                      outline=INK)


def frame_pic(img, d, th, name, x, y, size, col, rot=0):
    lay = Image.new('RGBA', (int(size * 1.5 * K), int(size * 1.5 * K)))
    ld = ImageDraw.Draw(lay)
    s = lay.width
    ld.rounded_rectangle((s * .1, s * .1, s * .9, s * .9), radius=s * .05, fill=rgba(col), outline=INK, width=3 * K)
    ld.rectangle((s * .18, s * .18, s * .82, s * .82), fill=(255, 252, 240, 255), outline=INK, width=2 * K)
    sp = sprite(name, s * .5, th['acentos'])
    lay.alpha_composite(sp, (int(s * .25), int(s * .25)))
    paste(img, lay, x, y, rot=rot)


def shelf(img, d, th, x0, x1, y):
    d.rounded_rectangle(box(x0, y, x1, y + 26), radius=6 * K, fill=(185, 125, 75, 255), outline=INK, width=3 * K)
    for bx in (x0 + 40, x1 - 60):
        d.polygon([P(bx, y + 26), P(bx + 20, y + 26), P(bx + 20, y + 80)], fill=(160, 105, 60, 255), outline=INK)
    items = th['estante']
    n = len(items)
    for i, name in enumerate(items):
        sz = 120 if i != 1 else 140
        paste(img, sprite(name, sz * K, th['acentos']), x0 + (i + .5) * (x1 - x0) / n, y - sz / 2 + 6)


def furniture(img, d, th, place):
    """The big piece behind the kids: a sofa in the living room, the counter in the kitchen, the bed's headboard in
    the bedroom (their bodies hide most of it, what shows fills the wall with colour)."""
    c = th.get('sofa', th['acentos'][-1])
    dark = mix(c, (40, 20, 50), .25)
    if place == 'cocina':
        d.rectangle(box(-MARGIN, 1180, W + MARGIN, FLOOR), fill=(255, 255, 255, 255))
        for x in range(-MARGIN, W + MARGIN, 60):                    # tiles
            for y in range(1180, 1300, 60):
                d.rectangle(box(x + 3, y + 3, x + 57, y + 57), fill=rgba(mix(c, (255, 255, 255), .55 if (x // 60 + y // 60) % 2 else .75)))
        d.rectangle(box(-MARGIN, 1290, W + MARGIN, 1320), fill=(240, 235, 230, 255), outline=INK, width=3 * K)
        for x in range(-MARGIN, W + MARGIN, 190):
            d.rounded_rectangle(box(x + 8, 1330, x + 182, FLOOR - 20), radius=12 * K, fill=rgba(c), outline=INK, width=3 * K)
            d.rounded_rectangle(box(x + 80, 1360, x + 110, 1372), radius=6 * K, fill=INK)
        return
    if place == 'dormitorio':
        d.rounded_rectangle(box(80, 1120, 1010, FLOOR + 40), radius=80 * K, fill=rgba(c), outline=INK, width=4 * K)
        for i, x in enumerate(range(160, 960, 140)):
            paste(img, sprite('estrella', 70 * K, [(255, 255, 255), mix(c, (255, 255, 255), .5)], alpha=170), x, 1220 + 30 * (i % 2))
        d.rounded_rectangle(box(40, 1400, 1050, FLOOR + 60), radius=30 * K, fill=(255, 255, 255, 255), outline=INK, width=3 * K)
        return
    if place != 'salon':
        return
    d.rounded_rectangle(box(40, 1150, 1050, 1470), radius=70 * K, fill=rgba(c), outline=INK, width=4 * K)
    for x0 in (110, 410, 710):                                     # back cushions
        d.rounded_rectangle(box(x0, 1190, x0 + 270, 1420), radius=50 * K, fill=rgba(mix(c, (255, 255, 255), .12)),
                            outline=rgba(dark), width=3 * K)
    d.rounded_rectangle(box(60, 1380, 1030, 1530), radius=40 * K, fill=rgba(mix(c, (255, 255, 255), .2)), outline=INK,
                        width=4 * K)
    for x0 in (-10, 960):                                           # arms
        d.rounded_rectangle(box(x0, 1260, x0 + 140, 1540), radius=60 * K, fill=rgba(c), outline=INK, width=4 * K)
    a = th['acentos']
    for i, (x, rot) in enumerate(((210, -12), (880, 10))):         # cushions in the theme's colours
        lay = Image.new('RGBA', (180 * K, 180 * K))
        ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle((10 * K, 10 * K, 170 * K, 170 * K), radius=40 * K, fill=rgba(a[i + 1 if i else 1]),
                             outline=INK, width=3 * K)
        lay.alpha_composite(sprite(th['papel'], 90 * K, a), (45 * K, 45 * K))
        paste(img, lay, x, 1330, rot=rot)
    for x in (120, 970):
        d.rounded_rectangle(box(x - 14, 1530, x + 14, FLOOR + 30), radius=6 * K, fill=(120, 80, 50, 255))


def lamp(img, d, th, x):
    c = th['acentos'][1]
    d.rectangle(box(x - 6, 1150, x + 6, FLOOR + 50), fill=INK)
    d.ellipse(box(x - 60, FLOOR + 30, x + 60, FLOOR + 70), fill=(120, 90, 110, 255), outline=INK, width=2 * K)
    d.polygon([P(x - 90, 1160), P(x + 90, 1160), P(x + 55, 1030), P(x - 55, 1030)], fill=rgba(c), outline=INK,
              width=3 * K)


def exterior(img, d, th, w, h, rng, place):
    """Outdoors (calle, parque): sky, sun, clouds, town or trees, ground; the theme in balloons and a big sign."""
    yy = np.linspace(0, 1, h)[:, None, None]
    sky = np.array((90, 180, 255), float) * (1 - yy) + np.array((215, 240, 255), float) * yy
    img.paste(Image.fromarray(np.broadcast_to(sky, (h, w, 3)).astype(np.uint8)).convert('RGBA'))
    paste(img, sprite('sol', 300 * K, th['acentos']), 940, 120)
    for (x, y, s) in ((80, 180, 260), (520, 80, 200), (1200, 300, 230), (-300, 420, 240)):
        paste(img, sprite('nube', s * K, th['acentos']), x, y)
    if place == 'calle':
        x = -MARGIN
        i = 0
        while x < W + MARGIN:
            bw = rng.uniform(170, 260)
            top = rng.uniform(620, 900)
            c = mix(th['acentos'][i % len(th['acentos'])], (255, 255, 255), .35)
            d.rectangle(box(x, top, x + bw, FLOOR), fill=rgba(c), outline=INK, width=3 * K)
            for wy in range(int(top) + 40, FLOOR - 120, 110):
                for wx in (x + bw * .18, x + bw * .58):
                    d.rounded_rectangle(box(wx, wy, wx + bw * .24, wy + 60), radius=6 * K, fill=(255, 244, 180, 255),
                                        outline=INK, width=2 * K)
            d.rectangle(box(x - 6, top - 20, x + bw + 6, top), fill=rgba(mix(c, (0, 0, 0), .25)), outline=INK, width=2 * K)
            x += bw + 14
            i += 1
        ground = (205, 200, 210)
    else:
        for k_, (c, top) in enumerate((((150, 220, 120), 1120), ((110, 200, 100), 1260))):
            d.ellipse(box(-MARGIN - 300 + k_ * 500, top, W + MARGIN + 300 - k_ * 200, top + 1200), fill=rgba(c))
        for x in (-80, 120, 980, 1180):
            d.rectangle(box(x - 18, 1100, x + 18, FLOOR + 10), fill=(150, 95, 60, 255), outline=INK, width=2 * K)
            for (dx, dy, r) in ((0, 960, 130), (-80, 1040, 90), (80, 1040, 90)):
                d.ellipse(box(x + dx - r, dy - r, x + dx + r, dy + r), fill=(80, 180, 100, 255), outline=INK, width=3 * K)
        ground = (130, 205, 110)
    d.rectangle(box(-MARGIN, FLOOR, W + MARGIN, H + MARGIN), fill=rgba(ground))
    d.line((*P(-MARGIN, FLOOR), *P(W + MARGIN, FLOOR)), fill=INK, width=3 * K)
    # the theme on a sign and in balloons
    frame_pic(img, d, th, th['cuadros'][0], 545, 440, 230, th['acentos'][0])
    for k_, (x, y) in enumerate(((60, 620), (180, 520), (930, 560), (1040, 660))):
        paste(img, sprite('globo', 110 * K, th['acentos'], i=k_), x, y)


def make_set(theme, place='salon', seed=7):
    """The whole background of a theme in a place, in world coordinates at K times the size."""
    th = TEMAS[theme]
    rng = np.random.default_rng(seed)
    w, h = (W + 2 * MARGIN) * K, (H + 2 * MARGIN) * K
    img = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(img, 'RGBA')
    if place in ('calle', 'parque'):
        exterior(img, d, th, w, h, rng, place)
    else:
        wall(img, d, th, w, h, rng)
        bunting(img, d, th)
        if place == 'cole':
            blackboard(img, d, th, rng)
        else:
            window(img, d, th, rng)
        a = th['acentos']
        # what the camera sees around the kids: a strip on each side (close ups) and the wall above their heads
        frame_pic(img, d, th, th['cuadros'][0], 70, 520, 200, a[2], rot=4)
        frame_pic(img, d, th, th['cuadros'][1], -150, 820, 170, a[3], rot=-5)
        if not th.get('reloj'):
            frame_pic(img, d, th, th['cuadros'][1], 1020, 430, 190, a[1], rot=-4)
        shelf(img, d, th, 950, 1290, 880)
        furniture(img, d, th, place)
        floor(img, d, th, w, h)
        paste(img, sprite('planta', 280 * K, [a[1]]), 40, FLOOR - 30)
        lamp(img, d, th, 1060)
    # a soft light behind the kids so they stand out, and a gentle vignette
    glow = Image.new('L', (w // 8, h // 8))
    gd = ImageDraw.Draw(glow)
    for (cx, cy, rx, ry) in ((300, 900, 300, 420), (790, 780, 320, 450)):
        gd.ellipse(((cx - rx + MARGIN) * K / 8, (cy - ry + MARGIN) * K / 8, (cx + rx + MARGIN) * K / 8,
                    (cy + ry + MARGIN) * K / 8), fill=150)
    glow = glow.filter(ImageFilter.GaussianBlur(30)).resize((w, h), Image.BILINEAR)
    light = Image.new('RGBA', (w, h), (255, 250, 235, 255))
    light.putalpha(glow)
    img.alpha_composite(light)
    return img


# ---------------------------------------------------------------- the things that move
class Fondo:
    """The set of a script and its life: .frame(z, cx, cy, t) like escena_rig.background(z, cx, cy)."""

    def __init__(self, g=None, theme=None, place=None, seed=7):
        g = g or {}
        self.theme = theme or elegir(g)
        self.place = place or g.get('escenario', 'salon')
        self.th = TEMAS[self.theme]
        self.set = make_set(self.theme, self.place, seed)
        rng = np.random.default_rng(seed + 1)
        # motifs drifting in the air, above the heads and at the sides (never over the faces)
        spots = [(130, 330), (300, 450), (240, 290), (420, 250), (880, 300), (1030, 650), (-20, 760), (1040, 1120),
                 (-30, 1180), (700, 290)]
        self.floaters = []
        for i, (x, y) in enumerate(spots):
            name = self.th['flotan'][i % len(self.th['flotan'])]
            size = rng.uniform(80, 115)
            self.floaters.append({'sp': sprite(name, size * 3, self.th['acentos'], i=i) if name == 'globo'
                                  else sprite(name, size * 3, self.th['acentos']),
                                  'x': x, 'y': y, 'size': size, 'ph': rng.uniform(0, 6.3), 'sp_t': rng.uniform(.5, .9)})
        self.twinkles = [(rng.uniform(-200, 1280), rng.uniform(80, 520), rng.uniform(24, 40), rng.uniform(0, 6.3))
                         for _ in range(14)]
        self.star = sprite('estrella', 120, [(255, 255, 255), (255, 240, 150)])
        self.clock = None
        if self.th.get('reloj') and self.place not in ('calle', 'parque'):
            self.clock = (1000, 400, 230)
            face = sprite('reloj', 230 * K, self.th['acentos'], hands=False)
            paste(self.set, face, 1000, 400)
            s = 600
            hand = Image.new('RGBA', (s, s))
            hd = ImageDraw.Draw(hand)
            hd.rounded_rectangle((s / 2 - 14, s * .2, s / 2 + 14, s / 2 + 20), radius=14, fill=INK)
            self.min_hand = hand
            hand = Image.new('RGBA', (s, s))
            hd = ImageDraw.Draw(hand)
            hd.rounded_rectangle((s / 2 - 16, s * .3, s / 2 + 16, s / 2 + 20), radius=16, fill=rgba(self.th['acentos'][2]),
                                 outline=INK, width=6)
            self.hour_hand = hand

    def to_screen(self, x, y, z, cx, cy):
        return W / 2 + (x - cx) * z, H / 2 + (y - cy) * z

    def frame(self, z, cx, cy, t):
        k = K
        x0, y0 = (cx - W / 2 / z + MARGIN) * k, (cy - H / 2 / z + MARGIN) * k
        img = self.set.transform((W, H), Image.AFFINE, (k / z, 0, x0, 0, k / z, y0), resample=Image.BILINEAR)
        if self.clock:                                  # the hands race round: time flies
            x, y, size = self.clock
            sx, sy = self.to_screen(x, y, z, cx, cy)
            px = int(size * z * .78)
            for hand, turn in ((self.hour_hand, 0.12), (self.min_hand, 0.9)):
                hh = hand.rotate(-360 * turn * t, resample=Image.BICUBIC).resize((px, px), Image.BILINEAR)
                img.alpha_composite(hh, (int(sx - px / 2), int(sy - px / 2)))
            r = max(4, int(10 * z))
            ImageDraw.Draw(img).ellipse((sx - r, sy - r, sx + r, sy + r), fill=INK)
        for (x, y, s, ph) in self.twinkles:
            k_ = 0.5 + 0.5 * math.sin(2.4 * t + ph)
            if k_ < 0.15:
                continue
            sx, sy = self.to_screen(x, y, z, cx, cy)
            px = int(s * z * (0.5 + 0.6 * k_))
            if -px < sx < W + px and -px < sy < H + px:
                st = self.star.resize((px, px), Image.BILINEAR)
                st.putalpha(st.getchannel('A').point(lambda v: int(v * k_ * .9)))
                img.alpha_composite(st, (int(sx - px / 2), int(sy - px / 2)))
        for f in self.floaters:
            u = t * f['sp_t'] + f['ph']
            x = f['x'] + 22 * math.sin(u)
            y = f['y'] + 26 * math.sin(1.3 * u + 1)
            sx, sy = self.to_screen(x, y, z, cx, cy)
            px = int(f['size'] * z)
            if not (-px < sx < W + px and -px < sy < H + px):
                continue
            sp = f['sp'].resize((px, px), Image.BILINEAR).rotate(12 * math.sin(.8 * u), resample=Image.BILINEAR)
            img.alpha_composite(sp, (int(sx - px / 2), int(sy - px / 2)))
        return img


if __name__ == '__main__':
    import json
    a = sys.argv[1:]
    if len(a) == 2:
        g = json.load(open(os.path.join(ROOT, 'content/guiones/es', a[0] + '.json')))
        f = Fondo(g)
    else:
        f = Fondo(theme=a[0], place=a[1])
    print(f.theme, f.place)
    f.frame(1.15, 545, 1040, 1.0).convert('RGB').save(a[-1])
