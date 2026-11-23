"""Minimal local engine smoke check (3 seconds)."""
import time
from engine import Evolution
engine=Evolution('runs')
engine.start('quadrant',3,42,12)
while engine.snapshot()['status'] in ('running','paused'):time.sleep(.1)
s=engine.snapshot()
assert s['status']=='completed', s
assert s['best'] and s['generation']>0
print('PASS',s['id'],s['generation'],'generations',s['evaluated'],'evaluations',s['best']['metrics']['fitness'],'fitness')
