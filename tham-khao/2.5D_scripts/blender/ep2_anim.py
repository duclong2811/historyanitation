# Episode 2 ("cầm tay chỉ việc" tutorial) animation, cameras, markers. exec'd inside build_scene.py with EP=2.
# Only the H shots of tap2/build/timeline.json are rendered here; panels and reused ep1 footage are composited later.
WT = [F(w['start']) for w in TL['words']]           # word index -> frame
def W(i, d=0): return WT[i] + d
s = SH
sc.render.resolution_x, sc.render.resolution_y = 720, 1280    # rendered at 720p, upscaled in the compositor

# ---- extra storyboards (a second row = "shot list")
for i, x in enumerate((-0.55, -0.05, 0.45)):
    plane(f'board2_{i}', 0.36, 0.48, (x, 2.98, 1.78 + (0.03 if i == 2 else 0)), image_mat(f'sb2{i}', os.path.join(TEX, f'storyboard{(i + 1) % 3}.png'), emissive=False),
          rot=(math.pi / 2, (1 - i) * 0.05, 0), parent=G['decor'])
    sphere(f'pin2_{i}', 0.018, (x, 2.95, 1.99 + (0.03 if i == 2 else 0)), bsdf_mat('pinred', (0.8, 0.1, 0.1), 0.4), parent=G['decor'])

# ---- primitives for the "cube -> desk, cylinder -> lamp" beat
grey = bsdf_mat('primgrey', (0.62, 0.62, 0.64), 0.5)
prim_cube = box('prim_cube', (0.5, 0.5, 0.5), (DX, DY, DZ + 0.25), grey)
prim_cyl = cyl('prim_cyl', 0.09, 0.5, (LX - 0.05, LY, DZ + 0.25), grey)

# ---- Blender-style camera gizmo (pyramid of thin bars) for step 7
giz_m = emit_mat('gizmo', (1.0, 0.55, 0.12), 4.0)
GIZ = empty('GIZMO', (-1.0, 0.0, 1.05))
def bar(name, p, q, r=0.008):
    p, q = Vector(p), Vector(q); d = q - p
    ob = cyl(name, r, d.length, (p + q) / 2, giz_m, seg=8, noline=True)
    ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); ob.parent = GIZ; return ob
hw, hh, dz = 0.16, 0.28, -0.5
corners = [(-hw, -hh, dz), (hw, -hh, dz), (hw, hh, dz), (-hw, hh, dz)]
for i, c in enumerate(corners):
    bar(f'giz_r{i}', (0, 0, 0), c); bar(f'giz_e{i}', c, corners[(i + 1) % 4])
bar('giz_t0', (-0.09, hh + 0.03, dz), (0.09, hh + 0.03, dz)); bar('giz_t1', (-0.09, hh + 0.03, dz), (0, hh + 0.13, dz)); bar('giz_t2', (0.09, hh + 0.03, dz), (0, hh + 0.13, dz))
giz_body = box('giz_body', (0.16, 0.12, 0.2), (0, 0, 0.1), bsdf_mat('gizbody', (0.15, 0.15, 0.17), 0.4)); giz_body.parent = GIZ

# ---------------------------------------------------------------- host
def host_state(f, loc, rot_z=0.0, img=None, shadow=0.75):
    key(HOST, 'location', f, Vector(loc)); key(HOST, 'rotation_euler', f, Vector((0, 0, rot_z))); key(HOST, 'scale', f, Vector((1, 1, 1)))
    for nm, ob in host_planes.items(): key(ob, 'hide_render', f, nm != img)
    key(contact, 'hide_render', f, img is None)
    SHADOW_AMT.default_value = shadow; SHADOW_AMT.keyframe_insert('default_value', frame=f)

DESK_HOST = (DX, DY + 0.55, 0.0)
OPEN_SPOT = (-1.0, 1.6, 0.0)
host_state(0, DESK_HOST, img='type')
a, b = s['i1']
for k, f in enumerate(range(a, W(5), 5)): host_state(f, OPEN_SPOT, img='waveA' if k % 2 else 'waveB')
host_state(W(5), OPEN_SPOT, img='smile')
host_state(s['b1a'][0], DESK_HOST, img='type_cam')
host_state(s['b3a'][0], (-1.05, 2.45, 0), img='point')
host_state(s['b4d'][0], DESK_HOST, img=None)
host_state(s['b5a'][0], OPEN_SPOT, img='neutral'); host_state(W(116), OPEN_SPOT, img='smile')
host_state(s['b5e'][0], OPEN_SPOT, img='neutral', shadow=0.0)
SHADOW_AMT.default_value = 0.0; SHADOW_AMT.keyframe_insert('default_value', frame=W(145))
SHADOW_AMT.default_value = 0.85; SHADOW_AMT.keyframe_insert('default_value', frame=W(148))
host_state(W(152), OPEN_SPOT, img='smile', shadow=0.85)
host_state(s['b6a'][0], DESK_HOST, img='type'); host_state(W(158, 4), DESK_HOST, img='type_cam')
host_state(s['b6b'][0], DESK_HOST, img='type')
host_state(s['b7a'][0], OPEN_SPOT, img='neutral'); host_state(W(190), OPEN_SPOT, img='smile')
host_state(s['b7c'][0], DESK_HOST, img='type')

