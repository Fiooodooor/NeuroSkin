# NeuroSkin Evolution Lab 2.1.1 — Windows Ctrl+C / graceful shutdown hotfix

## Observed behaviour

On Windows 11 / Python 3.14, a Ctrl+C at the shared console was received by every `multiprocessing` spawned worker in addition to the parent Uvicorn process. The child tasks could be idle and blocked on `call_queue.get()`; every one then emitted a `KeyboardInterrupt` traceback. This is an interrupt propagation/shutdown lifecycle defect, **not** evidence that the FEM solver failed.

The pasted log was launched in a `v200-neuroskin_evolution_lab_v20` folder. This hotfix builds on v2.1 and includes the expanded v2.1 search space and hybrid rotation work.

## Fixes

1. `evolution_worker_initializer()` sets `signal.SIGINT` to `SIG_IGN` in *worker processes*. The parent Uvicorn process still receives Ctrl+C normally.
2. FastAPI application lifespan calls `EvolutionV5.shutdown()` before the event loop exits. `shutdown()` clears pause and sets stop, joins the controller for up to 8 s, then calls `ProcessPoolExecutor.terminate_workers()` (Python 3.14+) to break a long-running pool if necessary.
3. Normal API Stop also clears Pause and changes status to `stopping` until fully stopped.
4. If workers are forcibly stopped while in `map()`, `BrokenProcessPool` is treated as an *expected user stop*, and the last fully completed generation is atomically persisted in `results.json` rather than marked as a solver failure.
5. Normal successful completion and interrupted completion are separate statuses; old saved stage files are unchanged.
6. `launch_windows.ps1` avoids the Windows CMD **Terminate batch job (Y/N)?** prompt, which is intrinsic to aborting a `.bat` script, not an application exception.

## Windows launch

```powershell
# From extracted folder. Activate your virtualenv beforehand if desired:
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\launch_windows.ps1 -Cores auto
```

You can still launch the old `launch_windows.bat` script, but CMD can ask `Terminate batch job (Y/N)?` upon Ctrl+C, regardless of the application code.

To avoid that prompt completely:

```powershell
python server.py --cores auto --open --port 8765
```

## Validation

- Unit test: spawned worker's SIGINT disposition is `SIG_IGN`.
- Unit test: stopping a paused run clears the paused state and terminates.
- Unit test: application lifespan invokes the controller shutdown.
- Linux subprocess integration: server launched with 2 workers, started 300-second evolution, then received SIGINT sent to its whole process group. Exit code 0, no `KeyboardInterrupt` tracebacks.
- This runtime does not have Windows: the exact Windows PowerShell/CMD signal behaviour still requires a run on your workstation.

## Limitations

- A single FEM call running inside the server process cannot be interrupted at arbitrary native linear-algebra instructions; the controller will still return from its bounded shutdown. Prefer the GUI **Stop** before Ctrl+C when an ultrafine local FEM is running.
- Console Ctrl+C sent during the first milliseconds of spawning a child, before the initializer starts, can still interrupt that process; rare startup races cannot be completely ruled out.
- Ctrl+C sent twice in rapid succession can force Uvicorn/AnyIO cancellation of a manual HTTP calculation, potentially producing a separate `CancelledError` traceback.
