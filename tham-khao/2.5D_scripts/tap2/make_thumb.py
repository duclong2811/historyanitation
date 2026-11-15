"""Episode 2 reel cover: hero still (b7b, camera gizmo pushing in on the host) + headline + tool checklist.
Run: python make_thumb.py  -> D:\\2.5D\\Thumbnail_Tap2.jpg/.png"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FB = 'C:/Windows/Fonts/seguibl.ttf'
W, H = 1080, 1920
YEL, RED, INK, GREEN = (255, 200, 42), (224, 48, 42), (20, 15, 16), (60, 190, 100)

def text_c(img, y, s, size, fill, stroke=10):
    f = ImageFont.truetype(FB, size); d = ImageDraw.Draw(img); w = d.textlength(s, font=f)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2 + 8, y + 12), s, font=f, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK)

def main():
    im = Image.open(os.path.join(HERE, '..', 'blender', 'renders', 'hero2_1866.png')).convert('RGBA').resize((W, H), Image.LANCZOS)
    g = Image.new('L', (1, H))
    for y in range(H): g.putpixel((0, y), int(205 * max(0, 1 - y / 860) ** 1.5))
    im.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), 8)] * 3 + [g.resize((W, H))]))
    d = ImageDraw.Draw(im); f = ImageFont.truetype(FB, 54); s = '2.5D  ·  TẬP 2'
    tw = d.textlength(s, font=f); x0 = (W - tw) / 2 - 34
    d.rounded_rectangle([x0, 290, x0 + tw + 68, 382], radius=46, fill=RED); d.text((x0 + 34, 296), s, font=f, fill='white')
    text_c(im, 380, '9 BƯỚC', 230, YEL, stroke=13)
    text_c(im, 640, 'LÀM HOẠT HÌNH 2.5D', 92, 'white', stroke=8)
    # tool checklist card (right, over the desk)
    card = Image.new('RGBA', im.size, (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
    bx0, by0, bx1, by1 = 600, 1180, 1010, 1480
    cd.rounded_rectangle((bx0 + 8, by0 + 14, bx1 + 8, by1 + 14), 34, fill=(0, 0, 0, 150)); card = card.filter(ImageFilter.GaussianBlur(14)); cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((bx0, by0, bx1, by1), 34, fill=(18, 16, 24, 235), outline=(255, 255, 255, 60), width=3)
    ft = ImageFont.truetype(FB, 56)
    for i, nm in enumerate(['Blender', 'Python', 'FFmpeg']):
        y = by0 + 42 + i * 82; sz = 56
        cd.ellipse((bx0 + 36, y, bx0 + 36 + sz, y + sz), fill=GREEN)
        cd.line([(bx0 + 36 + sz * 0.27, y + sz * 0.52), (bx0 + 36 + sz * 0.44, y + sz * 0.68), (bx0 + 36 + sz * 0.74, y + sz * 0.34)], fill='white', width=7, joint='curve')
        cd.text((bx0 + 120, y + sz / 2), nm, font=ft, fill='white', anchor='lm')
    im.alpha_composite(card)
    out = os.path.join(HERE, '..', 'Thumbnail_Tap2')
    rgb = im.convert('RGB'); rgb.save(out + '.png'); rgb.save(out + '.jpg', quality=94)
    prev = Image.new('RGB', (540 * 3 + 40, 960), (40, 40, 40)); prev.paste(rgb.resize((540, 960)), (0, 0))
    prev.paste(rgb.crop((0, (H - 1350) // 2, W, (H + 1350) // 2)).resize((540, 675)), (560, 0))
    prev.paste(rgb.crop((0, (H - 1080) // 2, W, (H + 1080) // 2)).resize((540, 540)), (1120, 0))
    prev.save(os.path.join(HERE, 'build', 'thumb_crops.png')); print('ok', out + '.jpg')

if __name__ == '__main__':
    main()
