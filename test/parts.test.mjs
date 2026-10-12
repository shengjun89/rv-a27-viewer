import test from 'node:test';import assert from 'node:assert/strict';import * as T from 'three';import {buildParts,createIsolation} from '../src/parts.js';
test('部件目录覆盖所有绘制对象，单独显示后恢复原隐藏状态',()=>{const model=new T.Group();const a=new T.Mesh(),b=new T.Mesh(),c=new T.Line();a.userData.zone='sofa';b.userData.zone='wet';c.userData.zone='sofa';c.visible=false;model.add(a,b,c);const p=buildParts([model]);assert.equal(p.byObject.size,3);const i=createIsolation(p);i.toggle('sleep');assert.ok(a.visible);assert.equal(b.visible,false);assert.equal(c.visible,false);i.toggle('wet');assert.ok(b.visible);assert.equal(a.visible,false);i.toggle('wet');assert.ok(a.visible&&b.visible);assert.equal(c.visible,false);});

test('功能分组把柜体柜门、办公家具和新增设备归入完整产品功能',()=>{
 const model=new T.Group();
 const add=(name,zone,motion)=>{const o=new T.Mesh();o.name=name;o.userData={zone,...(motion?{motions:{[motion]:{}}}:{})};model.add(o);return o;};
 const cabinet=add('body','overhead'),door=add('door','overhead','OH_L01');
 const desk=add('table','office'),chair=add('CC_Seat','office','living'),keys=add('KT_Keys','office','living');
 const sofa=add('S27_Frame','sofa','living'),ladder=add('step','ladder','upright_ladder');
 const toilet=add('坐便器重新建模','wet'),fridge=add('fridge','wet','AP_FridgeSwing');
 const inverter=add('沙发底充逆主机'),remote=add('独立LCD'),shell=add('shell','structure');
 const p=buildParts([model]);assert.equal(p.groups.length,7);assert.equal(p.byObject.size,12);
 for(const [objects,id]of [[[cabinet,door],'storage'],[[desk,chair,keys],'office'],[[sofa],'sleep'],[[ladder],'access'],[[toilet,fridge],'wet'],[[inverter,remote],'power'],[[shell],'vehicle']])for(const o of objects)assert.equal(p.byObject.get(o),id);
 const isolation=createIsolation(p);isolation.toggle('storage');assert.ok(cabinet.visible&&door.visible);assert.equal(desk.visible,false);isolation.toggle('storage');assert.ok(model.children.every(o=>o.visible));
});
