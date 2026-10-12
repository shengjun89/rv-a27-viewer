import * as T from 'three';
const functions=[
 {id:'office',label:'办公与音乐',description:'工作台、办公椅、琴托与书酒柜'},
 {id:'sleep',label:'休息与睡眠',description:'沙发成床、床架与额头床'},
 {id:'wet',label:'厨卫与洗衣',description:'厨房、冰箱、卫浴与洗衣机'},
 {id:'storage',label:'储物收纳',description:'吊柜、入口衣柜与配套柜门'},
 {id:'access',label:'上床通行',description:'藏梯、踏步与配套机构'},
 {id:'power',label:'生活用电',description:'充逆变一体机与独立操作面板'},
 {id:'vehicle',label:'车体与驾驶',description:'驾驶舱、车壳、地板与窗框'},
];
const zoneFunctions={office:'office',sofa:'sleep',cabover_reference:'sleep',wet:'wet',overhead:'storage',cabinet:'storage',ladder:'access',structure:'vehicle',cab:'vehicle'};
export function buildParts(roots){
 const groups=new Map(functions.map(f=>[f.id,{...f,objects:[]}])),byObject=new Map();
 for(const root of roots)root.traverse(o=>{
  if(!o.isMesh&&!o.isLine)return;
  let p=o,meta={};const chain=[];
  while(p){meta={...p.userData,...meta};chain.push(p.name);p=p.parent;}
  const name=chain.join('/'),motions=Object.keys(meta.motions||{});let key;
  if(/沙发底充逆|独立LCD/.test(name))key='power';
  else if(name.includes('坐便器重新建模'))key='wet';
  else if(/^CC_|^KT_/.test(o.name))key='office';
  else if(/^S27_|^SB_/.test(o.name))key='sleep';
  else if(motions.some(m=>m==='upright_ladder'))key='access';
  else if(motions.some(m=>/^(OH_|SS_OH_|SS_ED_)/.test(m)))key='storage';
  else if(motions.some(m=>/^(bath$|AP_|WD_)/.test(m)))key='wet';
  else key=zoneFunctions[meta.zone]||'vehicle';
  groups.get(key).objects.push(o);byObject.set(o,key);
 });
 return {groups:[...groups.values()].filter(g=>g.objects.length),byObject};
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
