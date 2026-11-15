"""Flat textures used inside the 3D sets: night city through the window, rug, laptop UI, wall screen thumbnail,
views graph, storyboard sketches. Run: python make_textures.py"""
import os, random, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(__file__); OUT = os.path.join(HERE, 'tex'); CH = os.path.join(HERE, 'chars')
FB = 'C:/Windows/Fonts/seguibl.ttf'; FS = 'C:/Windows/Fonts/segoeuib.ttf'; FM = 'C:/Windows/Fonts/consolab.ttf'
def font(p, s):
    try: return ImageFont.truetype(p, s)
    except OSError: return ImageFont.truetype(FS, s)

def grad(w, h, top, bot):
    im = Image.new('RGB', (w, h)); d = ImageDraw.Draw(im)
    for y in range(h):
        k = y / (h - 1); d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))
    return im

def night_city():
    r = random.Random(4); w, h = 1600, 1200
    im = grad(w, h, (12, 16, 44), (70, 52, 96)); d = ImageDraw.Draw(im)
    for _ in range(260): x, y = r.random() * w, r.random() * h * 0.55; s = r.choice([1, 1, 2, 3]); d.ellipse([x, y, x + s, y + s], fill=(230, 235, 255))
    mx, my = 1150, 260
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow); gd.ellipse([mx - 260, my - 260, mx + 260, my + 260], fill=(190, 200, 255, 70)); glow = glow.filter(ImageFilter.GaussianBlur(80))
    im.paste(glow, (0, 0), glow); d.ellipse([mx - 80, my - 80, mx + 80, my + 80], fill=(248, 244, 225)); d.ellipse([mx - 40, my - 50, mx - 10, my - 20], fill=(225, 220, 200))
    for layer, (col, hmin, hmax, lit) in enumerate([((40, 34, 70), 250, 520, 0.18), ((24, 20, 42), 180, 420, 0.3)]):
        x = -20
        while x < w:
            bw = r.randint(70, 170); bh = r.randint(hmin, hmax); top = h - bh
            d.rectangle([x, top, x + bw, h], fill=col)
            if r.random() < 0.3: d.polygon([(x, top), (x + bw / 2, top - r.randint(30, 80)), (x + bw, top)], fill=col)
            for wy in range(top + 18, h - 10, 34):
                for wx in range(x + 12, x + bw - 14, 26):
                    if r.random() < lit: d.rectangle([wx, wy, wx + 12, wy + 16], fill=r.choice([(255, 200, 120), (255, 220, 150), (255, 180, 100)]))
            x += bw + r.randint(-10, 12)
    im.save(os.path.join(OUT, 'night_city.png'))

def rug():
    w = h = 1024; im = Image.new('RGB', (w, h), (120, 40, 44)); d = ImageDraw.Draw(im)
    d.rectangle([40, 40, w - 40, h - 40], outline=(222, 170, 90), width=26); d.rectangle([110, 110, w - 110, h - 110], outline=(40, 52, 96), width=40)
    for i in range(6):
        for j in range(6):
            cx, cy = 230 + i * 113, 230 + j * 113
            d.polygon([(cx, cy - 40), (cx + 40, cy), (cx, cy + 40), (cx - 40, cy)], fill=(222, 170, 90) if (i + j) % 2 else (40, 52, 96))
    im = im.filter(ImageFilter.GaussianBlur(1.2)); im.save(os.path.join(OUT, 'rug.png'))

def laptop_ui():
    w, h = 1600, 1000; im = Image.new('RGB', (w, h), (16, 20, 32)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 50], fill=(28, 32, 48))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): d.ellipse([20 + i * 34, 15, 40 + i * 34, 35], fill=c)
    pv = grad(720, 430, (40, 30, 70), (150, 80, 70)); im.paste(pv, (30, 80))
    host = Image.open(os.path.join(CH, 'smile.png')).resize((180, 270), Image.LANCZOS); im.paste(host, (300, 230), host)
    f = font(FM, 34); col = [(130, 200, 255), (255, 205, 130), (190, 240, 140), (255, 160, 200), (130, 200, 255)]
    for i, ln in enumerate(["shot('s07', {", "  light: lamp.on(),", "  dust: true,", "  shadow: 'contact',", "})"]): d.text((800, 90 + i * 56), ln, font=f, fill=col[i])
    for r_ in range(4):
        for c in range(9):
            x = 30 + c * 170 + (r_ * 37) % 50; d.rounded_rectangle([x, 560 + r_ * 100, x + 110 + (r_ * c * 13) % 50, 640 + r_ * 100], radius=12, fill=[(214, 74, 51), (58, 110, 165), (242, 194, 26), (138, 90, 214)][r_])
    d.rectangle([620, 545, 628, 990], fill=(255, 70, 60))
    im.save(os.path.join(OUT, 'laptop_ui.png'))

