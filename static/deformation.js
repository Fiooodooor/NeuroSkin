/* NeuroSkin deformation preview: kinematic interpolation, NOT FEM.
 * UMD so the exact browser implementation can be regression-tested with Node.
 */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.NeuroDeform=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
 const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
 const norm=a=>Math.hypot(...a);
 // Rotation vector converted to rotation via Rodrigues, avoiding small-angle artifacts.
 function rotate(v,w){const t=norm(w);if(t<1e-12)return [...v];const axis=w.map(q=>q/t),av=cross(axis,v),dot=axis.reduce((s,a,i)=>s+a*v[i],0);return v.map((q,i)=>q*Math.cos(t)+av[i]*Math.sin(t)+axis[i]*dot*(1-Math.cos(t)));}
 function computeScale(m,g,requested=1){
   const h=Math.max(1,Number(g.height)||1),u=m.displacement_mm||[0,0,0],r=m.rotation_rad||[0,0,0];
   const maxAllowedTranslation=.28*h;const maxAllowedAngle=.35;
   let effective=clamp(Number(requested)||1,0,20);
   if(norm(u)>1e-12)effective=Math.min(effective,maxAllowedTranslation/norm(u));
   if(norm(r)>1e-12)effective=Math.min(effective,maxAllowedAngle/norm(r));
   const validity=(norm(u)/h>.15 || norm(r)>.2)?'outside-small-deformation-regime':'small-displacement-proxy';
   return {effectiveScale:effective,requestedScale:requested,capped:effective<requested-1e-8,validity};
 }
 /** Piecewise arc-length interpolation on the nearest *undeformed* centerline.
  * This is more faithful than interpolating only global Z, but still NOT FEM.
  */
 function nearestArcProgress(v,paths){
   let best=Infinity,bestT=null;
   for(const path of (paths||[])){
     if(!Array.isArray(path)||path.length<2)continue;
     const lens=[];let total=0;
     for(let i=1;i<path.length;i++){let l=norm(path[i].map((q,j)=>q-path[i-1][j]));lens.push(l);total+=l;}
     let accum=0;
     for(let i=1;i<path.length;i++){
       const a=path[i-1],b=path[i],d=b.map((q,j)=>q-a[j]);
       const dd=d.reduce((z,x)=>z+x*x,0)||1e-15;
       const t=clamp(v.reduce((z,x,j)=>z+(x-a[j])*d[j],0)/dd,0,1);
       const proj=a.map((x,j)=>x+t*d[j]);const dist=norm(v.map((x,j)=>x-proj[j]));
       if(dist<best){best=dist;bestT=total>0?(accum+lens[i-1]*t)/total:0;}
       accum+=lens[i-1];
     }
   }
   return bestT;
 }
 function transformVertex(part,v,m,g,requested=1,paths=null){
   const p=[...v];const {effectiveScale:k}=computeScale(m,g,requested);
   const u=(m.displacement_mm||[0,0,0]).map(x=>x*k),r=(m.rotation_rad||[0,0,0]).map(x=>x*k);
   const strain=Number(m.substrate_strain)||0;
   const h=Number(g.height)||1, offset=[Number(g.pad_offset_x)||0,Number(g.pad_offset_y)||0,h];
   // Base and embedded electrodes follow substrate extension, not contact-pad motion.
   if(part==='base'||part==='sensor')return [p[0]*(1+strain),p[1],p[2]];
   // The pad remains rigid in the reduced model; rotate about its *own* center.
   if(part==='contact'){
     const q=rotate(p.map((x,i)=>x-offset[i]),r);
     return q.map((x,i)=>x+offset[i]+u[i]);
   }
   const footZ=.8;
   const arc=(part==='flexure'||part==='piezo')?nearestArcProgress(p,paths):null;
   const t=arc===null?clamp((p[2]-footZ)/Math.max(h-footZ,.1),0,1):arc;
   const s=t*t*(3-2*t); // cubic Hermite interpolation: fixed base, full motion at top.
   const base=[p[0]*strain,0,0];
   const local=[p[0]-offset[0],p[1]-offset[1],p[2]-h];
   const rotated=rotate(local,r).map((x,i)=>x-local[i]);
   const top=u.map((x,i)=>x+rotated[i]);
   return p.map((x,i)=>x+(1-s)*base[i]+s*top[i]);
 }
 return {transformVertex,computeScale,rotate,nearestArcProgress};
});
