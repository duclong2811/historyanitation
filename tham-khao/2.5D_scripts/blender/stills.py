# render one mid-frame still per shot at half size: blender -b episode.blend --python stills.py
import bpy, os
sc = bpy.context.scene; sc.render.resolution_percentage = 50; sc.eevee.taa_render_samples = 4
out = bpy.path.abspath('//renders/stills/'); os.makedirs(out, exist_ok=True)
ms = sorted(sc.timeline_markers, key=lambda m: m.frame); ends = [m.frame for m in ms[1:]] + [sc.frame_end + 1]
only = os.environ.get('SHOTS', '').split(',') if os.environ.get('SHOTS') else None
for m, e in zip(ms, ends):
    if only and m.name not in only: continue
    f = int(os.environ.get('AT_' + m.name, (m.frame + e) // 2)); sc.frame_set(f); sc.camera = m.camera
    sc.render.filepath = out + f'{m.name}_{f:04d}.png'; bpy.ops.render.render(write_still=True)
