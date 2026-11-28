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
  header.after(commands,nav);
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
  // Audit grid had a label in the old pipeline header. Its empty wrapper is harmless.
  const overview=make('section','workspace-overview');main.append(overview);overview.append(left,stage,right);
  stage.querySelector('.bar').classList.add('workspace-modelbar');
  for(const id of ['piezoOverride','piezoWiring'])el(id).parentElement.classList.add('advanced-only');
  const results=make('section','workspace-stack');tests[0].classList.add('workspace-result');results.append(audit,tests[0]);
  fem.open=true;const femPanel=make('section','panel workspace-fem');femPanel.append(fem);
  const signals=make('section','workspace-stack');signals.append(tests[1],tests[2]);
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
  const frame=make('iframe','workspace-labframe');frame.title='Multiscale engineering lab';frame.id='workspaceLabFrame';frame.hidden=true;
  labBar.append(labContext,sync,standalone);lab.append(labBar,frame);
  const views=[['overview','Overview',overview,false],['results','Results',results,false],['fem','FEM',femPanel,true],['signals','Signals',signals,true],['multiscale','Multiscale',lab,true],['library','Library',library,false],['runs','Runs',archive,false],['history','History',history,true]];
  let active='overview',bound=null,advanced=false;
  const panels=new Map(),tabs=new Map();
  for(const [id,title,node,expert] of views){
    const pane=make('section','workspace-pane');pane.id='workspace-panel-'+id;pane.setAttribute('role','tabpanel');pane.setAttribute('aria-labelledby','workspace-tab-'+id);pane.append(node);main.append(pane);panels.set(id,pane);
    const tab=button('workspace-tab-'+id,title,()=>show(id));tab.setAttribute('role','tab');tab.setAttribute('aria-controls',pane.id);if(expert)tab.classList.add('advanced-only');nav.append(tab);tabs.set(id,tab);
  }
  function mode(){advanced=!document.body.classList.contains('basic');el('basicMode').setAttribute('aria-pressed',String(!advanced));el('advancedMode').setAttribute('aria-pressed',String(advanced));if(!advanced&&views.find(v=>v[0]===active)?.[3])show('overview');else update();}
  function resize(){requestAnimationFrame(()=>{for(const plot of main.querySelectorAll('.js-plotly-plot'))if(plot.getClientRects().length&&plot._fullLayout)try{Plotly.Plots.resize(plot);}catch{}});}
  function show(id){if(!panels.has(id)||(!advanced&&views.find(v=>v[0]===id)[3]))id='overview';active=id;
    for(const [key,p] of panels){p.hidden=key!==id;const t=tabs.get(key);t.setAttribute('aria-selected',String(key===id));t.tabIndex=key===id?0:-1;}
    if(id==='multiscale'&&!bound)bindLab(false);update();resize();
  }
  nav.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;const visible=views.filter(v=>advanced||!v[3]).map(v=>v[0]);let i=visible.indexOf(active);i=e.key==='Home'?0:e.key==='End'?visible.length-1:(i+(e.key==='ArrowRight'?1:-1)+visible.length)%visible.length;e.preventDefault();show(visible[i]);tabs.get(visible[i]).focus();});
  function current(){const p=selectedPayload(),c=findCandidate(currentSelection);if(!p||!c)return null;
    const libraryKind=['seed','hybrid'].includes(p.selection);return {selection:p.selection,index:p.index,family:c.family,run_id:p.run_id,generation:p.generation,piezo_count_override:p.piezo_count_override,piezo_wiring_override:p.piezo_wiring_override,expected_live_run_id:!p.run_id&&!libraryKind?state?.id:null,expected_candidate_id:String(c.id)};}
  function labUrl(p,embedded){const q=new URLSearchParams();for(const [k,v] of Object.entries(p))if(v!=null)q.set(k,v);if(embedded)q.set('embedded','1');return '/v30?'+q;}
  function bindLab(force){const p=current();if(!p)return;if(bound&&JSON.stringify(bound)===JSON.stringify(p)&&!force)return;bound=p;frame.hidden=false;frame.src=labUrl(p,true);standalone.href=labUrl(p,false);update();}
  function updateRuns(){const opts=[new Option('Live experiment',''),...[...el('archiveSelect').options].filter(o=>o.value).map(o=>new Option(o.textContent,o.value))];const key=JSON.stringify(opts.map(o=>[o.value,o.textContent]));if(runSwitch.dataset.options!==key){runSwitch.replaceChildren(...opts);runSwitch.dataset.options=key;}runSwitch.value=archiveRunId||'';}
  runSwitch.onchange=()=>{if(runSwitch.value){el('archiveSelect').value=runSwitch.value;el('openArchive').click();}else el('returnLive').click();show('overview');};
  function update(){const p=current();updateRuns();runLabel.textContent=archiveRunId?`Archive ${archiveRunId}${archiveGeneration!=null?' · generation '+archiveGeneration:''}`:(p&&['seed','hybrid'].includes(p.selection)?'Library preview':'Live session');live.hidden=!archiveRunId;
    candidateLabel.textContent=p?`${p.family} · ${p.expected_candidate_id}`:'No candidate selected';
    if(archiveRunId)el('start').disabled=true;
    summary.textContent=`${el('cores').value} CPU · population ${el('population').value} · ${el('enable_fem').checked?'FEM on':'FEM off'} · ${el('physical_gate').checked?'gate on':'gate off'}`;
    sync.disabled=!p;const mismatch=bound&&JSON.stringify(bound)!==JSON.stringify(p);labContext.textContent=bound?`${bound.run_id?'Archive '+bound.run_id:'Live / library'} · ${bound.family} · ${bound.expected_candidate_id}${mismatch?' — selection changed; use current candidate to rebind':''}`:'Select a candidate in Overview or Library.';labContext.classList.toggle('workspace-stale',Boolean(mismatch));
  }
  // The legacy mode toggles remain authoritative; observe only presentation/state.
  new MutationObserver(mode).observe(document.body,{attributes:true,attributeFilter:['class']});
  new MutationObserver(update).observe(el('viewtitle'),{childList:true,characterData:true,subtree:true});
  new MutationObserver(update).observe(el('archiveNotice'),{childList:true,characterData:true,subtree:true});
  new MutationObserver(updateRuns).observe(el('archiveSelect'),{childList:true,subtree:true});
  document.addEventListener('change',update);document.addEventListener('input',update);
  el('multiscaleLab').onclick=()=>{setView('advanced');advanced=true;show('multiscale');};
  el('multiscaleLab').classList.add('advanced-only');
  // Preview actions in the library should return directly to the 3D workspace.
  library.addEventListener('click',e=>{if(e.target.closest('[data-hybrid],[data-preview-seed]'))show('overview');});
  archive.addEventListener('click',e=>{if(e.target.closest('#openArchive,#openStage,#returnLive'))show('overview');});
  window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===frame.contentWindow&&e.data?.type==='neuroskin:lab-height'&&Number.isFinite(e.data.height))frame.style.height=Math.max(500,Math.min(18000,e.data.height+12))+'px';});
  window.NeuroWorkspace={show,update,resize};
  mode();show('overview');
})();
