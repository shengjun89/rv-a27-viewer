import test from 'node:test';import assert from 'node:assert/strict';import * as T from 'three';import {createRenderLayers} from '../src/render-layers.js';
test('出图层默认关闭；分区和电路模式不能泄露或丢失显隐选择',()=>{
 const root=new T.Group();for(const layer of ['cockpit','roof']){const o=new T.Mesh(new T.BoxGeometry(),new T.MeshStandardMaterial({opacity:layer==='cockpit'?.22:1,transparent:layer==='cockpit'}));o.userData.renderLayer=layer;root.add(o);}
 const c=createRenderLayers(root);assert.equal(c.visibleMeshes,0);
 c.set('cockpit',true);assert.equal(c.visibleMeshes,1);assert.equal(root.children[1].visible,false);
 c.ghost(true);assert.equal(root.children[0].material.opacity,.04);assert.equal(root.children[1].visible,false);
 c.isolate('office');assert.equal(c.visibleMeshes,0);c.set('roof',true);assert.equal(c.visibleMeshes,0);
 c.isolate(null);assert.equal(c.visibleMeshes,2);c.ghost(false);assert.equal(root.children[0].material.opacity,.22);
 c.set('cockpit',false);c.isolate('vehicle');assert.equal(c.visibleMeshes,1);c.isolate('sleep');c.isolate(null);assert.equal(root.children[0].visible,false);assert.equal(root.children[1].visible,true);
});

test('实际出图资产保持米制坐标与43材质组，加载时全部隐藏',async()=>{
 const {readFileSync}=await import('node:fs');const {GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');const b=readFileSync(new URL('../public/render-details.glb',import.meta.url));const root=(await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'')).scene;
 const meshes=[];root.traverse(o=>{if(o.isMesh)meshes.push(o);});assert.equal(meshes.length,43);
 const layers=createRenderLayers(root);assert.equal(layers.visibleMeshes,0);layers.set('cockpit',true);
 const box=new T.Box3();for(const o of meshes.filter(o=>o.visible))box.union(new T.Box3().setFromObject(o));assert.ok(box.min.x < -2 && box.max.x < -.30,'驾驶舱在前方，不能错用毫米或落到家具区');assert.ok(box.max.y<2.5&&box.min.y>.3,'竖向坐标使用glTF的Y轴');layers.set('roof',true);assert.equal(layers.visibleMeshes,43);
});
