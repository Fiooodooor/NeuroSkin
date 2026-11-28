const assert=require('node:assert/strict'),P=require('../static/fem_previews.js');
const packet={vertices_mm:[[0,0,0],[1,0,0],[0,1,0]],faces:[[0,1,2]],cases:{}};
for(const [i,name] of P.order.entries())packet.cases[name]={displacement_mm:[[0,0,-i],[0,0,0],[0,0,0]],stress_vm_MPa:[i,i+1,i+2],principal_strain:[-i,0,i]};
let range=P.bounds(packet,'stress_vm_MPa',2);assert.equal(range.cmin,0);assert.equal(range.cmax,5);
const t=P.traces(packet,'torsion_z','stress_vm_MPa',2,true,range);assert.equal(t.length,2);assert.equal(t[1].z[0],-6);assert.equal(t[1].cmax,5);assert(range.ranges[2][0]<-6);
range=P.bounds(packet,'principal_strain',1);assert.equal(range.cmin,-3);assert.equal(range.cmax,3);
assert.equal(P.bounds(packet,'displacement_mm',1).cmax,3);
console.log('FEM shared scale tests passed');
