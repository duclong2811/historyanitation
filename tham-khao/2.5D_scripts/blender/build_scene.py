"""Build the whole 2.5D episode in Blender: three 3D sets (attic workshop, empty soundstage, night street),
a flat 2D host cut-out (unlit image planes, replacement expressions), 20 shot cameras bound to timeline markers,
light/prop animation synced to the voiceover. Freestyle outlines give the illustrated look.
Run: blender -b --python build_scene.py      (writes episode.blend next to this file)
"""
import bpy, math, os, random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex'); CHR = os.path.join(HERE, 'chars')
FPS = 30
F = lambda t: int(round(t * FPS))
SHOTS = [('s01', 0.0, 2.3), ('s02', 2.3, 4.25), ('s03', 4.25, 5.22), ('s04', 5.22, 6.25), ('s05', 6.25, 7.25),
         ('s06', 7.25, 9.25), ('s07', 9.25, 11.15), ('s08', 11.15, 11.98), ('s09', 11.98, 12.62), ('s10', 12.62, 13.62),
         ('s11', 13.62, 14.92), ('s12', 14.92, 16.85), ('s13', 16.85, 20.3), ('s14', 20.3, 21.5), ('s15', 21.5, 23.15),
         ('s16', 23.15, 24.7), ('s17', 24.7, 26.95), ('s18', 26.95, 27.85), ('s19', 27.85, 29.5), ('s20', 29.5, 34.1)]
SH = {k: (F(a), F(b)) for k, a, b in SHOTS}
END = F(34.1)
EP = os.environ.get('EP', '1')
if EP == '2':
    import json
    TL = json.load(open(os.path.join(HERE, '..', 'tap2', 'build', 'timeline.json'), encoding='utf-8'))
    SHOTS = [(s['id'], s['start'], s['end']) for s in TL['shots']]
    SH = {k: (F(a), F(b)) for k, a, b in SHOTS}
    END = F(TL['duration'])
rnd = random.Random(7)

# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'CONSTANT'
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, 100
sc.render.fps = FPS; sc.frame_start, sc.frame_end = 0, END - 1
sc.eevee.taa_render_samples = 8
sc.frame_step = 2
try: sc.eevee.use_shadows = True
except AttributeError: pass
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.0
sc.render.film_transparent = False
world = bpy.data.worlds.new('World'); sc.world = world
try: world.use_nodes = True
except Exception: pass
wn = world.node_tree.nodes; wn['Background'].inputs[0].default_value = (0.05, 0.045, 0.09, 1); wn['Background'].inputs[1].default_value = 0.6

COL = sc.collection
NOLINE = bpy.data.collections.new('NOLINE'); COL.children.link(NOLINE)

# ---------------------------------------------------------------- material helpers
_mats = {}
def bsdf_mat(name, color, rough=0.8, metal=0.0, emit=None, emit_strength=0.0):
    if name in _mats: return _mats[name]
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = emit_strength
    _mats[name] = m; return m

def emit_mat(name, color, strength=1.0):
    if name in _mats: return _mats[name]
    m = bpy.data.materials.new(name); nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (*color, 1); e.inputs[1].default_value = strength
    o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o.inputs[0]); _mats[name] = m; return m

def image_mat(name, path, strength=1.0, alpha=False, emissive=True):
    m = bpy.data.materials.new(name); nt = m.node_tree; nt.nodes.clear()
    img = bpy.data.images.load(path, check_existing=True)
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = img; tx.interpolation = 'Cubic'
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    if emissive:
        sh = nt.nodes.new('ShaderNodeEmission'); nt.links.new(tx.outputs['Color'], sh.inputs['Color']); sh.inputs['Strength'].default_value = strength
    else:
        sh = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(tx.outputs['Color'], sh.inputs['Base Color']); sh.inputs['Roughness'].default_value = 0.9
    if alpha:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(tx.outputs['Alpha'], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(sh.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], o.inputs[0])
        try: m.surface_render_method = 'DITHERED'
        except AttributeError: m.blend_method = 'HASHED'
    else:
        nt.links.new(sh.outputs[0], o.inputs[0])
    return m

