# EP2 step 5 proof: same shot rendered with the host's Emission material vs a lit Principled BSDF.
# blender -b episode2.blend --python compare_mat.py   -> renders/mat_emission.png, renders/mat_principled.png
import bpy, json
sc = bpy.context.scene; sc.eevee.taa_render_samples = 24; sc.render.resolution_percentage = 100
TL = json.load(open(bpy.path.abspath('//../tap2/build/timeline.json'), encoding='utf-8'))
s = next(x for x in TL['shots'] if x['id'] == 'b5a')
sc.frame_set(int(s['end'] * 30) - 3); sc.camera = bpy.data.objects['CAM_b5a']
sc.render.filepath = bpy.path.abspath('//renders/mat_emission.png'); bpy.ops.render.render(write_still=True)
for nm in ('chr_smile', 'chr_neutral'):
    nt = bpy.data.materials[nm].node_tree
    em = next(n for n in nt.nodes if n.type == 'EMISSION'); tx = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    pb = nt.nodes.new('ShaderNodeBsdfPrincipled'); pb.inputs['Roughness'].default_value = 0.6
    nt.links.new(tx.outputs['Color'], pb.inputs['Base Color'])
    for l in list(em.outputs[0].links): nt.links.new(pb.outputs[0], l.to_socket)
sc.render.filepath = bpy.path.abspath('//renders/mat_principled.png'); bpy.ops.render.render(write_still=True)
