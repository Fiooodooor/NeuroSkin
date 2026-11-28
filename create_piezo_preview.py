"""Produce an honest model-generated preview from explicit surrogate assumptions."""
from pathlib import Path
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from advanced import new_genome
from electromechanics import raw_mechanics
from piezoelectric import response
root=Path(__file__).resolve().parent/'artifacts'/'previews'
root.mkdir(parents=True,exist_ok=True)
fig,axes=plt.subplots(1,3,figsize=(15,4.6),layout='constrained')
for fam in ['crown','chiral','quadrant']:
 g=new_genome(fam,random.Random(31))
 m=raw_mechanics(fam,g,'normal')
 r=response(fam,g,m,frequency_hz=25.)
 axes[0].plot(r['time_s'],[x*1000 for x in r['waveform_V']],label=fam.title())
 axes[1].plot(r['hold_time_s'],[x*1000 for x in r['step_hold_V']],label=fam.title())
 frequencies=np.logspace(-2,3,65)
 r0=r['initial_charge_amplifier_V'];tau=r['leak_tau_s']
 att=[abs(r0)*(2*np.pi*f*tau)/np.sqrt(1+(2*np.pi*f*tau)**2) for f in frequencies]
 axes[2].plot(frequencies,np.asarray(att)*1000,label=fam.title())
axes[0].set(title='PVDF · dynamic load (25 Hz)',xlabel='Time (s)',ylabel='Predicted output (mV)')
axes[1].set(title='Step then hold · charge leakage',xlabel='Time (s)',ylabel='Predicted output (mV)')
axes[2].set(title='RC high-pass frequency response',xlabel='Frequency (Hz)',ylabel='Peak output (mV)',xscale='log')
for ax in axes:
 ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('NeuroSkin 3 · synthetic piezoelectric response (NOT measured, NOT coupled FEM)',fontsize=12)
fig.savefig(root/'piezoelectric_preview.png',dpi=150)
print(root/'piezoelectric_preview.png')
