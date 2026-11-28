const assert=require('node:assert/strict'),P=require('../static/workspace_profiles.js');
const controls={};for(const id of P.fields)controls[id]={tagName:'SELECT',value:'a',options:[{value:'a'},{value:'b'}]};
for(const id of ['seconds','cores','searchPrecision','explore'])controls[id]={tagName:'INPUT',type:'number',value:'4',min:'0',max:'40'};
for(const id of ['physical_gate','enable_fem'])controls[id]={tagName:'INPUT',type:'checkbox',checked:true};
const get=id=>controls[id],base=P.capture(get);assert(!('seed' in base));assert.deepEqual(P.validate(base,get),base);
assert.throws(()=>P.apply({...base,cores:'80',mode:'b'},get),/Out of range/);assert.equal(get('mode').value,'a');
P.apply({...base,cores:'20',mode:'b',physical_gate:false},get);assert.equal(get('cores').value,'20');assert.equal(get('physical_gate').checked,false);
assert.throws(()=>P.validate({...base,mode:'obsolete'},get),/Unavailable/);
const store=new Map(),storage={getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v)};
let list=P.save(storage,[],'Z840',base);list=P.save(storage,list,'Z840',P.capture(get));assert.equal(list.length,1);assert.deepEqual(P.load(storage),list);
for(let i=0;i<5;i++)list=P.save(storage,list,'Profile '+i,base);assert.throws(()=>P.save(storage,list,'Too many',base),/six/);assert.equal(P.load(storage).length,6);assert.equal(P.remove(storage,list,'Z840').length,5);
console.log('evolution preset tests passed');

for(const [id,options] of Object.entries({mode:['single:all','hybrid:all'],population:['24','48'],searchStrategy:['adaptive','explore'],objective:['balanced','electronics'],fem_backend:['hex8'],fem_pitch:['0.625'],gate_grid:['3'],audit_grid:['3','5']}))controls[id]={tagName:'SELECT',value:options[0],options:options.map(value=>({value}))};
for(const [id,min,max,value] of [['seconds','3','3600','60'],['cores','1','2','1'],['searchPrecision','0','100','80'],['explore','0','100','55']])controls[id]={tagName:'INPUT',type:'number',min,max,value};
const examples=P.examples(get);assert.equal(examples.length,4);assert.equal(examples[0].values.enable_fem,false);assert.equal(examples[2].values.objective,'electronics');
for(const p of examples){assert(!('seed' in p.values));assert(Number(p.values.cores)<=2);P.validate(p.values,get);}
const stored=P.load(storage);P.apply(examples[0].values,get);assert.deepEqual(P.load(storage),stored);assert.equal(get('seconds').value,'15');
console.log('example preset hardware and storage isolation tests passed');
