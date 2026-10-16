"""Run in Blender to project touch regions and render visible-floor ID masks.
Does not save or modify upper.blend. Finish with prepare-interaction.py.
"""
import bpy
import json
import re
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE=Path(__file__).resolve().parent
model=json.loads((HERE/'model.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(HERE/'upper.blend'))
scene=bpy.context.scene
origin=model['coordinate_system']['origin']; scale=model['coordinate_system']['units_per_metre']
palette=['#ff0000','#00ff00','#0000ff','#ffff00','#ff00ff','#00ffff','#ff8000','#8000ff','#00ff80','#80ff00']
data={'version':3,'width':2400,'height':2000,'rooms':[]}
def project(p):
    point=Vector(((p[0]-origin[0])/scale,(origin[1]-p[1])/scale,.035))
    v=world_to_camera_view(scene,scene.camera,point)
    return [round(v.x,6),round(1-v.y,6)]
def emission(name,hexcolor):
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    mat.node_tree.nodes.clear()
    out=mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    node=mat.node_tree.nodes.new('ShaderNodeEmission')
    rgb=[int(hexcolor[i:i+2],16)/255 for i in (1,3,5)]
    linear=[c/12.92 if c<.04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    node.inputs['Color'].default_value=(*linear,1)
    node.inputs['Strength'].default_value=1
    mat.node_tree.links.new(node.outputs[0],out.inputs['Surface'])
    return mat
black=emission('Non-floor mask','#000000')
for obj in scene.objects:
    if obj.type=='MESH':
        obj.data.materials.clear(); obj.data.materials.append(black)
        for face in obj.data.polygons: face.material_index=0
    if obj.type=='LIGHT': obj.hide_render=True
for i,room in enumerate(model['rooms']):
    path=HERE.parents[1]/'dashboards'/'home'/'rooms'/(room['id']+'.yaml')
    source=path.read_text() if path.exists() else ''
    entities=list(dict.fromkeys(re.findall(r'entity:\s*([a-z_]+\.[a-zA-Z0-9_]+)',source)))
    lights=[e for e in entities if e.startswith('light.')]
    speakers=[e for e in entities if e.startswith('media_player.')]
    covers=[e for e in entities if e.startswith('cover.')]
    scenes=[e for e in entities if e.startswith('scene.')]
    r={'id':room['id'],'label':room['label'],'polygon':[project(p) for p in room['polygon']],
       'anchor':project(room['label_anchor']),'route':'/dashboard-home/'+room['route'],
       'lights':lights,'media':speakers,'covers':covers,'scenes':scenes,
       'mask':'masks/'+room['id']+'.png','mask_color':palette[i]}
    xs=[p[0] for p in r['polygon']]; ys=[p[1] for p in r['polygon']]
    r['bounds']=[min(xs),min(ys),max(xs),max(ys)]
    data['rooms'].append(r)
    obj=bpy.data.objects.get(room['id'])
    assert obj is not None,room['id']
    obj.data.materials.clear(); obj.data.materials.append(emission(room['id']+' ID',palette[i]))
    for face in obj.data.polygons: face.material_index=0
(HERE/'room-interaction.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
scene.render.engine='CYCLES'; scene.cycles.samples=1; scene.cycles.use_denoising=False
scene.cycles.max_bounces=0
scene.view_settings.view_transform='Standard'; scene.view_settings.look='None'; scene.view_settings.exposure=0
scene.view_settings.gamma=1
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
scene.render.film_transparent=False
scene.render.resolution_x=2400; scene.render.resolution_y=2000; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
scene.render.filepath=str(HERE/'room-id.png')
bpy.ops.render.render(write_still=True)
print('INTERACTION_PROJECTION_READY',flush=True)
