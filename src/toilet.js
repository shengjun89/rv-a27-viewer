import * as T from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
export const toiletBounds={min:[2.345951,.711,-.879019],max:[2.765951,1.151,-.539019]};
export function replaceToilet(model){
 model.updateMatrixWorld(true);
 const old=model.getObjectByName('wet_1');
 if(!old?.isMesh)throw new Error('未找到原坐便器占位');
 const b=new T.Box3().setFromObject(old);
 if(b.min.distanceTo(new T.Vector3(...toiletBounds.min))>1e-5||b.max.distanceTo(new T.Vector3(...toiletBounds.max))>1e-5)throw new Error('坐便器源包络已变化，请重新核对');
 old.removeFromParent();
 // Remove only the old cuboid's line segments from the shared static outline batch.
 const edges=model.getObjectByName('wet_edges');
 if(edges?.isLineSegments){
  const g=edges.geometry,p=g.attributes.position,idx=g.index,keep=[];const bounds=b.clone().expandByScalar(.00001);
  for(let i=0;i<(idx?.count??p.count);i+=2){const a=new T.Vector3().fromBufferAttribute(p,idx?idx.getX(i):i),c=new T.Vector3().fromBufferAttribute(p,idx?idx.getX(i+1):i+1);if(bounds.containsPoint(a.clone().applyMatrix4(edges.matrixWorld))&&bounds.containsPoint(c.clone().applyMatrix4(edges.matrixWorld)))continue;keep.push(...a.toArray(),...c.toArray());}
  edges.geometry=new T.BufferGeometry();edges.geometry.setAttribute('position',new T.Float32BufferAttribute(keep,3));
 }
 const group=new T.Group();group.name='坐便器重新建模｜420×340×440外包候选';group.position.set(2.555951,.711,-.709019);group.rotation.y=-Math.PI/2;
 group.userData={zone:'wet',candidate:true,manufacturerModelConfirmed:false};
 const white=new T.MeshStandardMaterial({color:'#f4f1e7',roughness:.24});const seatMat=new T.MeshStandardMaterial({color:'#e5e4db',roughness:.36});const dark=new T.MeshStandardMaterial({color:'#767c76',metalness:.35,roughness:.4});
 const mesh=(name,geo,mat,pos,parent=group)=>{let m=new T.Mesh(geo,mat);m.name=name;m.position.set(...pos);parent.add(m);return m;};
 mesh('圆角下部壳体',new RoundedBoxGeometry(.30,.18,.365,5,.034),white,[0,.09,.015]);
 mesh('底部安装裙边｜固定孔待选型',new RoundedBoxGeometry(.324,.026,.39,5,.012),seatMat,[0,.013,.005]);
 mesh('后部铰链承台',new RoundedBoxGeometry(.285,.22,.08,4,.015),white,[0,.27,-.158]);
 const points=[[0,.19],[.05,.192],[.085,.22],[.115,.29],[.137,.369],[.145,.382],[.155,.385],[.162,.375],[.15,.33],[.118,.24],[.10,.155],[0,.155]].map(p=>new T.Vector2(...p));
 const bowl=mesh('内凹便盆与圆润外壳',new T.LatheGeometry(points,64),white,[0,.016,.013]);bowl.scale.z=1.15;
 const ring=new T.Shape();ring.absellipse(0,0,.167,.19,0,Math.PI*2,false,0);const hole=new T.Path();hole.absellipse(0,.006,.111,.137,0,Math.PI*2,true,0);ring.holes.push(hole);
 const seat=mesh('椭圆座圈｜贯通开口',new T.ExtrudeGeometry(ring,{depth:.016,bevelEnabled:true,bevelSize:.002,bevelThickness:.002,bevelSegments:3,curveSegments:48}),seatMat,[0,.403,.008]);seat.rotation.x=-Math.PI/2;
 const pivot=new T.Group();pivot.name='便盖铰轴候选';pivot.position.set(0,.427,-.175);group.add(pivot);
 const lidShape=new T.Shape();lidShape.absellipse(0,0,.168,.195,0,Math.PI*2,false,0);
 const lid=mesh('圆润便盖',new T.ExtrudeGeometry(lidShape,{depth:.009,bevelEnabled:true,bevelSize:.002,bevelThickness:.002,bevelSegments:3,curveSegments:48}),white,[0,0,.18],pivot);lid.rotation.x=-Math.PI/2;
 for(const x of [-.09,.09]){const h=mesh('便盖铰链外形占位',new T.CylinderGeometry(.008,.008,.04,20),dark,[x,.416,-.175]);h.rotation.z=Math.PI/2;}
 model.add(group);
 return {group,setOpen(open){pivot.rotation.x=open?-Math.PI/2:0;group.updateMatrixWorld(true);}};
}
