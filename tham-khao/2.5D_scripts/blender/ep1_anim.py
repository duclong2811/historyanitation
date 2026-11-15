# Episode 1 animation tables (exec'd inside build_scene.py)
# ---------------------------------------------------------------- animation tables
def host_state(f, loc, rot_z=0.0, img=None, scale=1.0, shadow=0.75):
    key(HOST, 'location', f, Vector(loc)); key(HOST, 'rotation_euler', f, Vector((0, 0, rot_z))); key(HOST, 'scale', f, Vector((scale,) * 3))
    for nm, ob in host_planes.items(): key(ob, 'hide_render', f, nm != img)
    key(contact, 'hide_render', f, img is None)
    SHADOW_AMT.default_value = shadow; SHADOW_AMT.keyframe_insert('default_value', frame=f)

DESK_HOST = (DX, DY + 0.55, 0.0)
OPEN_SPOT = (-1.0, 1.6, 0.0)
s = SH
host_state(s['s01'][0], DESK_HOST, img='type')
host_state(s['s02'][0], DESK_HOST, img='type'); host_state(s['s02'][0] + 12, DESK_HOST, img='type_cam')
host_state(s['s03'][0], DESK_HOST, img=None)
host_state(s['s06'][0], OPEN_SPOT, img='smile')
f0 = s['s06'][0] + 30; key(HOST, 'rotation_euler', f0, Vector((0, 0, 0)), 'BEZIER'); key(HOST, 'rotation_euler', f0 + 10, Vector((0, 0, math.radians(88))), 'CONSTANT')
host_state(s['s07'][0], OPEN_SPOT, img='smile')
host_state(s['s08'][0], DESK_HOST, img='type'); host_state(s['s08'][0] + 8, DESK_HOST, img='type_surprised')
host_state(s['s09'][0], DESK_HOST, img=None)
host_state(s['s10'][0], OPEN_SPOT, img='neutral', shadow=0.0)
f0 = s['s10'][0] + 5; SHADOW_AMT.default_value = 0.0; SHADOW_AMT.keyframe_insert('default_value', frame=f0)
SHADOW_AMT.default_value = 0.85; SHADOW_AMT.keyframe_insert('default_value', frame=f0 + 14)
host_state(s['s11'][0], DESK_HOST, img='type')
host_state(s['s12'][0], (1.25, 1.55, 0), img='point')
host_state(s['s13'][0], (1.25, 1.55, 0), img=None)
host_state(s['s14'][0], DESK_HOST, img='type')
host_state(s['s15'][0], DESK_HOST, img=None)
host_state(s['s17'][0], DESK_HOST, img='think'); host_state(s['s17'][0] + 27, DESK_HOST, img='determined')
host_state(s['s18'][0], DESK_HOST, img=None)
a, b = s['s19']
for k, f in enumerate(range(a, b, 5)): host_state(f, (-0.6, 1.7, 0), img='smile' if f < a + 6 else ('waveA' if k % 2 else 'waveB'))
host_state(s['s20'][0], DESK_HOST, img=None)
DROP = s['s20'][0] + 72
host_state(DROP, (DX, DY + 0.55, 1.2), img='type'); key(HOST, 'location', DROP + 7, Vector(DESK_HOST), 'CONSTANT')
for fc in HOST.animation_data.action.fcurves if hasattr(HOST.animation_data.action, 'fcurves') else []:
    pass

# lamp: on, except s08 where it snaps on, and s20 where it turns on at the end
def lamp_on(f, k):
    lamp.data.energy = 90 * k; lamp.data.keyframe_insert('energy', frame=f)
    lamp_pt.data.energy = 35 * k; lamp_pt.data.keyframe_insert('energy', frame=f)
    lamp_bulb_m.node_tree.nodes['Emission'].inputs[1].default_value = 8 * k + 0.2; lamp_bulb_m.node_tree.nodes['Emission'].inputs[1].keyframe_insert('default_value', frame=f)
lamp_on(0, 1)
a = s['s08'][0]; lamp_on(a, 0); lamp_on(a + 5, 1); lamp_on(a + 7, 0.25); lamp_on(a + 9, 1)
lamp_on(s['s09'][0], 1)
lamp_on(s['s20'][0], 0); lamp_on(DROP + 12, 1)
# fill + strings also dim in s08 before the snap and during the s20 build
for f, k in [(0, 1), (s['s08'][0], 0.15), (s['s08'][0] + 5, 1), (s['s20'][0], 0.25), (DROP + 12, 1)]:
    fill.data.energy = 140 * k; fill.data.keyframe_insert('energy', frame=f)
    strings.data.energy = 60 * k; strings.data.keyframe_insert('energy', frame=f)

# stage spot: off for every shot outside s03/s04; flicker-off in each
def spot(f, k):
    stage_spot.data.energy = 1800 * k; stage_spot.data.keyframe_insert('energy', frame=f)
    spot_lens.data.materials[0].node_tree.nodes['Emission'].inputs[1].default_value = 12 * k + 0.05
    spot_lens.data.materials[0].node_tree.nodes['Emission'].inputs[1].keyframe_insert('default_value', frame=f)
    beam.data.materials[0].node_tree.nodes['Emission'].inputs[1].default_value = 0.35 * k
    beam.data.materials[0].node_tree.nodes['Emission'].inputs[1].keyframe_insert('default_value', frame=f)
