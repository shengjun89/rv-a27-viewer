import * as T from 'three';
const zones={structure:'车壳 · 地板 · 窗框',cab:'驾驶舱',office:'工作台 · 书酒柜固定件',wet:'厨房 · 卫浴固定件',sofa:'沙发 · 电池舱',overhead:'吊柜箱体',cabover_reference:'额头床外壳',cabinet:'入口衣柜',ladder:'收纳梯'};
export function buildParts(roots,actions=[]){
 const groups=new Map(),byObject=new Map();
 const labels=Object.fromEntries(actions.map(a=>[a.id,a.label]));
 for(const root of roots)root.traverse(o=>{
  if(!o.isMesh&&!o.isLine)return;
  let p=o,meta={};while(p){meta={...p.userData,...meta};p=p.parent;}
  const chain=[];p=o;while(p){chain.push(p.name);p=p.parent;}
  const name=chain.join('/');let key,label;
  if(name.includes('坐便器重新建模')){key='toilet';label='坐便器';}
  else if(name.includes('沙发底充逆')){key='inverter';label='充逆变一体机';}
  else if(name.includes('独立LCD')){key='remote';label='独立操作面板';}
  else if(/^CC_/.test(o.name)){key='chair';label='办公椅';}
  else if(/^KT_/.test(o.name)){key='midi';label='MIDI键盘 · 琴托';}
  else if(/^S27_|^SB_/.test(o.name)){key='sofa';label='沙发 · 电池舱';}
  else {const motion=Object.keys(meta.motions||{})[0];if(motion){key=motion;label=labels[motion]||motion;}else{key=meta.zone||'other';label=zones[key]||'其他固定件';}}
  if(!groups.has(key))groups.set(key,{id:key,label,objects:[]});groups.get(key).objects.push(o);byObject.set(o,key);
 });
 return {groups:[...groups.values()],byObject};
}
export function createIsolation(parts){
 let active=null;const saved=new Map();
 return {get active(){return active;},restore(){for(const[o,v]of saved)o.visible=v;saved.clear();active=null;},toggle(id){const same=active===id;this.restore();if(same)return;for(const g of parts.groups)for(const o of g.objects){saved.set(o,o.visible);o.visible=g.id===id&&o.visible;}active=id;}};
}
export function thumbnail(part,renderer){
 const s=new T.Scene();s.background=new T.Color('#eeeae0');const g=new T.Group();s.add(g);
 for(const o of part.objects){if(!o.isMesh||!o.visible)continue;const copy=new T.Mesh(o.geometry,o.material);o.updateWorldMatrix(true,false);copy.matrixAutoUpdate=false;copy.matrix.copy(o.matrixWorld);g.add(copy);}
 const box=new T.Box3().setFromObject(g);if(box.isEmpty())return '';
 const center=box.getCenter(new T.Vector3()),size=box.getSize(new T.Vector3()).length();
 const c=new T.PerspectiveCamera(35,1,.001,100);c.position.copy(center).add(new T.Vector3(1,.75,1).normalize().multiplyScalar(size*1.8));c.lookAt(center);
 s.add(new T.HemisphereLight(0xfff9ed,0x7f8b7f,2));const light=new T.DirectionalLight(0xffffff,2);light.position.set(2,6,4);s.add(light);renderer.render(s,c);return renderer.domElement.toDataURL();
}
