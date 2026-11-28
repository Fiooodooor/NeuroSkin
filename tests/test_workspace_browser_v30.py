"""Opt-in full browser regression against the local FastAPI server.

CI: install Playwright + Chromium, set NEUROSKIN_BROWSER=1, run this file.
No external service, hardware or physical T3 data is required.
"""
import copy
import json
import os
import socket
import threading
import time
import pytest

pytestmark=pytest.mark.skipif(os.environ.get('NEUROSKIN_BROWSER')!='1',reason='Opt-in Chromium integration test')


@pytest.fixture
def app_url(tmp_path,monkeypatch):
    import uvicorn
    import server
    from archive_store import ArchiveStore
    archives=ArchiveStore(tmp_path/'runs')
    monkeypatch.setattr(server,'ARCHIVES',archives)
    c=copy.deepcopy(server.select_candidate('hybrid','h01_serpentine_quadrant','quadrant'))
    c.update(id='archive-candidate',generation=2)
    state=server.EVO.empty()
    state.update(id='browser_archive',status='completed',generation=2,elapsed=3.,best=c,gallery=[c],champions={c['family']:c})
    folder=archives.path('browser_archive');folder.mkdir()
    (folder/'results.json').write_text(json.dumps(state),encoding='utf-8')
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    runner=uvicorn.Server(uvicorn.Config(server.app,log_level='error',lifespan='on'))
    worker=threading.Thread(target=runner.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
    try:
        deadline=time.monotonic()+15
        while not runner.started and worker.is_alive() and time.monotonic()<deadline:time.sleep(.05)
        assert runner.started,'FastAPI browser test server did not start'
        yield f'http://127.0.0.1:{port}'
    finally:
        runner.should_exit=True;worker.join(timeout=15);sock.close()
        assert not worker.is_alive(),'Browser test server failed to shut down'


def test_workspace_modes_context_and_multiscale(app_url):
    from playwright.sync_api import sync_playwright,expect
    import re
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1500,'height':1000})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(app_url,wait_until='domcontentloaded')
        expect(page.locator('#workspace-tab-overview')).to_be_visible(timeout=20000)
        expect(page.locator('.workspace-tabs button:visible')).to_have_count(4)
        page.locator('#advancedMode').click()
        expect(page.locator('.workspace-tabs button:visible')).to_have_count(8)
        expect(page.locator('#workspaceComputeStatus')).to_contain_text('Heavy-compute slot available',timeout=20000)
        page.locator('.workspace-settings').filter(has_text='Compute activity').locator('summary').click()
        expect(page.locator('#workspaceComputeHistory')).to_contain_text('Queue: disabled')
        page.locator('.workspace-settings').filter(has_text='Validation & FEM').locator('summary').click()
        page.locator('#fem_pitch').select_option('0.625')
        page.locator('.workspace-settings').filter(has_text='Evolution presets').locator('summary').click()
        expect(page.locator('#workspaceProfileSave')).to_be_enabled(timeout=20000)
        page.locator('#workspaceProfileName').fill('Browser preset')
        page.locator('#workspaceProfileSave').click()
        expect(page.locator('#workspaceProfileStatus')).to_contain_text('Saved preset')
        seed=page.locator('#seed').input_value()
        page.locator('#fem_pitch').select_option('1.25')
        page.locator('#workspaceProfileApply').click()
        assert page.locator('#fem_pitch').input_value()=='0.625'
        assert page.locator('#seed').input_value()==seed
        page.locator('#basicMode').click()
        expect(page.locator('#workspaceSettingsSummary')).to_contain_text('0.625 mm')
        assert page.locator('#fem_pitch').input_value()=='0.625'
        for id in ('start','pause','stop','evaluateAll','fem_pitch','audit_grid','piezoOverride'):
            expect(page.locator('#'+id)).to_have_count(1)
        page.locator('#workspace-tab-library').click()
        page.locator('[data-preview-seed]').first.click(timeout=20000)
        expect(page.locator('#workspaceCandidate')).to_contain_text('seed-',timeout=20000)
        page.locator('#advancedMode').click()
        for view in ('results','signals','fem'):
            page.locator('#workspace-tab-'+view).click()
            expect(page.locator('#workspace-panel-'+view+' #model')).to_be_visible()
            expect(page.locator('#model')).to_have_count(1)
        expect(page.locator('.workspace-fem-card')).to_have_count(4)
        expect(page.locator('#femPreviewGrid')).to_be_visible()
        page.locator('#workspace-tab-multiscale').click()
        expect(page.locator('#workspacePinnedGeometryStatus')).to_contain_text('pinned undeformed geometry',timeout=30000)
        expect(page.locator('#workspacePinnedGeometryStatus')).to_contain_text('seed-')
        frame=page.frame_locator('#workspaceLabFrame')
        expect(frame.locator('#labTabs')).to_be_visible(timeout=20000)
        expect(frame.locator('#selection')).to_be_disabled()
        assert frame.locator('html').evaluate('(n)=>getComputedStyle(n).backgroundColor')=='rgb(16, 30, 43)'
        assert frame.locator('body').evaluate('(n)=>getComputedStyle(n).backgroundColor')=='rgb(16, 30, 43)'
        page.wait_for_function("""(()=>{const f=document.querySelector('#workspaceLabFrame');return Math.abs(f.clientHeight-f.contentDocument.body.getBoundingClientRect().height-12)<=2;})()""",timeout=15000)
        frame.locator('#lab-tab-1').click()
        page.wait_for_function("""(()=>{const f=document.querySelector('#workspaceLabFrame');return Math.abs(f.clientHeight-f.contentDocument.body.getBoundingClientRect().height-12)<=2;})()""",timeout=15000)
        frame.locator('#tile').click()
        expect(frame.locator('.lab-status:visible')).to_contain_text('Completed',timeout=30000)
        result=json.loads(frame.locator('#tileResult').text_content())
        assert result['tier']=='T0' and result['force_balance_error_N']<1e-8
        page.locator('#workspaceComparison > summary').click()
        expect(page.locator('#workspaceReportStatus')).to_contain_text('1 latest successful',timeout=20000)
        page.locator('#workspaceSaveReports').click()
        expect(page.locator('#workspaceReportStatus')).to_contain_text('Saved locally')
        assert len(page.evaluate("JSON.parse(localStorage.getItem('neuroskin-diagnostic-reports-v1'))"))==1
        expect(page.locator('#workspaceReportTable')).to_contain_text(result['candidate_id'])
        page.locator('#workspace-tab-overview').click();page.locator('#workspace-tab-multiscale').click()
        assert json.loads(frame.locator('#tileResult').text_content())==result
        assert page.url.rstrip('/')==app_url
        page.locator('#workspaceContextSwitch').select_option('browser_archive',timeout=20000)
        expect(page.locator('#workspaceRun')).to_contain_text('Archive browser_archive',timeout=20000)
        expect(page.locator('#start')).to_be_disabled()
        expect(page.locator('#workspaceCandidate')).to_contain_text('archive-candidate')
        page.locator('#workspace-tab-multiscale').click()
        expect(page.locator('#workspaceLabContext')).to_contain_text('selection changed')
        expect(page.locator('#workspacePinnedGeometryStatus')).to_contain_text('seed-',timeout=30000)
        page.locator('#workspaceLabSync').click()
        expect(page.locator('#workspaceLabFrame')).to_have_attribute('src',re.compile('run_id=browser_archive'))
        expect(frame.locator('#labTabs')).to_be_visible(timeout=20000)
        # Rebinding creates a bounded inspection session; it does not reload
        # the previous frame or discard completed analysis.
        expect(page.locator('.workspace-labframe')).to_have_count(2)
        expect(page.locator('#workspacePinnedGeometryStatus')).to_contain_text('archive-candidate ·',timeout=30000)
        page.locator('#workspaceLabSessions').select_option(index=0)
        expect(page.locator('#workspaceLabFrame')).not_to_have_attribute('src',re.compile('run_id=browser_archive'))
        assert json.loads(frame.locator('#tileResult').text_content())==result
        expect(page.locator('#workspacePinnedGeometryStatus')).to_contain_text('seed-',timeout=30000)
        page.locator('#workspaceLabSessions').select_option(index=1)
        expect(page.locator('#workspaceLabFrame')).to_have_attribute('src',re.compile('run_id=browser_archive'))
        page.locator('#workspaceLabClose').click()
        expect(page.locator('.workspace-labframe')).to_have_count(1)
        assert json.loads(frame.locator('#tileResult').text_content())==result
        page.locator('#workspaceLive').click()
        expect(page.locator('#workspaceRun')).to_have_text('Live session',timeout=20000)
        expect(page.locator('#workspaceCandidate')).to_have_text('No candidate selected')
        page.locator('#basicMode').click();page.set_viewport_size({'width':390,'height':844})
        expect(page.locator('#workspace-tab-multiscale')).to_be_hidden()
        page.wait_for_function('document.documentElement.scrollWidth <= innerWidth + 1')
        page.set_viewport_size({'width':1500,'height':1000})
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('#workspace-tab-overview')).to_be_visible(timeout=20000)
        expect(page.locator('.workspace-tabs button:visible')).to_have_count(4)
        page.locator('#advancedMode').click()
        page.locator('.workspace-settings').filter(has_text='Evolution presets').locator('summary').click()
        page.locator('#workspaceProfileSelect').select_option('Browser preset')
        expect(page.locator('#workspaceProfileApply')).to_be_enabled(timeout=20000)
        page.locator('#workspaceProfileApply').click()
        assert page.locator('#fem_pitch').input_value()=='0.625'
        page.locator('#workspace-tab-multiscale').click()
        page.locator('#workspaceComparison > summary').click()
        expect(page.locator('#workspaceReportStatus')).to_contain_text('1 saved locally')
        expect(page.locator('#workspaceReportTable')).to_contain_text(result['candidate_id'])
        expect(page.locator('.workspace-labframe')).to_have_count(0)
        assert not errors,errors
        browser.close()


