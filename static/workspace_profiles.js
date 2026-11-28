/* Explicit next-run presets, not replay or live engine mutation. */
(function(root){
  'use strict';
  const key='neuroskin-evolution-presets-v1',limit=6;
  const fields=['mode','seconds','cores','population','searchStrategy','searchPrecision','explore','objective','physical_gate','enable_fem','fem_backend','fem_pitch','gate_grid','audit_grid'];
  const validName=s=>typeof s==='string'&&s.trim()===s&&s.length>0&&s.length<=40&&!/[\x00-\x1f]/.test(s);
  function capture(get){return Object.fromEntries(fields.map(id=>{const el=get(id);return [id,el.type==='checkbox'?el.checked:el.value];}));}
  function validate(values,get){if(!values||typeof values!=='object')throw Error('Invalid preset');
    const result={};for(const id of fields){const el=get(id),v=values[id];
      if(!el)throw Error('Missing control: '+id);
      if(el.type==='checkbox'){if(typeof v!=='boolean')throw Error('Invalid '+id);}
      else if(el.tagName==='SELECT'){if(typeof v!=='string'||![...el.options].some(o=>o.value===v&&!o.disabled))throw Error('Unavailable option: '+id);}
      else{const n=Number(v);if(typeof v!=='string'||!v.trim()||!Number.isFinite(n)||!Number.isInteger(n)||n<Number(el.min)||n>Number(el.max))throw Error('Out of range: '+id+' ('+el.min+'–'+el.max+')');}
      result[id]=v;
    }return result;
  }
  function load(storage){try{const data=JSON.parse(storage.getItem(key)||'[]');if(!Array.isArray(data)||data.length>limit)return [];return data.filter(x=>validName(x?.name)&&x.values&&typeof x.values==='object');}catch{return [];}}
  function save(storage,profiles,name,values){if(!validName(name))throw Error('Enter a profile name (1–40 characters).');
    const all=[...profiles.filter(x=>x.name!==name),{name,values}];if(all.length>limit)throw Error('Maximum six profiles. Delete one first.');storage.setItem(key,JSON.stringify(all));return all;}
  function remove(storage,profiles,name){const all=profiles.filter(x=>x.name!==name);storage.setItem(key,JSON.stringify(all));return all;}
  function apply(values,get){const safe=validate(values,get);for(const id of fields){const el=get(id);if(el.type==='checkbox')el.checked=safe[id];else el.value=safe[id];}return safe;}
  function examples(get){
    const cores=String(Math.max(1,Math.min(4,Number(get('cores').max)||1)));
    const base={mode:'single:all',seconds:'60',cores,population:'48',searchStrategy:'adaptive',searchPrecision:'80',explore:'55',objective:'balanced',physical_gate:true,enable_fem:true,fem_backend:'hex8',fem_pitch:'0.625',gate_grid:'3',audit_grid:'5'};
    const templates=[
      {id:'example:quick',name:'Quick exploration',description:'15 s search budget, one CPU worker, 24 candidates, synthetic screening without FEM.',values:{seconds:'15',cores:'1',population:'24',enable_fem:false,audit_grid:'3',searchStrategy:'explore',explore:'80'}},
      {id:'example:balanced',name:'Balanced mechanics',description:'Single-stage search with solid HEX8 at 0.625 mm and the full synthetic audit.',values:{}},
      {id:'example:electronics',name:'Electronics co-design',description:'Search with channel, readout power, bandwidth and saturation objectives.',values:{objective:'electronics'}},
      {id:'example:hybrids',name:'Two-stage hybrids',description:'Explore two-stage reference architectures with connected solid HEX8 mechanics.',values:{mode:'hybrid:all',seconds:'120',population:'24'}}
    ];
    return templates.flatMap(p=>{try{return [{...p,values:validate({...base,...p.values},get)}];}catch{return [];}});
  }
  const api={key,fields,capture,validate,load,save,remove,apply,examples};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NeuroProfiles=api;
})(globalThis);
