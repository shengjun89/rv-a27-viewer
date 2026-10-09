import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as T from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createCADMotion } from '../src/cad-motion.js';
import { createInverter, createRemotePanel, inverterPlacement } from '../src/inverter.js';

test('商品图竖向机壳、背衬及独立面板在当前模型和离散动作中无三角面相交', async()=>{
 const d=fs.readFileSync(new URL('../public/rv-a27.glb',import.meta.url));
 const model=(await new GLTFLoader().parseAsync(d.buffer.slice(d.byteOffset,d.byteOffset+d.byteLength),'')).scene;
 model.traverse(o=>{o.userData={...o.parent?.userData,...o.userData};});
 const motion=createCADMotion(model,JSON.parse(fs.readFileSync(new URL('../public/motion-data.json',import.meta.url))));
 const device=createInverter();device.updateMatrixWorld(true);
 const remote=createRemotePanel();remote.updateMatrixWorld(true);
 const boxes=[device,remote].map(o=>new T.Box3().setFromObject(o));
 assert.deepEqual(inverterPlacement.size,[.2876,.4317,.1155]);
 const shapes=[];model.traverse(o=>{if(o.isMesh)shapes.push(o);});
 let samples=0;
 for(const action of motion.actions.keys())for(const progress of [0,25,50,75,100]){
  motion.resetAll();motion.apply(action,progress);model.updateMatrixWorld(true);
  for(const box of boxes) for(const o of shapes){
   if(!box.intersectsBox(new T.Box3().setFromObject(o)))continue;
   const p=o.geometry.attributes.position,idx=o.geometry.index;
   for(let i=0;i<(idx?.count??p.count);i+=3){
    const v=[0,1,2].map(j=>new T.Vector3().fromBufferAttribute(p,idx?idx.getX(i+j):i+j).applyMatrix4(o.matrixWorld));
    assert.equal(box.intersectsTriangle(new T.Triangle(...v)),false,`${action}/${progress}/${o.name}`);
   }
  }
  samples++;
 }
 console.log(`一体机、背衬及操作面板外包：${samples}个离散动作状态三角面筛查；不代表实体包含、连续扫掠、人体或安装验收。`);
});
