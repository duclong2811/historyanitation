"""Composite the Blender frames into the final short: on-twos frames -> 30 fps, blueprint pass on s11, counter on s13,
badges, word-level captions (ASS), voice+music+SFX mix. Run: python make_final.py [--preview]"""
import json, os, subprocess, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.join(HERE, '..', 'growkaz-stickman-studio', 'projects', 'vo-short')
WORDS = json.load(open(os.path.join(STUDIO, 'timeline', 'words.json'), encoding='utf-8'))['words']
MIX = os.path.join(STUDIO, 'build', 'mix.wav')
OUT = os.path.join(HERE, '..', 'Video_25D_Blender.mp4')
DUR = 34.1
EMPH = {12, 13, 16, 19, 27, 33, 45, 52, 53, 56, 57, 58, 61, 63, 70, 75}
PUNCT = '.,!?;:…'

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
Style: Cap,Segoe UI Black,104,&H00FFFFFF,&H00FFFFFF,&H00140F10,&H64000000,0,0,0,0,100,100,0,0,1,7,3,2,60,60,400,1

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
            word = WORDS[k]['word'].strip().rstrip(PUNCT).lower()
            parts.append(r'{\c&H2AC8FF&}' + word + r'{\c&HFFFFFF&}' if k in EMPH else word)
        pop = r'{\fscx86\fscy86\t(0,90,\fscx100\fscy100)}'
        lines.append(f'Dialogue: 0,{ass_time(t0)},{ass_time(t1)},Cap,,0,0,0,,{pop}' + ' '.join(parts))
    open(path, 'w', encoding='utf-8-sig').write(head + '\n'.join(lines) + '\n')

def concat_list(path):
    fr = sorted(glob.glob(os.path.join(HERE, 'frames', 'f_*.png')))
    with open(path, 'w', encoding='utf-8') as f:
        for p in fr:
            f.write(f"file '{p.replace(os.sep, '/')}'\nduration {2 / 30:.6f}\n")
        f.write(f"file '{fr[-1].replace(os.sep, '/')}'\n")
    return len(fr)

def esc(s):   # drawtext text escaping inside a filter script
    return s.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'").replace('%', '\\%')

def filters(fontfile):
    ff = fontfile.replace(':', '\\:')
    code = ["light = lamp.on()", "dust = volume(0.08)", 'shadow = "contact"', "camera.push_in(1.08)"]
    bp0, bp1 = 13.62, 14.92
    f = [f"[0:v]fps=30,format=yuv420p,split=2[base][bp]",
         f"[bp]edgedetect=low=0.06:high=0.18,negate,colorchannelmixer=rr=0.15:gg=0.45:bb=1.0,eq=contrast=1.4[bp2]",
         f"[base][bp2]overlay=enable='between(t,{bp0},{bp1})'[v1]"]
    v = 'v1'
    for i, ln in enumerate(code):
        t = bp0 + 0.08 + i * 0.22
        f.append(f"[{v}]drawtext=fontfile='{ff}':text='{esc(ln)}':x=90:y={260 + i * 84}:fontsize=54:fontcolor=0xE8F2FF:borderw=3:bordercolor=0x0A1430:enable='between(t,{t:.2f},{bp1})'[c{i}]"); v = f'c{i}'
    # s13: view counter over the screen + 8 NGÀY badge
    t27, tend, t8 = 16.94, 18.05, 19.14
    cnt = f"%{{eif\\:min(27\\,max(0\\,(t-{t27})*27/{tend - t27}))\\:d}} TRIỆU"
    f.append(f"[{v}]drawtext=fontfile='{ff}':text='{cnt}':x=(w-text_w)/2:y=600:fontsize=150:fontcolor=0xFF5A8C:borderw=6:bordercolor=0x1A0E1E:enable='between(t,16.86,20.3)'[d1]")
    f.append("[d1]null[d2]")
    # s20: TẬP 2 badge
    f.append(f"[d2]drawtext=fontfile='{ff}':text='TẬP 2':x=(w-text_w)/2:y=170:fontsize=84:fontcolor=white:box=1:boxcolor=0xE0302A:boxborderw=26:enable='between(t,29.62,34.1)'[d3]")
    f.append("[d3]subtitles=captions.ass:fontsdir='C\\:/Windows/Fonts',fade=t=in:st=0:d=0.4,fade=t=out:st=33.3:d=0.8[vout]")
    return ';\n'.join(f)

if __name__ == '__main__':
    os.chdir(HERE)
    captions('captions.ass')
    n = concat_list('frames.txt'); print('frames', n)
    open('filters.txt', 'w', encoding='utf-8').write(filters('C:/Windows/Fonts/seguibl.ttf'))
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', 'frames.txt', '-i', MIX,
           '-/filter_complex', 'filters.txt', '-map', '[vout]', '-map', '1:a', '-t', str(DUR),
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT]
    r = subprocess.run(cmd); print('exit', r.returncode, OUT)
