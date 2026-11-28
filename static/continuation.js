/* Explicit archive-to-new-run workflow. Old results remain read-only. */
(() => {
  'use strict';
  const byId=id=>document.getElementById(id),panel=byId('continuationPanel'),status=byId('continuationStatus');
  let prepared=null,revision=0,previewRevision=0,timer=null,observedKey=null,accepted=null;
  const preview=document.createElement('div');preview.id='continuationPreview';preview.setAttribute('role','status');status.after(preview);
  const fields={mode:'mode',seconds:'seconds',seed:'seed',population:'population',exploration:'explore',
    objective:'objective',physical_gate:'physical_gate',gate_grid:'gate_grid',cores:'cores',audit_grid:'audit_grid',
    fem_enabled:'enable_fem',fem_pitch_mm:'fem_pitch',fem_backend:'fem_backend',search_strategy:'searchStrategy',search_precision:'searchPrecision'};
  const labels={mode:'Search space',seconds:'Additional seconds',seed:'Seed',population:'Population',exploration:'Exploration',objective:'Objective',physical_gate:'Physical gate',gate_grid:'Gate grid',cores:'CPU workers',audit_grid:'Audit grid',fem_enabled:'FEM enabled',fem_pitch_mm:'FEM pitch [mm]',fem_backend:'FEM backend',search_strategy:'Search strategy',search_precision:'Search precision'};
  function request(source){const out={};for(const [key,id] of Object.entries(fields)){const el=byId(id);
    if(el.type!=='checkbox'&&!el.value.trim())throw Error('Enter '+labels[key]);
    out[key]=el.type==='checkbox'?el.checked:['mode','objective','fem_backend','search_strategy'].includes(key)?el.value:Number(el.value);}
    out.exploration/=100;out.search_precision/=100;return {...out,generation:source.generation,source_digest:source.digest};}
  function update(){byId('loadContinuation').disabled=startPending||!archiveRunId||byId('archiveSelect').value!==archiveRunId;
    let key=null;
    if(prepared&&!startPending){try{const payload=request(prepared);key=JSON.stringify(payload);
      if(key!==observedKey){observedKey=key;accepted=null;const ticket=++previewRevision;clearTimeout(timer);
        preview.textContent='Checking selected settings and compatible saved geometries...';
        const source=prepared;timer=setTimeout(()=>check(source,payload,key,ticket),250);}
    }catch(e){observedKey=null;accepted=null;previewRevision++;clearTimeout(timer);preview.textContent=e.message;}}
    byId('continueEvolution').disabled=startPending||!prepared||!accepted||accepted.key!==key;
    byId('cancelContinuation').disabled=startPending;}
  function clear(){revision++;previewRevision++;clearTimeout(timer);accepted=null;observedKey=null;prepared=null;panel.hidden=true;preview.replaceChildren();update();}
  async function check(source,payload,key,ticket){
    try{const data=await api('POST','/archives/'+encodeURIComponent(source.run)+'/continuation/preview',payload);
      if(ticket!==previewRevision||source!==prepared)return;
      accepted={key,request:payload};preview.replaceChildren();
      const text=document.createElement('p');text.textContent='Inherit '+data.inherited_count+' of '+data.eligible_seed_count+' compatible saved geometries; '+data.excluded_seed_count+' excluded by scope. '+
        (data.random_state_restored?'Saved random stream restored. ':'New random stream. ')+
        (data.source_champion_eligible?'Saved champion receives a fresh full audit in the first generation.':data.source_genome_hash?'First compatible saved geometry receives a fresh full audit; the saved champion is outside this scope.':'First compatible saved geometry receives a fresh full audit.');preview.append(text);
      const changes=Object.entries(data.settings_changes);
      if(changes.length){const table=document.createElement('table');table.style.width='100%';table.style.textAlign='left';
        const header=document.createElement('tr');for(const name of ['Setting','Loaded','Selected']){const th=document.createElement('th');th.textContent=name;header.append(th);}table.append(header);
        for(const [name,values] of changes){const row=document.createElement('tr');for(const value of [labels[name]||name,values.from,values.to]){const cell=document.createElement('td');cell.textContent=value==null?'not recorded':typeof value==='boolean'?(value?'on':'off'):String(value);row.append(cell);}table.append(row);}preview.append(table);
      }else{const same=document.createElement('p');same.textContent='Controls match the loaded configuration.';preview.append(same);}
      update();
    }catch(e){if(ticket===previewRevision&&source===prepared){accepted=null;preview.textContent='Cannot preview continuation: '+e.message;update();}}
  }
  async function load(){
    if(startPending||!archiveRunId)return;const ticket=++revision,context=contextRevision,run=archiveRunId;
    const generation=byId('stageSelect').value,query=generation?'?generation='+encodeURIComponent(generation):'';
    prepared=null;panel.hidden=false;status.textContent='Loading saved controls and source geometries...';update();
    try{
      const data=await api('GET','/archives/'+encodeURIComponent(run)+'/continuation'+query);
      if(ticket!==revision||context!==contextRevision||run!==archiveRunId)return;
      const notes=[...data.warnings];
      for(const [key,id] of Object.entries(fields)){
        const el=byId(id);let value=data.settings[key];if(value==null)continue;
        if(key==='exploration'||key==='search_precision'){value*=100;el.step='any';}
        if(key==='cores'){const bounded=Math.max(1,Math.min(Number(el.max)||1,value));if(bounded!==value)notes.push('CPU workers adjusted from '+value+' to '+bounded+' for this machine.');value=bounded;}
        if(el.tagName==='SELECT'&&![...el.options].some(o=>o.value===String(value)))el.add(new Option('Saved: '+value,String(value)));
        if(el.type==='checkbox')el.checked=Boolean(value);else el.value=String(value);
      }
      prepared={run,generation:generation?Number(generation):null,digest:data.source_digest,base:data.parent_generation};observedKey=null;accepted=null;
      status.textContent='Run '+run+' / generation '+data.parent_generation+' -> '+(data.parent_generation+1)+'. '+
        (data.source_kind==='population_checkpoint'?'Saved population checkpoint. ':'Saved elite geometries; older archive has no population checkpoint. ')+
        (data.source_candidate_generation!=null?'Saved champion born in generation '+data.source_candidate_generation+'. ':'')+
        'Edit the controls below, then Continue. New run, fresh scoring; original session preserved. '+notes.join(' ');
      for(const id of Object.values(fields))byId(id).dispatchEvent(new Event('input',{bubbles:true}));
      update();
    }catch(e){if(ticket===revision){prepared=null;status.textContent='Cannot prepare continuation: '+e.message;update();}}
  }
  async function begin(){
    if(startPending||!prepared)return;let currentKey;try{currentKey=JSON.stringify(request(prepared));}catch{update();return;}
    if(!accepted||accepted.key!==currentKey){update();return;}
    const source=prepared,payload=accepted.request;startPending=true;update();
    const context=++contextRevision;
    try{
      const next=await api('POST','/archives/'+encodeURIComponent(source.run)+'/continue',payload);
      // A successful POST starts one run even if the user browsed another view meanwhile.
      if(context!==contextRevision){status.textContent='Continuation started as '+next.id+'. Return to live to inspect it.';return;}
      state=next;archiveRunId=null;archiveGeneration=null;fullArchiveState=null;pinnedCandidate=null;currentResponse=null;lastSpatial=null;
      follow=true;byId('auto').checked=true;currentSelection={kind:'best',index:0,family:'crown'};meshSignature='';
      clear();byId('error').textContent='';setArchiveNotice();display();
    }catch(e){status.textContent='Continuation not started: '+e.message;byId('error').textContent=e.message;}
    finally{startPending=false;update();if(state)display();}
  }
  byId('loadContinuation').onclick=load;byId('continueEvolution').onclick=begin;byId('cancelContinuation').onclick=clear;
  for(const type of ['input','change'])document.addEventListener(type,e=>{if(Object.values(fields).includes(e.target.id))update();});
  window.NeuroContinuation={clear,update,prepared:()=>!!prepared};update();
})();
