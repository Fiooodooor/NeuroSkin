const assert=require('node:assert/strict'),P=require('../static/fem_previews.js');
const packet={vertices_mm:[[0,0,0],[1,0,0],[0,1,0]],faces:[[0,1,2]],cases:{}};
for(const [i,name] of P.order.entries())packet.cases[name]={displacement_mm:[[0,0,-i],[0,0,0],[0,0,0]],stress_vm_MPa:[i,i+1,i+2],principal_strain:[-i,0,i]};
let range=P.bounds(packet,'stress_vm_MPa',2);assert.equal(range.cmin,0);assert.equal(range.cmax,5);
const t=P.traces(packet,'torsion_z','stress_vm_MPa',2,true,range);assert.equal(t.length,2);assert.equal(t[1].z[0],-6);assert.equal(t[1].cmax,5);assert(range.ranges[2][0]<-6);
range=P.bounds(packet,'principal_strain',1);assert.equal(range.cmin,-3);assert.equal(range.cmax,3);
assert.equal(P.bounds(packet,'displacement_mm',1).cmax,3);
console.log('FEM shared scale tests passed');

packet.cases.press_center.boundary_vectors={applied:{groups:[{position_mm:[0,0,0],force_N:[0,0,-.1],couple_Nmm:[0,0,0]}]},reaction:{groups:[{position_mm:[1,0,0],force_N:[0,0,.1],couple_Nmm:[0,0,0]}]}};
const scale=P.forceScale(packet);assert(scale>0);
const forces=P.boundaryTraces(packet.cases.press_center,scale);assert.equal(forces.length,4);assert(forces[0].z[1]<forces[0].z[0]&&forces[2].z[1]>0);
assert.equal(P.boundaryTraces(packet.cases.shear_x,scale).length,0);
const ext=P.extendBounds(P.bounds(packet,'stress_vm_MPa',1),packet,scale);assert(ext.ranges[2][1]>=forces[2].z[1]);

packet.cases.press_center.boundary_vectors.substrate_sections=[{groups:[{position_mm:[0,0,1],force_N:[0,0,.2],couple_Nmm:[0,0,0]}]}];
assert(P.forceScale(packet,false,true)>0);
assert.equal(P.boundaryTraces(packet.cases.press_center,scale,false,true)[0].name,'section 1 boundary force');
