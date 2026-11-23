"""Benchmark parallel candidate throughput (not solver accuracy)."""
import argparse, concurrent.futures, json, multiprocessing, os, random, time
for _v in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
 os.environ[_v]='1'
from advanced import evaluate_job,new_genome,FAMILIES

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cores',default='1,2,4');ap.add_argument('--population',type=int,default=96);ap.add_argument('--repeats',type=int,default=2);ap.add_argument('--gate',action='store_true');args=ap.parse_args()
 rng=random.Random(21);jobs=[(f,new_genome(f,rng),'balanced',args.gate,3) for i in range(args.population) for f in [FAMILIES[i%3]]]
 for n in [int(x.strip()) for x in args.cores.split(',')]:
  if n<1 or n>(os.cpu_count() or 1):continue
  t=time.perf_counter()
  if n==1:
   for _ in range(args.repeats):list(map(evaluate_job,jobs))
  else:
   with concurrent.futures.ProcessPoolExecutor(max_workers=n,mp_context=multiprocessing.get_context('spawn')) as pool:
    for _ in range(args.repeats):list(pool.map(evaluate_job,jobs,chunksize=max(1,args.population//(n*4))))
  seconds=time.perf_counter()-t
  print(json.dumps({'workers':n,'cases':len(jobs)*args.repeats,'wall_s':round(seconds,3),'cases_per_second':round(len(jobs)*args.repeats/seconds,2),'gate':args.gate}),flush=True)
if __name__=='__main__':main()
