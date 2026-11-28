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
  function inspector(host,onChange,id){
    const make=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
    const details=make('details');details.className='workspace-component-tree advanced-only';details.id=id;
    details.append(make('summary','Component tree · assembly'));
    const control=make('div');control.className='component-actions';
    const clear=make('button','Clear highlight');clear.type='button';
    const label=make('label','Structural centerlines (reference)');const check=make('input');check.type='checkbox';label.prepend(check);control.append(clear,label);
    const body=make('div');body.className='component-tree-body';
    const info=make('p','Select a design to inspect its components.');info.className='workspace-summary';info.setAttribute('role','status');
    details.append(control,body,info);host.append(details);
    let identity=null,model=null,selected=null;
    const fmt=v=>Number.isFinite(v)?v.toFixed(3):'—';
    function select(id){selected=id;render();onChange();}
    clear.onclick=()=>select(null);check.onchange=onChange;
    function render(){
      body.replaceChildren();const nodes=model?.component_tree?.nodes||[];
      clear.disabled=!selected;check.disabled=!nodes.length;
      const n=nodes.find(n=>n.id===selected);
      info.textContent=n?[n.label,n.stage,n.role,n.member_index!=null?'member '+(n.member_index+1):null,n.nominal_radius_mm!=null?'nominal radius '+fmt(n.nominal_radius_mm)+' mm':null,n.centerline_length_mm!=null?'centerline '+fmt(n.centerline_length_mm)+' mm':null,n.bonded_to?'bonded to '+n.bonded_to:null,'concept geometry; no local FEM ownership'].filter(Boolean).join(' · '):nodes.length?nodes.length+' generated components · select to highlight in 3D. Centerlines show structural layout, not solved force flow.':'Select a design to inspect its components.';
      for(const stage of model?.component_tree?.stage_order||[]){
        const group=nodes.filter(n=>n.stage===stage);if(!group.length)continue;
        const section=make('details');section.open=group.some(n=>n.id===selected);
        section.append(make('summary',stage+' · '+group.length));
        const items=make('div');items.className='component-items';
        for(const n of group){const b=make('button',n.label+(n.role?' · '+n.role:''));b.type='button';b.dataset.componentId=n.id;b.setAttribute('aria-pressed',String(n.id===selected));b.onclick=()=>select(n.id);items.append(b);}
        section.append(items);body.append(section);
      }
    }
    function set(data,key){
      const changed=identity!==key||!data;
      if(changed){identity=key;selected=null;check.checked=false;}
      if(model===data&&!changed)return;
      model=data;
      if(selected&&!model?.component_tree?.nodes.some(n=>n.id===selected))selected=null;
      render();
    }
    return {set,selected:()=>selected,paths:()=>check.checked};
  }
  const api={decorate,inspector};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NeuroComponents=api;
})(globalThis);