# ---------------------------------------------------------------- desk build (b4d): cube -> desk, cylinder -> lamp
def pop(ob, f, hold_from=0):
    sc0 = ob.scale.copy()
    key(ob, 'scale', hold_from, sc0); key(ob, 'scale', s['b4d'][0], sc0 * 0.001)
    key(ob, 'scale', f, sc0 * 0.001, 'BEZIER'); key(ob, 'scale', f + 4, sc0 * 1.1, 'BEZIER'); key(ob, 'scale', f + 7, sc0)
DESK_PARTS = [o for o in bpy.data.objects if o.name in ('desktop', 'modesty', 'drawer') or o.name.startswith('leg')]
LAMP_PARTS = [o for o in bpy.data.objects if o.name.startswith('lamp_')]
LATER = [o for o in bpy.data.objects if o.name.startswith(('lap_', 'stack', 'bk_', 'mug'))] + [bpy.data.objects['lid_pivot']]
fd, fl = W(101), W(106)
for i, o in enumerate(DESK_PARTS): pop(o, fd + 2 + i)
for i, o in enumerate(LAMP_PARTS): pop(o, fl + 2 + i * 2)
for o in LATER:
    sc0 = o.scale.copy(); key(o, 'scale', 0, sc0); key(o, 'scale', s['b4d'][0], sc0 * 0.001); key(o, 'scale', s['b4d'][1], sc0)
for o, f_in, f_morph, tgt_loc, tgt_scale in ((prim_cube, W(99), fd, (DX, DY, DZ - 0.03), (3.0, 1.5, 0.12)),
                                              (prim_cyl, W(104), fl, (LX - 0.02, LY, DZ + 0.22), (0.13, 0.13, 0.84))):
    l0 = o.location.copy()
    key(o, 'hide_render', 0, True); key(o, 'hide_render', f_in, False); key(o, 'hide_render', f_morph + 7, True)
    key(o, 'scale', 0, Vector((0.001,) * 3)); key(o, 'scale', f_in, Vector((0.001,) * 3), 'BEZIER'); key(o, 'scale', f_in + 5, Vector((1, 1, 1)), 'BEZIER')
    key(o, 'scale', f_morph, Vector((1, 1, 1)), 'BEZIER'); key(o, 'scale', f_morph + 6, Vector(tgt_scale))
    key(o, 'location', 0, l0); key(o, 'location', f_morph, l0, 'BEZIER'); key(o, 'location', f_morph + 6, Vector(tgt_loc))

# ---------------------------------------------------------------- lights
def lamp_on(f, k):
    lamp.data.energy = 90 * k; lamp.data.keyframe_insert('energy', frame=f)
    lamp_pt.data.energy = 35 * k; lamp_pt.data.keyframe_insert('energy', frame=f)
    lamp_bulb_m.node_tree.nodes['Emission'].inputs[1].default_value = 8 * k + 0.2; lamp_bulb_m.node_tree.nodes['Emission'].inputs[1].keyframe_insert('default_value', frame=f)
def room(f, fill_k, strings_k, moon_k):
    fill.data.energy = 140 * fill_k; fill.data.keyframe_insert('energy', frame=f)
    strings.data.energy = 60 * strings_k; strings.data.keyframe_insert('energy', frame=f)
    moon.data.energy = 220 * moon_k; moon.data.keyframe_insert('energy', frame=f)
lamp_on(0, 1); room(0, 1, 1, 1)
lamp_on(s['b4d'][0], 0); lamp_on(fl + 10, 1)                      # lamp lights up once it is built
a = s['b6a'][0]; lamp_on(a, 0); room(a, 0.12, 0.1, 0.0)
f = W(158); lamp_on(f, 1); lamp_on(f + 2, 0.25); lamp_on(f + 4, 1)  # "ánh sáng": lamp snaps on
room(W(166), 0.35, 0.1, 1.0)                                        # cold moon from the window
room(W(173), 0.6, 1.0, 1.0)                                         # strings + volume
room(s['b7a'][0], 1, 1, 1)
for ob in [volume] + dust:
    key(ob, 'hide_render', 0, True); key(ob, 'hide_render', W(173), False); key(ob, 'hide_render', s['b7a'][0], True)
