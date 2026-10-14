import { MathUtils } from 'three';
// The new rigid door replaces the old roller-door action without touching other timelines.
export function installBathDoor(model, doorScene, cadMotion) {
 const pivot=doorScene.getObjectByName('IB_LeafPivot');
 if(!pivot)throw new Error('工业风门缺少铰轴');
 doorScene.name='工业风磨砂卫浴门｜安装候选';
 doorScene.userData.zone='wet';
 doorScene.traverse(o=>{if(o.isMesh){o.userData.zone='wet';o.userData.actionId='bath';}});
 model.add(doorScene);
 const originalApply=cadMotion.apply.bind(cadMotion);
 const apply=(id,progress)=>{
  if(id==='bath'){pivot.rotation.y=MathUtils.degToRad(90*MathUtils.clamp(progress,0,100)/100);pivot.updateMatrixWorld(true);}
  else originalApply(id,progress);
 };
 cadMotion.apply=apply;
 cadMotion.reset=id=>apply(id,id==='bath'?0:cadMotion.actions.get(id).baselineProgress);
 cadMotion.resetAll=()=>{for(const id of cadMotion.actions.keys())cadMotion.reset(id);};
 apply('bath',0);
 return {pivot,scene:doorScene,get angle(){return MathUtils.radToDeg(pivot.rotation.y);}};
}
