#!/usr/bin/env python3
"""Repeatable NeuroSkin software checks; numerical or hardware qualification is separate."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent


def run(command, timeout=180, env=None):
    begin = time.monotonic()
    with tempfile.TemporaryFile(mode='w+t', encoding='utf-8', errors='replace') as out, tempfile.TemporaryFile(mode='w+t', encoding='utf-8', errors='replace') as err:
        process = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err, env=env,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            status = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            import psutil
            try:
                children = psutil.Process(process.pid).children(recursive=True)
            except psutil.Error:
                children = []
            for child in children:
                try: child.kill()
                except psutil.Error: pass
            process.kill()
            process.wait()
            status = 124
        out.seek(0); err.seek(0)
        return {'command': [str(x) for x in command], 'exit_code': status,
                'seconds': round(time.monotonic()-begin, 2),
                'stdout_tail': out.read()[-6000:], 'stderr_tail': err.read()[-6000:]}


def find_node():
    return shutil.which('node') or next((str(p) for p in sorted((ROOT/'.tools/node').glob('*/node.exe'))), None)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('artifacts/release-verification.json'))
    parser.add_argument('--browser', action='store_true', help='Include opt-in Chromium integration tests')
    parser.add_argument('--smoke-evolution', action='store_true')
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT/args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env['NEUROSKIN_BROWSER'] = '1' if args.browser else '0'
    checks = [run([sys.executable, '-m', 'pytest', '-q', 'tests', '--durations=15',
                   '--junitxml='+str(output.with_suffix('.xml'))], timeout=1800, env=env)]
    node = find_node()
    if node:
        for path in sorted((ROOT/'tests').glob('test_*.cjs')):
            checks.append(run([node, str(path)], timeout=60))
        checks.append(run([node, str(ROOT/'tests/test_deformation.js')], timeout=60))
        for path in sorted((ROOT/'static').glob('*.js')):
            if path.name != 'plotly.min.js': checks.append(run([node, '--check', str(path)], timeout=30))
        with tempfile.TemporaryDirectory(dir=output.parent) as directory:
            for index, source in enumerate((ROOT/'static/index.html', ROOT/'neuroskin_v30/lab.html')):
                code = '\n'.join(re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', source.read_text(encoding='utf-8'), re.DOTALL))
                script = Path(directory)/('inline-'+str(index)+'.js')
                script.write_text(code, encoding='utf-8')
                checks.append(run([node, '--check', str(script)], timeout=30))
    else:
        checks.append({'name': 'JavaScript checks', 'exit_code': 1, 'reason': 'Node.js unavailable'})
    if args.smoke_evolution and all(c['exit_code'] == 0 for c in checks):
        checks.append(run([sys.executable, 'smoke_test.py'], timeout=210))
    good = all(c['exit_code'] == 0 for c in checks)
    from validation_contract import runtime_versions
    report = {'release': (ROOT/'VERSION').read_text(encoding='utf-8').strip(),
              'software_checks_pass': good, 'browser_checks_enabled': args.browser,
              'release_ready': good and args.browser, 'physical_validation': False,
              'environment': runtime_versions(), 'checks': checks}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'pass': good, 'release_ready': report['release_ready'], 'report': str(output)}))
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
