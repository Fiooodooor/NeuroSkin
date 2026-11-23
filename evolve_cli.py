"""Headless timed evolution with multiprocessing. Run directly as a file, not via notebook."""
import argparse, os, json, sys, time, secrets
from pathlib import Path
for _v in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
 os.environ[_v]='1'
from advanced import EvolutionV5

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--cores',default='1',help='Logical CPU workers or auto (hardware-aware physical-core recommendation)')
 ap.add_argument('--seconds',type=float,default=60)
 ap.add_argument('--population',type=int,default=96)
 ap.add_argument('--mode',choices=['all','crown','chiral','quadrant'],default='all')
 ap.add_argument('--objective',choices=['balanced','touch','robust','dynamic'],default='balanced')
 ap.add_argument('--seed',type=int,default=None,help='Optional reproducible override; default is randomized for each run')
 ap.add_argument('--exploration',type=float,default=.75)
 ap.add_argument('--gate',action='store_true')
 ap.add_argument('--grid',type=int,choices=[3,5,7],default=3)
 ap.add_argument('--audit-grid',type=int,choices=[3,5,7],default=5,help='identical exhaustive scan grid for the top three finalists')
 ap.add_argument('--fem',action=argparse.BooleanOptionalAction,default=True,help='Perform actual 3D HEX8 FEM on every Top-3 finalist (default: enabled)')
 ap.add_argument('--fem-pitch',type=float,default=.3125,help='HEX8 mesh pitch or beam element length [mm]. 0.3125=4x, 0.15625=8x finer than legacy 1.25')
 ap.add_argument('--fem-backend',choices=['hex8','beam','auto'],default='hex8',help='Explicit mechanical solver (default real 3D solid HEX8). Beam = faster, but not solid 3D resolution.')
 ap.add_argument('--out',default='runs_headless')
 args=ap.parse_args()
 if args.cores=='auto':
  from hardware_profile import profile
  args.cores=profile()['recommended']['evolution_cores']
 else:
  try: args.cores=int(args.cores)
  except ValueError: ap.error('--cores must be an integer or auto')
 if not 1<=args.cores<=(os.cpu_count() or 1):ap.error('cores outside available logical cores')
 if args.seed is None: args.seed=secrets.randbits(31)
 print(f'Run random seed: {args.seed}',flush=True)
 e=EvolutionV5(Path(args.out))
 e.start(args.mode,args.seconds,args.seed,args.population,args.exploration,args.objective,args.gate,args.grid,args.cores,args.audit_grid,args.fem,args.fem_pitch,args.fem_backend)
 last=-1
 try:
  while True:
   s=e.snapshot()
   if s['generation']!=last:
    last=s['generation'];print(json.dumps({'status':s['status'],'seconds':round(s['elapsed'],1),'generation':s['generation'],'evaluations':s['evaluated'],'eval_per_second':s.get('evaluations_per_second',0),'best_fitness':(s['best'] or {}).get('fitness'),'audited_utility':((s.get('audited_champion') or {}).get('audit') or {}).get('audit_score'),'stage':s.get('phase')}),flush=True)
   if s['status'] in ('completed','stopped','failed'):
    if s['status']=='failed':print(s['error'],file=sys.stderr);return 1
    return 0
   time.sleep(.35)
 except KeyboardInterrupt:
  e.stop();e.thread.join(timeout=20);return 130
if __name__=='__main__':raise SystemExit(main())
