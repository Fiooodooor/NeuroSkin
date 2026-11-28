/* Replicate accepted receptor geometry at the computed skin-patch placements. */
(function(root){
  'use strict';
  const colors={base:'#688a9c',flexure:'#6dd4b6',contact:'#b5ece0',sensor:'#eab56b',inner:'#b29cdb',piezo:'#ffcf64'};
  function box(name,side,z0,z1,color,opacity){
    return {type:'mesh3d',name,x:[0,side,side,0,0,side,side,0],y:[0,0,side,side,0,0,side,side],z:[z0,z0,z0,z0,z1,z1,z1,z1],
      i:[0,0,4,4,0,0,1,1,2,2,3,3],j:[2,3,5,6,1,5,2,6,3,7,0,4],k:[1,2,6,7,5,4,6,5,7,6,4,7],color,opacity,hoverinfo:'name',flatshading:true};
  }
  function patch(result,key,{membrane=true,pvdf=true,selected=null}={}){
    const p=result.skin_patches?.find(p=>p.key===key),t=p&&result.skin_templates?.[p.receptor_id];
    if(!p||!t||p.genome_hash!==t.genome_hash||p.placements.length!==p.size*p.size)throw Error('Computed skin geometry is unavailable or inconsistent');
    const traces=[box('Substrate',p.side_mm,-p.substrate_depth_mm,0,'#506b83',.5)];
    for(const component of t.components){
      if(component.part==='piezo'&&!pvdf)continue;
      const trace={type:'mesh3d',name:component.part==='piezo'?'PVDF films':component.part,x:[],y:[],z:[],i:[],j:[],k:[],color:colors[component.part]||'#8daab9',hoverinfo:'skip',flatshading:false,lighting:{ambient:.65,diffuse:.75,roughness:.7}};
      for(const placement of p.placements){
        const offset=trace.x.length,[dx,dy,dz]=placement.position_mm;
        for(const v of component.vertices){trace.x.push(v[0]+dx);trace.y.push(v[1]+dy);trace.z.push(v[2]+dz);}
        for(const f of component.faces){trace.i.push(f[0]+offset);trace.j.push(f[1]+offset);trace.k.push(f[2]+offset);}
      }
      traces.push(trace);
    }
    if(t.rendering==='structural_centerlines'){
      const x=[],y=[],z=[];
      for(const placement of p.placements)for(const path of t.centerlines_mm){for(const v of path){x.push(v[0]+placement.position_mm[0]);y.push(v[1]+placement.position_mm[1]);z.push(v[2]+placement.position_mm[2]);}x.push(null);y.push(null);z.push(null);}
      traces.push({type:'scatter3d',mode:'lines',name:'Receptor centerlines (reduced detail)',x,y,z,line:{color:colors.flexure,width:3},hoverinfo:'skip'});
    }
    if(membrane)traces.push(box('Nominal membrane',p.side_mm,p.membrane_z_mm,p.membrane_z_mm+p.membrane_thickness_mm,'#75d3bf',.16));
    traces.push({type:'scatter3d',mode:'markers',name:'Sensor positions',
      x:p.placements.map(v=>v.position_mm[0]),y:p.placements.map(v=>v.position_mm[1]),z:p.placements.map(()=>p.membrane_z_mm+p.membrane_thickness_mm+.4),
      customdata:p.placements.map(v=>v.id),text:p.placements.map(v=>v.id+' · '+p.receptor_id),
      marker:{size:p.placements.map(v=>v.id===selected?7:3),color:p.placements.map(v=>v.id===selected?'#ff836c':'#f3f8f8'),opacity:.9},
      hovertemplate:'%{text}<br>X %{x:.3g} mm · Y %{y:.3g} mm<extra></extra>'});
    return {traces,layout:{paper_bgcolor:'#101e2b',plot_bgcolor:'#101e2b',font:{color:'#b8ccd5',size:12},
      title:p.size+' × '+p.size+' skin patch · '+p.sensor_count+' sensors · '+p.side_mm+' mm',
      margin:{l:0,r:0,t:45,b:0},legend:{orientation:'h'},autosize:true,uirevision:'skin-patch-'+p.key,
      scene:{aspectmode:'data',xaxis:{title:'X [mm]'},yaxis:{title:'Y [mm]'},zaxis:{title:'Z [mm]'},camera:{eye:{x:1.45,y:1.5,z:1.7}}}}};
  }
  const api={patch};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NeuroSkinPatch=api;
})(globalThis);
