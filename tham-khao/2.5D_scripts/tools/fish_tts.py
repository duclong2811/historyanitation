"""Fish Audio text-to-speech for the 2.5D pipeline.

Key, voice and model come from D:\\2.5D\\.env (FISH_API_KEY, FISH_VOICE_ID, FISH_MODEL) or the environment.
Audio tags such as [excited] [laughing] [whispering] [break] go straight into the text.

  python tools/fish_tts.py "[excited] Xin chào!" -o vo-fish/hello.mp3
  python tools/fish_tts.py --file tap3/script_fish.txt -o tap3/vo      # one clip per non-empty line: 01.mp3, 02.mp3 …
  python tools/fish_tts.py --file tap3/script_fish.txt -o tap3/vo --join   # also writes tap3/vo/full.mp3
Options: --voice <reference_id>  --model <s2.1-pro-free|…>  --format mp3|wav  --gap 0.25 (seconds between joined clips)
"""
import argparse, json, os, subprocess, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'https://api.fish.audio/v1/tts'

def load_env():
    p = os.path.join(ROOT, '.env')
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            ln = ln.strip()
            if ln and not ln.startswith('#') and '=' in ln:
                k, v = ln.split('=', 1); os.environ.setdefault(k.strip(), v.strip())

def tts(text, out, voice, model, fmt, key, tries=4):
    body = json.dumps({'text': text, 'reference_id': voice, 'format': fmt}).encode('utf-8')
    req = urllib.request.Request(URL, data=body, method='POST', headers={
        'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'model': model})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r: data = r.read()
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            open(out, 'wb').write(data); return len(data)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:400]
            if e.code in (429, 500, 502, 503, 504) and k < tries - 1:
                time.sleep(2 * (k + 1)); continue
            sys.exit(f'Fish Audio error {e.code}: {msg}')
        except urllib.error.URLError as e:
            if k < tries - 1: time.sleep(2 * (k + 1)); continue
            sys.exit(f'network error: {e.reason}')

def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0

def join(paths, out, gap):
    lst = out + '.txt'; sil = os.path.join(os.path.dirname(out), '_gap.wav')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=mono', '-t', str(gap), sil], check=True)
    with open(lst, 'w', encoding='utf-8') as f:
        for i, p in enumerate(paths):
            f.write(f"file '{os.path.abspath(p).replace(os.sep, '/')}'\n")
            if gap > 0 and i < len(paths) - 1: f.write(f"file '{os.path.abspath(sil).replace(os.sep, '/')}'\n")
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-ar', '44100', '-ac', '1', out], check=True)
    os.remove(lst); os.remove(sil)

def main():
    load_env()
    ap = argparse.ArgumentParser(description='Fish Audio TTS')
    ap.add_argument('text', nargs='?'); ap.add_argument('--file'); ap.add_argument('-o', '--out', default='fish.mp3')
    ap.add_argument('--voice', default=os.environ.get('FISH_VOICE_ID')); ap.add_argument('--model', default=os.environ.get('FISH_MODEL', 's2.1-pro-free'))
    ap.add_argument('--format', default='mp3'); ap.add_argument('--join', action='store_true'); ap.add_argument('--gap', type=float, default=0.25)
    a = ap.parse_args()
    key = os.environ.get('FISH_API_KEY')
    if not key: sys.exit('FISH_API_KEY missing: add it to D:\\2.5D\\.env')
    if not a.voice: sys.exit('no voice: pass --voice <reference_id> or set FISH_VOICE_ID in .env')
    if a.file:
        lines = [l.strip() for l in open(a.file, encoding='utf-8') if l.strip() and not l.strip().startswith('#')]
        os.makedirs(a.out, exist_ok=True); outs = []
        for i, ln in enumerate(lines, 1):
            p = os.path.join(a.out, f'{i:02d}.{a.format}'); n = tts(ln, p, a.voice, a.model, a.format, key); outs.append(p)
            print(f'{i:02d}  {duration(p):5.2f}s  {n // 1024} KB  {ln[:60]}')
        if a.join:
            full = os.path.join(a.out, f'full.{a.format}'); join(outs, full, a.gap); print(f'joined -> {full} ({duration(full):.2f}s)')
    else:
        if not a.text: sys.exit('give text or --file')
        n = tts(a.text, a.out, a.voice, a.model, a.format, key); print(f'{a.out}  {duration(a.out):.2f}s  {n // 1024} KB')

if __name__ == '__main__':
    main()
