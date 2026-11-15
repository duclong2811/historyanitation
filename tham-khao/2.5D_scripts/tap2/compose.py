"""Episode 2 compositor: 3D renders (frames2, 720p -> 1080p), reused ep1 footage, tutorial panels, step HUD.
Writes a 15 fps 1080x1920 picture track (build/picture.mp4). Captions + audio are added by make_final.py.
  python compose.py                 full render
  python compose.py --at 12.3,40    preview PNGs in build/preview/"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.join(HERE, '..', 'blender')
BUILD = os.path.join(HERE, 'build')
TL = json.load(open(os.path.join(BUILD, 'timeline.json'), encoding='utf-8'))
WORDS = TL['words']; DUR = TL['duration']
SHOTS = TL['shots']; S = {s['id']: s for s in SHOTS}
EP1W = json.load(open(os.path.join(HERE, '..', 'growkaz-stickman-studio', 'projects', 'tap2', 'timeline', 'words.json'), encoding='utf-8'))['words']
W_, H_ = 1080, 1920
FPS = 15

# ------------------------------------------------------------------ style
FD = 'C:/Windows/Fonts/'
_fc = {}
def font(name, size):
    k = (name, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(FD + {'black': 'seguibl.ttf', 'bold': 'segoeuib.ttf', 'semi': 'seguisb.ttf', 'reg': 'segoeui.ttf',
                                                           'mono': 'consolab.ttf', 'monor': 'consola.ttf'}[name], size)
    return _fc[k]
INK = (20, 16, 22); WHITE = (255, 255, 255); YEL = (255, 200, 42); RED = (224, 48, 42); GREEN = (70, 200, 110)
BLUE = (90, 160, 255); PINK = (255, 110, 160); PANEL = (21, 22, 30); BAR = (34, 36, 46); DIM = (150, 155, 175)
CODE_COL = {'kw': (255, 130, 170), 'fn': (130, 200, 255), 'str': (190, 240, 140), 'num': (255, 205, 130), 'cm': (120, 128, 150), 'tx': (232, 236, 245)}
STEPS = ['VOICE', 'MỐC THỜI GIAN', 'SHOT LIST', 'DỰNG SET', 'NHÂN VẬT 2D', 'ÁNH SÁNG', 'CAMERA', 'RENDER', 'XUẤT VIDEO']
STEP_OF = {'b1': 1, 'b2': 2, 'b3': 3, 'b4': 4, 'b5': 5, 'b6': 6, 'b7': 7, 'b8': 8, 'b9': 9}
STEP_START = {1: 'b1a', 2: 'b2a', 3: 'b3a', 4: 'b4a', 5: 'b5a', 6: 'b6a', 7: 'b7a', 8: 'b8a', 9: 'b9a'}

def T(i): return WORDS[i]['start']
def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = cl(x); return x * x * (3 - 2 * x)
def back(x):   # overshoot pop
    x = cl(x); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def prog(t, a, d=0.25): return ease((t - a) / d)

# ------------------------------------------------------------------ sources
_cache = {}
def load(path, size=None):
    k = (path, size)
    if k not in _cache:
        if len(_cache) > 40: _cache.clear()
        im = Image.open(path).convert('RGB')
        if size and im.size != size: im = im.resize(size, Image.LANCZOS)
        _cache[k] = im
    return _cache[k]
def ep1(t):   # ep1 picture at ep1-time t (on-twos frames)
    f = min(1022, max(0, int(round(t * 30)) // 2 * 2)); return load(os.path.join(BL, 'frames', f'f_{f:04d}.png'))
def ep2(n, folder='frames2'):
    for f in (2 * n, 2 * n - 2, 2 * n + 2, 2 * n - 4):
        p = os.path.join(BL, folder, f'f_{f:04d}.png')
        if os.path.exists(p): return load(p, (W_, H_))
    return None
R_MAP = {'i2': (9.25, 0.96), 'b4e': (30.5, 1.0), 'b5c': (7.75, 1.0), 'o3': (27.85, 0.68)}
PLATE = {'i3': 20.9, 'b1b': 3.3, 'b1c': 3.3, 'b2a': 22.3, 'b2b': 22.3, 'b3b': 15.9, 'b3c': 15.9, 'b4a': 20.9, 'b4b': 20.9, 'b4c': 20.9,
         'b5b': 28.6, 'b5d': 8.0, 'b7c': 10.2, 'b8a': 1.2, 'b8b': 1.2, 'b8c': 1.2, 'b9a': 33.0, 'b9b': 33.0, 'b9c': 33.0, 'o1': 28.6, 'o2': 28.6}
_plates = {}
def plate(sid, lt, dur):
    if sid not in _plates:
        im = ep1(PLATE[sid]).resize((int(W_ * 1.08), int(H_ * 1.08)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(16))
        _plates[sid] = Image.blend(im, Image.new('RGB', im.size, (10, 8, 16)), 0.5)
    im = _plates[sid]; z = 1.0 + 0.06 * lt / max(dur, 0.1)
    w, h = int(W_ * z), int(H_ * z); x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h)).resize((W_, H_), Image.BILINEAR)

# ------------------------------------------------------------------ drawing helpers
def rr(d, box, r, fill=None, outline=None, width=1): d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)
def txt(d, xy, s, f, fill=WHITE, anchor='la', stroke=0, sfill=INK): d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill)
def tw(s, f): return f.getlength(s)

def layer(): return Image.new('RGBA', (W_, H_), (0, 0, 0, 0))
def comp(base, lay, alpha=1.0, dy=0, scale=1.0, center=None):
    if alpha <= 0.001: return
    if scale != 1.0:
        cx, cy = center or (W_ / 2, H_ / 2)
        lay = lay.transform(lay.size, Image.AFFINE, (1 / scale, 0, cx - cx / scale, 0, 1 / scale, cy - cy / scale), Image.BILINEAR)
    if dy: lay = lay.transform(lay.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy), Image.BILINEAR)
    if alpha < 1: a = lay.getchannel('A').point(lambda v: int(v * alpha)); lay.putalpha(a)
    base.alpha_composite(lay)

_shadow = {}
def window(box, title, icon_col=BLUE):
    """panel window: drop shadow + body + title bar. returns (layer, draw, content box)"""
    x0, y0, x1, y1 = box; L = layer()
    k = (box,)
    if k not in _shadow:
        sh = layer(); ImageDraw.Draw(sh).rounded_rectangle((x0 + 6, y0 + 18, x1 + 6, y1 + 22), 34, fill=(0, 0, 0, 170)); _shadow[k] = sh.filter(ImageFilter.GaussianBlur(22))
    L.alpha_composite(_shadow[k]); d = ImageDraw.Draw(L)
    rr(d, box, 30, fill=PANEL + (246,), outline=(70, 74, 92), width=2)
    rr(d, (x0, y0, x1, y0 + 74), 30, fill=BAR); d.rectangle((x0 + 2, y0 + 44, x1 - 2, y0 + 74), fill=BAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): d.ellipse((x0 + 28 + i * 34, y0 + 26, x0 + 50 + i * 34, y0 + 48), fill=c)
    txt(d, (x0 + 140, y0 + 37), title, font('semi', 32), (210, 214, 230), 'lm')
    return L, d, (x0 + 36, y0 + 104, x1 - 36, y1 - 30)

def chip(d, x, y, s, f, bg, fg=WHITE, pad=(22, 12), anchor='l', r=None):
    w = tw(s, f); h = f.size + pad[1] * 2
    if anchor == 'c': x -= (w + pad[0] * 2) / 2
    if anchor == 'r': x -= w + pad[0] * 2
    rr(d, (x, y, x + w + pad[0] * 2, y + h), r if r is not None else h // 2, fill=bg)
    txt(d, (x + pad[0], y + h / 2), s, f, fg, 'lm'); return x + w + pad[0] * 2

def code_line(d, x, y, s, f, nchars=None):
    """tiny syntax colouring: comments, strings, numbers, keywords, calls"""
    import re
    s = s if nchars is None else s[:max(0, nchars)]
    toks = re.findall(r'#.*$|"[^"]*"?|\'[^\']*\'?|\b\d+(?:\.\d+)?\b|\b(?:import|from|for|in|def|return|as)\b|[A-Za-z_][\w\.]*(?=\()|\s+|.', s)
    for t_ in toks:
        c = CODE_COL['tx']
        if t_.startswith('#'): c = CODE_COL['cm']
        elif t_[:1] in '"\'': c = CODE_COL['str']
        elif t_[:1].isdigit(): c = CODE_COL['num']
        elif t_ in ('import', 'from', 'for', 'in', 'def', 'return', 'as'): c = CODE_COL['kw']
        elif t_[:1].isalpha() and '(' in s[s.find(t_) + len(t_): s.find(t_) + len(t_) + 1]: c = CODE_COL['fn']
        d.text((x, y), t_, font=f, fill=c); x += f.getlength(t_)
    return x

def typed(t, a, cps, s): return int((t - a) * cps) if t >= a else 0

def check(d, x, y, sz, col=GREEN):
    d.ellipse((x, y, x + sz, y + sz), fill=col)
    d.line([(x + sz * 0.27, y + sz * 0.52), (x + sz * 0.44, y + sz * 0.68), (x + sz * 0.74, y + sz * 0.34)], fill=WHITE, width=max(3, int(sz * 0.12)), joint='curve')
def cross(d, x, y, sz, col=RED):
    d.ellipse((x, y, x + sz, y + sz), fill=col)
    for a, b in (((0.3, 0.3), (0.7, 0.7)), ((0.7, 0.3), (0.3, 0.7))):
        d.line([(x + sz * a[0], y + sz * a[1]), (x + sz * b[0], y + sz * b[1])], fill=WHITE, width=max(3, int(sz * 0.12)))

def callout(base, t, a, s, y, col=YEL, x=60, size=46, fg=INK):
    """pill label that pops in at time a (left aligned)"""
    if t < a: return
    L = layer(); d = ImageDraw.Draw(L); f = font('black', size)
    x1 = chip(d, x, y, s, f, col + (255,), fg, pad=(26, 14))
    comp(base, L, prog(t, a, 0.15), scale=0.85 + 0.15 * back((t - a) / 0.25), center=(x + (x1 - x) / 2, y + 40))

# ------------------------------------------------------------------ HUD + title cards
def hud(base, step, t, done=0):
    L = layer(); d = ImageDraw.Draw(L)
    f = font('black', 40); s = f'BƯỚC {step}/9'
    x1 = chip(d, 60, 186, s, f, RED + (255,), WHITE, pad=(24, 10))
    txt(d, (x1 + 20, 186 + 34), STEPS[step - 1], font('black', 44), WHITE, 'lm', stroke=5)
    for i in range(9):
        x = 60 + i * 107; c = (255, 255, 255, 235) if i < step - 1 or i < done else (YEL + (255,) if i == step - 1 else (255, 255, 255, 70))
        rr(d, (x, 266, x + 95, 278), 6, fill=c)
    comp(base, L)

def title_card(base, step, t, a, b):
    if not (a <= t < b): return
    L = layer(); d = ImageDraw.Draw(L)
    k_in = back((t - a) / 0.3); k_out = 1 - ease((t - (b - 0.2)) / 0.2)
    f1 = font('black', 110); f2 = font('black', 92)
    s1 = f'BƯỚC {step}'; s2 = STEPS[step - 1]
    w = max(tw(s1, f1), tw(s2, f2)) + 120; x0 = (W_ - w) / 2; y0 = 420
    rr(d, (x0, y0, x0 + w, y0 + 290), 40, fill=(15, 12, 20, 225))
    txt(d, (W_ / 2, y0 + 82), s1, f1, YEL, 'mm')
    txt(d, (W_ / 2, y0 + 200), s2, f2, WHITE, 'mm')
    comp(base, L, k_out, scale=0.6 + 0.4 * k_in, center=(W_ / 2, y0 + 145))

# ------------------------------------------------------------------ panels (one function per P shot)
PBOX = (60, 340, 1020, 1330)

def p_roadmap(base, sid, t, s, ticks=False):
    L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'Lộ trình · 9 bước')
    items = ['Voice — ElevenLabs + audio tag', 'Mốc thời gian — Whisper', 'Shot list — mỗi ý ~2 giây', 'Dựng set — Blender + Python',
             'Nhân vật 2D — PNG + Emission', 'Ánh sáng — đèn, trăng, khói', 'Camera — đẩy vào chậm', 'Render — Eevee, 8 sample', 'Xuất video — FFmpeg 9:16']
    a = s['start'] + 0.1
    for i, it in enumerate(items):
        ta = a + i * (0.09 if not ticks else 0.17); y = cy0 + 6 + i * 92
        if t < ta and not ticks: continue
        k = prog(t, ta, 0.15) if not ticks else 1
        num = font('black', 44); d.ellipse((cx0, y, cx0 + 64, y + 64), fill=(RED if not ticks else (60, 64, 80)))
        txt(d, (cx0 + 32, y + 33), str(i + 1), num, WHITE, 'mm')
        txt(d, (cx0 + 88, y + 32), it, font('bold', 40), (255, 255, 255, int(255 * k)), 'lm')
        if ticks and t >= ta: check(d, cx1 - 70, y, 64)
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)
    if not ticks:
        callout(base, t, T(15), 'LƯU LẠI ĐỂ LÀM THEO', y=1350 - 80, x=320, col=YEL)

def p_tts(base, sid, t, s):
    L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'ElevenLabs · Text to Speech')
    f = font('bold', 34); fm = font('semi', 30)
    chip(d, cx0, cy0, 'Model: Eleven v3', fm, (60, 52, 120), WHITE, pad=(18, 8))
    chip(d, cx0 + 300, cy0, 'Giọng: tiếng Việt', fm, (48, 52, 66), WHITE, pad=(18, 8))
    if sid == 'b1b':
        lines = ['Đây là cách tôi làm video hoạt hình 2.5D…', 'Bước một: voice.', 'Bước hai: chạy Whisper…', 'Bước ba: lên shot list.', 'Bước bốn: dựng set…']
        split = prog(t, T(27), 0.4)
        for i, ln in enumerate(lines):
            y = cy0 + 110 + i * (70 + 60 * split)
            rr(d, (cx0, y - 12, cx1, y + 58), 16, fill=(30, 32, 42) if split > 0.5 else None)
            txt(d, (cx0 + 20, y + 22), ln, f, WHITE, 'lm')
            ta = T(29) + i * 0.18
            if t >= ta: chip(d, cx1 - 170, y + 4, f'0{i + 1}.mp3', font('bold', 28), (40, 150, 90), WHITE, pad=(14, 6))
        txt(d, (cx0, cy1 - 30), 'Mỗi câu ngắn = 1 file. Sai câu nào, làm lại câu đó.', font('semi', 32), YEL, 'lm')
    else:
        rows = [('[confident]', 'Đây là cách tôi làm video 2.5D…'), ('[excited]', 'Lưu lại để làm theo nhé!'),
                ('[short pause]', 'Bước một: voice.'), ('[sighs]', 'Laptop của tôi mất… hai tiếng.')]
        cols = [(255, 140, 60), (255, 90, 140), (90, 160, 255), (150, 120, 255)]
        for i, (tag, ln) in enumerate(rows):
            y = cy0 + 110 + i * 120; ta = T(34) + i * 0.22
            x = cx0
            if t >= ta:
                k = back((t - ta) / 0.25)
                x = chip(d, cx0, y, tag, font('mono', 32), cols[i], WHITE, pad=(int(14 * k), 10)) + 14
            txt(d, (x, y + 26), ln, f, WHITE, 'lm')
        # waveform
        import random
        r = random.Random(3); y = cy0 + 640
        for k in range(70):
            h = (r.random() * 0.7 + 0.3) * 70 * (1.3 if 18 < k < 30 else 1)
            c = cols[min(3, k * 4 // 70)] if t >= T(37) else (90, 96, 120)
            d.rounded_rectangle((cx0 + k * 12.5, y - h / 2, cx0 + k * 12.5 + 7, y + h / 2), 3, fill=c)
        chip(d, cx0, cy1 - 66, '!  Chỉ model v3 hiểu audio tag', font('bold', 32), (90, 40, 30), (255, 200, 170), pad=(18, 10))
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)

def p_whisper(base, sid, t, s):
    L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'Terminal')
    fm = font('mono', 31); y = cy0
    if sid == 'b2a':
        a = max(s['start'] + 0.25, T(43) - 0.1)
        txt(d, (cx0, y), '$ pip install openai-whisper', fm, (150, 156, 175)); y += 52
        cmd = ['$ whisper tap2.mp3 --language vi', '    --model small --word_timestamps True', '    --output_format json']
        n = typed(t, a, 55, None)
        for ln in cmd:
            code_line(d, cx0, y, ln, fm, n); n -= len(ln); y += 46
        if t >= T(46) - 0.1:
            k0 = int((t - (T(46) - 0.1)) / 0.07)
            rows = [(w['start'], w['end'], w['word']) for w in EP1W[:40]]
            vis = rows[max(0, k0 - 12):k0]
            y += 20
            for st, en, wd in vis:
                d.text((cx0, y), f'[{st:05.2f} → {en:05.2f}]', font=fm, fill=(130, 200, 255)); d.text((cx0 + 380, y), wd, font=font('bold', 32), fill=WHITE); y += 44
        else:
            if int(t * 3) % 2: d.rectangle((cx0, y + 4, cx0 + 18, y + 36), fill=WHITE)
    else:
        txt(d, (cx0, y), 'words.json', font('bold', 34), YEL); y += 64
        fx = 'rán' if t < T(57) else 'dán'
        rows = [('hình', 8.30, 8.46), ('phẳng,', 8.46, 8.88), (fx, 9.38, 9.74), ('vào', 9.74, 9.86), ('một', 9.86, 10.02)]
        for i, (wd, st, en) in enumerate(rows):
            yy = y + i * 92
            hot = i == 2
            if hot: rr(d, (cx0 - 14, yy - 14, cx1, yy + 62), 14, fill=(80, 30, 34) if wd == 'rán' else (24, 70, 44))
            x = cx0; x = code_line(d, x, yy, '{ "word": ', fm)
            col = (255, 120, 120) if wd == 'rán' else ((130, 255, 160) if hot else CODE_COL['str'])
            d.text((x, yy), f'"{wd}"', font=fm, fill=col); x += fm.getlength(f'"{wd}"')
            code_line(d, x, yy, f', "start": {st:.2f} }}', fm)
            if hot and wd == 'rán' and t >= T(59): d.line([(cx0 + 205, yy + 18), (cx0 + 300, yy + 18)], fill=(255, 120, 120), width=5)
        y2 = y + 5 * 92 + 30
        if t >= T(53): callout_box(d, cx0, y2, 'Whisper nghe nhầm "dán" → "rán"', 'Sửa chữ, giữ nguyên số giây', t >= T(57))
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)

def callout_box(d, x, y, l1, l2, ok):
    (cross if not ok else check)(d, x, y + 6, 60)
    txt(d, (x + 84, y + 20), l1, font('bold', 36), WHITE, 'lm'); txt(d, (x + 84, y + 70), l2, font('semi', 32), YEL, 'lm')

def p_shotlist(base, sid, t, s):
    L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'shot list')
    if sid == 'b3b':
        rows = [('s01', '0.0–2.3s', 'Gác mái, gõ laptop'), ('s02', '2.3–4.3s', 'Cận mặt'), ('s03', '4.3–5.2s', 'Phim trường tắt đèn'),
                ('s04', '5.2–6.3s', 'Ghế trống'), ('s05', '6.3–7.3s', 'Máy quay cũ'), ('s06', '7.3–9.3s', 'Nhân vật xoay mỏng'), ('s07', '9.3–11.2s', 'Camera bay vòng')]
        fh = font('bold', 30); fb = font('mono', 32); fr = font('semi', 34)
        txt(d, (cx0, cy0), 'SHOT', fh, DIM); txt(d, (cx0 + 140, cy0), 'THỜI GIAN', fh, DIM); txt(d, (cx0 + 400, cy0), 'NỘI DUNG', fh, DIM)
        for i, (a_, b_, c_) in enumerate(rows):
            ta = T(68) + i * 0.16
            if t < ta: continue
            y = cy0 + 60 + i * 96; k = prog(t, ta, 0.15)
            rr(d, (cx0 - 10, y - 8, cx1, y + 74), 14, fill=(30, 32, 42))
            th = ep1({'s01': 1, 's02': 3.3, 's03': 4.6, 's04': 5.7, 's05': 6.6, 's06': 8.0, 's07': 10}[a_]).resize((36, 64))
            L.paste(th, (int(cx1 - 56), int(y + 2)))
            txt(d, (cx0 + 8, y + 33), a_, fb, YEL, 'lm'); txt(d, (cx0 + 140, y + 33), b_, fb, (130, 200, 255), 'lm'); txt(d, (cx0 + 400, y + 33), c_, fr, WHITE, 'lm')
        if t >= T(72): chip(d, cx0, cy1 - 64, 'Mỗi ý = 1 shot ≈ 2 giây', font('black', 36), YEL, INK, pad=(22, 10))
    else:
        # cut-early diagram on a waveform
        y = cy0 + 560; x0, x1 = cx0, cx1
        import random
        r = random.Random(5); words = [('…câu', 0.0, 0.32), ('nói', 0.36, 0.6), ('một', 0.66, 0.8), ('chút.', 0.84, 1.0)]
        for k in range(150):
            u = k / 150; h = 8
            for _, a_, b_ in [('', 0.02, 0.42), ('', 0.6, 0.98)]:
                if a_ < u < b_: h = (r.random() * 0.7 + 0.3) * 90
            d.rounded_rectangle((x0 + u * (x1 - x0), y - h / 2, x0 + u * (x1 - x0) + 3, y + h / 2), 2, fill=(110, 120, 150))
        txt(d, (x0, y - 90), 'câu A', font('bold', 34), WHITE); txt(d, (x0 + 0.6 * (x1 - x0), y - 90), 'câu B', font('bold', 34), WHITE)
        # shot blocks
        sa = ep1(1).resize((180, 320)); sb = ep1(3.3).resize((180, 320))
        phr = x0 + 0.6 * (x1 - x0); cut = phr - (0.15 * (x1 - x0) * prog(t, T(77), 0.4))
        L.paste(sa, (int(cut - 200), cy0 + 10)); L.paste(sb, (int(cut + 20), cy0 + 10))
        d.line([(cut, cy0), (cut, y + 120)], fill=YEL, width=6); txt(d, (cut, y + 135), 'CẮT', font('black', 40), YEL, 'mm')
        d.line([(phr, y + 60), (phr, y + 110)], fill=WHITE, width=3)
        if t >= T(77): txt(d, (cut + (phr - cut) / 2, y + 195), '← sớm 0,1–0,2 giây', font('bold', 36), WHITE, 'mm')
        txt(d, (cx0, cy1 - 40), 'Hình đổi trước, lời theo sau → nhìn "mượt" hơn', font('semi', 32), DIM, 'lm')
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)

BPY = ['import bpy', '', '# mặt bàn = 1 khối hộp', 'bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0.76))', 'ban = bpy.context.object',
       'ban.scale = (0.75, 0.375, 0.03)', '', '# chân đèn = 1 khối trụ', 'bpy.ops.mesh.primitive_cylinder_add(', '    radius=0.05, depth=0.4)']
def p_blender(base, sid, t, s):
    if sid == 'b4b':
        L = layer(); d = ImageDraw.Draw(L)
        cx, cy = W_ / 2, 760
        rr(d, (200, 520, 880, 1000), 40, fill=(15, 12, 20, 220))
        # mouse cursor + drag arrow
        d.polygon([(420, 620), (420, 820), (468, 776), (500, 846), (528, 832), (498, 764), (560, 760)], fill=WHITE, outline=INK)
        d.line([(580, 700), (760, 700)], fill=(200, 200, 210), width=8); d.polygon([(760, 680), (800, 700), (760, 720)], fill=(200, 200, 210))
        k = back((t - s['start'] - 0.15) / 0.3)
        if t > s['start'] + 0.15:
            d.line([(300, 600), (780, 920)], fill=RED, width=int(26 * cl(k))); d.line([(780, 600), (300, 920)], fill=RED, width=int(26 * cl(k)))
        txt(d, (cx, 960), 'KHÔNG KÉO THẢ', font('black', 60), WHITE, 'mm')
        comp(base, L, prog(t, s['start'], 0.12), scale=0.9 + 0.1 * back((t - s['start']) / 0.25), center=(cx, cy))
        return
    if sid == 'b4c':
        L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'Chat với AI')
        f = font('semi', 34)
        msg = ['Viết script Python cho Blender:', 'dựng phòng gác mái — sàn gỗ,', 'mái dốc, bàn, đèn bàn, kệ sách.']
        rr(d, (cx1 - 640, cy0, cx1, cy0 + 190), 28, fill=(56, 110, 230))
        for i, ln in enumerate(msg): txt(d, (cx1 - 610, cy0 + 40 + i * 50), ln, f, WHITE, 'lm')
        if t >= T(96) + 0.25:
            rr(d, (cx0, cy0 + 230, cx1 - 60, cy1 - 20), 28, fill=(36, 38, 50))
            n = typed(t, T(96) + 0.3, 300, None); y = cy0 + 260; fm = font('mono', 27)
            for ln in BPY + ['# kệ sách, sàn, mái…', 'for i in range(12): ...']:
                code_line(d, cx0 + 26, y, ln, fm, n); n -= len(ln) + 1; y += 40
        comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)
        return
    L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'Blender › Scripting')
    stepsx = ['Tab Scripting', '+ New', 'Dán code', 'Run Script (Alt+P)']
    x = cx0; fs_ = font('bold', 28)
    for i, st in enumerate(stepsx):
        on = t >= s['start'] + 0.3 + i * 0.45
        x = chip(d, x, cy0, f'{i + 1}. {st}', fs_, (YEL if on else (48, 52, 66)), (INK if on else DIM), pad=(14, 8)) + 10
    rr(d, (cx0, cy0 + 80, cx1, cy1 - 10), 18, fill=(14, 15, 20))
    fm = font('mono', 28); n = typed(t, s['start'] + 0.3, 230, None); y = cy0 + 106
    for i, ln in enumerate(BPY):
        d.text((cx0 + 10, y), f'{i + 1:2d}', font=font('monor', 26), fill=(80, 86, 104))
        code_line(d, cx0 + 60, y, ln, fm, n); n -= len(ln) + 1; y += 50
    if t >= T(91) - 0.2: chip(d, cx0 + 10, cy1 - 80, 'Không cần thuộc menu — code làm hết', font('bold', 30), (40, 150, 90), WHITE, pad=(16, 8))
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)

CHAR = None
def p_char(base, sid, t, s):
    global CHAR
    L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'host.py  →  host.png')
    fm = font('mono', 25)
    code = ['from PIL import Image, ImageDraw', 'img = Image.new("RGBA", (800, 1200),', '                (0, 0, 0, 0))  # trong suốt', 'd = ImageDraw.Draw(img)',
            '# đầu tròn trắng, viền đen dày', 'd.ellipse((188, 88, 612, 512),', '  fill="white", outline="black",', '  width=14)', '# … mắt, tóc, áo hoodie', 'img.save("host.png")']
    n = typed(t, s['start'] + 0.1, 240, None); y = cy0
    for ln in code: code_line(d, cx0, y, ln, fm, n); n -= len(ln) + 1; y += 38
    # checkerboard + character reveal
    bx0, by0, bx1, by1 = cx0 + 170, cy0 + 410, cx1 - 170, cy1 - 10
    for yy in range(by0, by1, 28):
        for xx in range(bx0, bx1, 28):
            d.rectangle((xx, yy, min(xx + 28, bx1), min(yy + 28, by1)), fill=(200, 200, 205) if ((xx - bx0) // 28 + (yy - by0) // 28) % 2 else (240, 240, 244))
    if CHAR is None: CHAR = Image.open(os.path.join(BL, 'chars', 'neutral.png')).convert('RGBA')
    h = by1 - by0 - 20; w = int(h * 800 / 1200); ch = CHAR.resize((w, h), Image.LANCZOS)
    rev = prog(t, T(119), 1.1)
    if rev > 0:
        m = Image.new('L', ch.size, 0); ImageDraw.Draw(m).rectangle((0, 0, w, int(h * rev)), fill=255)
        a = Image.composite(ch.getchannel('A'), Image.new('L', ch.size, 0), m); ch.putalpha(a)
        L.alpha_composite(ch, (int((bx0 + bx1 - w) / 2), by0 + 10))
    if t >= T(124): chip(d, bx0 - 150, by1 - 70, 'PNG nền trong suốt', font('black', 32), YEL, INK, pad=(18, 10))
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)

def p_emission(base, sid, t, s):
    L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'Shader Editor › vật liệu nhân vật')
    nodes = [('Image Texture', (90, 70, 40)), ('Emission', (40, 110, 70)), ('Mix Shader', (60, 60, 90)), ('Output', (90, 40, 40))]
    x = cx0; y = cy0
    for i, (nm, col) in enumerate(nodes):
        if t < s['start'] + 0.2 + i * 0.2: break
        w = 196; rr(d, (x, y, x + w, y + 84), 14, fill=(48, 50, 60), outline=col, width=4); rr(d, (x, y, x + w, y + 30), 14, fill=col)
        txt(d, (x + w / 2, y + 56), nm, font('bold', 24), WHITE, 'mm')
        if i: d.line([(x - 34, y + 56), (x, y + 56)], fill=YEL, width=4)
        x += w + 34
    txt(d, (cx0, y + 120), '+ Transparent BSDF nối vào Mix (dùng Alpha của ảnh)', font('semi', 28), DIM, 'lm')
    ya = cy0 + 190; cw = (cx1 - cx0 - 30) // 2; chh = int(cw * 16 / 9) if int(cw * 16 / 9) < cy1 - ya - 60 else cy1 - ya - 60
    for i, (fn, lab, ok) in enumerate((('mat_principled.png', 'Principled BSDF', False), ('mat_emission.png', 'Emission', True))):
        ta = T(137) + i * 0.5
        if t < ta: continue
        p = os.path.join(BL, 'renders', fn)
        im = Image.open(p).convert('RGB') if os.path.exists(p) else Image.new('RGB', (9, 16), (80, 80, 80))
        sc_ = max(cw / im.width, chh / im.height); im = im.resize((int(im.width * sc_), int(im.height * sc_)), Image.LANCZOS)
        im = im.crop(((im.width - cw) // 2, int((im.height - chh) * 0.3), (im.width - cw) // 2 + cw, int((im.height - chh) * 0.3) + chh))
        x = cx0 + i * (cw + 30); L.paste(im, (x, ya))
        (check if ok else cross)(d, x + 16, ya + 16, 64)
        rr(d, (x, ya + chh - 80, x + cw, ya + chh), 0, fill=(0, 0, 0, 170))
        txt(d, (x + cw / 2, ya + chh - 40), lab + (' — giữ màu' if ok else ' — bẩn màu'), font('black', 30), (130, 255, 160) if ok else (255, 140, 140), 'mm')
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)

def p_markers(base, sid, t, s):
    L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'Timeline')
    shots = [('s01', 1.0), ('s02', 3.3), ('s03', 4.6), ('s04', 5.7)]
    u = cl((t - s['start'] - 0.3) / (s['end'] - s['start'] - 0.5)); idx = min(3, int(u * 4))
    pv = ep1(shots[idx][1]).resize((270, 480)); L.paste(pv, (int((cx0 + cx1) / 2 - 135), cy0 + 10))
    txt(d, ((cx0 + cx1) / 2, cy0 + 520), f'CAM_{shots[idx][0]}', font('mono', 32), YEL, 'mm')
    y = cy0 + 600; rr(d, (cx0, y, cx1, y + 170), 14, fill=(30, 32, 42))
    for k in range(0, 41):
        x = cx0 + 20 + k * (cx1 - cx0 - 40) / 40; d.line([(x, y + 10), (x, y + (30 if k % 5 == 0 else 20))], fill=(90, 96, 120), width=2)
    for i, (nm, _) in enumerate(shots):
        x = cx0 + 20 + i * (cx1 - cx0 - 40) / 4
        d.polygon([(x - 14, y + 120), (x + 14, y + 120), (x, y + 140)], fill=YEL if i <= idx else DIM)
        rr(d, (x - 20, y + 58, x + 28, y + 92), 6, fill=(60, 64, 80)); d.polygon([(x + 28, y + 66), (x + 44, y + 58), (x + 44, y + 92), (x + 28, y + 84)], fill=(60, 64, 80))
        txt(d, (x + 4, y + 158), nm, font('mono', 26), WHITE, 'mm')
    px = cx0 + 20 + u * (cx1 - cx0 - 40); d.line([(px, y - 10), (px, y + 175)], fill=(90, 160, 255), width=4)
    chip(d, cx0, cy1 - 66, 'Marker › Bind Camera to Markers  (Ctrl+B)', font('bold', 30), YEL if t >= T(198) + 0.3 else (48, 52, 66), INK if t >= T(198) + 0.3 else DIM, pad=(18, 10))
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)

def p_render(base, sid, t, s):
    if sid == 'b8a':
        L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'Properties › Render', BLUE)
        rows = [('Render Engine', 'EEVEE', T(209)), ('Sampling › Render', '8', T(212)), ('Freestyle', 'BẬT', None),
                ('Output › Resolution', '1080 × 1920', None), ('Output › Frame Rate', '30 fps', None), ('Output › Frame Step', '2', T(218))]
        for i, (k_, v_, hot_t) in enumerate(rows):
            y = cy0 + 20 + i * 132; hot = hot_t is not None and t >= hot_t
            rr(d, (cx0, y, cx1, y + 104), 18, fill=(52, 46, 20) if hot else (30, 32, 42), outline=YEL if hot else None, width=4)
            txt(d, (cx0 + 30, y + 52), k_, font('semi', 36), WHITE if hot else DIM, 'lm')
            rr(d, (cx1 - 330, y + 18, cx1 - 24, y + 86), 12, fill=(60, 64, 80))
            txt(d, (cx1 - 177, y + 52), v_, font('black', 38), YEL if hot else WHITE, 'mm')
        comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)
    elif sid == 'b8b':
        L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'on twos = vẽ 15 hình, chiếu 30 hình')
        cols = [(214, 74, 51), (58, 110, 165), (242, 194, 26), (138, 90, 214), (40, 160, 110), (230, 110, 160), (90, 160, 255), (200, 140, 60)]
        y1 = cy0 + 80; y2 = cy0 + 470; n = 8; cw = (cx1 - cx0) / 16
        txt(d, (cx0, cy0 + 20), 'Blender render: 15 hình / giây', font('black', 36), WHITE)
        for i in range(n):
            if t < T(220) + i * 0.08: break
            rr(d, (cx0 + i * cw * 2 + 6, y1, cx0 + i * cw * 2 + cw * 2 - 6, y1 + 200), 14, fill=cols[i])
            txt(d, (cx0 + i * cw * 2 + cw, y1 + 100), str(i + 1), font('black', 60), WHITE, 'mm')
        if t >= T(225):
            txt(d, (cx0, y2 - 60), 'Video xuất ra: 30 khung / giây (mỗi hình giữ 2 khung)', font('black', 32), YEL)
            for j in range(16):
                ta = T(225) + j * 0.05
                if t < ta: break
                i = j // 2; x = cx0 + j * cw + 4
                rr(d, (x, y2, x + cw - 8, y2 + 160), 10, fill=cols[i]); txt(d, (x + cw / 2 - 4, y2 + 80), str(i + 1), font('black', 40), WHITE, 'mm')
        chip(d, cx0, cy1 - 140, 'Blender: Frame Step = 2', font('bold', 32), (48, 52, 66), WHITE, pad=(18, 10))
        chip(d, cx0, cy1 - 70, 'FFmpeg: -vf fps=30', font('mono', 30), (48, 52, 66), WHITE, pad=(18, 10))
        if t >= T(222): chip(d, cx1, cy1 - 140, 'nhanh gấp 2 lần', font('black', 34), (40, 150, 90), WHITE, pad=(18, 10), anchor='r')
        comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)
    else:
        L, d, (cx0, cy0, cx1, cy1) = window((60, 520, 1020, 1180), 'Blender Render')
        u = prog(t, s['start'] + 0.2, s['end'] - s['start'] - 0.5)
        fr = int(512 * u); secs_ = int(7297 * u)
        txt(d, (cx0, cy0 + 20), f'Fra: {fr} / 512', font('mono', 44), WHITE)
        txt(d, (cx0, cy0 + 90), f'Thời gian: {secs_ // 3600}:{secs_ % 3600 // 60:02d}:{secs_ % 60:02d}', font('mono', 44), YEL)
        rr(d, (cx0, cy0 + 190, cx1, cy0 + 240), 25, fill=(48, 52, 66)); rr(d, (cx0, cy0 + 190, cx0 + max(50, (cx1 - cx0) * u), cy0 + 240), 25, fill=(90, 160, 255))
        txt(d, (cx0, cy0 + 300), 'Laptop · Intel UHD 620 (card onboard)', font('semi', 32), DIM)
        txt(d, (cx0, cy0 + 360), 'Máy có card rời: chỉ vài phút', font('semi', 32), (130, 255, 160))
        comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)

def p_ffmpeg(base, sid, t, s):
    if sid == 'b9a':
        L, d, (cx0, cy0, cx1, cy1) = window(PBOX, 'Terminal')
        fm = font('mono', 29)
        cmd = ['$ ffmpeg -framerate 15 -i frames/f_%04d.png', '    -i voice.wav', '    -vf "fps=30,subtitles=phude.ass"', '    -c:v libx264 -crf 18 -pix_fmt yuv420p', '    -s 1080x1920 tap2.mp4']
        n = typed(t, s['start'] + 0.2, 150, None); y = cy0
        for ln in cmd: code_line(d, cx0, y, ln, fm, n); n -= len(ln); y += 50
        y = cy0 + 380; bw = 230
        items = [('HÌNH', 'frames/*.png', T(239), (58, 110, 165)), ('TIẾNG', 'voice.wav', T(242), (40, 150, 90)), ('PHỤ ĐỀ', '.ass', T(243), (200, 140, 60))]
        for i, (a_, b_, ta, col) in enumerate(items):
            if t < ta: continue
            x = cx0 + i * (bw + 60)
            rr(d, (x, y, x + bw, y + 200), 22, fill=col); txt(d, (x + bw / 2, y + 80), a_, font('black', 46), WHITE, 'mm'); txt(d, (x + bw / 2, y + 145), b_, font('mono', 26), WHITE, 'mm')
            if i: txt(d, (x - 30, y + 100), '+', font('black', 60), WHITE, 'mm')
        if t >= T(243) + 0.3:
            cxm = (cx0 + cx1) / 2; d.polygon([(cxm - 30, y + 235), (cxm + 30, y + 235), (cxm, y + 285)], fill=YEL)
            chip(d, (cx0 + cx1) / 2, y + 310, 'tap2.mp4', font('black', 44), YEL, INK, anchor='c')
        comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)
    elif sid == 'b9b':
        L = layer(); d = ImageDraw.Draw(L)
        rr(d, (120, 420, 960, 1180), 40, fill=(15, 12, 20, 215))
        txt(d, (540, 510), 'Phụ đề 1–2 chữ / lần', font('black', 50), WHITE, 'mm')
        ex = ['không phim', 'không diễn', 'không máy']
        k = min(2, int((t - s['start']) / 0.4)); f = font('black', 104)
        w0 = ex[k].split()
        x = 540 - tw(ex[k], f) / 2
        txt(d, (x, 770), w0[0], f, YEL, 'lm', stroke=7); txt(d, (x + tw(w0[0] + ' ', f), 770), w0[1], f, WHITE, 'lm', stroke=7)
        txt(d, (540, 960), 'chữ trắng, viền đen dày, từ khoá màu vàng', font('semi', 34), DIM, 'mm')
        txt(d, (540, 1040), 'đặt giữa – thấp, tránh nút bấm của app', font('semi', 34), DIM, 'mm')
        comp(base, L, prog(t, s['start'], 0.15))
    else:
        L = layer(); d = ImageDraw.Draw(L)
        pw, ph = 380, 676; px, py = (W_ - pw) // 2, 420
        rr(d, (px - 20, py - 20, px + pw + 20, py + ph + 20), 50, fill=(15, 15, 18), outline=(120, 120, 130), width=4)
        im = ep1(9.3 + (t - s['start'])).resize((pw, ph)); m = Image.new('L', (pw, ph), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, pw, ph), 34, fill=255)
        L.paste(im, (px, py), m)
        chip(d, W_ / 2, py + ph + 50, '1080 × 1920  ·  9:16  ·  30 fps', font('black', 40), YEL, INK, anchor='c')
        comp(base, L, prog(t, s['start'], 0.15), scale=0.9 + 0.1 * ease((t - s['start']) / 0.4), center=(W_ / 2, 760))

def p_comment(base, sid, t, s):
    L, d, (cx0, cy0, cx1, cy1) = window((60, 520, 1020, 1240), 'Bình luận')
    d.ellipse((cx0, cy0 + 20, cx0 + 90, cy0 + 110), fill=(90, 160, 255)); txt(d, (cx0 + 45, cy0 + 65), 'B', font('black', 48), WHITE, 'mm')
    rr(d, (cx0 + 120, cy0 + 20, cx1 - 120, cy0 + 110), 45, fill=(48, 52, 66))
    s_ = 'code'[:typed(t, T(263), 8, None)]
    txt(d, (cx0 + 160, cy0 + 65), s_ if s_ else 'Viết bình luận…', font('bold', 44), WHITE if s_ else DIM, 'lm')
    sent = t >= T(265)
    d.ellipse((cx1 - 100, cy0 + 20, cx1 - 10, cy0 + 110), fill=(90, 160, 255) if s_ else (60, 64, 80))
    d.polygon([(cx1 - 75, cy0 + 45), (cx1 - 30, cy0 + 65), (cx1 - 75, cy0 + 85)], fill=WHITE)
    if sent:
        k = back((t - T(265)) / 0.3)
        rr(d, (cx0 + 120, cy0 + 180, cx1, cy0 + 380), 30, fill=(40, 150, 90))
        txt(d, (cx0 + 160, cy0 + 240), 'Đã gửi bộ script:', font('black', 40), WHITE, 'lm')
        txt(d, (cx0 + 160, cy0 + 310), 'build_scene.py · make_chars.py · …', font('mono', 30), WHITE, 'lm')
    comp(base, L, prog(t, s['start'], 0.2), dy=(1 - prog(t, s['start'], 0.3)) * 50)
    callout(base, t, T(262), 'COMMENT: code', y=380, x=60, col=YEL)

PANELS = {'i3': p_roadmap, 'b1b': p_tts, 'b1c': p_tts, 'b2a': p_whisper, 'b2b': p_whisper, 'b3b': p_shotlist, 'b3c': p_shotlist,
          'b4a': p_blender, 'b4b': p_blender, 'b4c': p_blender, 'b5b': p_char, 'b5d': p_emission, 'b7c': p_markers,
          'b8a': p_render, 'b8b': p_render, 'b8c': p_render, 'b9a': p_ffmpeg, 'b9b': p_ffmpeg, 'b9c': p_ffmpeg,
          'o1': lambda b, sid, t, s: p_roadmap(b, sid, t, s, ticks=True), 'o2': p_comment}

# ------------------------------------------------------------------ per-shot overlays on 3D / reused footage
def overlays(base, sid, t, s):
    if sid == 'i1':
        callout(base, t, 0.15, 'TẬP 2 · CẦM TAY CHỈ VIỆC', y=200, x=60, col=RED, fg=WHITE)
    elif sid == 'i2':
        L = layer(); d = ImageDraw.Draw(L)
        if t >= T(9): cross(d, 60, 360, 80); txt(d, (160, 400), 'vẽ tay', font('black', 64), WHITE, 'lm', stroke=6)
        if t >= T(12): check(d, 60, 480, 80); txt(d, (160, 520), 'chỉ bằng code', font('black', 64), YEL, 'lm', stroke=6)
        comp(base, L)
    elif sid == 'b4d':
        callout(base, t, T(99), 'khối hộp  →  cái bàn', y=360)
        callout(base, t, T(104), 'khối trụ  →  cây đèn', y=460)
    elif sid == 'b4e':
        callout(base, t, s['start'] + 0.1, 'ghép lại = căn phòng', y=360)
    elif sid == 'b5c':
        callout(base, t, s['start'] + 0.1, 'PNG dán lên 1 tấm Plane', y=360)
    elif sid == 'b5e':
        if t < T(148): callout(base, t, s['start'] + 0.2, 'không bóng → lơ lửng', y=360, col=(255, 140, 140))
        else: callout(base, t, T(148), 'có bóng → đứng vững', y=360, col=(130, 255, 160))
        callout(base, t, T(149), 'Plane đen, mờ dần ra mép', y=460, col=(48, 52, 66), fg=WHITE, size=38)
    elif sid == 'b6b':
        callout(base, t, T(160), '1. Đèn chính · Spot · ấm', y=360, col=(255, 170, 90))
        callout(base, t, T(166), '2. Trăng · Area · lạnh', y=460, col=(140, 180, 255))
        callout(base, t, T(173), '3. Volume · khói bụi', y=560, col=(220, 220, 235))
    elif sid == 'b6c':
        callout(base, t, s['start'] + 0.1, 'Render › Freestyle: BẬT', y=360)
    elif sid == 'b7a':
        callout(base, t, T(189), 'camera = khung nhìn', y=360)
    elif sid == 'b7b':
        callout(base, t, T(190), '1 shot = 1 camera', y=360)
        callout(base, t, T(194), 'đẩy vào chậm (push-in)', y=460, col=(130, 200, 255))
    elif sid == 'o3':
        L = layer(); d = ImageDraw.Draw(L)
        chip(d, W_ / 2, 360, 'TẬP 3: BẠN CHỌN CHUYỆN', font('black', 52), RED, WHITE, anchor='c', pad=(30, 16))
        if t >= T(270):
            k = back((t - T(270)) / 0.3); rr(d, (340, 470, 740, 570), 50, fill=(40, 120, 255)); txt(d, (540, 520), '+ THEO DÕI', font('black', 48), WHITE, 'mm')
        comp(base, L)

# ------------------------------------------------------------------ frame
def step_of(sid):
    return STEP_OF.get(sid[:2])

def frame(n):
    t = n / FPS
    s = next(x for x in SHOTS if x['start'] <= t < x['end']) if t < SHOTS[-1]['end'] else SHOTS[-1]
    sid, lt, dur = s['id'], t - s['start'], s['end'] - s['start']
    if s['kind'] == 'H':
        im = ep2(n)
        if sid == 'b6c':
            nf = ep2(n, 'frames2nf'); u = prog(t, T(179) - 0.1, 0.9)
            if nf is not None and u < 1:
                x = int(W_ * u); im = im.copy(); im.paste(nf.crop((x, 0, W_, H_)), (x, 0))
                d = ImageDraw.Draw(im); d.rectangle((x - 3, 0, x + 3, H_), fill=(255, 230, 150))
        if im is None: im = Image.new('RGB', (W_, H_), (40, 30, 40))
    elif s['kind'] == 'R':
        a, spd = R_MAP[sid]; im = ep1(a + lt * spd)
    else:
        im = plate(sid, lt, dur)
    base = im.convert('RGBA')
    overlays(base, sid, t, s)
    st = step_of(sid)
    if sid in PANELS:
        sp = s
        if st and sid == STEP_START[st]:
            sp = dict(s, start=max(S[sid]['start'] + 1.25, T(s['word'] + 2) + 0.3) - 0.2)
        if t >= sp['start']: PANELS[sid](base, sid, t, sp)
    if st:
        first = S[STEP_START[st]]
        if sid == STEP_START[st]:
            tc_end = max(first['start'] + 1.25, T(first['word'] + 2) + 0.3)
            title_card(base, st, t, first['start'], tc_end)
            if t >= tc_end - 0.15: hud(base, st, t)
        else: hud(base, st, t)
    elif sid == 'o1': hud(base, 9, t, done=9)
    return base.convert('RGB')

def main():
    if '--at' in sys.argv:
        out = os.path.join(BUILD, 'preview'); os.makedirs(out, exist_ok=True)
        for x in sys.argv[sys.argv.index('--at') + 1].split(','):
            n = int(round(float(x) * FPS)); frame(n).save(os.path.join(out, f'p_{float(x):06.2f}.png'))
        return
    N = int(math.ceil(DUR * FPS))
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W_}x{H_}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '12', '-preset', 'medium', '-pix_fmt', 'yuv420p', os.path.join(BUILD, 'picture.mp4')], stdin=subprocess.PIPE)
    for n in range(N):
        p.stdin.write(frame(n).tobytes())
        if n % 60 == 0: print(f'{n}/{N}', flush=True)
    p.stdin.close(); p.wait(); print('picture done', p.returncode)

if __name__ == '__main__':
    main()
