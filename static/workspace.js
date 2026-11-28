/* One DOM, one controller, one selected candidate. No duplicate engine controls. */
(() => {
  'use strict';
  const main=document.querySelector('main'), header=document.querySelector('header');
  const el=id=>document.getElementById(id);
  const make=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text)n.textContent=text;return n;};
  const button=(id,text,fn)=>{const b=make('button','workspace-button',text);b.id=id;b.type='button';b.onclick=fn;return b;};
  const left=main.querySelector('.left'),stage=main.querySelector('.stage'),right=main.querySelector('.right');
  const archive=main.querySelector('.archive-panel'),libraries=[...main.querySelectorAll('.seed-panel')];
  const tests=[...main.querySelectorAll('.testpanel')],history=main.querySelector('.chart');
  const audit=el('top3Pipeline'),fem=el('femDetails');
  if(!left||!stage||!right||!archive||libraries.length!==2||tests.length!==3||!history||!audit||!fem)return;
  document.body.classList.add('workspace');
  const nav=make('nav','workspace-tabs');nav.setAttribute('aria-label','Workspace views');nav.setAttribute('role','tablist');
  const commands=make('div','workspace-commands');
  const context=make('div','workspace-context');
  const runLabel=make('strong','workspace-run','Live session'),candidateLabel=make('span','workspace-candidate','No candidate selected');
  runLabel.id='workspaceRun';candidateLabel.id='workspaceCandidate';
  const runSwitch=make('select','workspace-run-select');runSwitch.id='workspaceContextSwitch';runSwitch.setAttribute('aria-label','Switch experiment context');
  const live=button('workspaceLive','Return to live',()=>{el('returnLive').click();show('overview');});
  context.append(runSwitch,runLabel,candidateLabel,live);
  const actions=make('div','workspace-actions');
  for(const id of ['start','pause','stop','evaluateAll'])actions.append(el(id));
  commands.append(context,actions);
  const toolbar=make('div','workspace-toolbar');header.before(toolbar);toolbar.append(header,commands,nav);
  // Empty legacy action rows are removed, not cloned. Existing handlers stay attached.
  for(const n of [...left.querySelectorAll('.row')])if(!n.children.length)n.remove();
  const summary=make('small','workspace-summary');summary.id='workspaceSettingsSummary';
  left.insertBefore(summary,el('error'));commands.append(el('error'));
  const followLabel=el('auto').parentElement;stage.querySelector('.bar').append(followLabel);
  const group=(title,ids)=>{
    const d=make('details','workspace-settings advanced-only');d.append(make('summary','',title));
    const body=make('div','workspace-settings-body');d.append(body);
    // Move each control with its label and immediate explanatory small print.
    for(const id of ids){const n=el(id);if(!n)continue;const p=n.parentElement;
      if(p.matches('label')){const note=p.nextElementSibling;body.append(p);if(note?.matches('small'))body.append(note);}
      else{const label=n.previousElementSibling,note=n.nextElementSibling;if(label?.matches('label'))body.append(label);body.append(n);if(note?.matches('small'))body.append(note);}
    }
    left.insertBefore(d,summary);return d;
  };
  group('Search strategy & mutation',['searchStrategy','searchPrecision','explore']);
  group('Compute & population',['cores','population']);
  group('Validation & FEM',['physical_gate','enable_fem','fem_backend','fem_pitch','gate_grid','audit_grid']);
  group('Replay seed',['seed']);
  const profiles=window.NeuroProfiles;let presets=[];try{presets=profiles.load(localStorage);}catch{}
  const profilePanel=make('details','workspace-settings advanced-only');profilePanel.append(make('summary','','Evolution presets'));
  const profileBody=make('div','workspace-settings-body'),profileSelect=make('select');profileSelect.id='workspaceProfileSelect';profileSelect.setAttribute('aria-label','Saved evolution presets');
  const profileName=make('input');profileName.id='workspaceProfileName';profileName.placeholder='Preset name';profileName.maxLength=40;profileName.setAttribute('aria-label','Preset name');
  const profileStatus=make('small','','For the next run only. Does not restore a seed or change a running experiment.');profileStatus.id='workspaceProfileStatus';profileStatus.setAttribute('role','status');
  const profileButtons=make('div','workspace-profile-actions');
  const profileSave=button('workspaceProfileSave','Save / replace',()=>profileAction(()=>{const name=profileName.value.trim();presets=profiles.save(localStorage,presets,name,profiles.validate(profiles.capture(el),el));refreshProfiles(name);profileStatus.textContent='Saved preset '+name;}));
  const profileApply=button('workspaceProfileApply','Load preset',()=>profileAction(()=>{const preset=presets.find(x=>x.name===profileSelect.value);if(!preset)throw Error('Select a preset');profiles.apply(preset.values,el);for(const id of profiles.fields)el(id).dispatchEvent(new Event('input',{bubbles:true}));for(const id of profiles.fields)el(id).dispatchEvent(new Event('change',{bubbles:true}));update();profileStatus.textContent='Loaded '+preset.name+' for the next run. Seed unchanged.';}));
  const profileDelete=button('workspaceProfileDelete','Delete',()=>profileAction(()=>{presets=profiles.remove(localStorage,presets,profileSelect.value);refreshProfiles();profileStatus.textContent='Preset deleted.';}));
  profileButtons.append(profileSave,profileApply,profileDelete);profileBody.append(profileSelect,profileName,profileButtons,profileStatus);profilePanel.append(profileBody);left.insertBefore(profilePanel,summary);
  function profileAllowed(){return !!state&&!archiveRunId&&!startPending&&!['running','paused','stopping'].includes(state.status)&&el('coreinfo').textContent.includes('logical CPUs available')&&el('mode').options.length>3;}
  function profileAction(fn){try{if(!profileAllowed())throw Error('Presets require idle live context and loaded hardware/catalogue settings.');fn();}catch(e){profileStatus.textContent=e.message;}}
  function refreshProfiles(name){profileSelect.replaceChildren(new Option('Select saved preset',''),...presets.map(p=>new Option(p.name,p.name)));profileSelect.value=name||'';profileName.value=name||'';updateProfileButtons();}
  function updateProfileButtons(){const allowed=profileAllowed();profileSave.disabled=!allowed;profileApply.disabled=!allowed||!profileSelect.value;profileDelete.disabled=!allowed||!profileSelect.value;}
  profileSelect.onchange=()=>{profileName.value=profileSelect.value;updateProfileButtons();};
  refreshProfiles();
  // Audit grid had a label in the old pipeline header. Its empty wrapper is harmless.
  const overview=make('section','workspace-overview');main.append(overview);overview.append(left,stage,right);
  stage.querySelector('.bar').classList.add('workspace-modelbar');
  const empty=make('div','workspace-empty');empty.append(make('strong','','Start with a design'),make('p','','Run evolution or choose a reference architecture to inspect its geometry and sensor response.'),button('workspaceBrowse','Browse reference designs',()=>show('library')));el('model').before(empty);
  for(const id of ['piezoOverride','piezoWiring'])el(id).parentElement.classList.add('advanced-only');
  const results=make('section','workspace-stack');tests[0].classList.add('workspace-result');
  const evaluationCards=make('div','workspace-metrics');evaluationCards.id='workspaceEvaluationCards';evaluationCards.setAttribute('aria-live','polite');
  el('allEvalStatus').after(evaluationCards);
  for(const id of ['validationMetrics','allEvalResult']){const pre=el(id),d=make('details','workspace-raw advanced-only');d.append(make('summary','',id==='validationMetrics'?'Validation report':'Full engineering report'));pre.before(d);d.append(pre);}
  results.append(tests[0],audit);
  fem.open=true;const femPanel=make('section','panel workspace-fem');femPanel.append(make('p','workspace-summary','Manual inspection settings apply to Evaluate All. Top-3 evolution settings are in Overview → Validation & FEM.'),fem);
  const signals=make('section','workspace-stack');signals.append(tests[1],tests[2]);
  // The actual selected-geometry plot and controls are moved, never cloned.
  // Overview retains the full-size view; analytical tabs use a compact dock.
  const geometryDocks=new Map();
  for(const [key,host] of [['results',results],['fem',femPanel],['signals',signals]]){
    const dock=make('details','workspace-geometry-dock advanced-only');dock.open=true;
    dock.append(make('summary','','Selected geometry · interactive 3D'));host.prepend(dock);
    geometryDocks.set(key,dock);dock.addEventListener('toggle',resize);
  }
  // Explicit manual refresh actions, using the existing request functions.
  const signalActions=make('div','workspace-signal-actions');
  signalActions.append(button('workspaceCharacterize','Refresh response',()=>runCharacterization()),button('workspaceSpatial','Run spatial scan',()=>runSpatial()));
  signals.prepend(signalActions);
  const library=make('section','workspace-stack');libraries.forEach((n,i)=>{n.querySelector('details').open=i===0;library.append(n);});
  archive.open=true;
  const lab=make('section','panel workspace-lab');
  const labBar=make('div','workspace-labbar');const labContext=make('span','','Select a candidate in Overview or Library.');labContext.id='workspaceLabContext';
  const sync=button('workspaceLabSync','Use current candidate',()=>bindLab(true));
  const standalone=make('a','workspace-button','Open separately');standalone.target='_blank';standalone.rel='noopener';standalone.href='/v30';
  const sessions=make('select','workspace-run-select');sessions.id='workspaceLabSessions';sessions.setAttribute('aria-label','Open Multiscale inspection sessions');
  const close=button('workspaceLabClose','Close session',()=>closeSession());
  const frames=make('div','workspace-lab-sessions');
  labBar.append(labContext,sync,sessions,close,standalone);
  const pinnedGeometry=make('details','workspace-pinned-geometry');pinnedGeometry.open=true;
  const pinnedStatus=make('p','workspace-summary','Select an inspection session.');pinnedStatus.id='workspacePinnedGeometryStatus';
  const pinnedPlot=make('div','workspace-pinned-plot');pinnedPlot.id='workspacePinnedGeometryPlot';
  const pinnedActions=make('div','workspace-pinned-actions');
  const pinnedReset=button('workspacePinnedReset','Reset camera',()=>{if(pinnedPlot._fullLayout)Plotly.relayout(pinnedPlot,{'scene.camera':baseLayout.scene.camera});});
  const pinnedFilm=make('input');pinnedFilm.type='checkbox';pinnedFilm.checked=true;pinnedFilm.id='workspacePinnedPVDF';
  const pinnedFilmLabel=make('label','','PVDF layer');pinnedFilmLabel.prepend(pinnedFilm);
  pinnedActions.append(pinnedFilmLabel,pinnedReset);
  pinnedGeometry.append(make('summary','','Selected geometry · interactive 3D (inspection session)'),pinnedStatus,pinnedActions,pinnedPlot);
  lab.append(labBar,pinnedGeometry,frames);
  const views=[['overview','Overview',overview,false],['results','Results',results,false],['fem','FEM',femPanel,true],['signals','Signals',signals,true],['multiscale','Multiscale',lab,true],['library','Library',library,false],['runs','Runs',archive,false],['history','History',history,true]];
  let active='overview',bound=null,advanced=false,labBusy=false,frame=null;
  const openLabs=new Map(),labLimit=3;
  let geometryRequest=0,pinnedDraw=Promise.resolve();
  function mountGeometry(){
    const dock=advanced?geometryDocks.get(active):null;
    const target=dock||overview;
    if(stage.parentElement!==target){
      stage.classList.toggle('workspace-compact-stage',!!dock);
      if(dock)dock.append(stage);else overview.insertBefore(stage,right);
    }
  }
  function purgePlot(plot){if(plot._fullLayout||plot.data)Plotly.purge(plot);}
  function renderPinnedGeometry(){
    const revision=++geometryRequest, key=bound?JSON.stringify(bound):null,item=openLabs.get(key);
    if(active!=='multiscale'||!pinnedGeometry.open||!item){
      pinnedDraw=pinnedDraw.catch(()=>{}).then(()=>{if(revision===geometryRequest){purgePlot(pinnedPlot);pinnedStatus.textContent='Select an inspection session.';}});
      return;
    }
    const p=item.context;
    pinnedStatus.textContent='Loading '+p.expected_candidate_id+' · undeformed geometry';
    pinnedDraw=pinnedDraw.catch(()=>{}).then(async()=>{
      if(revision!==geometryRequest)return;
      purgePlot(pinnedPlot);
      try{
        if(!item.geometry){
          const q=new URLSearchParams({kind:p.selection,index:p.index,family:p.family,quality:'10'});
          for(const k of ['run_id','generation','piezo_count_override','piezo_wiring_override','expected_live_run_id','expected_candidate_id'])if(p[k]!=null)q.set(k,p[k]);
          const res=await fetch('/api/mesh?'+q);if(!res.ok)throw Error('Geometry unavailable ('+res.status+')');
          const data=await res.json();if(String(data.candidate.id)!==p.expected_candidate_id)throw Error('Geometry identity mismatch');
          item.geometry=data;
        }
        if(revision!==geometryRequest)return;
        const traces=item.geometry.model.components.filter(c=>c.part!=='piezo'||pinnedFilm.checked).map(c=>({
          type:'mesh3d',name:c.part,x:c.vertices.map(v=>v[0]),y:c.vertices.map(v=>v[1]),z:c.vertices.map(v=>v[2]),
          i:c.faces.map(f=>f[0]),j:c.faces.map(f=>f[1]),k:c.faces.map(f=>f[2]),color:colors[c.part]||'#a0b3bd',hoverinfo:'skip',opacity:1,flatshading:false
        }));
        await Plotly.react(pinnedPlot,traces,{...baseLayout,uirevision:key},{responsive:true,displaylogo:false});
        if(revision===geometryRequest)pinnedStatus.textContent=p.expected_candidate_id+' · '+p.family+' · pinned undeformed geometry · PVDF '+(p.piezo_count_override??'as saved')+' / wiring '+(p.piezo_wiring_override??'as saved');
        else purgePlot(pinnedPlot);
      }catch(e){if(revision===geometryRequest){purgePlot(pinnedPlot);pinnedStatus.textContent='Pinned geometry unavailable: '+e.message;}}
    });
  }
  pinnedFilm.onchange=renderPinnedGeometry;pinnedGeometry.addEventListener('toggle',renderPinnedGeometry);
  const femGrid=el('femPreviewGrid'),preview=window.NeuroFEMPreviews;
  const femLegend=make('p','workspace-fem-legend','Run Evaluate All to compute four standard load cases.');femLegend.id='workspaceFEMLegend';
  const femNote=make('small','workspace-summary','Same reference geometry, visual scale and color limits. Standard loads are independent of the custom inspector settings.');
  const femCards=make('div','workspace-fem-grid'),plots=new Map();
  const femActions=make('div','workspace-fem-actions');
  const resetCases=button('workspaceResetFEMCameras','Reset all cameras',()=>{for(const {plot} of plots.values())if(plot._fullLayout)Plotly.relayout(plot,{'scene.camera':baseLayout.scene.camera});});
  const swatch=make('span','workspace-field-swatch');swatch.setAttribute('aria-label','Viridis low to high field scale');
  femActions.append(swatch,resetCases);
  for(const name of preview.order){
    const card=make('details','workspace-fem-card');card.open=true;card.dataset.case=name;
    const plot=make('div','workspace-fem-preview-plot');plot.id='femPreview-'+name;
    const caption=make('small','workspace-fem-case-metrics','No solved field yet.');
    const expand=button('femExpand-'+name,'Expand panel',()=>{const wide=!card.classList.contains('workspace-fem-wide');for(const v of plots.values()){v.card.classList.remove('workspace-fem-wide');v.expand.textContent='Expand panel';v.expand.setAttribute('aria-pressed','false');}card.classList.toggle('workspace-fem-wide',wide);expand.textContent=wide?'Restore grid':'Expand panel';expand.setAttribute('aria-pressed',String(wide));resize();});expand.setAttribute('aria-pressed','false');
    const toolbar=make('div','workspace-fem-card-toolbar');toolbar.append(caption,expand);
    card.append(make('summary','',preview.labels[name]),toolbar,plot);femCards.append(card);plots.set(name,{card,plot,caption,expand});
    card.addEventListener('toggle',()=>renderFEMPreviews());
  }
  femGrid.append(femNote,femLegend,femActions,femCards);
  let previewDraw=Promise.resolve(),previewRevision=0,lastPreviewPacket=null,femStale=false;
  function markFEMStale(){femStale=true;renderFEMPreviews();}
  function renderFEMPreviews(){
    const packet=femPreviewFields,rev=++previewRevision;
    if(packet!==lastPreviewPacket){lastPreviewPacket=packet;femStale=false;}
    const visible=active==='fem'&&advanced&&fem.open;
    const key=el('femColor').value,scale=Number(el('femScale').value),ghost=el('femReference').checked;
    const valid=packet?.schema===1&&preview.order.every(name=>packet.cases?.[name]);
    const units={stress_vm_MPa:'von Mises stress [MPa]',principal_strain:'Principal strain [1]',displacement_mm:'Displacement [mm]'};
    const range=valid&&visible?preview.bounds(packet,key,scale):null;
    femLegend.textContent=valid?(femStale?'Settings changed — last solved fields only. ':'')+
      (range?units[key]+' · shared displayed range '+range.cmin.toPrecision(4)+' to '+range.cmax.toPrecision(4)+' · '+scale+'× visual scale · '+packet.display_surface_triangles+' triangles'+(packet.display_downsampled?' (sampled)':''):'Four standard load fields available.'):
      (femPreviewError?'FEM comparison fields unavailable: '+femPreviewError:'No solved fields. Select a receptor and run Evaluate All with FEM enabled.');
    femLegend.classList.toggle('workspace-stale',femStale&&valid);femActions.hidden=!valid;
    previewDraw=previewDraw.catch(()=>{}).then(async()=>{
      if(rev!==previewRevision)return;
      for(const [name,{card,plot,caption}] of plots){
        if(rev!==previewRevision)return;
        if(!valid){caption.textContent='No solved field yet.';purgePlot(plot);continue;}
        const c=packet.cases[name],m=c.metrics||{},l=c.load||{},fmt=n=>Number.isFinite(n)?Number(n).toPrecision(4):'—';
        caption.textContent='F ['+(l.load_force_N||[]).join(', ')+'] N · offset ['+(l.offset_mm||[]).join(', ')+'] mm · Mz '+(l.torque_z_Nmm??0)+' Nmm · max |u| '+fmt(m.max_displacement_mm)+' mm · max stress '+fmt(m.max_von_mises_MPa)+' MPa';
        if(!visible||!card.open){purgePlot(plot);continue;}
        const scene={...baseLayout.scene,xaxis:{...baseLayout.scene.xaxis,range:range.ranges[0]},yaxis:{...baseLayout.scene.yaxis,range:range.ranges[1]},zaxis:{...baseLayout.scene.zaxis,range:range.ranges[2]}};
        try{await Plotly.react(plot,preview.traces(packet,name,key,scale,ghost,range),{...baseLayout,scene,showlegend:false,uirevision:'standard-'+name+'-'+selectionIdentity()},{responsive:true,displaylogo:false});}
        catch(e){caption.textContent+=' · preview unavailable: '+e.message;}
      }
    });
  }
  function isFEMVisible(){return active==='fem'&&advanced&&fem.open;}
  function updateDetailedFEM(){if(isFEMVisible()){renderSolvedFEM();renderLaminateShell();}else{purgePlot(el('femPlot'));purgePlot(el('laminatePlot'));}}
  fem.addEventListener('toggle',()=>{updateDetailedFEM();if(!isFEMVisible())renderFEMPreviews();});
  const reports=window.NeuroReports;
  let saved=[];try{saved=reports.load(localStorage);}catch{}
  const comparison=make('details','workspace-comparison');comparison.id='workspaceComparison';comparison.append(make('summary','','Compare & save inspection reports'));
  const reportActions=make('div','workspace-report-actions');
  const reportType=make('select','workspace-run-select');reportType.id='workspaceReportType';reportType.setAttribute('aria-label','Diagnostic comparison type');
  for(const [path,label] of [['tile','Skin tile'],['fusion','Sensor fusion'],['nonlinear/candidate','Candidate contact'],['nonlinear/contact-box','Verification box']])reportType.append(new Option(label,path));
  const saveReports=button('workspaceSaveReports','Save current reports',()=>{try{saved=reports.save(localStorage,saved,currentReports());renderReports('Saved locally. No calculations resumed.');}catch(e){renderReports(e.message);}});
  const exportReports=button('workspaceExportReports','Export JSON',()=>{const blob=new Blob([JSON.stringify({schema:1,reports:allReports()},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=make('a');a.href=url;a.download='neuroskin-diagnostic-reports.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  const clearReports=button('workspaceClearReports','Clear saved reports',()=>{try{reports.clear(localStorage);saved=[];renderReports('Saved reports cleared. Open sessions unchanged.');}catch(e){renderReports(e.message);}});
  const reportStatus=make('p','workspace-summary');reportStatus.id='workspaceReportStatus';reportStatus.setAttribute('role','status');
  const reportTable=make('div','workspace-report-table');reportTable.id='workspaceReportTable';
  reportActions.append(reportType,saveReports,exportReports,clearReports);comparison.append(reportActions,reportStatus,reportTable);lab.append(comparison);
  reportType.onchange=()=>renderReports();
  function currentReports(){return [...openLabs.values()].flatMap(item=>[...item.reports.values()]);}
  function allReports(){const map=new Map();for(const r of [...saved,...currentReports()])map.set(reports.identity(r),r);return [...map.values()];}
  function renderReports(message){
    const current=currentReports(),all=allReports(),rows=all.filter(r=>r.diagnostic_context.path===reportType.value);
    saveReports.disabled=!current.length;exportReports.disabled=!all.length;clearReports.disabled=!saved.length;
    reportStatus.textContent=message||`${current.length} latest successful open-session reports · ${saved.length} saved locally. Compare only matching condition keys. Diagnostic results, not qualification.`;
    reportTable.replaceChildren();if(!rows.length){reportTable.append(make('p','workspace-summary','Run an analysis in one or more sessions to compare results.'));return;}
    const groups=new Map();for(const r of rows){const key=r.diagnostic_context.comparison_key;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r);}
    if(groups.size>1)reportTable.append(make('p','workspace-stale','Different experiment settings or solver versions: separate groups, no cross-group ranking.'));
    const currentIds=new Set(current.map(reports.identity));
    for(const [key,group] of groups){const c=group[0].diagnostic_context,block=make('section','workspace-report-group');
      block.append(make('strong','','Conditions '+key.slice(0,12)+' · '+group.length+' report(s)'));
      const details=make('details','workspace-raw');details.append(make('summary','','Effective settings & provenance'),make('pre','',JSON.stringify({settings:c.settings,solver_hash:c.solver_hash,runtime:c.runtime},null,2)));block.append(details);
      const wrap=make('div','workspace-report-scroll'),table=make('table'),head=make('tr');for(const name of ['Candidate / context',...reports.metrics(group[0]).map(m=>m[0])])head.append(make('th','',name));table.append(head);
      for(const r of group){const d=r.diagnostic_context,tr=make('tr'),cell=make('td');cell.append(make('strong','',d.candidate_id||'Reference box'),make('small','',`${d.selection?.run_id||d.selection?.expected_live_run_id||'Library / reference'} · ${d.genome_hash?.slice(0,10)||'box'} · ${currentIds.has(reports.identity(r))?'open':'saved'}`));tr.append(cell);
        for(const [,value] of reports.metrics(r))tr.append(make('td','',Number.isFinite(value)?Number(value).toPrecision(5):'—'));table.append(tr);}
      wrap.append(table);block.append(wrap);reportTable.append(block);
    }
  }
  const panels=new Map(),tabs=new Map();
  for(const [id,title,node,expert] of views){
    const pane=make('section','workspace-pane');pane.id='workspace-panel-'+id;pane.setAttribute('role','tabpanel');pane.setAttribute('aria-labelledby','workspace-tab-'+id);pane.append(node);main.append(pane);panels.set(id,pane);
    const tab=button('workspace-tab-'+id,title,()=>show(id));tab.setAttribute('role','tab');tab.setAttribute('aria-controls',pane.id);if(expert)tab.classList.add('advanced-only');nav.append(tab);tabs.set(id,tab);
  }
  const simpleLabels={all:'Everything', 'single:all':'Single-stage designs','hybrid:all':'All two-stage hybrids',balanced:'Balanced',touch:'Sensitive touch',robust:'Strain robustness',dynamic:'Dynamic events'};
  function updateLabels(){for(const id of ['mode','objective'])for(const opt of el(id).options){if(!opt.dataset.fullLabel)opt.dataset.fullLabel=opt.textContent;opt.title=opt.dataset.fullLabel;const text=advanced?opt.dataset.fullLabel:(simpleLabels[opt.value]||opt.dataset.fullLabel);if(opt.textContent!==text)opt.textContent=text;}}
  function mode(){advanced=!document.body.classList.contains('basic');el('basicMode').setAttribute('aria-pressed',String(!advanced));el('advancedMode').setAttribute('aria-pressed',String(advanced));updateLabels();if(!advanced&&views.find(v=>v[0]===active)?.[3])show('overview');else{mountGeometry();update();resize();}}
  function resize(){requestAnimationFrame(()=>{for(const plot of main.querySelectorAll('.js-plotly-plot'))if(plot.getClientRects().length&&plot._fullLayout)try{Plotly.Plots.resize(plot);}catch{}});}
  function show(id){if(!panels.has(id)||(!advanced&&views.find(v=>v[0]===id)[3]))id='overview';active=id;
    for(const [key,p] of panels){p.hidden=key!==id;const t=tabs.get(key);t.setAttribute('aria-selected',String(key===id));t.tabIndex=key===id?0:-1;}
    if(id==='multiscale'&&!bound)bindLab(false);mountGeometry();update();renderPinnedGeometry();updateDetailedFEM();if(!isFEMVisible())renderFEMPreviews();resize();
  }
  nav.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;const visible=views.filter(v=>advanced||!v[3]).map(v=>v[0]);let i=visible.indexOf(active);i=e.key==='Home'?0:e.key==='End'?visible.length-1:(i+(e.key==='ArrowRight'?1:-1)+visible.length)%visible.length;e.preventDefault();show(visible[i]);tabs.get(visible[i]).focus();});
  function current(){const p=selectedPayload(),c=findCandidate(currentSelection);if(!p||!c)return null;
    const libraryKind=['seed','hybrid'].includes(p.selection);return {selection:p.selection,index:p.index,family:c.family,run_id:p.run_id,generation:p.generation,piezo_count_override:p.piezo_count_override,piezo_wiring_override:p.piezo_wiring_override,expected_live_run_id:!p.run_id&&!libraryKind?state?.id:null,expected_candidate_id:String(c.id)};}
  function labUrl(p,embedded){const q=new URLSearchParams();for(const [k,v] of Object.entries(p))if(v!=null)q.set(k,v);if(embedded)q.set('embedded','1');return '/v30?'+q;}
  function activateSession(key){
    const item=openLabs.get(key);if(!item||labBusy)return;
    for(const entry of openLabs.values()){entry.frame.hidden=true;entry.frame.removeAttribute('id');}
    bound=item.context;frame=item.frame;frame.id='workspaceLabFrame';frame.hidden=false;
    standalone.href=labUrl(bound,false);labBusy=item.busy;update();renderPinnedGeometry();
  }
  function bindLab(force){const p=current();if(!p||labBusy)return;const key=JSON.stringify(p);
    if(openLabs.has(key)){activateSession(key);return;}
    if(openLabs.size>=labLimit){update();return;}
    const f=make('iframe','workspace-labframe');f.title='Multiscale engineering lab';f.hidden=true;f.src=labUrl(p,true);
    openLabs.set(key,{context:p,frame:f,busy:false,reports:new Map()});frames.append(f);activateSession(key);
  }
  function closeSession(){if(!bound||labBusy)return;const key=JSON.stringify(bound),item=openLabs.get(key);if(!item)return;
    item.frame.remove();openLabs.delete(key);bound=null;frame=null;labBusy=false;standalone.href='/v30';
    if(openLabs.size)activateSession(openLabs.keys().next().value);else{update();renderPinnedGeometry();}renderReports();
  }
  sessions.onchange=()=>activateSession(sessions.value);
  function updateSessions(p){const opts=[...openLabs].map(([key,item])=>new Option(`${item.context.expected_candidate_id} · ${item.context.run_id||'live / library'}${item.context.generation!=null?' / gen '+item.context.generation:''} · PVDF ${item.context.piezo_count_override??'saved'} / wiring ${item.context.piezo_wiring_override??'saved'}`,key));
    const sig=JSON.stringify(opts.map(o=>[o.value,o.textContent]));if(sessions.dataset.options!==sig){sessions.replaceChildren(...opts);sessions.dataset.options=sig;}
    sessions.hidden=!openLabs.size;sessions.disabled=labBusy;sessions.value=bound?JSON.stringify(bound):'';close.hidden=!bound;close.disabled=labBusy;
    const full=openLabs.size>=labLimit&&p&&!openLabs.has(JSON.stringify(p));sync.disabled=!p||labBusy||!!full;sync.textContent=full?'Close a session first':p&&openLabs.has(JSON.stringify(p))?'Switch to current candidate':'Use current candidate';
  }
  function updateRuns(){const opts=[new Option('Live experiment',''),...[...el('archiveSelect').options].filter(o=>o.value).map(o=>new Option(o.textContent,o.value))];const key=JSON.stringify(opts.map(o=>[o.value,o.textContent]));if(runSwitch.dataset.options!==key){runSwitch.replaceChildren(...opts);runSwitch.dataset.options=key;}runSwitch.value=archiveRunId||'';}
  runSwitch.onchange=()=>{if(runSwitch.value){el('archiveSelect').value=runSwitch.value;el('openArchive').click();}else el('returnLive').click();show('overview');};
  function update(){const p=current();updateRuns();runLabel.textContent=archiveRunId?`Archive ${archiveRunId}${archiveGeneration!=null?' · generation '+archiveGeneration:''}`:(p&&['seed','hybrid'].includes(p.selection)?'Library preview':'Live session');live.hidden=!archiveRunId;
    const c=findCandidate(currentSelection);candidateLabel.textContent=p?`${p.family} / ${c.genome.topology} · ${p.expected_candidate_id}`:'No candidate selected';
    empty.hidden=!!p;el('model').classList.toggle('workspace-model-empty',!p);
    if(archiveRunId)el('start').disabled=true;
    summary.textContent=`${el('cores').value} CPU · population ${el('population').value} · ${el('enable_fem').checked?`${el('fem_backend').value.toUpperCase()} ${el('fem_pitch').value} mm`:'FEM off'} · ${el('physical_gate').checked?'gate on':'gate off'}`;
    updateProfileButtons();updateSessions(p);const mismatch=bound&&JSON.stringify(bound)!==JSON.stringify(p);labContext.textContent=bound?`${bound.run_id?'Archive '+bound.run_id:'Live / library'} · ${bound.family} · ${bound.expected_candidate_id}${mismatch?' — selection changed; use current candidate to rebind':''}${labBusy?' · computing':''}`:'Select a candidate in Overview or Library.';labContext.classList.toggle('workspace-stale',Boolean(mismatch));
  }
  function renderEvaluation(data){evaluationCards.replaceChildren();if(!data)return;
    const a=data.audit||{},v=data.validation_v30||{},m=v.metrics||{},d=m.decoder_holdout||{},f=data.fem;
    const fmt=(n,digits=3)=>Number.isFinite(n)?Number(n).toFixed(digits):'—';
    const add=(name,value,note)=>{const card=make('div','workspace-metric');card.append(make('small','',name),make('strong','',value));if(note)card.append(make('small','',note));evaluationCards.append(card);};
    add('Audit utility',fmt(a.audit_score,2)+'/100',a.feasible?'Screen passes':'Not feasible');
    add('Evidence tier',v.tier||'—',v.pass_current_tier?'Synthetic screen PASS':'Not qualified');
    add('Force RMSE',Number.isFinite(d.force_rmse_norm_N)?fmt(1000*d.force_rmse_norm_N,2)+' mN':'—','Held-out, synthetic');
    add('Position MAE',fmt(d.position_mae_mm)+' mm','Held-out, synthetic');
    add('Mechanical FEM',!f?'Not run':f.failed?'Failed':f.feasible_linear?'Linear screen PASS':'Not feasible',f?.inflated_features?`${f.inflated_features} inflated members`:null);
  }
  // The legacy mode toggles remain authoritative; observe only presentation/state.
  new MutationObserver(mode).observe(document.body,{attributes:true,attributeFilter:['class']});
  new MutationObserver(update).observe(el('viewtitle'),{childList:true,characterData:true,subtree:true});
  new MutationObserver(update).observe(el('archiveNotice'),{childList:true,characterData:true,subtree:true});
  new MutationObserver(updateRuns).observe(el('archiveSelect'),{childList:true,subtree:true});
  new MutationObserver(()=>{updateLabels();updateProfileButtons();}).observe(el('mode'),{childList:true,subtree:true});
  new MutationObserver(updateProfileButtons).observe(el('coreinfo'),{childList:true,subtree:true});
  // Native selects emit input before change; don't reset a pending context choice.
  const onControlChange=e=>{if(e.target!==runSwitch&&e.target!==sessions)update();};
  document.addEventListener('change',onControlChange);document.addEventListener('input',onControlChange);
  el('multiscaleLab').onclick=()=>{setView('advanced');advanced=true;show('multiscale');};
  el('multiscaleLab').classList.add('advanced-only');
  // Preview actions in the library should return directly to the 3D workspace.
  library.addEventListener('click',e=>{if(e.target.closest('[data-hybrid],[data-preview-seed]'))show('overview');});
  archive.addEventListener('click',e=>{if(e.target.closest('#openArchive,#openStage,#returnLive'))show('overview');});
  window.addEventListener('message',e=>{if(e.origin!==location.origin)return;const item=[...openLabs.values()].find(x=>x.frame.contentWindow===e.source);if(!item)return;if(e.data?.type==='neuroskin:lab-height'&&Number.isFinite(e.data.height))item.frame.style.height=Math.max(500,Math.min(18000,e.data.height+12))+'px';else if(e.data?.type==='neuroskin:lab-report'){const r=reports.record(e.data.result);if(r&&reports.matchesFrame(r,item.context)){item.reports.set(r.diagnostic_context.path,r);renderReports();}}else if(e.data?.type==='neuroskin:lab-busy'&&typeof e.data.busy==='boolean'){item.busy=e.data.busy;if(item.frame===frame){labBusy=item.busy;update();}}});
  window.NeuroWorkspace={show,update,resize,renderEvaluation,renderFEMPreviews,markFEMStale,isFEMVisible};
  mode();show('overview');renderReports();
})();
