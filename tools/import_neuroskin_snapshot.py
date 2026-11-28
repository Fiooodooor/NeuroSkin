"""Import the complete snapshot bundle into a clean develop/v3 checkout.
Default dry-run. --apply stages and commits. --push additionally publishes.
Requires Python 3 and Git. Preserves remote-only paths, never force-pushes.
"""
import argparse
import pathlib
import subprocess
import tempfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=pathlib.Path)
    p.add_argument('--repo', type=pathlib.Path, default=pathlib.Path('.'))
    p.add_argument('--snapshot', choices=['v22', 'alpha2'], default='v22')
    p.add_argument('--apply', action='store_true')
    p.add_argument('--push', action='store_true')
    a = p.parse_args()
    if a.push and not a.apply:
        p.error('--push requires --apply')
    bundle = a.bundle.resolve(strict=True)
    def git(*args, raw=False):
        data = subprocess.check_output(['git', '-C', str(a.repo), *map(str,args)])
        return data if raw else data.decode('utf-8').strip()
    if git('branch','--show-current') != 'develop/v3':
        raise SystemExit('Checkout develop/v3 first')
    if git('status','--porcelain','--untracked-files=all'):
        raise SystemExit('Working tree must be clean')
    remote = git('remote','get-url','origin')
    if remote.rstrip('/').removesuffix('.git').lower() not in ('https://github.com/fiooodooor/neuroskin','git@github.com:fiooodooor/neuroskin','ssh://git@github.com/fiooodooor/neuroskin'):
        raise SystemExit('Unexpected origin: '+remote)
    # Verify and fetch objects, not a branch update; FETCH_HEAD is temporary.
    git('bundle','verify',bundle)
    git('fetch','--no-tags',bundle,'refs/heads/'+a.snapshot)
    source=git('rev-parse','FETCH_HEAD')
    paths=git('ls-tree','-r','--name-only','-z',source,raw=True)
    names=[n for n in paths.split(b'\0') if n]
    print(f'Snapshot {a.snapshot}: {source}; {len(names)} files. Remote-only files remain untouched.')
    if not a.apply:
        print('Dry-run: no tracked files changed. Re-run with --apply, optionally --push.')
        return
    # No git add: restore blobs directly to index, preserving binary and ignored files.
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(paths); path=pathlib.Path(handle.name)
    try:
        git('restore','--source='+source,'--staged','--worktree','--pathspec-from-file='+str(path),'--pathspec-file-nul')
    finally:
        path.unlink()
    expected={line.split(b'\t',1)[1]:line.split(b'\t',1)[0].split()[2] for line in git('ls-tree','-r','-z',source,raw=True).split(b'\0') if line}
    actual={line.split(b'\t',1)[1]:line.split(b'\t',1)[0].split()[1] for line in git('ls-files','--stage','-z',raw=True).split(b'\0') if line}
    if any(actual.get(k)!=v for k,v in expected.items()):
        raise SystemExit('Index blob mismatch: do not commit; inspect git status')
    print('All snapshot blob hashes match the staged index.')
    if git('diff','--cached','--name-only'):
        print(git('commit','-m',f'Import complete NeuroSkin {a.snapshot} snapshot'))
    else:
        print('Snapshot already present.')
    if a.push:
        print(git('push','origin','HEAD:refs/heads/develop/v3'))

if __name__=='__main__':
    main()
