import * as THREE from 'three';

// Order follows electrical.js paths. AC arrows indicate net energy, not instantaneous current.
export function flowDirections(mode='battery') {
  const charging=mode==='shore'||mode==='charger';
  return [2,charging?-1:1,charging?1:-1,1,mode==='shore'?1:0,mode==='charger'?1:0,charging?1:0,1,1,1,1,1,1,0,0];
}

export function createFlowTrail(points) {
  const group=new THREE.Group();
  const segments=[];let length=0;
  for(let i=1;i<points.length;i++) {
    const delta=points[i].clone().sub(points[i-1]), size=delta.length();
    if(size<1e-8)continue;
    segments.push({start:points[i-1],direction:delta.divideScalar(size),offset:length,size});length+=size;
  }
  const material=new THREE.MeshBasicMaterial({color:0xfff9dc,depthTest:true});
  const shaft=new THREE.CylinderGeometry(.004,.004,.024,6);
  const tip=new THREE.ConeGeometry(.008,.018,8);
  const count=Math.max(1,Math.floor(length/.22));
  for(let i=0;i<count;i++) {
    const marker=new THREE.Group();
    marker.add(new THREE.Mesh(shaft,material));
    const arrow=new THREE.Mesh(tip,material);arrow.position.y=.02;marker.add(arrow);group.add(marker);
  }
  group.update=(seconds,direction)=>{
    group.visible=direction!==0 && length>0;
    if(!group.visible)return;
    group.children.forEach((marker,i)=>{
      // Communication is illustrative bidirectional traffic, on alternating markers.
      const sign=direction===2?(i%2?-1:1):direction;
      const distance=((i+.5)*length/count+seconds*.22*sign)%length;
      const d=(distance+length)%length;
      const s=segments.find(s=>d<s.offset+s.size)||segments.at(-1);
      marker.position.copy(s.start).addScaledVector(s.direction,d-s.offset);
      marker.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),s.direction.clone().multiplyScalar(sign));
    });
  };
  return group;
}
