"""Episode 2 final: picture.mp4 (15 fps) -> 30 fps, word captions (ASS, 1-2 words), voice+music+SFX mix.
Run: python make_final.py"""
import json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, 'build', 'timeline.json'), encoding='utf-8'))
WORDS = TL['words']; DUR = TL['duration']
MIX = os.path.join(HERE, '..', 'growkaz-stickman-studio', 'projects', 'tap2', 'build', 'mix.wav')
OUT = os.path.join(HERE, '..', 'Tap2_Huong_dan_2.5D.mp4')
# gold words (tools & key terms); these also keep their original capitalisation
EMPH = {8, 14, 26, 34, 35, 44, 66, 67, 88, 90, 96, 123, 135, 146, 159, 174, 179, 189, 197, 201, 209, 211, 218, 219, 238, 248, 264}
KEEP_CASE = {8, 26, 44, 88, 90, 96, 123, 179, 211, 238}
PUNCT = '.,!?;:…"'

def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def captions(path):
    groups, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(i)
        if len(cur) >= 2 or w['word'].strip()[-1] in PUNCT: groups.append(cur); cur = []
    if cur: groups.append(cur)
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Segoe UI Black,100,&H00FFFFFF,&H00FFFFFF,&H00140F10,&H64000000,0,0,0,0,100,100,0,0,1,7,3,2,60,60,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for gi, g in enumerate(groups):
        t0 = WORDS[g[0]]['start'] - 0.04
        t1 = WORDS[groups[gi + 1][0]]['start'] - 0.04 if gi + 1 < len(groups) else WORDS[g[-1]]['end'] + 0.5
        t1 = min(t1, WORDS[g[-1]]['end'] + 0.45)
        parts = []
        for k in g:
            word = WORDS[k]['word'].strip().strip(PUNCT)
            word = word if k in KEEP_CASE else word.lower()
            parts.append(r'{\c&H2AC8FF&}' + word + r'{\c&HFFFFFF&}' if k in EMPH else word)
        pop = r'{\fscx86\fscy86\t(0,90,\fscx100\fscy100)}'
        lines.append(f'Dialogue: 0,{ass_time(t0)},{ass_time(t1)},Cap,,0,0,0,,{pop}' + ' '.join(parts))
    open(path, 'w', encoding='utf-8-sig').write(head + '\n'.join(lines) + '\n')

if __name__ == '__main__':
    os.chdir(os.path.join(HERE, 'build'))
    captions('captions.ass')
    vf = f"fps=30,subtitles=captions.ass:fontsdir='C\\:/Windows/Fonts',fade=t=in:st=0:d=0.3,fade=t=out:st={DUR - 0.7:.2f}:d=0.7"
    cmd = ['ffmpeg', '-y', '-v', 'error', '-i', 'picture.mp4', '-i', MIX, '-vf', vf, '-map', '0:v', '-map', '1:a', '-t', str(DUR),
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT]
    r = subprocess.run(cmd); print('exit', r.returncode, os.path.abspath(OUT))
