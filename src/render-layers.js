import { Box3 } from 'three';
import { createGhostMode } from './electrical.js';
// Independent from animation and functional isolation: the user's choices survive both.
export function createRenderLayers(root) {
 const enabled={cockpit:false,exterior:false};const ghost=createGhostMode(root);
 let active=null;
 const meshes=[];root.traverse(o=>{if(o.isMesh){if(!Object.hasOwn(enabled,o.userData.renderLayer))throw new Error('Unknown render layer');meshes.push(o);}});
 const apply=()=>{for(const o of meshes)o.visible=enabled[o.userData.renderLayer]&&(!active||active==='vehicle');};
 apply();
 return {set(id,value){if(!Object.hasOwn(enabled,id))throw new Error('Unknown render layer');enabled[id]=!!value;apply();},isolate(id){active=id;apply();},ghost,expandBounds(box){for(const o of meshes)if(o.visible)box.union(new Box3().setFromObject(o));return box;},setAllHidden(){for(const id in enabled)enabled[id]=false;apply();},get state(){return {...enabled};},get visibleMeshes(){return meshes.filter(o=>o.visible).length;}};
}
