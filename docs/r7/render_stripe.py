import bpy
from pathlib import Path
from mathutils import Vector
r=Path('/Users/bytedance/Documents/房车方案');out=r/'work/车头连续曲面_R7_20261015/A13';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(r/'work/工业风卫浴门_20261014/rv-a27-render-base.glb'));base=list(bpy.data.objects)
for o in base:
 if 'edges' in o.name:o.hide_render=True
bpy.ops.import_scene.gltf(filepath=str(r/'work/工业风卫浴门_20261014/wc01.glb'));bpy.ops.import_scene.gltf(filepath=str(r/'work/工业风卫浴门_20261014/industrial-bath-door.glb'));base=list(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(out/'render-details.glb'));details=[o for o in bpy.data.objects if o not in base];s=bpy.context.scene
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.003));ground=bpy.context.object;ground.name='出图地面_非车辆部件';gm=bpy.data.materials.new('暖灰地面');gm.diffuse_color=(.65,.63,.59,1);ground.data.materials.append(gm)
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.7,.75,.85,1);next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.7
for loc,power,size in [((-1,0,4),200,4),((-3,-3,3),200,4)]:
 bpy.ops.object.light_add(type='AREA',location=loc);bpy.context.object.data.energy=power;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=size
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.clip_start=.02
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100
s.view_settings.view_transform='AgX'
def render(name,eye,target,lens,roof,cockpit):
 for o in details:o.hide_render=not (roof if o.get('renderLayer')=='exterior' else cockpit)
 cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens;s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)


for ob in details:
 for mat in ob.data.materials if ob.type=='MESH' else []:
  if mat and mat.use_nodes:
   bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
   if bs and bs.inputs['Alpha'].default_value>.9:bs.inputs['Base Color'].default_value=(.25,.25,.25,1);bs.inputs['Roughness'].default_value=.22
for ob in list(bpy.data.objects):
 if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True)
for loc in [(-4,-3,3),(-4,3,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=220;ob.data.shape='RECTANGLE';ob.data.size=.4;ob.data.size_y=3;ob.rotation_euler=(Vector((-2,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
render('条形高光_右前',(-5.2,4.9,2.9),(-2.1,0,1.1),60,True,True)
render('条形高光_左前',(-5.2,-4.8,2.9),(-2.1,0,1.1),60,True,True)
render('条形高光_低位',(-4.6,-4,1.1),(-2.1,0,.9),60,True,True)