for shot, off in (('s03', 13), ('s04', 16)):
    a = s[shot][0]; spot(a, 1); spot(a + off, 0.1); spot(a + off + 2, 0.8); spot(a + off + 4, 0)
spot(s['s05'][0], 0)
key(chair, 'hide_render', 0, True)
for ob in chair.children: key(ob, 'hide_render', 0, True); key(ob, 'hide_render', s['s04'][0], False)
a = s['s05'][0]
for f, k in [(a, 1.0), (a + 4, 0.4), (a + 8, 1.0), (a + 15, 0.0)]:
    rec_m.node_tree.nodes['Emission'].inputs[1].default_value = 25 * k; rec_m.node_tree.nodes['Emission'].inputs[1].keyframe_insert('default_value', frame=f)
cam_spot.data.energy = 500; cam_spot.data.keyframe_insert('energy', frame=a); cam_spot.data.energy = 120; cam_spot.data.keyframe_insert('energy', frame=a + 16)

# volume + dust only in s09 (and dust also in s18)
key(volume, 'hide_render', 0, True); key(volume, 'hide_render', s['s09'][0], False); key(volume, 'hide_render', s['s09'][1], True)
for d in dust:
    key(d, 'hide_render', 0, True); key(d, 'hide_render', s['s09'][0], False); key(d, 'hide_render', s['s09'][1], True)
    p0 = d.location.copy(); key(d, 'location', s['s09'][0], p0, 'LINEAR'); key(d, 'location', s['s09'][1], p0 + Vector((rnd.uniform(-0.05, 0.05), 0, rnd.uniform(0.04, 0.12))), 'LINEAR')

# book opens in s18
a, b = s['s18']
key(hinge, 'rotation_euler', 0, Vector((0, math.radians(178), 0)))
key(hinge, 'rotation_euler', a + 2, Vector((0, math.radians(178), 0)), 'BEZIER'); key(hinge, 'rotation_euler', a + 16, Vector((0, math.radians(4), 0)), 'CONSTANT')
gm = book_glow.data.materials[0].node_tree.nodes['Emission'].inputs[1]
for f, v in [(0, 0.0), (a + 6, 0.0), (a + 18, 0.5)]:
    gm.default_value = v; gm.keyframe_insert('default_value', frame=f)
for f, v in [(0, 0.0), (a + 6, 0.0), (a + 18, 6.0), (b, 6.0), (b + 1, 0.0)]:
    book_light.data.energy = v; book_light.data.keyframe_insert('energy', frame=f)

key(book_glow, 'hide_render', 0, True); key(book_glow, 'hide_render', s['s18'][0], False); key(book_glow, 'hide_render', s['s18'][1], True)
key(scr_graph, 'hide_render', 0, True); key(scr_graph, 'hide_render', s['s13'][0], False); key(scr_graph, 'hide_render', s['s13'][1], True)
key(scr_thumb, 'hide_render', 0, False); key(scr_thumb, 'hide_render', s['s13'][0], True); key(scr_thumb, 'hide_render', s['s13'][1], False)
# s20 build: every attic group pops in, in order
a = s['s20'][0]
G['desk'].children  # easel joins the desk group
set_parent(easel, G['shelf'])
order = [('floor', 31), ('rug', 36), ('back', 40), ('left', 44), ('window', 48), ('roof', 52), ('shelf', 56), ('decor', 60), ('desk', 64)]
for g, d in order:
    key(G[g], 'scale', a - 1, Vector((1, 1, 1))); key(G[g], 'scale', a, Vector((0.001,) * 3), 'BEZIER')
    key(G[g], 'scale', a + d, Vector((0.001,) * 3), 'BEZIER'); key(G[g], 'scale', a + d + 7, Vector((1.08,) * 3), 'BEZIER'); key(G[g], 'scale', a + d + 10, Vector((1, 1, 1)))
for ob in (moon,):
    ob.data.energy = 220; ob.data.keyframe_insert('energy', frame=0); ob.data.energy = 0; ob.data.keyframe_insert('energy', frame=a)
    ob.data.energy = 220; ob.data.keyframe_insert('energy', frame=a + 50)

