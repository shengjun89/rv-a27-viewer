import test from 'node:test';
import assert from 'node:assert/strict';
import {Group,Mesh,BoxGeometry,MeshBasicMaterial} from 'three';
import {installBathDoor} from '../src/bath-door.js';
test('rigid bathroom door opens inward, clamps, resets, and preserves other actions',()=>{
 const model=new Group(),scene=new Group(),pivot=new Group();pivot.name='IB_LeafPivot';scene.add(pivot);pivot.add(new Mesh(new BoxGeometry(),new MeshBasicMaterial()));
 const calls=[];const motion={actions:new Map([['bath',{baselineProgress:94}],['living',{baselineProgress:0}]]),apply:(id,p)=>calls.push([id,p])};
 const door=installBathDoor(model,scene,motion);
 assert.equal(door.angle,0);motion.apply('bath',100);assert.equal(door.angle,90);
 motion.apply('bath',200);assert.equal(door.angle,90);motion.apply('bath',-20);assert.equal(door.angle,0);
 motion.apply('bath',50);assert.equal(door.angle,45);motion.apply('living',30);assert.deepEqual(calls.at(-1),['living',30]);
 motion.resetAll();assert.equal(door.angle,0);assert.deepEqual(calls.at(-1),['living',0]);
});