def thumb():
    w, h = 900, 1600; im = grad(w, h, (36, 28, 60), (150, 82, 64)); d = ImageDraw.Draw(im)
    g = Image.new('RGBA', (w, h), (0, 0, 0, 0)); gd = ImageDraw.Draw(g); gd.ellipse([150, 300, 750, 900], fill=(255, 210, 140, 110)); g = g.filter(ImageFilter.GaussianBlur(120)); im.paste(g, (0, 0), g)
    d.rectangle([0, 1080, w, h], fill=(60, 36, 44))
    host = Image.open(os.path.join(CH, 'point.png')).resize((560, 840), Image.LANCZOS); im.paste(host, (120, 520), host)
    d.polygon([(380, 620), (560, 720), (380, 820)], fill=(255, 255, 255))
    d.rounded_rectangle([60, 1500, 840, 1514], radius=7, fill=(255, 255, 255, 80)); d.rounded_rectangle([60, 1500, 420, 1514], radius=7, fill=(255, 60, 50))
    im.save(os.path.join(OUT, 'thumb.png'))

def graph():
    w, h = 900, 1600; im = Image.new('RGB', (w, h), (22, 18, 34)); d = ImageDraw.Draw(im)
    d.text((70, 120), 'LƯỢT XEM', font=font(FB, 84), fill=(255, 238, 220)); d.text((74, 230), '1 VIDEO 2.5D · 65 GIÂY', font=font(FS, 40), fill=(200, 170, 200))
    for i in range(6): d.line([(70, 700 + i * 140), (830, 700 + i * 140)], fill=(60, 50, 80), width=3)
    pts = [(80 + 740 * u, 1400 - 640 * (u ** 0.55)) for u in [i / 60 for i in range(61)]]
    d.line(pts, fill=(255, 90, 140), width=12, joint='curve'); x, y = pts[-1]; d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(255, 220, 230))
    d.text((70, 1430), 'NGÀY 1', font=font(FS, 40), fill=(200, 170, 200)); d.text((700, 1430), 'NGÀY 8', font=font(FS, 40), fill=(200, 170, 200))
    im.save(os.path.join(OUT, 'graph.png'))

def storyboard(i):
    w, h = 600, 800; im = Image.new('RGB', (w, h), (236, 228, 210)); d = ImageDraw.Draw(im)
    d.rectangle([30, 30, w - 30, 520], outline=(60, 50, 50), width=6)
    names = ['neutral', 'think', 'waveA']; host = Image.open(os.path.join(CH, names[i] + '.png')).convert('L').resize((220, 330), Image.LANCZOS)
    host = Image.merge('RGBA', [host, host, host, Image.open(os.path.join(CH, names[i] + '.png')).split()[3].resize((220, 330))])
    im.paste(host, (190, 170), host)
    for k in range(4): d.line([(40, 580 + k * 50), (w - 60 - (k * 70) % 200, 580 + k * 50)], fill=(120, 110, 100), width=8)
    im.save(os.path.join(OUT, f'storyboard{i}.png'))

def stars():
    r = random.Random(9); w, h = 2048, 1024; im = grad(w, h, (8, 10, 30), (40, 34, 74)); d = ImageDraw.Draw(im)
    for _ in range(900): x, y = r.random() * w, r.random() * h * 0.8; s = r.choice([1, 1, 1, 2, 3]); d.ellipse([x, y, x + s, y + s], fill=(230, 235, 255))
    im.save(os.path.join(OUT, 'stars.png'))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    night_city(); rug(); laptop_ui(); thumb(); graph(); stars()
    for i in range(3): storyboard(i)
    print('ok')
