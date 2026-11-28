"""Explicit current-engine smoke check; importing this module performs no work."""
import argparse
import json
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory


def main(argv=None):
    from advanced import EvolutionEngine
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Persist the experiment; otherwise use a temporary directory')
    args = parser.parse_args(argv)
    with nullcontext(args.out) if args.out is not None else TemporaryDirectory() as folder:
        engine = EvolutionEngine(folder)
        try:
            engine.start('quadrant', 3, 42, 12, audit_grid=3, fem=False)
            engine.thread.join(timeout=180)
            state = engine.snapshot()
            if state['status'] != 'completed' or not state['best'] or state['generation'] < 1:
                raise RuntimeError('Smoke evolution did not complete: ' + state.get('error', state['status']))
            print(json.dumps({'pass': True, 'run_id': state['id'], 'generation': state['generation']}))
        finally:
            if not engine.shutdown(10):
                raise RuntimeError('Smoke controller failed to stop')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
