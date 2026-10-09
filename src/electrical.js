import * as THREE from 'three';

// Snapshot each shared material once. Never change geometry, poses or visibility.
export function createGhostMode(model) {
  const saved = new Map();
  let enabled = false;
  return (next) => {
    if (next === enabled) return;
    enabled = next;
    if (next) {
      model.traverse((object) => {
        if (!object.material) return;
        for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
          if (saved.has(material)) continue;
          saved.set(material, { opacity: material.opacity, transparent: material.transparent, depthWrite: material.depthWrite });
          Object.assign(material, { opacity: .04, transparent: true, depthWrite: false, needsUpdate: true });
        }
      });
    } else {
      for (const [material, original] of saved) Object.assign(material, original, { needsUpdate: true });
      saved.clear();
    }
  };
}

export const circuitNodes = [
  {id:'B', name:'48V · 8kWh 电池', p:[2.3775,.877,.702], color:0xc74d45},
  {id:'F', name:'近电池熔断 / 隔离', p:[2.04,.89,.77], color:0xc74d45},
  {id:'I', name:'充逆变一体机', p:[1.73,.97,.77], color:0xc74d45},
  {id:'A', name:'220V 配电', p:[1.38,1.18,.80], color:0xc38220},
  {id:'D', name:'48→12V / 直流配电', p:[1.38,.85,.80], color:0x167caa},
  {id:'S', name:'岸电入口', p:[2.64,.80,.94], color:0xc38220},
  {id:'Q', name:'取电器 · 220V输出', p:[2.68,.53,1.12], color:0xc38220},
  {id:'T', name:'双源互锁 / 输入保护', p:[2.17,.72,.91], color:0xc38220},
  {id:'K', name:'厨房插座', p:[-.10,1.45,-.80], color:0xc38220},
  {id:'W', name:'洗衣机支路', p:[1.39,1.02,-.77], color:0xc38220},
  {id:'O', name:'办公插座', p:[.24,1.25,.75], color:0xc38220},
  {id:'R', name:'冰箱支路 · 电压待核', p:[-.08,1.02,-.78], color:0x167caa},
  {id:'L', name:'灯 / 风扇 / 水泵', p:[.90,2.28,.79], color:0x167caa},
  {id:'E', name:'PE 排 / 车体连接', p:[1.78,.73,.79], color:0x518346},
];
const paths = [
  ['dc48', ['B','F','I']],
  ['return', [[2.3775,.83,.66],[2.04,.83,.70],[1.73,.83,.70],[1.73,.94,.70]]],
  ['dc48', ['F',[1.96,.78,.77],[1.38,.78,.80],'D']],
  ['ac', ['S',[2.50,.75,.94],'T']],
  ['ac', ['Q',[2.47,.53,1.02],[2.17,.53,1.02],'T']],
  ['ac', ['T',[1.73,.72,.91],'I']],
  ['ac', ['I',[1.60,1.18,.80],'A']],
  ['ac', ['A',[1.20,1.18,.80],[1.20,.78,.80],[1.20,.78,-.86],[-.10,.78,-.86],'K']],
  ['ac', [[1.20,.78,-.86],[1.39,.78,-.86],'W']],
  ['ac', ['A',[.24,1.18,.80],'O']],
  ['dc12', ['D',[1.05,.73,.76],[1.05,.73,-.90],[-.08,.73,-.90],'R']],
  ['dc12', ['D',[.90,.85,.83],'L']],
  ['pe', ['S',[2.54,.70,.83],[1.78,.70,.83],'E','I']],
  ['pe', ['E',[1.38,.73,.86],'A']],
];
export const circuitColors = {dc48:0xc74d45, return:0x536575, ac:0xc38220, dc12:0x167caa, pe:0x518346};

export function createElectricalOverlay() {
  const group = new THREE.Group(); group.name = '电路布局候选'; group.visible = false;
  const locations = Object.fromEntries(circuitNodes.map(n=>[n.id,n.p]));
  for (const [kind, path] of paths) {
    const points = path.map(p=>new THREE.Vector3(...(typeof p === 'string' ? locations[p] : p)));
    for (let i=1;i<points.length;i++) {
      const delta = points[i].clone().sub(points[i-1]);
      const tube = new THREE.Mesh(new THREE.CylinderGeometry(.009,.009,delta.length(),8),new THREE.MeshBasicMaterial({color:circuitColors[kind]}));
      tube.position.copy(points[i-1]).add(points[i]).multiplyScalar(.5);
      tube.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());
      group.add(tube);
    }
  }
  for (const node of circuitNodes) {
    const sphere = new THREE.Mesh(new THREE.SphereGeometry(.032,12,8),new THREE.MeshBasicMaterial({color:node.color}));
    sphere.position.set(...node.p); group.add(sphere);
    const canvas = document.createElement('canvas'); canvas.width=128; canvas.height=80;
    const ctx=canvas.getContext('2d'); ctx.fillStyle='#fffdf5';ctx.beginPath();ctx.roundRect(4,4,120,72,18);ctx.fill();
    ctx.strokeStyle=`#${node.color.toString(16).padStart(6,'0')}`;ctx.lineWidth=5;ctx.stroke();ctx.fillStyle='#233b33';
    ctx.font='bold 44px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(node.id,64,42);
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
    const label=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false,depthWrite:false}));
    label.position.set(node.p[0],node.p[1]+.11,node.p[2]);label.scale.set(.17,.106,1);label.renderOrder=10;group.add(label);
  }
  return group;
}
