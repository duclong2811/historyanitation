"""Reel cover / thumbnail: hero still (frame 470, 48 samples) + headline. Run: python make_thumb.py"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FB = 'C:/Windows/Fonts/seguibl.ttf'
W, H = 1080, 1920
YEL, RED, INK = (255, 200, 42), (224, 48, 42), (20, 15, 16)

def text_c(img, y, s, size, fill, stroke=10, track=0):
    f = ImageFont.truetype(FB, size); d = ImageDraw.Draw(img)
    w = d.textlength(s, font=f) + track * (len(s) - 1)
    # soft drop shadow
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    sd.text(((W - w) / 2 + 8, y + 12), s, font=f, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK)
    return f.getbbox(s)[3]

def main():
    im = Image.open(os.path.join(HERE, 'renders', 'hero_0470.png')).convert('RGBA').resize((W, H), Image.LANCZOS)
    # darken the top so the headline reads; keep the host bright
    g = Image.new('L', (1, H))
    for y in range(H): g.putpixel((0, y), int(200 * max(0, 1 - y / 900) ** 1.6))
    im.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), 8)] * 3 + [g.resize((W, H))]))
    # pill badge
    d = ImageDraw.Draw(im); f = ImageFont.truetype(FB, 54); s = '2.5D  ·  TẬP 1'
    tw = d.textlength(s, font=f); x0 = (W - tw) / 2 - 34
    d.rounded_rectangle([x0, 300, x0 + tw + 68, 392], radius=46, fill=RED)
    d.text((x0 + 34, 306), s, font=f, fill='white')
    text_c(im, 420, 'LÀM HOẠT HÌNH', 118, 'white', stroke=9)
    text_c(im, 555, 'BẰNG CODE', 168, YEL, stroke=12)
    out = os.path.join(HERE, '..', 'Thumbnail_25D.png')
    im.convert('RGB').save(out); im.convert('RGB').save(os.path.join(HERE, '..', 'Thumbnail_25D.jpg'), quality=94)
    # crop previews: 4:5 feed, 1:1 grid, and reel-UI overlay check
    im = im.convert('RGB'); prev = Image.new('RGB', (540 * 3 + 40, 960), (40, 40, 40))
    prev.paste(im.resize((540, 960)), (0, 0))
    c45 = im.crop((0, (H - 1350) // 2, W, (H + 1350) // 2)).resize((540, 675)); prev.paste(c45, (560, 0))
    c11 = im.crop((0, (H - 1080) // 2, W, (H + 1080) // 2)).resize((540, 540)); prev.paste(c11, (1120, 0))
    prev.save(os.path.join(HERE, 'renders', 'thumb_crops.png'))
    print('ok', out)

if __name__ == '__main__':
    main()
