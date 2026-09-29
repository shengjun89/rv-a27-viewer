import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {prepareTrack,sampleTransform,cycleProgress} from '../src/cad-motion.js';
const data=JSON.parse(fs.readFileSync(new URL('../public/motion-data.json', import.meta.url)));
const checks=JSON.parse(fs.readFileSync(new URL('./fixtures/cad-checks.json', import.meta.url)));
const info=JSON.parse(fs.readFileSync(new URL('../public/model-info.json',import.meta.url)));
assert.equal(info.version,'A27 R7');assert.equal(info.actions.length,15);
assert.equal(data.modelHash,info.modelHash);
for(const id of ['AP_WasherSwing','AP_FridgeSwing','WD_LeftDoor']){
 assert.equal(data.actions[id].interaction,'door');
 assert.ok(Object.keys(data.actions[id].tracks).length>=1);
}
assert.ok(!data.actions.SS_ED_Middle);
assert.deepEqual(info.batteryBoundsMm,[2055,-793.1,745,2700,-610.9,1009]);
let hingeError=0;
for(const sample of checks.hinges){
 assert.ok(Math.abs(sample.hinge.degrees)<=110,`${sample.action}: hinge takes the short arc`);
 const track=prepareTrack(data.actions[sample.action].tracks[sample.object]);
 for(const frame of sample.samples){
  const object=new THREE.Object3D();sampleTransform(track, frame.progress,object);object.updateMatrix();
  const error=Math.max(...object.matrix.elements.map((v,i)=>Math.abs(v-frame.matrix[i])));
  hingeError=Math.max(error,hingeError);
  assert.ok(error<2e-6,`${sample.action}/${sample.object} hinge error ${error}`);
 }
 const inverse=new THREE.Matrix4().fromArray(sample.baseMatrix).invert();
 const localHinge=new THREE.Vector3(...sample.hinge.pivot).applyMatrix4(inverse);
 for(const p of [12.345,37.1,73.91]){
  const object=new THREE.Object3D();sampleTransform(track,p,object);object.updateMatrix();
  assert.ok(localHinge.clone().applyMatrix4(object.matrix).distanceTo(new THREE.Vector3(...sample.hinge.pivot))<1e-9);
 }
}
const ladder=checks.cadSamples.upright_ladder;
for(const {progress,controls} of ladder){
 const c=controls.TL_Control;
 if(progress<=25) assert.ok(Math.abs(c.Tilt+38.6598082540901)<1e-7);
 if(progress<=70) assert.equal(c.SideTravel,0);
 if(progress>=65) assert.equal(c.Tilt,0);
 if(progress<95) assert.equal(c.PocketDoorOpen,1);
 if(progress>=95) assert.equal(c.SideTravel,344);
}
const living=checks.cadSamples.living;
for(const {progress,controls} of living){
 if(progress>=15) assert.equal(controls.KT_Moving.PullOut,0);
 if(progress<=15) assert.equal(controls.CC_Control.ChairY,-80);
 if(progress>=30) assert.equal(controls.CC_Control.ChairY,-600);
 if(progress<=36) assert.equal(controls.S27_Params.Travel,0);
}
for(const baseline of [0,100]){
 assert.equal(cycleProgress(0,baseline),baseline);
 assert.equal(cycleProgress(.5,baseline),100-baseline);
 assert.equal(cycleProgress(1,baseline),baseline);
}
console.log(JSON.stringify({passed:true,hingeTests:checks.hinges.length,hingeMaxMatrixError:hingeError,ladderStageSamples:ladder.length,livingStageSamples:living.length},null,2));