def test_four_real_fem_fields_and_geometry_override(app_url):
    from playwright.sync_api import sync_playwright,expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1500,'height':1000})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(app_url,wait_until='domcontentloaded')
        page.locator('#advancedMode').click()
        page.locator('#workspace-tab-library').click()
        page.locator('#hybridLibrary').locator('xpath=ancestor::details[1]/summary').click()
        page.locator('[data-hybrid="h01_serpentine_quadrant"]').click(timeout=30000)
        expect(page.locator('#workspaceCandidate')).to_contain_text('h01',timeout=20000)
        tree=page.locator('#workspaceComponentTree');tree.locator('summary').first.click()
        group=tree.locator('details').filter(has_text='upper ·').first
        group.locator('summary').click(timeout=30000)
        selected=group.locator('button[data-component-id^="flexure:"]').first
        selected.click();expect(selected).to_have_attribute('aria-pressed','true')
        page.wait_for_function("""document.querySelector('#model').data?.some(t=>t.facecolor?.includes('#ffcf70'))""",timeout=30000)
        tree.get_by_text('Clear highlight',exact=True).click()
        with page.expect_response(lambda r:'/api/mesh?' in r.url and 'piezo_count_override=4' in r.url,timeout=30000) as response:
            page.locator('#piezoOverride').select_option('4')
        assert response.value.ok,response.value.text()
        assert 'piezo_wiring_override=null' not in response.value.url
        page.locator('#workspace-tab-fem').click()
        page.locator('#femViewPitch').select_option('1.25')
        with page.expect_response(lambda r:r.url.endswith('/api/evaluate_all'),timeout=180000) as response:
            page.locator('#evaluateAll').click()
        assert response.value.ok,response.value.text()
        data=response.value.json()
        assert data['fem']['preview_fields']['case_order']==['press_center','press_x_plus','shear_x','torsion_z']
        assert 'preview_fields' not in data['audit']['fem']
        expect(page.locator('#evaluateAll')).to_be_enabled(timeout=180000)
        page.locator('#workspace-tab-fem').click()
        expect(page.locator('#workspaceFEMLegend')).to_contain_text('shared displayed range',timeout=30000)
        film=page.locator('#workspaceComponentTree button[data-component-id^="piezo:"]').first
        film.locator('xpath=ancestor::details[1]/summary').click() if not film.is_visible() else None
        film.click()
        expect(page.locator('#workspaceComponentTree .component-evidence')).to_contain_text('Charge [pC]')
        expect(page.locator('#workspaceComponentTree .component-evidence tbody tr, #workspaceComponentTree .component-evidence table tr')).to_have_count(5)
        page.locator('#workspaceComponentTree').get_by_text('Clear highlight',exact=True).click()
        page.wait_for_function("""[...document.querySelectorAll('.workspace-fem-preview-plot')].every(p=>p.data?.length)""",timeout=60000)
        scales=page.evaluate("""[...document.querySelectorAll('.workspace-fem-preview-plot')].map(p=>{const t=p.data.find(t=>t.type==='mesh3d'&&t.intensity);return[t.cmin,t.cmax]})""")
        assert len(scales)==4 and all(s==scales[0] for s in scales)
        page.wait_for_function("""[...document.querySelectorAll('.workspace-fem-preview-plot')].every(p=>p.data?.some(t=>t.name==='reaction boundary force'))""",timeout=30000)
        expect(page.locator('#workspaceSectionForces')).to_be_enabled()
        page.locator('#workspaceSectionForces').check()
        page.wait_for_function("""[...document.querySelectorAll('.workspace-fem-preview-plot')].every(p=>p.data?.some(t=>t.name==='section 1 boundary force'))""",timeout=30000)
        page.locator('#workspaceSectionForces').uncheck()
        page.locator('#workspaceBoundaryForces').uncheck()
        page.wait_for_function("""[...document.querySelectorAll('.workspace-fem-preview-plot')].every(p=>p.data?.length&&!p.data.some(t=>t.name==='reaction boundary force'))""",timeout=30000)
        page.locator('#femExpand-press_center').click()
        expect(page.locator('.workspace-fem-wide')).to_have_count(1)
        page.locator('#femExpand-press_center').click()
        expect(page.locator('.workspace-fem-wide')).to_have_count(0)
        page.locator('#workspace-tab-signals').click()
        page.wait_for_function("""[...document.querySelectorAll('.workspace-fem-preview-plot')].every(p=>!p.data)""",timeout=30000)
        expect(page.locator('#workspace-panel-signals #model')).to_be_visible()
        assert not errors,errors
        browser.close()
