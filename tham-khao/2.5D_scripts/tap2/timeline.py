"""Episode 2 timeline: re-time the voice (breathing gaps before each step), shot table keyed to word indices.
Run: python timeline.py   -> build/voice_rt.wav, build/timeline.json"""
import json, os, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.join(HERE, '..', 'growkaz-stickman-studio', 'projects', 'tap2')
BUILD = os.path.join(HERE, 'build')
SR = 48000
GAP = 0.45
GAP_IDX = [21, 41, 63, 83, 114, 156, 187, 207, 236, 255]   # "Bước một" … "Bước chín", outro
TAIL = 1.0

# (id, first word index, kind)   kinds: H = new 3D render, R = reuse ep1 frames, P = tutorial panel
SHOTS = [
    ('i1', 0, 'H'), ('i2', 9, 'R'), ('i3', 15, 'P'),
    ('b1a', 21, 'H'), ('b1b', 24, 'P'), ('b1c', 32, 'P'),
    ('b2a', 41, 'P'), ('b2b', 53, 'P'),
    ('b3a', 63, 'H'), ('b3b', 68, 'P'), ('b3c', 75, 'P'),
    ('b4a', 83, 'P'), ('b4b', 91, 'P'), ('b4c', 94, 'P'), ('b4d', 99, 'H'), ('b4e', 109, 'R'),
    ('b5a', 114, 'H'), ('b5b', 118, 'P'), ('b5c', 127, 'R'), ('b5d', 132, 'P'), ('b5e', 142, 'H'),
    ('b6a', 156, 'H'), ('b6b', 160, 'H'), ('b6c', 178, 'H'),
    ('b7a', 187, 'H'), ('b7b', 190, 'H'), ('b7c', 198, 'P'),
    ('b8a', 207, 'P'), ('b8b', 214, 'P'), ('b8c', 230, 'P'),
    ('b9a', 236, 'P'), ('b9b', 243, 'P'), ('b9c', 249, 'P'),
    ('o1', 255, 'P'), ('o2', 262, 'P'), ('o3', 270, 'R'),
]

def main():
    os.makedirs(BUILD, exist_ok=True)
    words = json.load(open(os.path.join(STUDIO, 'timeline', 'words.json'), encoding='utf-8'))['words']
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(HERE, 'tap2.mp3'), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    voice = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    cuts = [(words[i - 1]['end'] + words[i]['start']) / 2 for i in GAP_IDX]
    parts, prev = [], 0
    for c in cuts:
        k = int(c * SR); seg = voice[prev:k].copy()
        f = int(0.01 * SR); seg[-f:] *= np.linspace(1, 0, f)[:, None]
        parts += [seg, np.zeros((int(GAP * SR), 2), np.float32)]; prev = k
    seg = voice[prev:].copy(); f = int(0.01 * SR); seg[:f] *= np.linspace(0, 1, f)[:, None]; parts.append(seg)
    out = np.concatenate(parts)
    shift = lambda t: t + GAP * sum(1 for c in cuts if t >= c)
    rt = [dict(word=w['word'], start=round(shift(w['start']), 3), end=round(shift(w['end']), 3)) for w in words]
    dur = round(rt[-1]['end'] + TAIL, 3)
    out = np.concatenate([out, np.zeros((max(0, int(dur * SR) - len(out)), 2), np.float32)])
    wav = os.path.join(BUILD, 'voice_rt.wav')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-i', '-', '-c:a', 'pcm_s16le', wav], input=out.tobytes(), check=True)
    cut_new = {i: round(c + GAP * k, 3) for k, (i, c) in enumerate(zip(GAP_IDX, cuts))}
    shots = []
    for n, (sid, wi, kind) in enumerate(SHOTS):
        t0 = 0.0 if wi == 0 else (cut_new[wi] if wi in cut_new else round(rt[wi]['start'] - 0.12, 3))
        shots.append(dict(id=sid, word=wi, kind=kind, start=t0))
    for a, b in zip(shots, shots[1:]): a['end'] = b['start']
    shots[-1]['end'] = dur
    json.dump(dict(duration=dur, gap=GAP, words=rt, shots=shots), open(os.path.join(BUILD, 'timeline.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for s in shots: print(f"{s['id']:4s} {s['kind']} {s['start']:6.2f}-{s['end']:6.2f} ({s['end'] - s['start']:.2f})  {rt[s['word']]['word']}")
    print('duration', dur)

if __name__ == '__main__':
    main()
