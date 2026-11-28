/* Bounded local diagnostic snapshots. Never restore an engine or candidate. */
(function(root){
  'use strict';
  const key='neuroskin-diagnostic-reports-v1',limit=12,maxBytes=512000,paths=['nonlinear/contact-box','nonlinear/candidate','tile','fusion','tile/optimize'];
  const hex=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
  function record(result){
    const c=result?.diagnostic_context;
    if(!c||c.schema!==1||!paths.includes(c.path)||!hex(c.comparison_key)||!hex(c.solver_hash)||!c.settings||!c.runtime)return null;
    if(c.path==='nonlinear/contact-box'?c.candidate_id!==null:(!c.candidate_id||!hex(c.genome_hash)||!c.selection))return null;
    // Geometry is a disposable preview; keep bounded numerical reports usable.
    try{const {skin_templates,skin_patches,...numerical}=result;const json=JSON.stringify(numerical);if(json.length>maxBytes)return null;return JSON.parse(json);}catch{return null;}
  }
  function identity(r){const c=r.diagnostic_context;return JSON.stringify([c.path,c.comparison_key,c.genome_hash,c.candidate_id,c.selection?.run_id,c.selection?.generation,c.selection?.expected_live_run_id]);}
  function merge(old,added){const map=new Map();for(const raw of [...old,...added]){const r=record(raw);if(r)map.set(identity(r),r);}const all=[...map.values()];if(all.length>limit||JSON.stringify(all).length>maxBytes)throw Error('Report storage limit reached; export or clear saved reports first.');return all;}
  function load(storage){try{const a=JSON.parse(storage.getItem(key)||'[]');return Array.isArray(a)?merge([],a):[];}catch{return [];}}
  function save(storage,old,added){const all=merge(old,added);storage.setItem(key,JSON.stringify(all));return all;}
  function clear(storage){storage.removeItem(key);}
  function matchesFrame(r,context){const c=r.diagnostic_context;if(c.path==='nonlinear/contact-box')return true;
    return c.candidate_id===context.expected_candidate_id&&['selection','index','family','run_id','generation','piezo_count_override','piezo_wiring_override','expected_live_run_id','expected_candidate_id'].every(k=>(c.selection[k]??null)===(context[k]??null));}
  function metrics(r){const c=r.diagnostic_context;
    if(c.path.startsWith('nonlinear/'))return [['Peak force [N]',Math.max(0,...(r.stages||[]).map(s=>s.contact_force_N||0))],['Residual displacement [mm]',r.stages?.at(-1)?.displacement_max_mm],['Inflated members',r.inflated_features??0]];
    if(c.path==='tile/optimize')return [['Screened designs',r.screening.length],['Refined designs',r.refined.length],['Refined Pareto',r.refined_pareto_ids.length]];
    if(c.path==='tile')return [['Grid RMSE [mN]',1000*r.reconstruction_grid_rmse_N],['Transfer condition',r.transfer_condition],['Balance error [N]',r.force_balance_error_N]];
    const f=r.models?.static_stage_pvdf;return [['Fused force RMSE [mN]',1000*f?.force_rmse_norm_N],['Fused position MAE [mm]',f?.position_mae_mm],['PVDF clipping [%]',100*r.pvdf_saturated_sample_fraction_assumed]];
  }
  const api={key,limit,paths,record,identity,merge,load,save,clear,matchesFrame,metrics};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NeuroReports=api;
})(globalThis);
