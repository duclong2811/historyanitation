"""Draw the host character as flat 2D cut-outs (transparent PNGs) for the 2.5D Blender scene.
Original design: round white head, big googly eyes, thick dark outline, flat red-orange hoodie.
Each PNG = one pose + expression (replacement animation). Run: python make_chars.py
"""
import math, os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), 'chars')
W, H = 800, 1200          # design units
FINAL = 2                 # px per unit in the saved PNG (1600x2400)
SS = 2                    # supersampling
K = FINAL * SS
INK = (27, 23, 32, 255); SKIN = (248, 244, 234, 255); HOOD = (214, 74, 51, 255); HOOD_D = (160, 48, 34, 255)
PANTS = (43, 47, 69, 255); HAIR = (52, 36, 30, 255); OL = 14

def P(x, y): return (x * K, y * K)

class Pen:
    def __init__(self):
        self.im = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
    def circle(self, x, y, r, fill, ol=OL):
        if ol: self.d.ellipse([P(x - r - ol / 2, y - r - ol / 2), P(x + r + ol / 2, y + r + ol / 2)], fill=INK)
        self.d.ellipse([P(x - r + ol / 2, y - r + ol / 2), P(x + r - ol / 2, y + r - ol / 2)], fill=fill)
    def ellipse(self, box, fill, ol=OL):
        x0, y0, x1, y1 = box
        if ol: self.d.ellipse([P(x0 - ol / 2, y0 - ol / 2), P(x1 + ol / 2, y1 + ol / 2)], fill=INK)
        self.d.ellipse([P(x0 + ol / 2, y0 + ol / 2), P(x1 - ol / 2, y1 - ol / 2)], fill=fill)
    def line(self, pts, w, fill, ol=OL):
        pts = [P(*p) for p in pts]
        for width, col in ([(w + 2 * ol, INK)] if ol else []) + [(w, fill)]:
            self.d.line(pts, fill=col, width=int(width * K), joint='curve')
            for p in pts: r = width * K / 2; self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)
    def poly(self, pts, fill, ol=OL):
        pts = [P(*p) for p in pts]
        if ol: self.d.polygon(pts, fill=INK, outline=INK, width=int(ol * 2 * K))
        self.d.polygon(pts, fill=fill)
    def save(self, name):
        im = self.im.resize((W * FINAL, H * FINAL), Image.LANCZOS)
        im.save(os.path.join(OUT, name + '.png'))

CX = 400
POSES = {   # (screen-left arm: elbow, hand), (screen-right arm: elbow, hand)
    'relaxed': (((285, 740), (290, 880)), ((515, 740), (510, 880))),
    'type':    (((280, 730), (345, 820)), ((520, 730), (455, 820))),
    'point':   (((285, 740), (290, 880)), ((600, 600), (720, 560))),
    'waveA':   (((285, 740), (290, 880)), ((610, 560), (660, 400))),
    'waveB':   (((285, 740), (290, 880)), ((620, 580), (720, 440))),
    'think':   (((285, 740), (290, 880)), ((600, 700), (470, 520))),
}

def eyes(p, look=(0, 0), big=False, brows='flat'):
    for ex in (CX - 78, CX + 78):
        r = 54 if big else 50
        p.circle(ex, 300, r, SKIN, ol=11)
        pr = 15 if big else 21
        p.d.ellipse([P(ex + look[0] * 22 - pr, 300 + look[1] * 22 - pr), P(ex + look[0] * 22 + pr, 300 + look[1] * 22 + pr)], fill=INK)
        hx, hy = ex + look[0] * 22 - pr * 0.35, 300 + look[1] * 22 - pr * 0.35
        p.d.ellipse([P(hx - 5, hy - 5), P(hx + 5, hy + 5)], fill=SKIN)
    for side in (-1, 1):
        bx = CX + side * 78
        if brows == 'flat':     a, b = (bx - 34, 222), (bx + 34, 222)
        elif brows == 'raised': a, b = (bx - 34, 206), (bx + 34, 200)
        elif brows == 'angry':  a, b = (bx - 34 * side, 232), (bx + 34 * side, 214)
        else:                   a, b = (bx - 34 * side, 212), (bx + 34 * side, 230)   # worried
        if brows == 'raised' and side == -1: a, b = (bx - 34, 200), (bx + 34, 206)
        p.line([a, b], 9, INK, ol=0)

