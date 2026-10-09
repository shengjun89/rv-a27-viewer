import * as THREE from 'three';

// User product drawing: width includes mounting flanges. No hole sizes or service clearances supplied.
export const inverterPlacement = {
  center:[.79,1.18,-.80], size:[.2876,.4317,.1155],
  bodyWidth:.273, status:'商品图外形287.6×431.7×115.5mm；安装位置与散热待核',
};
export function createInverter() {
  const group=new THREE.Group();group.name='壁挂充逆变一体机｜商品图外形';group.position.set(...inverterPlacement.center);group.rotation.y=-Math.PI/2;
  group.userData={candidate:true,dimensionsMm:[287.6,431.7,115.5],installationApproved:false};
  const shell=new THREE.MeshStandardMaterial({color:'#343838',metalness:.4,roughness:.55});
  const dark=new THREE.MeshStandardMaterial({color:'#151c1b',metalness:.15,roughness:.65});
  const mount=new THREE.MeshStandardMaterial({color:'#777b73',metalness:.45,roughness:.6});
  function box(name,size,pos,mat=shell){const mesh=new THREE.Mesh(new THREE.BoxGeometry(...size),mat);mesh.name=name;mesh.position.set(...pos);group.add(mesh);return mesh;}
  box('机身273宽×431.7高×115.5深',[.273,.4317,.1155],[0,0,0]);
  for(const x of [-.14015,.14015])box('壁挂安装边｜孔径待核',[.0073,.4317,.006],[x,0,-.05475],dark);
  box('前面板',[.267,.424,.001],[0,0,.05725]);
  box('控制显示器面框',[.082,.069,.001],[0,-.071,.0574],dark);
  box('LCD显示窗口占位',[.061,.025,.0006],[0,-.055,.05765],new THREE.MeshBasicMaterial({color:'#729e86'}));
  for(let i=0;i<4;i++){
    const key=new THREE.Mesh(new THREE.CylinderGeometry(.0035,.0035,.0005,12),mount);
    key.name='控制键外形占位';key.rotation.x=Math.PI/2;key.position.set(-.0195+i*.013,-.087,.0577);group.add(key);
  }
  box('下部接线盖分缝',[.248,.0018,.0004],[0,-.159,.0577],dark);
  // Side grille is a visual reference, not a verified airflow or aperture specification.
  for(const x of [-.1365,.1365])for(let row=0;row<12;row++)for(let col=0;col<5;col++){
    const hole=new THREE.Mesh(new THREE.CircleGeometry(.0019,6),new THREE.MeshBasicMaterial({color:'#101717',side:THREE.DoubleSide}));
    hole.name='侧下部散热孔外形参考';hole.rotation.y=Math.PI/2;hole.position.set(x,-.19+row*.006,-.022+col*.009);group.add(hole);
  }
  // Separate installation candidate, not supplied appliance hardware or an approved anchorage.
  box('独立背衬安装面候选｜锚固待设计',[.35,.50,.006],[0,0,-.066],mount);
  for(const x of [-.139,.139])for(const y of [-.185,0,.185])box('370与185节距标记｜非钻孔',[.003,.008,.001],[x,y,-.0583],dark);
  return group;
}

export const remotePanelPlacement={center:[-.15,1.67,.870],size:[.20,.11,.025],status:'独立操作面板：200×110×25mm展示占位，尺寸待核'};
export function createRemotePanel() {
  const group=new THREE.Group();group.name='独立LCD操作面板｜尺寸待核';group.position.set(...remotePanelPlacement.center);group.rotation.y=Math.PI;
  group.userData={candidate:true,dimensionsConfirmed:false,displayOnly:true};
  const dark=new THREE.MeshStandardMaterial({color:'#272d2e',roughness:.58});
  function box(name,size,pos,color){const m=new THREE.Mesh(new THREE.BoxGeometry(...size),new THREE.MeshStandardMaterial({color,roughness:.55}));m.name=name;m.position.set(...pos);group.add(m);return m;}
  box('200×110×25外形占位',remotePanelPlacement.size,[0,0,0],'#272d2e');
  box('浅色面框',[.169,.102,.001],[0,0,.0126],'#e5e6df');
  box('LCD屏幕',[.09,.046,.001],[0,.007,.0133],'#183d40');
  for(const x of [-.043,-.015,.013,.041]){
    const key=new THREE.Mesh(new THREE.CylinderGeometry(.009,.009,.001,20),new THREE.MeshStandardMaterial({color:'#eeeae1'}));key.rotation.x=Math.PI/2;key.position.set(x,-.034,.014);key.name='取消/向上/向下/确认按键外形';group.add(key);
  }
  for(const [y,color]of [[.02,'#67a97c'],[.004,'#aeaa65'],[-.012,'#a77064']]){
    const led=new THREE.Mesh(new THREE.CircleGeometry(.0023,12),new THREE.MeshBasicMaterial({color}));led.name='状态灯外形｜非实时数据';led.position.set(-.065,y,.014);group.add(led);
  }
  const power=new THREE.Mesh(new THREE.CircleGeometry(.006,16),dark);power.position.set(.066,0,.014);group.add(power);
  for(const x of [-.091,.091])for(const y of [-.041,.041]){const screw=new THREE.Mesh(new THREE.CircleGeometry(.0027,12),new THREE.MeshStandardMaterial({color:'#9c9e98'}));screw.position.set(x,y,.0128);group.add(screw);}
  box('面板接线头占位',[.012,.01,.009],[0,-.059,-.002],'#beb8aa');
  box('安装垫片候选｜固定点待核',[.18,.085,.006],[0,0,-.016],'#81857b');
  if (typeof document !== 'undefined') {
    const canvas=document.createElement('canvas');canvas.width=850;canvas.height=550;
    const ctx=canvas.getContext('2d');ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillStyle='#86c4b7';ctx.font='28px sans-serif';ctx.fillText('示意 · 未连接',425,236);
    ctx.fillStyle='#333a37';ctx.font='22px sans-serif';
    ['取消','向上','向下','确认'].forEach((text,i)=>ctx.fillText(text,425+(-.043+i*.028)/.17*850,445));
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
    const legends=new THREE.Mesh(new THREE.PlaneGeometry(.17,.11),new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false}));legends.name='面板标识｜展示未连接';legends.position.z=.015;group.add(legends);
  }
  return group;
}
