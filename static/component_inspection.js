/* Interactive conceptual assembly tree. One plot, face spans, no new WebGL context. */
(function(root){
  'use strict';
  function decorate(traces,model,selected,paths,showPaths,colors){
    const nodes=model?.component_tree?.nodes||[],picked=nodes.find(n=>n.id===selected);
    const out=traces.map(t=>{
      if(!picked)return t;
      if(t.name!==picked.part)return {...t,opacity:Math.min(t.opacity??1,.25)};
      const base=colors[t.name]||'#a0b3bd',end=picked.face_start+picked.face_count;
      return {...t,facecolor:t.i.map((_,i)=>i>=picked.face_start&&i<end?'#ffcf70':base)};
    });
    if(showPaths&&paths){
      // These are reference structural centerlines, NOT computed force trajectories.
      for(const stage of ['upper','lower','single']){
        const points=[];
        for(const n of nodes.filter(n=>n.part==='flexure'&&n.stage===stage)){
          const path=paths[n.member_index];if(path)points.push(...path,[null,null,null]);
        }
        if(points.length)out.push({type:'scatter3d',mode:'lines',name:stage+' structural paths (concept)',x:points.map(p=>p[0]),y:points.map(p=>p[1]),z:points.map(p=>p[2]),line:{color:stage==='upper'?'#ffcf70':stage==='lower'?'#a99be9':'#e6f3f4',width:5},hoverinfo:'skip'});
      }
    }
    return out;
  }
  function filmRows(packet,node,nodes){
    if(!node||!packet?.cases)return [];
    const films=nodes.filter(n=>n.part==='piezo'&&(node.part==='piezo'?n.id===node.id:node.part==='flexure'&&n.bonded_to===node.id));
    return (packet.case_order||[]).flatMap(name=>films.flatMap(n=>{
      const found=(packet.cases[name]?.film_results||[]).filter(f=>f.film_index===n.film_index&&f.member_index===n.member_index);
      return found.length===1?[{case:name,film:n.label,...found[0]}]:[];
    }));
  }
  function inspector(host,onChange,id){
    const make=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
    const details=make('details');details.className='workspace-component-tree advanced-only';details.id=id;
    details.append(make('summary','Component tree · assembly'));
    const control=make('div');control.className='component-actions';
    const clear=make('button','Clear highlight');clear.type='button';
    const label=make('label','Structural centerlines (reference)');const check=make('input');check.type='checkbox';label.prepend(check);control.append(clear,label);
    const body=make('div');body.className='component-tree-body';
    const info=make('p','Select a design to inspect its components.');info.className='workspace-summary';info.setAttribute('role','status');
    const evidence=make('div');evidence.className='component-evidence';evidence.hidden=true;
    details.append(control,body,info,evidence);host.append(details);
    let identity=null,model=null,selected=null,packet=null,stale=false,referenceAvailable=true;
    const fmt=v=>Number.isFinite(v)?v.toFixed(3):'—';
    function select(id){selected=id;render();onChange();}
    clear.onclick=()=>select(null);check.onchange=onChange;
    function render(){
      const expanded=new Set([...body.querySelectorAll('details[open]')].map(n=>n.dataset.stage));
      body.replaceChildren();const nodes=model?.component_tree?.nodes||[];
      clear.disabled=!selected;check.disabled=!nodes.length||!referenceAvailable;label.title=referenceAvailable?'Reference centerlines':'Reference centerlines are hidden in the deformed view';
      const n=nodes.find(n=>n.id===selected);
      info.textContent=n?[n.label,n.stage,n.role,n.member_index!=null?'member '+(n.member_index+1):null,n.nominal_radius_mm!=null?'nominal radius '+fmt(n.nominal_radius_mm)+' mm':null,n.centerline_length_mm!=null?'centerline '+fmt(n.centerline_length_mm)+' mm':null,n.bonded_to?'bonded to '+n.bonded_to:null,n.bounds_mm?'bounds '+n.bounds_mm[1].map((v,i)=>fmt(v-n.bounds_mm[0][i])).join(' × ')+' mm':null,'concept geometry; no local FEM ownership'].filter(Boolean).join(' · '):nodes.length?nodes.length+' generated components · select to highlight in 3D. Centerlines show structural layout, not solved force flow.':'Select a design to inspect its components.';
      evidence.replaceChildren();
      evidence.hidden=!n||!['flexure','piezo'].includes(n.part);
      if(!evidence.hidden){
        evidence.append(make('strong','Bonded PVDF · four standard FEM cases'));
        const rows=filmRows(packet,n,nodes);
        if(!rows.length)evidence.append(make('small','No matching solved film response. Run Evaluate All for this candidate in the main workspace.'));
        else{
          const note=make('small',stale?'Last solved configuration — settings changed.':'Reduced bonded-film model · assumed charge, not measured output. No substrate local-stress attribution.');
          if(stale)note.className='workspace-stale';evidence.append(note);
          const wrap=make('div');wrap.className='component-evidence-scroll';
          const table=make('table'),header=make('tr');
          for(const col of ['Load case','Film','Strain [µε]','Charge [pC]','Energy [µJ]'])header.append(make('th',col));table.append(header);
          const labels=window.NeuroFEMPreviews?.labels||{};
          for(const r of rows){const tr=make('tr');for(const v of [labels[r.case]||r.case,r.film,Number.isFinite(r.effective_strain)?(r.effective_strain*1e6).toPrecision(4):'—',Number.isFinite(r.estimated_charge_pC)?r.estimated_charge_pC.toPrecision(4):'—',Number.isFinite(r.mechanical_energy_Nmm)?(r.mechanical_energy_Nmm*1000).toPrecision(4):'—'])tr.append(make('td',v));table.append(tr);}
          wrap.append(table);evidence.append(wrap);
        }
      }
      for(const stage of model?.component_tree?.stage_order||[]){
        const group=nodes.filter(n=>n.stage===stage);if(!group.length)continue;
        const section=make('details');section.dataset.stage=stage;section.open=expanded.has(stage)||group.some(n=>n.id===selected);
        section.append(make('summary',stage+' · '+group.length));
        const items=make('div');items.className='component-items';
        for(const n of group){const b=make('button',n.label+(n.role?' · '+n.role:''));b.type='button';b.dataset.componentId=n.id;b.setAttribute('aria-pressed',String(n.id===selected));b.onclick=()=>select(n.id);items.append(b);}
        section.append(items);body.append(section);
      }
    }
    function set(data,key){
      const changed=identity!==key||!data;
      if(changed){identity=key;selected=null;check.checked=false;packet=null;stale=false;}
      if(model===data&&!changed)return;
      model=data;
      if(selected&&!model?.component_tree?.nodes.some(n=>n.id===selected))selected=null;
      render();
    }
    function setEvidence(next,isStale){if(packet===next&&stale===isStale)return;packet=next;stale=isStale;render();}
    function setReferenceAvailable(value){if(referenceAvailable===value)return;referenceAvailable=value;render();}
    return {set,setEvidence,setReferenceAvailable,selected:()=>selected,paths:()=>check.checked&&referenceAvailable};
  }
  const api={decorate,inspector,filmRows};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NeuroComponents=api;
})(globalThis);
