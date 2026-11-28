const assert=require('node:assert/strict'),V=require('../static/skin_patch_visual.js');
for(const n of [3,5,7]){
  const placements=Array.from({length:n*n},(_,i)=>({id:'sensor-'+i,position_mm:[(i%n+.5)*20,(Math.floor(i/n)+.5)*20,0]}));
  const result={skin_templates:{receptor:{genome_hash:'same',rendering:'surface_mesh',components:[{part:'flexure',vertices:[[0,0,0],[1,0,0],[0,1,1]],faces:[[0,1,2]]},{part:'piezo',vertices:[[0,0,0],[1,0,0],[0,1,1]],faces:[[0,1,2]]}]}},skin_patches:[{key:'refined:design',size:n,sensor_count:n*n,side_mm:n*20,substrate_depth_mm:4,membrane_thickness_mm:.5,membrane_z_mm:6,genome_hash:'same',receptor_id:'receptor',placements}]};
  const out=V.patch(result,'refined:design');
  const flexure=out.traces.find(t=>t.name==='flexure'),positions=out.traces.find(t=>t.name==='Sensor positions');
  assert.equal(positions.x.length,n*n);assert.equal(flexure.x.length,n*n*3);assert.equal(flexure.i.length,n*n);
  assert.equal(Math.max(...flexure.k),n*n*3-1);assert.deepEqual(flexure.x.slice(0,3),[10,11,10]);
  assert.equal(positions.x.at(-1),n*20-10);assert.equal(positions.y.at(-1),n*20-10);
  assert(out.traces.some(t=>t.name==='PVDF films'));assert(out.traces.some(t=>t.name==='Nominal membrane'));
  const hidden=V.patch(result,'refined:design',{membrane:false,pvdf:false,selected:'sensor-0'});
  assert(!hidden.traces.some(t=>t.name==='PVDF films'||t.name==='Nominal membrane'));
  assert.equal(hidden.traces.find(t=>t.name==='Sensor positions').marker.size[0],7);
  result.skin_templates.receptor.genome_hash='stale';assert.throws(()=>V.patch(result,'refined:design'),/inconsistent/);
}
console.log('3D skin patch placements, mesh indices, toggles and context tests passed');
