import gzip
import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
r=Path('/Users/bytedance/Documents/房车方案');out=r/'work/车头连续曲面_R7_20261015/A13';patch=out/'patch.py'
exec(compile(patch.read_text(),str(patch),'exec'))
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
selected=[]
for o in list(bpy.data.objects):
 n=o.name;low=n.lower();layer=None
 if o.type not in ('MESH','CURVE','FONT') or o.hide_render:continue
 if n.startswith(('V15','V18','V80 detail')):
  if any(w in low for w in ['seat','cushion','headrest','head restraint','backrest','belt','buckle','release key','recline','shoulder webbing','pedestal']):continue
  layer='cockpit'
 if n in ['Panoramic windshield','Windshield rubber perimeter','L Sliding window glass','R Sliding window glass'] or n.startswith('Windshield wiper'):layer='cockpit'
 if n.startswith(('V11 single shell','V6 flush curved','V80 OEM rooflight','PV ','Roof ','Rear roof vent','Solar |')) or n=='V15 Cab headliner':layer='exterior'
 # Remaining visible source objects are exterior components; seats stay in the R7 base.
 if layer is None and not n.startswith(('V15','V18','V80 detail')) and n not in ('Studio floor','Driver_Body'):layer='exterior'
 if layer:selected.append((o,layer,None))
records=[];new=[]
for idx,(o,layer,facefilter) in enumerate(selected):
 ev=o.evaluated_get(dg);m=ev.to_mesh();m.calc_loop_triangles();vs=[o.matrix_world@v.co for v in m.vertices];nm=o.matrix_world.to_3x3().inverted().transposed();vn=[(nm@n.vector).normalized() for n in m.vertex_normals];isbody=o.name=='A12｜V02左右双窗候选车壳'

 if isbody:
  # Diagnostic only: smooth full-source normals before paint splitting.
  ids={v.index for v in m.vertices if -2.95<v.co.x<-2.03 and .40<v.co.z<1.38+min(0,v.co.x+1.8)*.25+.035}
  adj={i:[] for i in ids}
  for e in m.edges:
   a,b=e.vertices
   if a in adj:adj[a].append(b)
   if b in adj:adj[b].append(a)
  for _ in range(40):
   nxt={i:(vn[i]+sum((vn[j] for j in adj[i]),Vector())).normalized() for i in ids}
   for i,n in nxt.items():vn[i]=n
 bymat={};paint={}
 for mi,mat in enumerate(m.materials):
  if mat and mat.use_nodes:
   mixes=[n for n in mat.node_tree.nodes if n.type=='MIX_RGB']
   if mixes:
    mix=next((n for n in mixes if not n.inputs[1].is_linked and not n.inputs[2].is_linked),None)
    if mix:paint[mi]=(list(mix.inputs[1].default_value),list(mix.inputs[2].default_value))
 # Split paint-boundary triangles in their existing planes; no vertex displacement.
 # Positional two-tone preview avoids baking the source's normal-dependent colour seams.
 def height(p):return 1.38+min(0,p.x+1.8)*.25
 def clipped(poly,upper):
  result=[]
  for (p,pn),(q,qn) in zip(poly,poly[1:]+poly[:1]):
   dp=p.z-height(p);dq=q.z-height(q);ip=(dp>=0) if upper else (dp<=0);iq=(dq>=0) if upper else(dq<=0)
   if ip:result.append((p,pn))
   if ip!=iq:
    t=dp/(dp-dq);result.append((p+(q-p)*t,pn.lerp(qn,t).normalized()))
  return result
 for t in m.loop_triangles:
  if facefilter and not facefilter([vs[i] for i in t.vertices]):continue
  mi=t.material_index
  if mi in paint:
   poly=[vs[i] for i in t.vertices]
   signs=[p.z-height(p) for p in poly]
   if min(signs)>=0 or max(signs)<=0:
    shade=tuple(paint[mi][1 if min(signs)>=0 else 0]);bymat.setdefault((mi,shade),[]).append(tuple(t.vertices));continue
   for upper in (False,True):
    cut=clipped([(vs[i],vn[i])for i in t.vertices],upper)
    if len(cut)<3:continue
    ids=[]
    for p,n in cut:ids.append(len(vs));vs.append(p);vn.append(n)
    key=(mi,tuple(paint[mi][1 if upper else 0]))
    bymat.setdefault(key,[]).extend([(ids[0],ids[j],ids[j+1])for j in range(1,len(ids)-1)])
  else:bymat.setdefault((mi,None),[]).append(tuple(t.vertices))
 for (mi,shade),fs in bymat.items():
  used=sorted({i for f in fs for i in f});remap={a:b for b,a in enumerate(used)};verts=[list(vs[i]) for i in used];faces=[[remap[i] for i in f] for f in fs]
  mat=m.materials[mi] if mi<len(m.materials) else None;color=list(mat.diffuse_color) if mat else [.5,.5,.5,1]
  if mat and mat.use_nodes:
   bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
   if bs:color=list(bs.inputs['Base Color'].default_value)
  if shade is not None:color=list(shade)
  name=f'RD_{layer}_{idx:03d}_{mi}'
  glass=('glass' in o.name.lower() or 'transparent' in o.name.lower() or '玻璃占位' in o.name or o.name in ['Panoramic windshield','V6 flush curved panoramic rooflight'])
  records.append({'id':name,'source':o.name,'layer':layer,'color':color,'glass':glass,'vertices':verts,'faces':faces,'normals':[list(vn[i])for i in used],'body_normal':[isbody]*len(used)})
 ev.to_mesh_clear()
