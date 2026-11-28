/* Compact view-only FEM comparisons. Shared field scale and spatial bounds. */
(function(root){
  'use strict';
  const labels={press_center:'Central pressure',press_x_plus:'Off-center pressure +X',shear_x:'Shear X + preload',torsion_z:'Torsion Z + preload'};
  const order=Object.keys(labels);
  function scalar(c,key){return key==='displacement_mm'?c.displacement_mm.map(p=>Math.hypot(...p)):c[key];}
  function bounds(packet,key,scale){
    const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];let min=Infinity,max=-Infinity;
    for(const name of order){const c=packet.cases[name],s=scalar(c,key);
      for(const v of s){min=Math.min(min,v);max=Math.max(max,v);}
      for(let i=0;i<packet.vertices_mm.length;i++)for(let j=0;j<3;j++){
        const a=packet.vertices_mm[i][j],b=a+scale*c.displacement_mm[i][j];lo[j]=Math.min(lo[j],a,b);hi[j]=Math.max(hi[j],a,b);}
    }
    const ranges=lo.map((a,j)=>{const pad=Math.max((hi[j]-a)*.04,.01);return[a-pad,hi[j]+pad];});
    return {cmin:Math.min(0,min),cmax:Math.max(max,Math.min(0,min)+1e-12),ranges};
  }
  function traces(packet,name,key,scale,ghost,range){
    const c=packet.cases[name],v=packet.vertices_mm,d=c.displacement_mm,f=packet.faces;
    const common={type:'mesh3d',i:f.map(p=>p[0]),j:f.map(p=>p[1]),k:f.map(p=>p[2]),showlegend:false};
    const out=[];
    if(ghost)out.push({...common,x:v.map(p=>p[0]),y:v.map(p=>p[1]),z:v.map(p=>p[2]),color:'#91a7b6',opacity:.1,hoverinfo:'skip',showscale:false});
    out.push({...common,x:v.map((p,i)=>p[0]+scale*d[i][0]),y:v.map((p,i)=>p[1]+scale*d[i][1]),z:v.map((p,i)=>p[2]+scale*d[i][2]),intensity:scalar(c,key),cmin:range.cmin,cmax:range.cmax,colorscale:'Viridis',showscale:false,hovertemplate:'Field %{intensity:.5g}<extra></extra>'});
    return out;
  }
  function forceGroups(c,boundary=true,sections=false){
    const b=c.boundary_vectors,out=[];
    if(boundary)for(const [key,color] of [['applied','#ffba61'],['reaction','#68d8f1']])if(b?.[key])out.push([key,color,b[key]]);
    if(sections)for(const [i,s] of (b?.substrate_sections||[]).entries())out.push(['section '+(i+1),i===0?'#d8a6ff':'#f18bb9',s]);
    return out;
  }
  function forceScale(packet,boundary=true,sections=false){
    // Shared vector magnification across all four cases, in display mm/N.
    const all=order.flatMap(name=>forceGroups(packet.cases[name],boundary,sections).flatMap(([, ,g])=>g.groups));
    const max=Math.max(0,...all.map(g=>Math.hypot(...g.force_N)));
    if(!max)return 0;
    const ext=[0,1,2].map(j=>{let lo=Infinity,hi=-Infinity;for(const p of packet.vertices_mm){lo=Math.min(lo,p[j]);hi=Math.max(hi,p[j]);}return hi-lo;});
    return .22*Math.max(...ext,.1)/max;
  }
  function arrowPoints(g,factor,tipAtPosition=false){
    const origin=g.position_mm,f=g.force_N,mag=Math.hypot(...f);if(!mag||!factor)return [];
    const u=f.map(x=>x/mag),v=u.map(x=>x*mag*factor),p=tipAtPosition?origin.map((x,j)=>x-v[j]):origin,tip=tipAtPosition?origin:p.map((x,j)=>x+v[j]);
    // Pick a stable perpendicular for two visible arrowhead lines.
    const axis=Math.abs(u[2])<.9?[0,0,1]:[0,1,0];
    const cross=[u[1]*axis[2]-u[2]*axis[1],u[2]*axis[0]-u[0]*axis[2],u[0]*axis[1]-u[1]*axis[0]];
    const norm=Math.hypot(...cross);
    const head=Math.min(mag*factor*.3,.8),ends=[-1,1].map(s=>tip.map((x,j)=>x-head*u[j]+s*.5*head*cross[j]/norm));
    return [p,tip,[null,null,null],ends[0],tip,ends[1],[null,null,null]];
  }
  function boundaryTraces(c,factor,boundary=true,sections=false){
    const out=[];
    for(const [key,color,group] of forceGroups(c,boundary,sections)){
      const pts=group.groups.flatMap(g=>arrowPoints(g,factor,key==='applied'));
      if(pts.length)out.push({type:'scatter3d',mode:'lines',name:key+' boundary force',x:pts.map(p=>p[0]),y:pts.map(p=>p[1]),z:pts.map(p=>p[2]),line:{color,width:5},hoverinfo:'skip',showlegend:false});
      const gs=group.groups;
      out.push({type:'scatter3d',mode:'markers',name:key+' boundary origin',x:gs.map(g=>g.position_mm[0]),y:gs.map(g=>g.position_mm[1]),z:gs.map(g=>g.position_mm[2]),marker:{color,size:3},text:gs.map(g=>'F ['+g.force_N.map(x=>x.toPrecision(3)).join(', ')+'] N · free couple ['+g.couple_Nmm.map(x=>x.toPrecision(3)).join(', ')+'] Nmm'),hovertemplate:'%{text}<extra>'+key+'</extra>',showlegend:false});
    }
    return out;
  }
  function extendBounds(range,packet,factor,boundary=true,sections=false){
    for(const name of order)for(const trace of boundaryTraces(packet.cases[name],factor,boundary,sections)){
      for(const [j,key] of ['x','y','z'].entries())for(const val of trace[key])if(Number.isFinite(val)){range.ranges[j][0]=Math.min(range.ranges[j][0],val);range.ranges[j][1]=Math.max(range.ranges[j][1],val);}
    }
    return range;
  }
  const api={labels,order,bounds,traces,forceScale,boundaryTraces,extendBounds};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NeuroFEMPreviews=api;
})(globalThis);
