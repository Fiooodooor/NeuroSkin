#!/usr/bin/env python3
"""Repeatable software-release regression gate for the *surrogate* simulator.

This verifies software behavior, never physical accuracy or scientific novelty.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import time
import tempfile
import unittest
import io
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def run(command: list[str], timeout: int = 150):
    """Capture output in files: worker processes must not hold pipes open."""
    start=time.monotonic()
    with tempfile.TemporaryFile(mode='w+t') as out, tempfile.TemporaryFile(mode='w+t') as err:
        try:
            p=subprocess.run(command,cwd=ROOT,stdout=out,stderr=err,timeout=timeout)
            status=p.returncode
        except subprocess.TimeoutExpired:
            status=124
        out.seek(0);err.seek(0)
        return {'command':command,'exit_code':status,
                'seconds':round(time.monotonic()-start,2),
                'stdout_tail':out.read()[-1500:],'stderr_tail':err.read()[-1500:]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke-evolution',action='store_true',help='Run a 3-second surrogate evolution and save an archive')
    parser.add_argument('--out',default='release_verification.json')
    args=parser.parse_args()
    checks=[]
    checks.append(run([sys.executable,'-m','compileall','-q','.'],timeout=30))
    # Run Python tests in the current process: process workers spawned by tests
    # must not retain an inherited subprocess output pipe after test completion.
    stream=io.StringIO();begin=time.monotonic()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(stream=stream,verbosity=1).run(suite)
    checks.append({'name':'Python regression suite','exit_code':0 if result.wasSuccessful() else 1,
                   'tests_run':result.testsRun,'seconds':round(time.monotonic()-begin,2),
                   'stdout_tail':'','stderr_tail':stream.getvalue()[-1500:]})
    if shutil.which('node'):
        import re
        html=(ROOT/'static'/'index.html').read_text(encoding='utf-8')
        blocks=re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',html,re.DOTALL)
        path=ROOT/'_script_under_test.js'
        try:
            path.write_text('\n'.join(blocks),encoding='utf-8')
            checks.append(run(['node','--check',str(path)],timeout=15))
            checks.append(run(['node',str(ROOT/'tests'/'test_deformation.js')],timeout=15))
        finally:
            path.unlink(missing_ok=True)
    else:
        checks.append({'name':'JavaScript syntax and deformation checks','skipped':'Node.js not installed'})
    if args.smoke_evolution and all(c.get('exit_code',0)==0 for c in checks):
        checks.append(run([sys.executable,'evolve_cli.py','--seconds','3',
                           '--population','12','--cores','1','--gate',
                           '--grid','3','--audit-grid','3',
                           '--out','runs_v05'],timeout=65))
    good=all(c.get('exit_code',0)==0 for c in checks)
    report={'release':'1.1','software_checks_pass':good,'physical_validation':False,
            'checks':checks,'note':'Proxy software verification only; not contact FEM or calibrated hardware'}
    (ROOT/args.out).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'pass':good,'checks':[(c.get('command') or c.get('name'),c.get('exit_code','skipped')) for c in checks]},indent=2))
    return 0 if good else 1

if __name__=='__main__':raise SystemExit(main())