# Merge only identical display materials within one toggle layer; keep source membership in metadata.
merged={}
for a in records:
 key=(a['layer'],tuple(a['color']),a['glass'])
 b=merged.setdefault(key,{'id':f'RD_{a["layer"]}_{len(merged):03d}','source':[],'layer':a['layer'],'color':a['color'],'glass':a['glass'],'vertices':[],'faces':[],'normals':[],'body_normal':[]})
 offset=len(b['vertices']);b['vertices'].extend(a['vertices']);b['faces'].extend([[v+offset for v in f] for f in a['faces']]);b['source'].append(a['source']);b['normals'].extend(a['normals']);b['body_normal'].extend(a['body_normal'])
for o in new:bpy.data.objects.remove(o,do_unlink=True)
new=[];records=list(merged.values())
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
import gc;gc.collect()
for a in records:
 mesh=bpy.data.meshes.new(a['id']);mesh.from_pydata(a['vertices'],[],a['faces']);mesh.update()
 import bmesh
 # Keep R5 welding/shading everywhere; carry custom normals only on the front body.
 bm=bmesh.new();bm.from_mesh(mesh);nl=bm.verts.layers.float_vector.new('R7_front_normal');ml=bm.verts.layers.float.new('R7_front_mask');bm.verts.ensure_lookup_table()
 for v in bm.verts:
  v[nl]=Vector(a['normals'][v.index]);v[ml]=1.0 if a['body_normal'][v.index] and v.co.x<-2.03 else 0.0
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
 for poly in mesh.polygons:poly.use_smooth=True
 mesh.set_sharp_from_angle(angle=math.radians(35))
 cn0=[n.vector.copy() for n in mesh.corner_normals];nattr=mesh.attributes['R7_front_normal'];mattr=mesh.attributes['R7_front_mask']
 for loop in mesh.loops:
  if mattr.data[loop.vertex_index].value>.5:cn0[loop.index]=nattr.data[loop.vertex_index].vector.copy()
 mesh.normals_split_custom_set(cn0)
 mesh.attributes.remove(nattr);mesh.attributes.remove(mattr)
 # Continuous connector skin: old triangulated segment boundaries are not creases.
 sharp=mesh.attributes.get('sharp_edge')
 if sharp:
  for edge in mesh.edges:
   ps=[mesh.vertices[i].co for i in edge.vertices]
   if all(-.79<p.x<-.25 and .43<p.z<1.5 and abs(p.y-.0473)>.8 for p in ps):sharp.data[edge.index].value=False
 # Fair shading normals over the original finely segmented transition, without moving vertices.
 ids=[v.index for v in mesh.vertices if -.79<v.co.x<-.25 and .52<v.co.z<1.5 and abs(v.co.y-.0473)>.85]
 if ids:
  adj={i:[] for i in ids}
  for e in mesh.edges:
   u,v=e.vertices
   if u in adj:adj[u].append(v)
   if v in adj:adj[v].append(u)
  ns=[v.vector.copy() for v in mesh.vertex_normals]
  for _ in range(10):
   nxt={i:(ns[i]+sum((ns[j] for j in adj[i]),Vector()))/(1+len(adj[i])) for i in ids}
   for i,n in nxt.items():ns[i]=n.normalized()
  cn=[n.vector.copy() for n in mesh.corner_normals]
  for loop in mesh.loops:
   if loop.vertex_index in adj:cn[loop.index]=ns[loop.vertex_index]
  mesh.normals_split_custom_set(cn)
 obj=bpy.data.objects.new(a['id'],mesh);bpy.context.collection.objects.link(obj)
 mat=bpy.data.materials.new(a['id']+'_display');mat.diffuse_color=tuple(a['color']);mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=a['color'];bs.inputs['Roughness'].default_value=.5
 if a['glass']:bs.inputs['Alpha'].default_value=.22;mat.surface_render_method='DITHERED'
 mesh.materials.append(mat);obj['renderLayer']=a['layer'];obj['zone']='cab';new.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for o in new:o.select_set(True)
bpy.context.view_layer.objects.active=new[0]
bpy.ops.export_scene.gltf(filepath=str(out/'render-details.glb'),use_selection=True,export_extras=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
for a in records:a.pop('normals',None);a.pop('body_normal',None)
with gzip.open(out/'meshes.json.gz','wt',encoding='utf-8',compresslevel=3) as gz:json.dump(records,gz,ensure_ascii=False)
(out/'来源登记.json').write_text(json.dumps({'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'geometry_patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'geometry_patch_report':json.loads((out/'修形登记.json').read_text()),'scope':'Blender原比例网格出图参考；当前可见V02双窗外壳、车头车顶生活舱及外部装备；排除已隐藏历史窗壳和旧座椅家具；非厂家CAD','objects':[{k:v for k,v in a.items() if k not in ('vertices','faces')}|{'vertices':len(a['vertices']),'triangles':len(a['faces'])}for a in records]},ensure_ascii=False,indent=2))
print('EXPORTED',len(records),sum(len(a['faces'])for a in records))
