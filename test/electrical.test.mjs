import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createGhostMode } from '../src/electrical.js';

test('电路开关对共享、多材质和参考线设4%，重复开启不丢失原状态，关闭完全恢复', () => {
  const root = new THREE.Group();
  const a = new THREE.MeshStandardMaterial({opacity: .65, transparent: true, depthWrite: false});
  const b = new THREE.MeshStandardMaterial();
  const x = new THREE.Mesh(new THREE.BoxGeometry(), [a,b]);
  const y = new THREE.Mesh(new THREE.BoxGeometry(), b); y.visible = false;
  const line = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({opacity: .3, transparent:true}));
  root.add(x,y,line);
  const toggle = createGhostMode(root);
  toggle(true); toggle(true);
  for (const mat of [a,b,line.material]) { assert.equal(mat.opacity,.04); assert.equal(mat.depthWrite,false); }
  assert.equal(y.visible,false);
  toggle(false); toggle(false);
  assert.equal(a.opacity,.65); assert.equal(a.depthWrite,false);
  assert.equal(b.opacity,1); assert.equal(b.transparent,false); assert.equal(b.depthWrite,true);
  assert.equal(line.material.opacity,.3); assert.equal(y.visible,false);
});
