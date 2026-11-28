/* Actual diagnostic fields; no fabricated geometry or inferred hardware accuracy. */
(function(root){
  'use strict';
  const base={paper_bgcolor:'#101e2b',plot_bgcolor:'#101e2b',font:{color:'#b8ccd5',size:11},margin:{l:50,r:18,t:34,b:45},legend:{orientation:'h'},autosize:true};
  const scene={aspectmode:'data',xaxis:{title:'X [mm]',gridcolor:'#345363'},yaxis:{title:'Y [mm]',gridcolor:'#345363'},zaxis:{title:'Z [mm]',gridcolor:'#345363'},camera:{eye:{x:1.55,y:1.45,z:1.2}}};
  const config={responsive:true,displaylogo:false};
  const colors=['#71d5b4','#b09bdb','#f1bd6d','#78a9cc'];
  function contact(d,stage,scale,field='material'){
    const p=d.contact_fields,s=p.stages[stage],v=p.vertices_mm,f=p.faces,u=s.displacement_mm;
    const mesh={type:'mesh3d',x:v.map((a,i)=>a[0]+scale*u[i][0]),y:v.map((a,i)=>a[1]+scale*u[i][1]),z:v.map((a,i)=>a[2]+scale*u[i][2]),i:f.map(a=>a[0]),j:f.map(a=>a[1]),k:f.map(a=>a[2]),facecolor:p.face_material_ids.map(i=>colors[i%colors.length]),name:'Solved deformation',hoverinfo:'skip'};
    if(field!=='material'){const key=field==='stress'?'face_von_mises_MPa':'face_J';delete mesh.facecolor;mesh.intensity=s[key];mesh.intensitymode='cell';mesh.colorscale='Viridis';mesh.showscale=true;mesh.colorbar={title:field==='stress'?'Cauchy VM [MPa]':'J'};const all=p.stages.flatMap(t=>t[key]);mesh.cmin=all.reduce((a,b)=>Math.min(a,b),Infinity);mesh.cmax=all.reduce((a,b)=>Math.max(a,b),-Infinity);if(mesh.cmax===mesh.cmin)mesh.cmax=mesh.cmin+1e-12;}
    const ghost={...mesh,x:v.map(a=>a[0]),y:v.map(a=>a[1]),z:v.map(a=>a[2]),facecolor:undefined,intensity:undefined,showscale:false,color:'#92acba',opacity:.12,name:'Reference',hoverinfo:'skip'};
    const planeZ=Math.max(...v.map(a=>a[2]))-s.indentation_mm;
    // Rigid indenter is plotted at its physical position (not exaggerated).
    const z0=Math.min(...v.map(a=>a[2]));
    const plane=scale===1?{type:'mesh3d',x:[Math.min(...v.map(a=>a[0])),Math.max(...v.map(a=>a[0])),Math.max(...v.map(a=>a[0])),Math.min(...v.map(a=>a[0]))],y:[Math.min(...v.map(a=>a[1])),Math.min(...v.map(a=>a[1])),Math.max(...v.map(a=>a[1])),Math.max(...v.map(a=>a[1]))],z:[planeZ,planeZ,planeZ,planeZ],i:[0,0],j:[1,2],k:[2,3],color:'#efbd71',opacity:.18,name:'Rigid plane',hoverinfo:'skip'}:null;
    return {traces:[ghost,mesh,...(plane?[plane]:[])],layout:{...base,margin:{l:0,r:0,b:0,t:30},scene,title:'Solved nonlinear deformation · '+scale+'× · stage '+(stage+1),uirevision:'contact'}};
  }
  function contactCurve(d){
    const stages=d.stages;
    return {traces:[{type:'scatter',mode:'lines+markers',x:stages.map(s=>s.indentation_mm),y:stages.map(s=>s.contact_force_N),text:stages.map((s,i)=>'Step '+(i+1)),line:{color:'#75d3bf'},hovertemplate:'%{text}<br>Indent %{x:.4g} mm<br>Force %{y:.4g} N<extra></extra>'}],layout:{...base,title:'Load / unload path',xaxis:{title:'Indentation [mm]'},yaxis:{title:'Contact force [N]'}}};
  }
  function tile(d){
    const a=Array.from({length:d.reaction_N.length},(_,i)=>i*d.pitch_mm),n=a.length;
    const x=[],y=[],z=[],r=[];for(let j=0;j<n;j++)for(let i=0;i<n;i++){x.push(a[i]);y.push(a[j]);z.push(-d.displacement_mm[j][i]);r.push(d.reaction_N[j][i]);}
    const taxels={type:'scatter3d',mode:'markers',name:'Pad-average reaction',x,y,z,marker:{size:6,color:r,colorscale:'RdBu',reversescale:true,cmin:-Math.max(1e-12,...r.map(Math.abs)),cmax:Math.max(1e-12,...r.map(Math.abs)),showscale:true,colorbar:{title:'Reaction [N]',x:1.01},opacity:.95},text:r.map(v=>v.toPrecision(4)+' N'),hovertemplate:'Reaction %{text}<extra></extra>'};
    let traces=[taxels],title='Discrete taxel displacement and reaction';
    if(d.membrane_surface){
      const s=d.membrane_surface;
      traces=[{type:'surface',name:'Membrane',x:s.inplane_x_mm?s.inplane_x_mm.map(row=>row.map((v,i)=>s.axis_mm[i]+v)):s.axis_mm,y:s.inplane_y_mm?s.inplane_y_mm.map((row,j)=>row.map(v=>s.axis_mm[j]+v)):s.axis_mm,z:s.displacement_mm.map(row=>row.map(v=>-v)),surfacecolor:s.displacement_mm,colorscale:'Viridis',showscale:false,opacity:.8,hovertemplate:'x %{x:.3g} mm<br>y %{y:.3g} mm<br>z %{z:.4g} mm<extra>Membrane</extra>'},taxels];
      title='Solved membrane surface · undeformed XY coordinates';
    }
    if(d.substrate){const s=d.substrate.surface;traces.push({type:'surface',name:'3D substrate top',x:s.axis_mm,y:s.axis_mm,z:s.displacement_mm.map(row=>row.map(v=>s.reference_z_mm-v)),colorscale:'Cividis',showscale:false,opacity:.8});title='Membrane and substrate · nominal receptor height separation';}
    const contact=d.input_contacts||[];
    if(contact.length)traces.push({type:'scatter3d',mode:'markers',name:'Applied contact XY (reference z=0)',x:contact.map(c=>c.x_mm),y:contact.map(c=>c.y_mm),z:contact.map(()=>0),marker:{symbol:'diamond',color:'#f1bd6d',size:6},text:contact.map(c=>c.force_N.toPrecision(4)+' N'),hovertemplate:'Applied %{text}<extra></extra>'});
    return {traces,layout:{...base,title,scene:{...scene,aspectmode:'auto',zaxis:{...scene.zaxis,title:'− compression [mm]'}},margin:{l:0,r:65,t:38,b:0},uirevision:'tile'}};
  }
  function fusion(d){
    const names=Object.keys(d.models||{}),m=names.map(n=>d.models[n]);
    return {traces:[{type:'bar',name:'Force RMSE [mN]',x:names,y:m.map(v=>1000*v.force_rmse_norm_N),marker:{color:'#75d3bf'}},{type:'bar',name:'Position MAE [mm]',x:names,y:m.map(v=>v.position_mae_mm),yaxis:'y2',marker:{color:'#b09bdb'}}],layout:{...base,title:'Held-out readout comparison · synthetic',barmode:'group',margin:{l:55,r:55,t:50,b:85},xaxis:{tickangle:-20},yaxis:{title:'Force RMSE [mN]',rangemode:'tozero'},yaxis2:{title:'Position MAE [mm]',overlaying:'y',side:'right',rangemode:'tozero'}}};
  }
  function optimization(d){
    const traces=[];
    for(const [key,rows,front] of [['Screen',d.screening,d.screening_pareto_ids],['Refined',d.refined,d.refined_pareto_ids]]){
      const valid=rows.filter(r=>!r.failed);
      traces.push({type:'scatter',mode:'markers',name:key,x:valid.map(r=>r.metrics.power_mW),y:valid.map(r=>r.metrics.position_mae_mm),text:valid.map(r=>r.id+' · '+r.receptor.id+' · '+r.size+'×'+r.size+' · force RMSE '+(1000*r.metrics.force_rmse_N).toFixed(2)+' mN'),marker:{size:key==='Refined'?12:7,symbol:valid.map(r=>!r.diagnostic_screen_pass?'x':front.includes(r.id)?'diamond':'circle'),color:key==='Refined'?'#f1bd6d':'#75d3bf'},hovertemplate:'%{text}<br>Power %{x:.3g} mW<br>Position MAE %{y:.3g} mm<extra></extra>'});
    }
    return {traces,layout:{...base,title:'Tile tradeoffs · separate fidelities (diamonds = eligible Pareto)',xaxis:{title:'Assumed total power [mW]'},yaxis:{title:'Centroid MAE [mm]'}}};
  }
  const api={contact,contactCurve,tile,fusion,optimization,config};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NeuroLabVisuals=api;
})(globalThis);