# ---------------------------------------------------------------- cameras (one per shot, bound to markers)
CAMS = {   # shot: (lens, [(t_rel 0..1, cam_pos, target)], fstop)
    's01': (30, [(0, (-0.1, -3.4, 1.55), (0.3, 2.0, 1.4)), (1, (0.15, -2.7, 1.5), (0.35, 2.0, 1.35))], 5.6),
    's02': (40, [(0, (0.55, -0.55, 1.45), (0.4, 1.85, 1.3)), (1, (0.5, -0.15, 1.42), (0.4, 1.85, 1.32))], 2.8),
    's03': (24, [(0, (SX - 0.5, -9.5, 2.0), (SX, 3.0, 2.4)), (1, (SX + 0.4, -8.6, 2.0), (SX, 3.0, 2.3))], 8),
    's04': (40, [(0, (SX + 0.2, -1.6, 1.25), (SX, 2.0, 0.75)), (1, (SX + 0.1, -1.1, 1.2), (SX, 2.0, 0.75))], 2.8),
    's05': (45, [(0, (CMX - 1.3, CMY - 1.6, 1.6), (CMX - 0.05, CMY, 1.55)), (1, (CMX - 1.1, CMY - 1.3, 1.6), (CMX - 0.05, CMY, 1.55))], 2.8),
    's06': (35, [(0, (-0.75, -1.3, 1.15), (-1.0, 1.6, 0.85)), (1, (-0.85, -0.9, 1.1), (-1.0, 1.6, 0.85))], 2.8),
    's07': (30, 'orbit', 4),
    's08': (38, [(0, (0.75, -0.9, 1.5), (0.5, 1.6, 1.15)), (1, (0.7, -0.6, 1.48), (0.5, 1.6, 1.15))], 3.5),
    's09': (24, [(0, (-0.6, 0.0, 1.0), (-1.7, 3.2, 1.9)), (1, (-0.7, 0.3, 1.05), (-1.7, 3.2, 1.9))], 5.6),
    's10': (45, [(0, (-0.8, 0.05, 0.35), (-1.0, 1.6, 0.15)), (1, (-0.85, 0.3, 0.3), (-1.0, 1.6, 0.15))], 2.0),
    's11': (24, [(0, (-2.6, -1.8, 2.4), (0.3, 2.0, 1.0)), (1, (-2.3, -1.4, 2.3), (0.3, 2.0, 1.0))], 8),
    's12': (32, [(0, (1.75, -1.6, 1.25), (1.75, 1.6, 1.0)), (1, (1.7, -1.25, 1.22), (1.75, 1.6, 1.0))], 3.5),
    's13': (35, [(0, (2.2, 0.15, 1.15), (2.2, 1.6, 1.15)), (1, (2.2, 0.4, 1.15), (2.2, 1.6, 1.15))], 4),
    's14': (22, [(0, (-1.9, -3.9, 2.9), (0.3, 1.8, 0.9)), (1, (-1.6, -3.4, 2.7), (0.3, 1.8, 0.9))], 8),
    's15': (45, [(0, (DX - 0.05, DY + 0.32, 1.0), (DX - 0.05, DY - 0.11, 0.9)), (1, (DX - 0.05, DY + 0.22, 0.98), (DX - 0.05, DY - 0.11, 0.9))], 4),
    's16': (35, [(0, (NX, 6.0, 7.6), (NX, 12, 8.6)), (1, (NX, -9.0, 4.0), (NX, 12, 7.6))], 11),
    's17': (55, [(0, (0.42, 0.45, 1.3), (0.4, 1.85, 1.26)), (1, (0.42, 0.65, 1.3), (0.4, 1.85, 1.26))], 2.0),
    's18': (40, [(0, (BKX + 0.05, BKY - 0.75, 1.25), (BKX, BKY, 0.78)), (1, (BKX + 0.05, BKY - 0.6, 1.15), (BKX, BKY, 0.78))], 2.8),
    's19': (35, [(0, (-0.45, -1.5, 1.2), (-0.6, 1.7, 0.9)), (1, (-0.5, -1.2, 1.18), (-0.6, 1.7, 0.9))], 2.8),
    's20': (24, [(0, (0.4, -4.4, 2.3), (0.2, 1.8, 1.0)), (1, (0.2, -3.6, 1.9), (0.2, 1.8, 1.1))], 8),
}
for sid, (lens, path, fstop) in CAMS.items():
    a, b = s[sid]
    cd = bpy.data.cameras.new('CAM_' + sid); cd.lens = lens; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 36; cd.clip_start = 0.02; cd.clip_end = 300
    cam = bpy.data.objects.new('CAM_' + sid, cd); link(cam, True)
    tgt = empty('TGT_' + sid)
    con = cam.constraints.new('TRACK_TO'); con.target = tgt; con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
    cd.dof.use_dof = True; cd.dof.focus_object = tgt; cd.dof.aperture_fstop = fstop
    if path == 'orbit':
        piv = empty('PIV_s07', (OPEN_SPOT[0], OPEN_SPOT[1], 0)); cam.parent = piv; cam.location = (0, -3.3, 1.35)
        tgt.location = (OPEN_SPOT[0], OPEN_SPOT[1], 0.8)
        key(piv, 'rotation_euler', a, Vector((0, 0, math.radians(-15))), 'BEZIER'); key(piv, 'rotation_euler', b, Vector((0, 0, math.radians(78))), 'BEZIER')
    else:
        for tr_, pos, look in path:
            f = a + int(round(tr_ * (b - a)))
            key(cam, 'location', f, Vector(pos), 'BEZIER'); key(tgt, 'location', f, Vector(look), 'BEZIER')
    m = sc.timeline_markers.new(sid, frame=a); m.camera = cam
    if sid == 's01': sc.camera = cam
# s02 small "turn" bump; nothing else needed
