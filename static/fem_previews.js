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
  const api={labels,order,bounds,traces};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NeuroFEMPreviews=api;
})(globalThis);