def mouth(p, kind):
    y = 412
    if kind == 'neutral': p.line([(CX - 26, y), (CX + 26, y)], 9, INK, ol=0)
    elif kind == 'flat': p.line([(CX - 18, y + 4), (CX + 18, y + 4)], 9, INK, ol=0)
    elif kind == 'smirk': p.line([(CX - 30, y + 2), (CX + 10, y + 4), (CX + 34, y - 10)], 9, INK, ol=0)
    elif kind == 'smile': p.d.arc([P(CX - 42, y - 40), P(CX + 42, y + 22)], 20, 160, fill=INK, width=int(9 * K))
    elif kind == 'grin':
        p.d.chord([P(CX - 52, y - 36), P(CX + 52, y + 40)], 0, 180, fill=INK)
        p.d.chord([P(CX - 38, y - 8), P(CX + 38, y + 26)], 0, 180, fill=(220, 90, 90, 255))
    elif kind == 'o': p.ellipse((CX - 20, y - 18, CX + 20, y + 26), (120, 40, 40, 255), ol=9)

def hair(p):
    pts = []
    for i in range(0, 25):
        a = math.pi * (1.06 + 0.88 * i / 24); r = 222 + (14 if i % 3 == 0 else 0)
        pts.append((CX + math.cos(a) * r, 300 + math.sin(a) * r))
    bang = [(CX + 190, 200), (CX + 120, 168), (CX + 80, 196), (CX + 30, 150), (CX - 20, 190), (CX - 80, 156), (CX - 120, 196), (CX - 190, 200)]
    p.poly(pts + bang, HAIR)

def body(p, pose):
    # legs + shoes
    for lx in (CX - 52, CX + 52):
        p.poly([(lx - 42, 890), (lx + 42, 890), (lx + 40, 1130), (lx - 40, 1130)], PANTS)
        p.ellipse((lx - 58 + (0 if lx < CX else 16), 1112, lx + 42 + (0 if lx < CX else 16), 1168), (30, 26, 34, 255))
    # hoodie torso
    p.poly([(CX - 118, 540), (CX + 118, 540), (CX + 142, 910), (CX - 142, 910)], HOOD)
    p.line([(CX - 120, 905), (CX + 120, 905)], 26, HOOD_D, ol=0)
    p.d.rounded_rectangle([P(CX - 80, 770), P(CX + 80, 860)], radius=20 * K, outline=HOOD_D, width=int(7 * K))
    p.ellipse((CX - 120, 500, CX + 120, 590), HOOD_D)                      # hood collar
    for sx in (-28, 28): p.line([(CX + sx, 580), (CX + sx, 660)], 6, SKIN, ol=0)
    # arms
    (le, lh), (re, rh) = POSES[pose]
    for sh, el, hd in (((CX - 105, 590), le, lh), ((CX + 105, 590), re, rh)):
        p.line([sh, el, hd], 58, HOOD)
        p.circle(hd[0], hd[1], 34, SKIN, ol=11)

def draw(name, pose='relaxed', look=(0, 0), brows='flat', mth='neutral', big=False):
    p = Pen()
    body(p, pose)
    p.circle(CX, 300, 212, SKIN)          # head
    hair(p)
    eyes(p, look, big, brows)
    mouth(p, mth)
    if pose == 'think':                    # hand on chin drawn over the face
        p.circle(470, 470, 34, SKIN, ol=11)
    p.save(name)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    draw('type', 'type', look=(0.2, 0.9), mth='neutral')
    draw('type_cam', 'type', look=(0, 0), mth='smirk')
    draw('type_surprised', 'type', look=(0.4, -0.6), brows='raised', mth='o', big=True)
    draw('neutral', 'relaxed', look=(0, 0))
    draw('smile', 'relaxed', look=(0, 0), mth='smile')
    draw('point', 'point', look=(0.9, -0.1), mth='grin')
    draw('waveA', 'waveA', mth='grin')
    draw('waveB', 'waveB', mth='grin')
    draw('think', 'think', look=(-0.6, -0.7), brows='worried', mth='flat')
    draw('determined', 'relaxed', look=(0, 0), brows='angry', mth='smirk')
    # contact sheet
    names = ['type', 'type_cam', 'type_surprised', 'neutral', 'smile', 'point', 'waveA', 'waveB', 'think', 'determined']
    sheet = Image.new('RGBA', (5 * 400, 2 * 600), (70, 60, 80, 255))
    for i, n in enumerate(names):
        im = Image.open(os.path.join(OUT, n + '.png')).resize((400, 600), Image.LANCZOS)
        sheet.alpha_composite(im, ((i % 5) * 400, (i // 5) * 600))
    sheet.save(os.path.join(OUT, '_sheet.png'))
    print('ok', len(names))
