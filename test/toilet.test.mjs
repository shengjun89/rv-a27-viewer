import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import * as T from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';import {replaceToilet,toiletBounds} from '../src/toilet.js';
test('坐便器闭合外形保留原包络，便盖开合复位且其他部件不移动',async()=>{
 const d=fs.readFileSync(new URL('../public/rv-a27.glb',import.meta.url));const m=(await new GLTFLoader().parseAsync(d.buffer.slice(d.byteOffset,d.byteOffset+d.byteLength),'')).scene;m.updateMatrixWorld(true);
 const prior=new Map();m.traverse(o=>{if(o.isMesh&&o.name!=='wet_1')prior.set(o,o.matrixWorld.clone());});
 const wc=replaceToilet(m);m.updateMatrixWorld(true);assert.equal(m.getObjectByName('wet_1'),undefined);
 const limit=new T.Box3(new T.Vector3(...toiletBounds.min),new T.Vector3(...toiletBounds.max)).expandByScalar(.001);
 const shut=new T.Box3().setFromObject(wc.group);assert.ok(limit.containsBox(shut),JSON.stringify(shut));wc.setOpen(true);const opened=new T.Box3().setFromObject(wc.group);assert.ok(opened.max.y>shut.max.y+.3);wc.setOpen(false);assert.ok(shut.equals(new T.Box3().setFromObject(wc.group)));
 m.updateMatrixWorld(true);for(const [o,matrix]of prior)assert.ok(o.matrixWorld.equals(matrix));
});
