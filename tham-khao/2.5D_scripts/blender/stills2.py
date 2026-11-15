# EP2 review stills: blender -b episode2.blend --python stills2.py   (env AT="b4d:0.2,0.6;b6b:0.1,0.9", PCT=50)
import bpy, os, json
sc = bpy.context.scene; sc.render.resolution_percentage = int(os.environ.get('PCT', 50)); sc.eevee.taa_render_samples = 4
TL = json.load(open(bpy.path.abspath('//../tap2/build/timeline.json'), encoding='utf-8'))
sh = {s['id']: s for s in TL['shots'] if s['kind'] == 'H'}
want = {}
for part in os.environ.get('AT', '').split(';'):
    if ':' in part: k, v = part.split(':'); want[k] = [float(x) for x in v.split(',')]
if not want: want = {k: [0.15, 0.85] for k in sh}
out = bpy.path.abspath('//renders/stills2/'); os.makedirs(out, exist_ok=True)
for k, rels in want.items():
    s = sh[k]
    for r in rels:
        f = int(round((s['start'] + r * (s['end'] - s['start'])) * 30)); f = min(f, int(s['end'] * 30) - 1)
        sc.frame_set(f); sc.camera = bpy.data.objects['CAM_' + k]
        sc.render.filepath = out + f'{k}_{int(r * 100):02d}.png'; bpy.ops.render.render(write_still=True)
