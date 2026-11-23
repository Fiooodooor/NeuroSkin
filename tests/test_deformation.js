const assert=require('node:assert/strict');
const D=require('../static/deformation.js');
const g={height:6,pad_offset_x:1,pad_offset_y:-.5};
const m={displacement_mm:[.2,-.1,-.3],rotation_rad:[0,0,.1],substrate_strain:0};
const close=(a,b,t=1e-8)=>assert.ok(Math.abs(a-b)<t,`${a} != ${b}`);
// Fixed substrate & basal electrode must not move from pad pressure.
assert.deepEqual(D.transformVertex('base',[2,0,.4],m,g,1),[2,0,.4]);
assert.deepEqual(D.transformVertex('sensor',[2,0,.8],m,g,1),[2,0,.8]);
// A point at pad center moves by exactly the computed rigid-body translation.
const top=D.transformVertex('contact',[1,-.5,6],m,g,1); top.forEach((x,i)=>close(x,[1.2,-.6,5.7][i]));
// Rotation around pad center (not global origin).
const p=D.transformVertex('contact',[2,-.5,6],m,g,1);
close(p[0],1.2+Math.cos(.1));close(p[1],-.6+Math.sin(.1));close(p[2],5.7);
// Flexure rooted at base and following pad at top.
assert.deepEqual(D.transformVertex('flexure',[3,0,.8],m,g,1),[3,0,.8]);
const mid=D.transformVertex('flexure',[3,0,3.4],m,g,1);
assert.ok(mid[2]<3.4&&mid[2]>3.1);
// Stretch moves base and sensors affinely, rather than applying fictitious pad compression.
const stretch={displacement_mm:[0,0,0],rotation_rad:[0,0,0],substrate_strain:.05};
close(D.transformVertex('base',[4,1,.4],stretch,g,1)[0],4.2);
close(D.transformVertex('sensor',[4,1,.8],stretch,g,1)[0],4.2);
// Scaling is bounded for extremely soft candidates, keeping preview inspectable.
const dangerous={displacement_mm:[0,0,-30],rotation_rad:[0,0,2],substrate_strain:0};
const diag=D.computeScale(dangerous,g,12);assert.ok(diag.capped);assert.ok(diag.effectiveScale<1);
// Negative/zero loads should preserve geometry (no phantom movement).
const zero={displacement_mm:[0,0,0],rotation_rad:[0,0,0],substrate_strain:0};
assert.deepEqual(D.transformVertex('contact',[1,2,6],zero,g,3),[1,2,6]);
console.log('8 deformation regression assertions passed');
// Centerline arc length should track the actual bent leg instead of assuming Z progression.
const path=[[[0,0,.8],[3,0,3],[0,0,6]]];
close(D.nearestArcProgress([0,0,.8],path),0);
close(D.nearestArcProgress([0,0,6],path),1);
const deformedTop=D.transformVertex('flexure',[0,0,6],m,g,1,path);
const rigidEndpoint=D.transformVertex('contact',[0,0,6],m,g,1);
deformedTop.forEach((x,i)=>close(x,rigidEndpoint[i]));
const deformedBase=D.transformVertex('flexure',[0,0,.8],m,g,1,path);
deformedBase.forEach((x,i)=>close(x,[0,0,.8][i]));

const film=D.transformVertex('piezo',[0,0,6],m,g,1,path);film.forEach((x,i)=>close(x,rigidEndpoint[i]));
