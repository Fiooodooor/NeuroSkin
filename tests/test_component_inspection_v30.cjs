const assert=require('node:assert/strict'),C=require('../static/component_inspection.js');
const model={component_tree:{nodes:[{id:'flexure:0',part:'flexure',face_start:0,face_count:1,stage:'single',member_index:0},{id:'flexure:1',part:'flexure',face_start:1,face_count:2,stage:'single',member_index:1}]}};
const traces=[{name:'flexure',i:[0,1,2],opacity:1},{name:'base',i:[0],opacity:1}];
const out=C.decorate(traces,model,'flexure:1',[[[0,0,0],[0,0,1]],[[1,0,0],[1,0,1]]],true,{flexure:'green'});
assert.deepEqual(out[0].facecolor,['green','#ffcf70','#ffcf70']);assert.equal(out[1].opacity,.25);assert.equal(out[2].name,'single structural paths (concept)');assert.equal(traces[0].facecolor,undefined);
assert.deepEqual(C.decorate(traces,model,null,[],false,{}),traces);
console.log('component spans and paths passed');
