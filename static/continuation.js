/* Explicit archive-to-new-run workflow. Old results remain read-only. */
(() => {
  'use strict';
  const byId=id=>document.getElementById(id),panel=byId('continuationPanel'),status=byId('continuationStatus');
  let prepared=null,revision=0;
  const fields={mode:'mode',seconds:'seconds',seed:'seed',population:'population',exploration:'explore',
    objective:'objective',physical_gate:'physical_gate',gate_grid:'gate_grid',cores:'cores',audit_grid:'audit_grid',
    fem_enabled:'enable_fem',fem_pitch_mm:'fem_pitch',fem_backend:'fem_backend',search_strategy:'searchStrategy',search_precision:'searchPrecision'};
  function update(){byId('loadContinuation').disabled=startPending||!archiveRunId||byId('archiveSelect').value!==archiveRunId;
    byId('continueEvolution').disabled=startPending||!prepared;byId('cancelContinuation').disabled=startPending;}
  function clear(){revision++;prepared=null;panel.hidden=true;update();}
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
      prepared={run,generation:generation?Number(generation):null,digest:data.source_digest,base:data.parent_generation};
      status.textContent='Run '+run+' / generation '+data.parent_generation+' -> '+(data.parent_generation+1)+'. '+
        (data.source_kind==='population_checkpoint'?'Saved population checkpoint. ':'Saved elite geometries; older archive has no population checkpoint. ')+
        'Edit the controls below, then Continue. New run, fresh scoring; original session preserved. '+notes.join(' ');
      for(const id of Object.values(fields))byId(id).dispatchEvent(new Event('input',{bubbles:true}));
      update();
    }catch(e){if(ticket===revision){prepared=null;status.textContent='Cannot prepare continuation: '+e.message;update();}}
  }
  async function begin(){
    if(startPending||!prepared)return;const source=prepared;startPending=true;update();
    const context=++contextRevision;
    try{
      const request={};for(const [key,id] of Object.entries(fields)){const el=byId(id);request[key]=el.type==='checkbox'?el.checked:['mode','objective','fem_backend','search_strategy'].includes(key)?el.value:Number(el.value);}
      request.exploration/=100;request.search_precision/=100;
      Object.assign(request,{generation:source.generation,source_digest:source.digest});
      const next=await api('POST','/archives/'+encodeURIComponent(source.run)+'/continue',request);
      // A successful POST starts one run even if the user browsed another view meanwhile.
      if(context!==contextRevision){status.textContent='Continuation started as '+next.id+'. Return to live to inspect it.';return;}
      state=next;archiveRunId=null;archiveGeneration=null;fullArchiveState=null;pinnedCandidate=null;currentResponse=null;lastSpatial=null;
      follow=true;byId('auto').checked=true;currentSelection={kind:'best',index:0,family:'crown'};meshSignature='';
      clear();byId('error').textContent='';setArchiveNotice();display();
    }catch(e){status.textContent='Continuation not started: '+e.message;byId('error').textContent=e.message;}
    finally{startPending=false;update();if(state)display();}
  }
  byId('loadContinuation').onclick=load;byId('continueEvolution').onclick=begin;byId('cancelContinuation').onclick=clear;
  window.NeuroContinuation={clear,update,prepared:()=>!!prepared};update();
})();