def proc_mat(name, kind, c1, c2, c3=(0.05, 0.04, 0.05), scale=1.0):
    """procedural: 'planks' (floor), 'bricks' (wall), 'plaster', 'wood', 'concrete'"""
    m = bpy.data.materials.new(name); nt = m.node_tree; b = nt.nodes.get('Principled BSDF'); b.inputs['Roughness'].default_value = 0.85
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); nt.links.new(tc.outputs['Object'], mp.inputs[0])
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 6.0; nt.links.new(mp.outputs[0], noise.inputs[0])
    if kind in ('planks', 'bricks'):
        br = nt.nodes.new('ShaderNodeTexBrick'); nt.links.new(mp.outputs[0], br.inputs[0])
        br.inputs['Color1'].default_value = (*c1, 1); br.inputs['Color2'].default_value = (*c2, 1); br.inputs['Mortar'].default_value = (*c3, 1)
        if kind == 'planks':
            br.inputs['Scale'].default_value = 1.0; br.inputs['Mortar Size'].default_value = 0.008; br.inputs['Brick Width'].default_value = 1.6; br.inputs['Row Height'].default_value = 0.16; br.offset = 0.37
        else:
            br.inputs['Scale'].default_value = 1.0; br.inputs['Mortar Size'].default_value = 0.012; br.inputs['Brick Width'].default_value = 0.24; br.inputs['Row Height'].default_value = 0.085
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 0.35
        nt.links.new(br.outputs['Color'], mx.inputs[6]); nt.links.new(noise.outputs['Color'], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    else:
        ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (*c1, 1); ramp.color_ramp.elements[1].color = (*c2, 1)
        nt.links.new(noise.outputs['Fac'], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs['Base Color'])
        if kind == 'wood': noise.inputs['Scale'].default_value = 3.0; noise.inputs['Detail'].default_value = 8
    return m

# ---------------------------------------------------------------- geometry helpers
def link(ob, noline=False):
    (NOLINE if noline else COL).objects.link(ob); return ob

def mesh_obj(name, verts, faces, mat=None, noline=False, uv=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    if uv:
        lay = me.uv_layers.new();
        for i, l in enumerate(me.loops): lay.data[i].uv = uv[l.vertex_index]
    ob = bpy.data.objects.new(name, me)
    if mat: ob.data.materials.append(mat)
    return link(ob, noline)

def box(name, size, loc, mat, rot=(0, 0, 0), noline=False, parent=None):
    sx, sy, sz = [s / 2 for s in size]
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz), (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    ob = mesh_obj(name, v, f, mat, noline); ob.location = loc; ob.rotation_euler = rot
    if parent: set_parent(ob, parent)
    return ob

def cyl(name, r, h, loc, mat, rot=(0, 0, 0), seg=24, r2=None, noline=False, parent=None):
    r2 = r if r2 is None else r2; v = []; f = []
    for i in range(seg):
        a = 2 * math.pi * i / seg; v += [(math.cos(a) * r, math.sin(a) * r, -h / 2), (math.cos(a) * r2, math.sin(a) * r2, h / 2)]
    for i in range(seg):
        j = (i + 1) % seg; f.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    f.append(tuple(2 * i for i in reversed(range(seg)))); f.append(tuple(2 * i + 1 for i in range(seg)))
    ob = mesh_obj(name, v, f, mat, noline); ob.location = loc; ob.rotation_euler = rot
    for p in ob.data.polygons: p.use_smooth = True
    if parent: set_parent(ob, parent)
    return ob

def sphere(name, r, loc, mat, noline=False, seg=16, parent=None):
    v = []; f = []; rings = seg // 2
    for i in range(rings + 1):
        th = math.pi * i / rings
        for j in range(seg):
            ph = 2 * math.pi * j / seg; v.append((r * math.sin(th) * math.cos(ph), r * math.sin(th) * math.sin(ph), r * math.cos(th)))
    for i in range(rings):
        for j in range(seg):
            a = i * seg + j; b = i * seg + (j + 1) % seg; f.append((a, b, b + seg, a + seg))
    ob = mesh_obj(name, v, f, mat, noline); ob.location = loc
    for p in ob.data.polygons: p.use_smooth = True
    if parent: set_parent(ob, parent)
    return ob

def plane(name, w, h, loc, mat, rot=(math.pi / 2, 0, 0), noline=True, parent=None, origin_bottom=False):
    z0, z1 = (0, h) if origin_bottom else (-h / 2, h / 2)
    v = [(-w / 2, z0, 0), (w / 2, z0, 0), (w / 2, z1, 0), (-w / 2, z1, 0)]
    ob = mesh_obj(name, v, [(0, 1, 2, 3)], mat, noline, uv={0: (0, 0), 1: (1, 0), 2: (1, 1), 3: (0, 1)})
    ob.location = loc; ob.rotation_euler = rot
    if parent: set_parent(ob, parent)
    return ob

def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); e.location = loc; e.empty_display_size = 0.2; link(e, True); return e

def world_m(o):   # matrix_world is stale until a depsgraph update, so compute it from the transforms
    from mathutils import Matrix
    m = Matrix.LocRotScale(o.location, o.rotation_euler, o.scale)
    return (world_m(o.parent) @ o.matrix_parent_inverse @ m) if o.parent else m

def set_parent(ob, par):   # keep ob where it is: its loc/rot stay in world terms
    ob.parent = par; ob.matrix_parent_inverse = world_m(par).inverted()

def light(name, kind, loc, energy, color, rot=(0, 0, 0), size=0.2, spot=None, parent=None):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind in ('POINT', 'SPOT'): ld.shadow_soft_size = size
    if kind == 'AREA': ld.size = size
    if spot: ld.spot_size = math.radians(spot); ld.spot_blend = 0.5
    ob = bpy.data.objects.new(name, ld); ob.location = loc; ob.rotation_euler = rot; link(ob, True)
    if parent: set_parent(ob, parent)
    return ob

PREFS = bpy.context.preferences.edit
def key(datablock, path, frame, value, interp='CONSTANT', index=-1):
    if index >= 0: getattr(datablock, path)[index] = value
    else: setattr(datablock, path, value)
    datablock.keyframe_insert(path, frame=frame, index=index)
    WANT[(datablock.name, path, frame)] = interp
WANT = {}
LINEAR_IDS = set()
def all_fcurves(idb):
    ad = getattr(idb, 'animation_data', None)
    if not ad or not ad.action: return []
    act = ad.action; out = []
    for layer in getattr(act, 'layers', []):
        for strip in layer.strips:
            for cb in getattr(strip, 'channelbags', []): out += list(cb.fcurves)
    if not out and hasattr(act, 'fcurves'): out = list(act.fcurves)
    return out
def fix_interpolation():
    pools = list(bpy.data.objects) + list(bpy.data.lights) + list(bpy.data.cameras) + [m.node_tree for m in bpy.data.materials if m.node_tree]
    n = 0
    for idb in pools:
        dflt = 'LINEAR' if idb.name in LINEAR_IDS else 'CONSTANT'
        for fc in all_fcurves(idb):
            for kp in fc.keyframe_points:
                kp.interpolation = WANT.get((idb.name, fc.data_path, int(round(kp.co[0]))), dflt); n += 1
    print('interp set on', n, 'keys')

def set_interp(ob, interp='BEZIER'):
    pass

def aim(ob, target):
    d = Vector(target) - ob.location; ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- ATTIC (origin). Camera looks toward +Y; back wall at y=3
G = {n: empty('G_' + n, loc) for n, loc in [('floor', (0, 1, 0)), ('back', (0, 3, 0)), ('left', (-3.2, 1, 0)), ('roof', (2, 2, 3)),
                                              ('window', (-1.6, 3, 0.8)), ('shelf', (1.6, 3, 1.2)), ('desk', (0.4, 1.3, 0)), ('rug', (0.2, 1.2, 0)), ('decor', (-0.2, 2.9, 2.2))]}
wood_dark = proc_mat('wood_dark', 'wood', (0.10, 0.055, 0.035), (0.20, 0.11, 0.06))
wood_mid = proc_mat('wood_mid', 'wood', (0.28, 0.15, 0.08), (0.45, 0.26, 0.13))
floor_m = proc_mat('floor', 'planks', (0.36, 0.20, 0.11), (0.27, 0.14, 0.08), (0.08, 0.04, 0.03), 1.0)
brick_m = proc_mat('brick', 'bricks', (0.42, 0.20, 0.14), (0.33, 0.15, 0.11), (0.55, 0.47, 0.40), 1.0)
plaster_m = proc_mat('plaster', 'plaster', (0.55, 0.45, 0.40), (0.66, 0.56, 0.48))
metal_m = bsdf_mat('metal', (0.12, 0.12, 0.14), 0.35, 0.8)
black_m = bsdf_mat('blackish', (0.035, 0.03, 0.04), 0.6)

box('floor', (9, 8, 0.1), (0, 1, -0.05), floor_m, parent=G['floor'])
# back wall with a window opening x[-2.25,-0.95] z[0.8,2.6]
for nm, sx, cx, sz, cz in [('wallL', 1.75, -3.125, 3.8, 1.9), ('wallR', 4.95, 1.525, 3.8, 1.9), ('wallB', 1.3, -1.6, 0.8, 0.4), ('wallT', 1.3, -1.6, 1.2, 3.2)]:
    box(nm, (sx, 0.2, sz), (cx, 3.1, cz), brick_m, parent=G['back'])
box('wallLeft', (0.2, 8, 3.8), (-4.0, 1, 1.9), plaster_m, parent=G['left'])
# sloped roof on the right + beams
roof = box('roof', (4.8, 6.5, 0.12), (3.3, 1.2, 3.35), wood_dark, rot=(0, math.radians(-35), 0), parent=G['roof'])
box('ceiling', (9, 8, 0.1), (0, 1, 4.1), wood_dark, parent=G['roof'])
box('wallTop', (9, 0.25, 0.5), (0, 3.1, 3.95), wood_dark, parent=G['back'])
for y in (-0.6, 0.6, 1.8, 2.9):
    box(f'rafter{y}', (4.9, 0.16, 0.18), (3.25, y, 3.25), wood_mid, rot=(0, math.radians(-35), 0), parent=G['roof'])
box('ridge', (9, 0.22, 0.22), (0, 1.0, 3.75), wood_dark, rot=(math.pi / 2, 0, math.pi / 2), parent=G['roof'])
box('tiebeam', (9, 0.2, 0.24), (0, 2.6, 3.05), wood_dark, parent=G['roof'])
# window: frame + mullions + night city behind
for nm, s, l in [('wf_l', (0.12, 0.18, 1.9), (-2.28, 3.0, 1.7)), ('wf_r', (0.12, 0.18, 1.9), (-0.92, 3.0, 1.7)), ('wf_b', (1.5, 0.3, 0.12), (-1.6, 2.95, 0.78)),
                 ('wf_t', (1.5, 0.18, 0.12), (-1.6, 3.0, 2.62)), ('wm_v', (0.06, 0.1, 1.8), (-1.6, 3.02, 1.7)), ('wm_h1', (1.3, 0.1, 0.06), (-1.6, 3.02, 1.4)), ('wm_h2', (1.3, 0.1, 0.06), (-1.6, 3.02, 2.0))]:
    box(nm, s, l, wood_mid, parent=G['window'])
plane('city_bg', 3.6, 2.7, (-1.6, 4.6, 1.75), image_mat('city', os.path.join(TEX, 'night_city.png'), 1.0), parent=G['window'])
# shelves with books
for i, z in enumerate((1.45, 2.05)):
    box(f'shelf{i}', (2.2, 0.32, 0.05), (1.6, 2.86, z), wood_mid, parent=G['shelf'])
    x = 0.6
    while x < 2.6:
        w = rnd.uniform(0.04, 0.08); h = rnd.uniform(0.2, 0.32)
        col = rnd.choice([(0.5, 0.12, 0.1), (0.12, 0.2, 0.4), (0.55, 0.42, 0.12), (0.2, 0.33, 0.18), (0.35, 0.15, 0.35), (0.65, 0.55, 0.4)])
        tilt = rnd.choice([0, 0, 0, 0.18]) if x < 2.4 else 0
        box(f'book{i}_{x:.2f}', (w, 0.22, h), (x, 2.84, z + 0.025 + h / 2 - (0.02 if tilt else 0)), bsdf_mat(f'bk{col}', col, 0.7), rot=(0, tilt, 0), parent=G['shelf'])
        x += w + rnd.uniform(0.0, 0.015) + (0.12 if rnd.random() < 0.1 else 0)
    for bx_ in (0.55, 2.65): box(f'bracket{i}{bx_}', (0.04, 0.25, 0.18), (bx_, 2.9, z - 0.1), metal_m, parent=G['shelf'])
# storyboards pinned on the wall
for i, x in enumerate((-0.55, -0.05, 0.45)):
    plane(f'board{i}', 0.36, 0.48, (x, 2.98, 2.35 + (0.04 if i == 1 else 0)), image_mat(f'sb{i}', os.path.join(TEX, f'storyboard{i}.png'), emissive=False), rot=(math.pi / 2, (i - 1) * 0.06, 0), parent=G['decor'])
    sphere(f'pin{i}', 0.018, (x, 2.95, 2.56 + (0.04 if i == 1 else 0)), bsdf_mat('pinred', (0.8, 0.1, 0.1), 0.4), parent=G['decor'])
# string lights along the back wall
bulb_m = emit_mat('bulb_warm', (1.0, 0.75, 0.4), 6.0)
for i in range(26):
    x = -3.0 + i * 0.24; z = 3.0 - 0.18 * math.sin(math.pi * ((i % 13) / 12))
    sphere(f'sl{i}', 0.03, (x, 2.95, z), bulb_m, noline=True, parent=G['decor'])
# rug
plane('rug', 2.6, 1.8, (0.2, 1.3, 0.006), image_mat('rug', os.path.join(TEX, 'rug.png'), emissive=False), rot=(0, 0, 0), parent=G['rug'])
# plant
cyl('pot', 0.16, 0.3, (-2.6, 2.4, 0.15), bsdf_mat('terracotta', (0.55, 0.25, 0.14), 0.8), r2=0.2, parent=G['decor'])
leaf_m = bsdf_mat('leaf', (0.12, 0.32, 0.16), 0.7)
for i in range(7):
    a = i * 0.9; sphere(f'leaf{i}', rnd.uniform(0.16, 0.24), (-2.6 + math.cos(a) * 0.15, 2.4 + math.sin(a) * 0.15, 0.55 + i * 0.07), leaf_m, parent=G['decor'])
# desk + laptop + lamp + mug + book
DX, DY, DZ = 0.4, 1.3, 0.76
box('desktop', (1.5, 0.75, 0.06), (DX, DY, DZ - 0.03), wood_mid, parent=G['desk'])
for lx in (-0.68, 0.68):
    for ly in (-0.32, 0.32): box(f'leg{lx}{ly}', (0.06, 0.06, DZ - 0.06), (DX + lx, DY + ly, (DZ - 0.06) / 2), wood_dark, parent=G['desk'])
box('modesty', (1.36, 0.03, 0.42), (DX, DY - 0.3, DZ - 0.27), wood_dark, parent=G['desk'])
box('drawer', (0.5, 0.65, 0.18), (DX + 0.45, DY, DZ - 0.15), wood_dark, parent=G['desk'])
lap_m = bsdf_mat('laptop', (0.2, 0.21, 0.24), 0.4, 0.6)
box('lap_base', (0.36, 0.25, 0.02), (DX - 0.05, DY + 0.02, DZ + 0.01), lap_m, parent=G['desk'])
lid = empty('lid_pivot', (DX - 0.05, DY - 0.105, DZ + 0.02)); set_parent(lid, G['desk']); lid.rotation_euler = (math.radians(-12), 0, 0)
box('lap_lid', (0.36, 0.015, 0.24), (DX - 0.05, DY - 0.11, DZ + 0.14), lap_m, parent=lid)
plane('lap_screen', 0.33, 0.21, (DX - 0.05, DY - 0.1, DZ + 0.14), image_mat('lapui', os.path.join(TEX, 'laptop_ui.png'), 1.3), rot=(math.pi / 2, 0, math.pi), parent=lid)
sphere('lap_logo', 0.018, (DX - 0.05, DY - 0.12, DZ + 0.15), emit_mat('logo', (0.9, 0.95, 1.0), 2.0), noline=True, parent=lid)
LX, LY = DX + 0.55, DY + 0.15
cyl('lamp_base', 0.09, 0.03, (LX, LY, DZ + 0.015), metal_m, parent=G['desk'])
cyl('lamp_arm1', 0.012, 0.42, (LX - 0.02, LY, DZ + 0.22), metal_m, rot=(0, math.radians(-10), 0), parent=G['desk'])
cyl('lamp_arm2', 0.012, 0.3, (LX - 0.15, LY, DZ + 0.46), metal_m, rot=(0, math.radians(-70), 0), parent=G['desk'])
cyl('lamp_head', 0.03, 0.16, (LX - 0.3, LY, DZ + 0.44), bsdf_mat('lampgreen', (0.12, 0.3, 0.22), 0.4, 0.3), rot=(0, math.radians(-150), 0), r2=0.1, parent=G['desk'])
lamp_bulb_m = emit_mat('lampbulb', (1.0, 0.85, 0.6), 8.0)
lamp_bulb = sphere('lamp_bulb', 0.035, (LX - 0.33, LY, DZ + 0.39), lamp_bulb_m, noline=True, parent=G['desk'])
cyl('mug', 0.045, 0.1, (DX + 0.3, DY - 0.2, DZ + 0.05), bsdf_mat('mug', (0.85, 0.82, 0.75), 0.5), parent=G['desk'])
for i in range(3): box(f'stack{i}', (0.22, 0.3, 0.04), (DX - 0.55, DY + 0.1, DZ + 0.02 + i * 0.042), bsdf_mat(f'st{i}', [(0.5, 0.12, 0.1), (0.12, 0.2, 0.4), (0.55, 0.42, 0.12)][i], 0.7), rot=(0, 0, 0.1 * i), parent=G['desk'])

SCX, SCY = 2.25, 1.65
easel = empty('EASEL', (SCX, SCY, 0))
for dx in (-0.22, 0.22): box(f'easel_leg{dx}', (0.04, 0.04, 1.6), (SCX + dx, SCY + 0.1, 0.78), wood_dark, rot=(math.radians(-6), dx * 0.3, 0), parent=easel)
box('screen_frame', (0.66, 0.05, 1.12), (SCX, SCY, 1.12), black_m, parent=easel)
scr_thumb = plane('screen_thumb', 0.58, 1.03, (SCX, SCY - 0.03, 1.12), image_mat('thumb', os.path.join(TEX, 'thumb.png'), 1.1), parent=easel)
scr_graph = plane('screen_graph', 0.58, 1.03, (SCX, SCY - 0.031, 1.12), image_mat('graph', os.path.join(TEX, 'graph.png'), 1.1), parent=easel)
screen_light = light('screen_light', 'AREA', (SCX, SCY - 0.4, 1.12), 25, (1.0, 0.75, 0.6), rot=(math.radians(-90), 0, 0), size=0.6)
# the old book (s18): right half fixed, left cover hinged at the spine (local x=0)
BKX, BKY, BKZ = DX - 0.3, DY - 0.18, DZ
book = empty('BOOK', (BKX, BKY, BKZ)); set_parent(book, G['desk'])
cover_m = bsdf_mat('cover', (0.35, 0.12, 0.08), 0.6); page_m = bsdf_mat('page', (0.93, 0.87, 0.72), 0.9)
box('bk_rcover', (0.2, 0.28, 0.008), (BKX + 0.1, BKY, BKZ + 0.004), cover_m, parent=book)
box('bk_rpages', (0.19, 0.27, 0.03), (BKX + 0.1, BKY, BKZ + 0.023), page_m, parent=book)
hinge = empty('bk_hinge', (BKX, BKY, BKZ + 0.04)); set_parent(hinge, book)
box('bk_lcover', (0.2, 0.28, 0.008), (BKX - 0.1, BKY, BKZ + 0.004 + 0.0), cover_m, parent=hinge)
box('bk_lpages', (0.19, 0.27, 0.03), (BKX - 0.1, BKY, BKZ + 0.023), page_m, parent=hinge)
book_glow = plane('bk_glow', 0.5, 0.5, (BKX, BKY, BKZ + 0.05), emit_mat('bookglow', (1.0, 0.75, 0.35), 0.0), rot=(0, 0, 0), parent=book)

# ---------------------------------------------------------------- attic lights
moon = light('moon', 'AREA', (-1.6, 3.6, 1.9), 220, (0.6, 0.68, 1.0), rot=(math.radians(-80), 0, 0), size=1.4)
lamp = light('lamp_spot', 'SPOT', (LX - 0.33, LY, DZ + 0.38), 90, (1.0, 0.72, 0.42), rot=(math.radians(15), math.radians(-35), 0), size=0.05, spot=95)
lamp_pt = light('lamp_point', 'POINT', (LX - 0.4, LY - 0.3, DZ + 0.5), 35, (1.0, 0.7, 0.4), size=0.2)
fill = light('fill', 'AREA', (0.3, -2.5, 3.2), 140, (1.0, 0.78, 0.6), rot=(math.radians(55), 0, 0), size=4.0)
strings = light('strings', 'AREA', (0, 2.6, 2.9), 60, (1.0, 0.7, 0.4), rot=(math.radians(180), 0, 0), size=5.0)
book_light = light('book_light', 'POINT', (BKX, BKY - 0.05, BKZ + 0.2), 0, (1.0, 0.75, 0.4), size=0.1)

# god-ray volume + dust (s09 only)
vol_m = bpy.data.materials.new('volume'); 
try: vol_m.use_nodes = True
except Exception: pass
vn = vol_m.node_tree; vn.nodes.clear()
pv = vn.nodes.new('ShaderNodeVolumePrincipled'); pv.inputs['Density'].default_value = 0.08; pv.inputs['Color'].default_value = (0.75, 0.8, 1.0, 1)
vo = vn.nodes.new('ShaderNodeOutputMaterial'); vn.links.new(pv.outputs[0], vo.inputs['Volume'])
volume = box('volume', (3.5, 3.6, 3.0), (-1.3, 1.4, 1.5), vol_m, noline=True)
dust_m = emit_mat('dust', (1.0, 0.95, 0.85), 3.0)
dust = []
for i in range(70):
    p = (rnd.uniform(-2.3, -0.5), rnd.uniform(1.0, 2.9), rnd.uniform(0.6, 2.6)); d = sphere(f'dust{i}', rnd.uniform(0.004, 0.011), p, dust_m, noline=True, seg=6); dust.append(d)

# ---------------------------------------------------------------- SOUNDSTAGE (x = 40)
SX = 40
conc = proc_mat('concrete', 'plaster', (0.08, 0.08, 0.1), (0.14, 0.13, 0.16))
box('st_floor', (40, 40, 0.1), (SX, 6, -0.05), conc)
box('st_wall', (40, 0.3, 14), (SX, 14, 7), bsdf_mat('stwall', (0.05, 0.05, 0.07), 0.9))
for i in range(-6, 7): box(f'st_col{i}', (0.3, 0.4, 14), (SX + i * 3.2, 13.7, 7), black_m)
for y in (0.0, 4.0, 8.0):
    box(f'truss{y}', (30, 0.15, 0.15), (SX, y, 7.0), metal_m); box(f'truss2{y}', (30, 0.15, 0.15), (SX, y, 7.5), metal_m)
    for k in range(-14, 15): box(f'tr{y}_{k}', (0.05, 0.05, 0.55), (SX + k, y, 7.25), metal_m, rot=(0, 0.6 * (1 if k % 2 else -1), 0))
box('tapeX1', (0.6, 0.06, 0.005), (SX, 2.0, 0.003), bsdf_mat('tape', (0.85, 0.75, 0.2), 0.6), rot=(0, 0, 0.6), noline=True)
box('tapeX2', (0.6, 0.06, 0.005), (SX, 2.0, 0.003), bsdf_mat('tape', (0.85, 0.75, 0.2), 0.6), rot=(0, 0, -0.6), noline=True)
box('exit', (0.6, 0.05, 0.22), (SX - 6, 13.5, 2.8), emit_mat('exitred', (1.0, 0.15, 0.1), 4.0), noline=True)
# hanging spotlight fixture + visible beam cone
cyl('fix_body', 0.25, 0.45, (SX, 2.0, 6.6), black_m)
spot_lens = cyl('fix_lens', 0.2, 0.02, (SX, 2.0, 6.37), emit_mat('lens', (0.95, 0.97, 1.0), 12.0), noline=True)
beam_m = bpy.data.materials.new('beam'); 
try: beam_m.use_nodes = True
except Exception: pass
bn = beam_m.node_tree; bn.nodes.clear()
lw = bn.nodes.new('ShaderNodeLayerWeight'); lw.inputs[0].default_value = 0.5
em = bn.nodes.new('ShaderNodeEmission'); em.inputs[0].default_value = (0.8, 0.88, 1.0, 1); em.inputs[1].default_value = 0.35
tr = bn.nodes.new('ShaderNodeBsdfTransparent'); mx = bn.nodes.new('ShaderNodeMixShader'); bo = bn.nodes.new('ShaderNodeOutputMaterial')
bn.links.new(lw.outputs['Facing'], mx.inputs[0]); bn.links.new(em.outputs[0], mx.inputs[1]); bn.links.new(tr.outputs[0], mx.inputs[2]); bn.links.new(mx.outputs[0], bo.inputs[0])
try: beam_m.surface_render_method = 'BLENDED'
except AttributeError: beam_m.blend_method = 'BLEND'
beam = cyl('beam', 0.2, 6.3, (SX, 2.0, 3.2), beam_m, r2=None, noline=True)
beam.data.vertices.foreach_set('co', [c for v in beam.data.vertices for c in ((v.co.x * 9, v.co.y * 9, v.co.z) if v.co.z < 0 else (v.co.x, v.co.y, v.co.z))])
stage_spot = light('stage_spot', 'SPOT', (SX, 2.0, 6.3), 1800, (0.85, 0.9, 1.0), size=0.15, spot=28)
stage_amb = light('stage_amb', 'AREA', (SX, 4, 9), 120, (0.5, 0.55, 0.9), rot=(0, 0, 0), size=20)
# director chair (s04)
CHX, CHY = SX, 2.0
chair = empty('CHAIR', (CHX, CHY, 0))
canvas = bsdf_mat('canvas', (0.42, 0.08, 0.07), 0.8)
for sx_ in (-1, 1):
    box(f'ch_x1{sx_}', (0.04, 0.04, 0.62), (CHX + sx_ * 0.25, CHY, 0.3), wood_mid, rot=(math.radians(35), 0, 0), parent=chair)
    box(f'ch_x2{sx_}', (0.04, 0.04, 0.62), (CHX + sx_ * 0.25, CHY, 0.3), wood_mid, rot=(math.radians(-35), 0, 0), parent=chair)
    box(f'ch_post{sx_}', (0.04, 0.04, 0.55), (CHX + sx_ * 0.25, CHY + 0.2, 0.85), wood_mid, parent=chair)
    box(f'ch_arm{sx_}', (0.05, 0.5, 0.04), (CHX + sx_ * 0.25, CHY, 0.75), wood_mid, parent=chair)
box('ch_seat', (0.5, 0.42, 0.02), (CHX, CHY, 0.58), canvas, parent=chair)
box('ch_back', (0.52, 0.02, 0.2), (CHX, CHY + 0.21, 1.0), canvas, parent=chair)
# film camera on tripod (s05)
CMX, CMY = SX + 2.4, 1.2
fcam = empty('FILMCAM', (CMX, CMY, 0))
for a in (0, 2.1, 4.2):
    leg = box(f'tri{a}', (0.03, 0.03, 1.35), (CMX + math.cos(a) * 0.25, CMY + math.sin(a) * 0.25, 0.65), black_m, rot=(math.sin(a) * 0.35, -math.cos(a) * 0.35, 0), parent=fcam)
box('fc_body', (0.45, 0.25, 0.3), (CMX, CMY, 1.45), black_m, parent=fcam)
for i, (dx, r) in enumerate(((-0.12, 0.15), (0.14, 0.17))):
    cyl(f'fc_reel{i}', r, 0.06, (CMX + dx, CMY, 1.6 + r + 0.02), black_m, rot=(math.pi / 2, 0, 0), parent=fcam)
cyl('fc_lens', 0.07, 0.25, (CMX - 0.33, CMY, 1.45), black_m, rot=(0, math.pi / 2, 0), parent=fcam)
cyl('fc_lensrim', 0.085, 0.03, (CMX - 0.46, CMY, 1.45), metal_m, rot=(0, math.pi / 2, 0), parent=fcam)
rec_m = emit_mat('rec', (1.0, 0.08, 0.05), 25.0)
rec = sphere('fc_rec', 0.02, (CMX + 0.1, CMY - 0.13, 1.55), rec_m, noline=True, parent=fcam)
cam_spot = light('camspot', 'SPOT', (CMX - 0.5, CMY - 1.6, 3.2), 500, (0.8, 0.85, 1.0), rot=(math.radians(35), 0, math.radians(-15)), size=0.3, spot=40)

# ---------------------------------------------------------------- NIGHT STREET (x = -60)
NX = -60
box('n_ground', (80, 60, 0.1), (NX, 10, -0.05), bsdf_mat('asphalt', (0.06, 0.06, 0.09), 0.9))
plane('n_sky', 120, 60, (NX, 45, 24), image_mat('stars', os.path.join(TEX, 'stars.png'), 1.0))
sphere('moonball', 1.6, (NX + 14, 40, 28), emit_mat('moonm', (1.0, 0.97, 0.88), 3.0), noline=True)
win_warm = emit_mat('winwarm', (1.0, 0.72, 0.38), 1.2); win_dark = bsdf_mat('windark', (0.05, 0.05, 0.08), 0.4)
house_cols = [(0.18, 0.16, 0.26), (0.22, 0.17, 0.2), (0.14, 0.16, 0.22), (0.25, 0.2, 0.24)]
def house(cx, cy, w, h, d, col, hero=False):
    m = bsdf_mat(f'house{col}', col, 0.9)
    box(f'h{cx}_{cy}', (w, d, h), (cx, cy, h / 2), m)
    rh = w * 0.45
    v = [(-w / 2 - 0.2, -d / 2 - 0.2, 0), (w / 2 + 0.2, -d / 2 - 0.2, 0), (0, -d / 2 - 0.2, rh), (-w / 2 - 0.2, d / 2 + 0.2, 0), (w / 2 + 0.2, d / 2 + 0.2, 0), (0, d / 2 + 0.2, rh)]
    r_ = mesh_obj(f'roof{cx}_{cy}', v, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (0, 2, 5, 3)], bsdf_mat('rooftile', (0.12, 0.07, 0.08), 0.8)); r_.location = (cx, cy, h)
    for fl in range(int(h // 2.6)):
        for k in range(int(w // 1.6)):
            lit = rnd.random() < 0.35
            box(f'w{cx}_{cy}_{fl}_{k}', (0.6, 0.05, 0.9), (cx - w / 2 + 0.8 + k * 1.6, cy - d / 2 - 0.03, 1.3 + fl * 2.6), win_warm if lit else win_dark, noline=lit)
    if hero:
        cyl('attic_win', 0.55, 0.06, (cx, cy - d / 2 - 0.2, h + rh * 0.42), emit_mat('atticwin', (1.0, 0.8, 0.45), 6.0), rot=(math.pi / 2, 0, 0), noline=True)
        cyl('attic_frame', 0.62, 0.05, (cx, cy - d / 2 - 0.17, h + rh * 0.42), wood_dark, rot=(math.pi / 2, 0, 0))
        box('attic_mull_v', (0.05, 0.05, 1.1), (cx, cy - d / 2 - 0.25, h + rh * 0.42), wood_dark); box('attic_mull_h', (1.1, 0.05, 0.05), (cx, cy - d / 2 - 0.25, h + rh * 0.42), wood_dark)
        light('attic_glow', 'POINT', (cx, cy - d / 2 - 1.0, h + rh * 0.42), 300, (1.0, 0.7, 0.4), size=0.5)
HERO = (NX, 12, 7.0, 5.0)
house(NX, 12, 7.0, 7.0, 5.0, (0.2, 0.17, 0.26), hero=True)
for i, cx in enumerate([NX - 8.5, NX - 15, NX + 8, NX + 15, NX - 22, NX + 22]):
    house(cx, 12 + rnd.uniform(-1, 3), rnd.uniform(5, 7), rnd.uniform(5, 11), 5.0, house_cols[i % 4])
for i, cx in enumerate([NX - 12, NX - 4, NX + 4, NX + 12]):
    cyl(f'pole{i}', 0.06, 4.2, (cx, 7.5, 2.1), black_m); sphere(f'lampball{i}', 0.18, (cx, 7.5, 4.25), emit_mat('streetlamp', (1.0, 0.75, 0.45), 6.0), noline=True)
    light(f'streetl{i}', 'POINT', (cx, 7.3, 4.0), 250, (1.0, 0.7, 0.4), size=0.3)
for i, cx in enumerate([NX - 6.5, NX + 6.0, NX - 18, NX + 19]):
    cyl(f'trunk{i}', 0.15, 1.8, (cx, 9.0, 0.9), wood_dark); sphere(f'crown{i}', 1.3, (cx, 9.0, 2.6), bsdf_mat('treedark', (0.06, 0.1, 0.09), 0.9))
light('n_moonlight', 'SUN', (NX, 0, 30), 0.35, (0.55, 0.62, 1.0), rot=(math.radians(50), 0, math.radians(20)))

# ---------------------------------------------------------------- HOST cut-out (unlit image planes + contact shadow)
HOST = empty('HOST', (0, 0, 0))
IMAGES = ['type', 'type_cam', 'type_surprised', 'neutral', 'smile', 'point', 'waveA', 'waveB', 'think', 'determined']
CH_W, CH_H = 1.0, 1.5
host_planes = {}
for nm in IMAGES:
    m = image_mat('chr_' + nm, os.path.join(CHR, nm + '.png'), 1.0, alpha=True)
    ob = mesh_obj('host_' + nm, [(-CH_W / 2, 0, -0.04), (CH_W / 2, 0, -0.04), (CH_W / 2, 0, CH_H - 0.04), (-CH_W / 2, 0, CH_H - 0.04)], [(0, 1, 2, 3)], m, True, uv={0: (0, 0), 1: (1, 0), 2: (1, 1), 3: (0, 1)})
    ob.parent = HOST; ob.visible_shadow = False
    host_planes[nm] = ob
shadow_m = bpy.data.materials.new('contact'); 
try: shadow_m.use_nodes = True
except Exception: pass
sn = shadow_m.node_tree; sn.nodes.clear()
tc = sn.nodes.new('ShaderNodeTexCoord'); gr = sn.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'
mp = sn.nodes.new('ShaderNodeMapping'); mp.inputs['Location'].default_value = (0, 0, 0)
sn.links.new(tc.outputs['Object'], mp.inputs[0]); sn.links.new(mp.outputs[0], gr.inputs[0])
mpl = sn.nodes.new('ShaderNodeMath'); mpl.operation = 'MULTIPLY'; mpl.inputs[1].default_value = 0.75
sn.links.new(gr.outputs['Fac'], mpl.inputs[0])
shbs = sn.nodes.new('ShaderNodeEmission'); shbs.inputs[0].default_value = (0, 0, 0, 1)
trs = sn.nodes.new('ShaderNodeBsdfTransparent'); mxs = sn.nodes.new('ShaderNodeMixShader'); so = sn.nodes.new('ShaderNodeOutputMaterial')
sn.links.new(mpl.outputs[0], mxs.inputs[0]); sn.links.new(trs.outputs[0], mxs.inputs[1]); sn.links.new(shbs.outputs[0], mxs.inputs[2]); sn.links.new(mxs.outputs[0], so.inputs[0])
try: shadow_m.surface_render_method = 'BLENDED'
except AttributeError: shadow_m.blend_method = 'BLEND'
SHADOW_AMT = mpl.inputs[1]
contact = mesh_obj('contact', [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [(0, 1, 2, 3)], shadow_m, True)
contact.scale = (0.48, 0.2, 1); contact.location = (0, 0, 0.004); contact.parent = HOST; contact.visible_shadow = False

# ---------------------------------------------------------------- per-episode animation, cameras, markers
exec(open(os.path.join(HERE, f'ep{EP}_anim.py'), encoding='utf-8').read())

# ---------------------------------------------------------------- Freestyle outlines (illustrated look)
sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 3.0
vl = sc.view_layers[0]; fs = vl.freestyle_settings; fs.crease_angle = math.radians(140)
ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('lines')
ls.select_by_visibility = True; ls.select_by_edge_types = True; ls.select_by_collection = True; ls.collection = NOLINE; ls.collection_negation = 'EXCLUSIVE'
ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
if ls.linestyle is None: ls.linestyle = bpy.data.linestyles.new('outline')
ls.linestyle.color = (0.07, 0.05, 0.08); ls.linestyle.thickness = 1.0; ls.linestyle.alpha = 1.0
if EP == '2': sc.render.line_thickness = 2.0

LINEAR_IDS.update({shadow_m.node_tree.name, book_glow.data.materials[0].node_tree.name, 'book_light'})
fix_interpolation()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'episode.blend' if EP == '1' else f'episode{EP}.blend'))
print('BUILD OK frames', sc.frame_start, sc.frame_end)
