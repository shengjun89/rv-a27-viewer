import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import { flowDirections, createFlowTrail } from '../src/electrical-flow.js';
test('互锁输入、充放电反向和保护线静态',()=>{
 assert.deepEqual(flowDirections('battery').slice(1,8),[1,-1,1,0,0,0,1]);
 assert.deepEqual(flowDirections('shore').slice(1,8),[-1,1,1,1,0,1,1]);
 assert.deepEqual(flowDirections('charger').slice(4,7),[0,1,1]);
 assert.ok(flowDirections('shore').slice(13).every(x=>x===0));
});
test('蚂蚁线随时间移动、反向箭头、关闭无可见粒子',()=>{
 const trail=createFlowTrail([new T.Vector3(),new T.Vector3(1,0,0),new T.Vector3(1,0,1)]);
 trail.update(0,1);const a=trail.children[0].position.clone();
 trail.update(.2,1);assert.ok(trail.children[0].position.distanceTo(a)>0);
 trail.update(0,-1);const dir=new T.Vector3(0,1,0).applyQuaternion(trail.children[0].quaternion);assert.ok(dir.x<0);
 trail.update(0,0);assert.equal(trail.visible,false);
});