for d in dust:
    p0 = d.location.copy(); key(d, 'location', W(173), p0, 'LINEAR'); key(d, 'location', s['b7a'][0], p0 + Vector((rnd.uniform(-0.08, 0.08), 0, rnd.uniform(0.1, 0.3))), 'LINEAR')
# hidden ep1-only props
for ob in (book_glow, scr_graph): key(ob, 'hide_render', 0, True)
key(hinge, 'rotation_euler', 0, Vector((0, math.radians(178), 0)))
book_light.data.energy = 0
for ob in [chair] + list(chair.children): key(ob, 'hide_render', 0, True)

# gizmo only in step 7
for ob in [GIZ] + list(GIZ.children):
    key(ob, 'hide_render', 0, True); key(ob, 'hide_render', s['b7a'][0], False); key(ob, 'hide_render', s['b7c'][0], True)
def giz(f, loc, interp='BEZIER'):
    key(GIZ, 'location', f, Vector(loc), interp)
    d = Vector((OPEN_SPOT[0], OPEN_SPOT[1], 0.95)) - Vector(loc); key(GIZ, 'rotation_euler', f, d.to_track_quat('-Z', 'Y').to_euler(), interp)
giz(s['b7a'][0], (0.45, 0.75, 1.2)); giz(W(194), (0.45, 0.75, 1.2)); giz(s['b7b'][1], (-0.3, 1.1, 1.08))

# ---------------------------------------------------------------- cameras for the H shots
CAMS = {   # shot: (lens, [(t_rel, cam_pos, target)], fstop)
    'i1':  (28, [(0, (-0.35, -2.2, 1.4), (-0.9, 1.6, 0.95)), (1, (-0.5, -1.6, 1.3), (-0.95, 1.6, 0.9))], 4),
    'b1a': (40, [(0, (0.55, -0.55, 1.45), (0.4, 1.85, 1.3)), (1, (0.5, -0.15, 1.42), (0.4, 1.85, 1.32))], 2.8),
    'b3a': (30, [(0, (-0.4, -1.0, 1.45), (-0.4, 2.9, 1.5)), (1, (-0.4, -0.6, 1.47), (-0.4, 2.9, 1.55))], 4),
    'b4d': (35, [(0, (-0.35, -0.75, 1.55), (DX + 0.05, DY, 0.95)), (1, (-0.2, -0.45, 1.5), (DX + 0.05, DY, 0.95))], 5.6),
    'b5a': (35, [(0, (-0.75, -1.3, 1.15), (-1.0, 1.6, 0.85)), (1, (-0.85, -0.9, 1.1), (-1.0, 1.6, 0.85))], 2.8),
    'b5e': (45, [(0, (-0.8, 0.05, 0.35), (-1.0, 1.6, 0.15)), (0.5, (-0.82, 0.2, 0.32), (-1.0, 1.6, 0.15)), (1, (-0.85, -0.9, 1.0), (-1.0, 1.6, 0.75))], 2.8),
    'b6a': (38, [(0, (0.75, -0.9, 1.5), (0.5, 1.6, 1.15)), (1, (0.7, -0.6, 1.48), (0.5, 1.6, 1.15))], 3.5),
    'b6b': (24, [(0, (1.7, -1.9, 1.7), (-0.8, 2.2, 1.3)), (1, (1.5, -1.5, 1.65), (-0.8, 2.2, 1.3))], 8),
    'b6c': (24, [(0, (1.5, -1.5, 1.65), (-0.8, 2.2, 1.3)), (1, (1.4, -1.3, 1.62), (-0.8, 2.2, 1.3))], 8),
    'b7a': (28, [(0, (-1.3, -2.0, 1.55), (-0.4, 1.2, 1.0)), (1, (-1.2, -1.75, 1.52), (-0.4, 1.2, 1.0))], 5.6),
    'b7b': (28, [(0, (-1.2, -1.75, 1.52), (-0.4, 1.2, 1.0)), (1, (-1.1, -1.4, 1.48), (-0.5, 1.25, 1.0))], 5.6),
}
for sid, (lens, path, fstop) in CAMS.items():
    a, b = s[sid]
    cd = bpy.data.cameras.new('CAM_' + sid); cd.lens = lens; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 36; cd.clip_start = 0.02; cd.clip_end = 300
    cam = bpy.data.objects.new('CAM_' + sid, cd); link(cam, True)
    tgt = empty('TGT_' + sid)
    con = cam.constraints.new('TRACK_TO'); con.target = tgt; con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
    cd.dof.use_dof = True; cd.dof.focus_object = tgt; cd.dof.aperture_fstop = fstop
    for tr_, pos, look in path:
        f = a + int(round(tr_ * (b - a)))
        key(cam, 'location', f, Vector(pos), 'BEZIER'); key(tgt, 'location', f, Vector(look), 'BEZIER')
    m = sc.timeline_markers.new(sid, frame=a); m.camera = cam
    if sid == 'i1': sc.camera = cam
