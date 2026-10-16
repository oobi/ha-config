#!/usr/bin/env python3
"""Build the independent floorplan3d assets with Blender 5.

  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python www/floorplan3d/build.py -- --quality final

Everything written by this script stays alongside it. No changes to HA or the
original floorplan. Geometry is based on model.json; no furniture is invented.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = Path(__file__).resolve().parent
MODEL = json.loads((HERE / 'model.json').read_text())
ARGS = argparse.ArgumentParser()
ARGS.add_argument('--quality', choices=['draft', 'final'], default='final')
ARGS.add_argument('--scene', choices=['upper', 'outside', 'all'], default='all')
ARGS.add_argument('--skip-export', action='store_true')
OPTS = ARGS.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
RNG = random.Random(27)
COLLECTIONS = {}


def collection(name):
    if name not in COLLECTIONS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLLECTIONS[name] = c
    return COLLECTIONS[name]


def move_to(obj, group):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection(group).objects.link(obj)


def rgb(code):
    code = code.lstrip('#')
    values = [int(code[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4 for v in values)


def material(name, color, roughness=.65, grain=False):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb(color), 1)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*rgb(color), 1)
    bs.inputs['Roughness'].default_value = roughness
    if grain:
        tex = nodes.new('ShaderNodeTexCoord')
        mapping = nodes.new('ShaderNodeVectorMath')
        mapping.operation = 'MULTIPLY'
        mapping.inputs[1].default_value = (.8, 70, 7)
        links.new(tex.outputs['Object'], mapping.inputs[0])
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 2.8
        noise.inputs['Detail'].default_value = 2
        links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
        ramp = nodes.new('ShaderNodeValToRGB')
        base = rgb(color)
        ramp.color_ramp.elements[0].position = .18
        ramp.color_ramp.elements[0].color = (*[x * .78 for x in base], 1)
        ramp.color_ramp.elements[1].position = .82
        ramp.color_ramp.elements[1].color = (*[min(x * 1.12, 1) for x in base], 1)
        links.new(noise.outputs['Fac'], ramp.inputs[0])
        links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .13
        bump.inputs['Distance'].default_value = .008
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    return m


def cube(name, location, scale, mat, bevel=.015, group='Architecture'):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft edges', 'BEVEL')
        mod.width, mod.segments = bevel, 3
        mod = obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
    move_to(obj, group)
    return obj


def union_walls(boxes, mat):
    """Exact solid union, including sill blocks and lintels above openings."""
    boxes=[(x-w/2,x+w/2,y-d/2,y+d/2,z0,z1) for x,y,w,d,z0,z1 in boxes]
    xs=sorted({round(v,6) for b in boxes for v in b[:2]})
    ys=sorted({round(v,6) for b in boxes for v in b[2:4]})
    zs=sorted({round(v,6) for b in boxes for v in b[4:6]})
    cells=set()
    for i in range(len(xs)-1):
        x=(xs[i]+xs[i+1])/2
        candidates=[b for b in boxes if b[0]-1e-7<x<b[1]+1e-7]
        for j in range(len(ys)-1):
            y=(ys[j]+ys[j+1])/2
            spans=[b[4:] for b in candidates if b[2]-1e-7<y<b[3]+1e-7]
            if not spans: continue
            for k in range(len(zs)-1):
                z=(zs[k]+zs[k+1])/2
                if any(a<z<b for a,b in spans): cells.add((i,j,k))
    verts,faces=[],[]
    def face(points):
        start=len(verts); verts.extend(points); faces.append(tuple(range(start,start+len(points))))
    for i,j,k in sorted(cells):
        x0,x1,y0,y1,z0,z1=xs[i],xs[i+1],ys[j],ys[j+1],zs[k],zs[k+1]
        if (i,j,k+1) not in cells: face([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)])
        if (i,j,k-1) not in cells: face([(x0,y1,z0),(x1,y1,z0),(x1,y0,z0),(x0,y0,z0)])
        for di,dj,a,b in [(-1,0,(x0,y1),(x0,y0)),(1,0,(x1,y0),(x1,y1)),
                          (0,-1,(x0,y0),(x1,y0)),(0,1,(x1,y1),(x0,y1))]:
            if (i+di,j+dj,k) not in cells: face([(*a,z0),(*b,z0),(*b,z1),(*a,z1)])
    mesh=bpy.data.meshes.new('Continuous walls with openings')
    mesh.from_pydata(verts,[],faces); mesh.update()
    bm=bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.dissolve_limit(bm,angle_limit=.0001,verts=list(bm.verts),edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free()
    obj=bpy.data.objects.new('Continuous cutaway walls',mesh)
    collection('Architecture').objects.link(obj); mesh.materials.append(mat)
    mod=obj.modifiers.new('Soft plaster edges','BEVEL'); mod.width=.009; mod.segments=3
    obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return obj


def prism(name, polygon, z, height, mat, bevel=.012, group='Architecture'):
    """Extrude a simple (possibly concave) counter-clockwise polygon."""
    poly = list(polygon)
    if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])) < 0:
        poly.reverse()
    n = len(poly)
    verts = [(x,y,z) for x,y in poly] + [(x,y,z+height) for x,y in poly]
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection(group).objects.link(obj)
    mesh.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Edge softness', 'BEVEL')
        mod.width, mod.segments = bevel, 2
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def xy(point):
    origin=MODEL['coordinate_system']['origin']
    scale=MODEL['coordinate_system']['units_per_metre']
    return ((point[0]-origin[0])/scale, (origin[1]-point[1])/scale)


def clip(poly, axis, limit, above):
    if not poly:
        return []
    out = []
    a = poly[-1]
    ia = a[axis] >= limit if above else a[axis] <= limit
    for b in poly:
        ib = b[axis] >= limit if above else b[axis] <= limit
        if ia != ib:
            t = (limit-a[axis])/(b[axis]-a[axis])
            out.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])))
        if ib:
            out.append(b)
        a,ia = b,ib
    return out


def flooring(name, poly, mats, kind='oak', z=.025):
    """A single mesh of individually jointed boards / tiles, clipped to room."""
    x0,x1 = min(p[0] for p in poly),max(p[0] for p in poly)
    y0,y1 = min(p[1] for p in poly),max(p[1] for p in poly)
    width = .19 if kind=='oak' else .145 if kind=='deck' else .58
    length = 1.65 if kind=='oak' else 12 if kind=='deck' else .58
    gap = .007 if kind=='deck' else .003
    verts,faces,indices = [],[],[]
    row = math.floor(y0/width)
    while row*width < y1:
        ya,yb = row*width+gap/2,(row+1)*width-gap/2
        offset = ((row%3)*.55 if kind=='oak' else 0)
        col = math.floor((x0-offset)/length)
        while col*length+offset < x1:
            xa,xb = col*length+offset+gap/2,(col+1)*length+offset-gap/2
            p = poly
            for axis,limit,above in [(0,xa,True),(0,xb,False),(1,ya,True),(1,yb,False)]:
                p = clip(p,axis,limit,above)
            if len(p)>=3:
                area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]))
                if abs(area)>.00001:
                    if area<0: p.reverse()
                    start = len(verts)
                    verts += [(x,y,z) for x,y in p]
                    faces.append(tuple(range(start,start+len(p))))
                    indices.append(RNG.randrange(len(mats)))
            col += 1
        row += 1
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    for m in mats: mesh.materials.append(m)
    for face,idx in zip(mesh.polygons,indices): face.material_index = idx
    obj = bpy.data.objects.new(name,mesh)
    collection('Finishes').objects.link(obj)
    return obj


def reset():
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if c.name != 'Collection': bpy.data.collections.remove(c)
    COLLECTIONS.clear()
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24 if OPTS.quality=='draft' else 96
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.render.resolution_x = 1200 if OPTS.quality=='draft' else 2400
    scene.render.resolution_y = 1000 if OPTS.quality=='draft' else 2000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = .35
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.75,.81,.9,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    scene.unit_settings.system = 'METRIC'
    # GPU when available; CPU otherwise. This is read from Blender, not assumed.
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        gpu = [d for d in prefs.devices if d.type=='METAL']
        for d in prefs.devices: d.use = d.type=='METAL'
        if gpu: scene.cycles.device = 'GPU'
        print('FLOORPLAN_RENDER_DEVICE', scene.cycles.device, flush=True)
    except Exception as ex:
        print('Using CPU renderer:', ex, flush=True)
    return scene


def area_light(name, position, energy, size, color, target=(0,0,0)):
    data = bpy.data.lights.new(name,'AREA')
    data.energy, data.shape, data.size, data.color = energy,'DISK',size,color
    obj = bpy.data.objects.new(name,data)
    collection('Lighting').objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj


def camera(location, target, scale):
    data = bpy.data.cameras.new('Isometric camera')
    data.type, data.ortho_scale, data.lens = 'ORTHO',scale,50
    obj = bpy.data.objects.new('Isometric camera',data)
    collection('Presentation').objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.camera = obj
    return obj


def studio():
    mat = material('Warm porcelain background','#eae7e0',.88)
    ground = cube('Studio ground',(0,0,-.53),(200,200,.12),mat,0,'Presentation')
    key = area_light('Soft daylight',(-8,-3,16),2400,9,(1,.91,.78))
    fill = area_light('Sky fill',(8,7,12),1500,10,(.78,.87,1))
    return ground,key,fill


def render(filename):
    bpy.context.scene.render.filepath = str(HERE / filename)
    print('RENDERING',filename,flush=True)
    bpy.ops.render.render(write_still=True)


def save_model(name):
    if OPTS.skip_export: return
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / (name+'.blend')))
    bpy.ops.object.select_all(action='DESELECT')
    for c in ('Architecture','Finishes','Stairs','Openings','Furniture','Site'):
        for obj in collection(c).objects:
            if obj.type=='MESH': obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(HERE / (name+'.glb')),
                              export_format='GLB',use_selection=True,
                              export_apply=True,export_cameras=False,export_lights=False)
    bpy.ops.object.select_all(action='DESELECT')


def labels(filename, rooms):
    """Separate vector labels; exact camera projection, optional in preview."""
    w,h = bpy.context.scene.render.resolution_x,bpy.context.scene.render.resolution_y
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">',
             '<style>text{font-family:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'
             'font-weight:500;fill:#454c46;text-anchor:middle;paint-order:stroke;'
             'stroke:#f5f1e9;stroke-width:5;stroke-linejoin:round}</style>']
    positions = {}
    for room in rooms:
        p = xy(room['label_anchor'])
        v = world_to_camera_view(bpy.context.scene,bpy.context.scene.camera,Vector((*p,.045)))
        x,y = v.x*w,(1-v.y)*h
        size = w*.0105 if room['id'] not in ('hallway','ensuite','bathroom') else w*.009
        label = room['label'].replace('&','&amp;')
        parts.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size:.2f}">{label}</text>')
        positions[room['id']] = {'x':round(v.x*100,3),'y':round((1-v.y)*100,3)}
    parts.append('</svg>')
    (HERE/filename).write_text('\n'.join(parts)+'\n')
    (HERE/'room-anchors.json').write_text(json.dumps(positions,indent=2)+'\n')


def traced_architecture(plaster):
    """Build explicit traced walls, then real gaps, frames and door leaves."""
    scale=MODEL['coordinate_system']['units_per_metre']
    frame=material('Warm bronze window frames','#756e5d',.38)
    joinery=material('Off-white door joinery','#e6e1d5',.65)
    hardware=material('Satin brass hardware','#9a8966',.3)
    glass=material('Soft clear glazing','#c1d3cf',.17)
    shader=glass.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Transmission Weight'].default_value=.72
    shader.inputs['IOR'].default_value=1.45
    walls={w['id']:w for w in MODEL['walls']}
    boxes=[]
    for wall in MODEL['walls']:
        a,b=wall['start'],wall['end']
        horizontal=a[1]==b[1]
        axis=0 if horizontal else 1
        lo,hi=sorted((a[axis],b[axis]))
        h=wall['display_height_m']; thickness=wall['thickness_m']
        openings=sorted((o for o in MODEL['openings'] if o['wall']==wall['id']),key=lambda o:o['start'])
        def segment(start,end,z0,z1):
            if end-start<.001 or z1-z0<.001: return
            q=((start+end)/2,a[1]) if horizontal else (a[0],(start+end)/2)
            x,y=xy(q); length=(end-start)/scale
            w,d=(length,thickness) if horizontal else (thickness,length)
            boxes.append((x,y,w,d,z0,z1))
        cursor=lo
        for o in openings:
            assert lo<=o['start']<o['end']<=hi, o['id']
            assert o['start']>=cursor, ('Overlapping openings',o['id'])
            segment(cursor,o['start'],0,h)
            segment(o['start'],o['end'],0,min(h,o['sill_m']))
            segment(o['start'],o['end'],min(h,o['head_m']),h)
            cursor=o['end']
        segment(cursor,hi,0,h)
    union_walls(boxes,plaster)

    for opening in MODEL['openings']:
        wall=walls[opening['wall']]
        horizontal=wall['start'][1]==wall['end'][1]
        constant=wall['start'][1] if horizontal else wall['start'][0]
        lo,hi=opening['start'],opening['end']
        sill=opening['sill_m']; head=min(opening['head_m'],wall['display_height_m'])
        if head<=sill: continue
        height=head-sill
        name=opening['id']; kind=opening['kind']
        glazing=kind in ('window','sliding_glass')
        mat=frame if glazing else joinery
        fw=.026 if glazing else .035
        def piece(suffix,center,length,z,h,depth,material,offset=0):
            q=(center,constant) if horizontal else (constant,center)
            x,y=xy(q)
            if horizontal: y+=offset; dims=(length,depth,h)
            else: x+=offset; dims=(depth,length,h)
            return cube(name+' '+suffix,(x,y,z),dims,material,.004,'Openings')
        length=(hi-lo)/scale
        # Side jambs continue to the model's visible cut, not an invented arch.
        for position in (lo+fw*scale/2,hi-fw*scale/2):
            piece('jamb',position,fw,(head+sill)/2,height,.085,mat)
        if head>=opening['head_m']-.001 or glazing or kind=='wardrobe':
            piece('head',(lo+hi)/2,length,head-fw/2,fw,.085,mat)
        if glazing or kind=='wardrobe':
            piece('track',(lo+hi)/2,length,sill+fw/2,fw,.11,mat)
        if kind=='window':
            piece('stone sill',(lo+hi)/2,length+.08,sill-.015,.04,wall['thickness_m']+.06,plaster)
        if kind=='hinged_door':
            hinge=Vector((*xy(opening['hinge']),0))
            tip=Vector((*xy(opening['leaf_tip']),0))
            v=tip-hinge; width=v.length
            leaf=cube(name+' open leaf',tuple((hinge+tip)/2+Vector((0,0,(head+sill)/2))),
                      (width,.035,height-.025),joinery,.007,'Openings')
            leaf.rotation_euler.z=math.atan2(v.y,v.x)
            grip=hinge+v*.87
            grip.z=min(sill+.97,head-.12)
            normal=Vector((-v.y,v.x,0)).normalized()
            grip+=normal*.035
            handle=cube(name+' handle',tuple(grip),(.10,.025,.022),hardware,.006,'Openings')
            handle.rotation_euler.z=leaf.rotation_euler.z
        elif kind in ('window','sliding_glass','wardrobe'):
            count=opening.get('panels',2)
            panel=(hi-lo)/count
            for i in range(count):
                center=lo+(i+.5)*panel
                offset=.02*(i%2)
                if i==opening.get('open_panel'):
                    # Slide the leaf partly over the adjacent fixed panel.
                    direction=1 if i<count-1 else -1
                    center+=direction*panel*.82
                    offset=.065
                panel_width=panel/scale-fw
                if kind=='wardrobe':
                    piece('robe panel',center,panel_width,(head+sill)/2,height-fw*1.5,.028,joinery,offset)
                    piece('robe pull',center+panel*.37,.015,min(head-.13,.65),.14,.025,hardware,offset+.025)
                else:
                    piece('glass',center,panel_width-fw,(head+sill)/2,height-2*fw,.009,glass,offset)
                    for boundary in (center-panel/2+fw*scale,center+panel/2-fw*scale):
                        piece('sash stile',boundary,fw,(head+sill)/2,height-fw,.032,frame,offset)
                    for z in (sill+fw,head-fw):
                        piece('sash rail',center,panel_width,z,fw,.032,frame,offset)


def trace_plan():
    """Human-reviewable top view of the interpretation of the supplied image."""
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 930 958">',
           '<rect width="930" height="958" fill="#f7f5ef"/>']
    def points(poly): return ' '.join(f'{x},{y}' for x,y in poly)
    for r in MODEL['rooms']:
        color={'deck':'#d5c6af','tile':'#d6dfd9','oak':'#eee4d4'}[r['material']]
        parts.append(f'<polygon points="{points(r["polygon"])}" fill="{color}"/>')
    parts.append(f'<polygon points="{points(MODEL["balcony"])}" fill="#d5c6af"/>')
    for w in MODEL['walls']:
        a,b=w['start'],w['end']
        parts.append(f'<path d="M{a[0]} {a[1]} L{b[0]} {b[1]}" stroke="#42483f" stroke-width="7"/>')
    walls={w['id']:w for w in MODEL['walls']}
    for o in MODEL['openings']:
        w=walls[o['wall']]; horizontal=w['start'][1]==w['end'][1]
        c=w['start'][1] if horizontal else w['start'][0]
        a=(o['start'],c) if horizontal else (c,o['start'])
        b=(o['end'],c) if horizontal else (c,o['end'])
        color='#b5d6d6' if o['kind'] in ('window','sliding_glass') else '#f7f5ef'
        parts.append(f'<path d="M{a[0]} {a[1]} L{b[0]} {b[1]}" stroke="{color}" stroke-width="9"/>')
        if 'hinge' in o:
            h,t=o['hinge'],o['leaf_tip']
            parts.append(f'<path d="M{h[0]} {h[1]} L{t[0]} {t[1]}" stroke="#9a8966" stroke-width="3"/>')
        if o['kind']=='wardrobe':
            parts.append(f'<path d="M{a[0]} {a[1]} L{b[0]} {b[1]}" stroke="#b4a686" stroke-width="3"/>')
    for room in MODEL['rooms']:
        x,y=room['label_anchor']
        parts.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="12" fill="#4c5549" text-anchor="middle">{room["label"]}</text>')
    parts.append('<text x="465" y="930" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#697363">REFERENCE TRACE · approximate positions; cyan = glazing, tan = door leaves</text></svg>')
    (HERE/'reference-trace.svg').write_text('\n'.join(parts)+'\n')


def build_upper():
    scene = reset()
    trace_plan()
    plaster = material('Warm ivory plaster','#eee9dd',.85)
    edge = material('Limestone slab edge','#c9c4b6',.8)
    base = material('Floor joint shadow','#887c68',.85)
    grout = material('Warm grey grout','#aaa99f',.9)
    oak = [material('Natural oak %02d'%i,c,.6,True) for i,c in enumerate(
        ['#c4ad8b','#cbb597','#c8b191','#c2aa89','#d0b99b','#ccb496','#bfa787','#c6af90'])]
    deck = [material('Weathered deck %02d'%i,c,.8,True) for i,c in enumerate(
        ['#ac9c82','#b3a48c','#ae9e85','#b8a78e','#b2a18a'])]
    tile = [material('Honed limestone %02d'%i,c,.8) for i,c in enumerate(
        ['#d1d1c7','#d6d5cc','#cccec4','#d3d3c9'])]
    footprint = [xy(p) for p in MODEL['footprint']]
    prism('Upper floor slab',footprint,-.38,.38,edge,.035)
    prism('Continuous subfloor',footprint,0,.017,base,0)
    for room in MODEL['rooms']:
        poly = [xy(p) for p in room['polygon']]
        kind = room['material']
        if kind=='deck':
            prism('Front deck slab',poly,-.34,.34,edge,.025)
            prism('Deck joints',poly,0,.015,base,0)
        elif kind=='tile':
            prism(room['id']+' grout bed',poly,.018,.004,grout,0,'Finishes')
        flooring(room['id'],poly,{'oak':oak,'deck':deck,'tile':tile}[kind],kind)
    balcony = [xy(p) for p in MODEL['balcony']]
    prism('Balcony slab',balcony,-.34,.34,edge,.025)
    prism('Balcony joints',balcony,0,.015,base,0)
    flooring('Balcony boards',balcony,deck,'deck')

    for builtin in MODEL.get('builtins',[]):
        flooring(builtin['id']+' floor',[xy(p) for p in builtin['polygon']],oak,'oak')
    traced_architecture(plaster)

    # Flight shortened to match the supplied reference, with an open landing.
    stair=MODEL['stairs']
    stair_poly=[xy(p) for p in stair['polygon']]
    prism('Stair recess',stair_poly,.026,.012,material('Stairwell shade','#817b6f'),0,'Stairs')
    x0,x1=min(p[0] for p in stair_poly),max(p[0] for p in stair_poly)
    y0,y1=min(p[1] for p in stair_poly),max(p[1] for p in stair_poly)
    depth=(y1-y0)/stair['count']
    for i in range(stair['count']):
        h=.035+i*.05
        cube('Stair tread %02d'%(i+1),((x0+x1)/2,y0+(i+.5)*depth,h/2+.03),
             (x1-x0-.06,depth-.012,h),oak[2],.006,'Stairs')
    # Empty by default; furniture gets its own collection and model entries.
    collection('Furniture')
    for item in MODEL.get('furniture',[]):
        if item.get('type')!='box':
            raise ValueError('Unsupported furniture type: '+str(item.get('type')))
        x,y=xy(item['position'])
        width,depth,height=item['size_m']
        obj=cube(item['name'],(x,y,height/2+.03),(width,depth,height),
                 material(item['name']+' finish',item.get('color','#b0a38b')),.035,'Furniture')
        obj.rotation_euler.z=math.radians(item.get('rotation_deg',0))
    ground,key,fill=studio()
    cam=camera((19,-25,29),(0,-.5,.2),24.8)
    bpy.context.view_layer.update()
    label_rooms=MODEL['rooms']+[{'id':'balcony','label':'Balcony','label_anchor':MODEL['balcony_label_anchor']}]
    labels('upper-labels.svg',label_rooms)
    save_model('upper')
    render('upper.png')
    if OPTS.quality=='draft': return

    # A matching transparent asset is useful over Home Assistant themes.
    ground.hide_render=True
    scene.render.film_transparent=True
    render('upper-transparent.png')
    ground.hide_render=False
    scene.render.film_transparent=False

    # Dusk is a lighting study only, with identical camera and room positions.
    key.data.energy=280
    key.data.color=(.58,.69,1)
    fill.data.energy=520
    fill.data.color=(.48,.63,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.12
    for room in MODEL['rooms']:
        if room['id'] in ('deck','hallway'): continue
        x,y=xy(room['label_anchor'])
        area_light(room['label']+' warm light',(x,y,2.5),75,1.8,(1,.66,.34),(x,y,0))
    render('upper-dusk.png')


def build_outside():
    scene=reset()
    # Site plan has its own coordinate system. It is not aligned or scaled
    # to the upper plan because the source does not establish that transform.
    def p(points): return [((x-297.5)/60,(730-y)/60) for x,y in points]
    def rect(x,y,w,h): return p([(x,y),(x+w,y),(x+w,y+h),(x,y+h)])
    earth=material('Site edge','#a9a596')
    stone=material('Pale paving','#c9c5b7')
    coping=material('Pool coping','#e3ded0')
    grass=material('Lawn','#7f956b',.95)
    drive=material('Driveway','#aaa99e',.95)
    wall=material('House massing','#e5e0d2',.85)
    roof=material('Neutral massing top','#cec9bb',.85)
    deck=material('Site timber','#a89273',.8,True)
    boundary=p([(25,10),(570,10),(570,1100),(540,1260),(470,1450),(25,1450)])
    prism('Site base',boundary,-.42,.42,earth,.06,'Site')
    prism('Paths and paving',boundary,0,.025,stone,.01,'Site')
    for i,poly in enumerate([[(250,800),(570,800),(570,1100),(540,1260),(470,1450),(300,1450),(250,1200)],[(25,1000),(85,1000),(135,1230),(25,1230)]]):
        prism('Lawn %s'%i,p(poly),.03,.035,grass,.018,'Site')
    prism('Pool terrace',rect(25,15,335,515),.03,.06,coping,.025,'Site')
    prism('Pool surround',rect(55,45,275,455),.091,.009,stone,.01,'Site')
    pool=[(70,165),(210,165),(210,230),(260,230),(260,325),(210,325),(210,460),(70,460),(70,385),(55,385),(55,255),(70,255)]
    poolmat=material('Pool turquoise','#388e9c',.19)
    bs=poolmat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Metallic'].default_value=.18
    noise=poolmat.node_tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=22
    bump=poolmat.node_tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.25
    bump.inputs['Distance'].default_value=.025
    poolmat.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height'])
    poolmat.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    prism('Pool water',p(pool),.102,.008,poolmat,.035,'Site')
    spa=material('Spa water','#57a6af',.22)
    prism('Spa',rect(187,232,71,91),.113,.008,spa,.02,'Site')
    house=p([(65,575),(405,575),(405,235),(500,235),(500,855),(385,855),(385,790),(65,790)])
    prism('House footprint massing',house,.04,1.35,wall,.035,'Site')
    prism('House flat schematic cap',house,1.39,.04,roof,.025,'Site')
    prism('Porch',rect(400,170,100,65),.04,.18,stone,.01,'Site')
    prism('Shed footprint',rect(455,20,80,50),.03,.9,wall,.02,'Site')
    prism('Rear deck',rect(385,855,115,85),.03,.10,deck,.01,'Site')
    prism('Carport footprint',rect(80,790,170,210),.03,.015,drive,.01,'Site')
    prism('Driveway',p([(85,1000),(250,1000),(250,1200),(300,1450),(175,1450),(135,1230)]),.031,.015,drive,.01,'Site')
    prism('Pump enclosure',rect(25,555,40,45),.03,.4,wall,.01,'Site')
    studio()
    camera((22,-29,33),(0,0,0),29.2)
    save_model('outside')
    render('outside.png')


if OPTS.scene in ('upper','all'): build_upper()
if OPTS.scene in ('outside','all'): build_outside()
print('FLOORPLAN3D_COMPLETE',flush=True)
