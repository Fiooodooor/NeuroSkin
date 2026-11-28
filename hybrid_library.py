"""Ten purpose-designed two-stage NeuroSkin architectures.

Scores are pre-FEM engineering priors (0..10), not measured force accuracy,
novelty, experimental results or a certification. The catalogue is ordered by
sum of expert scores; actual evolutionary ranking always uses evaluated data.
"""
from __future__ import annotations
from dataclasses import dataclass

CRITERIA = (
 ('normal','Normal pressure response'), ('shear','Shear-force separation'),
 ('position','Off-center touch localization'), ('dynamic','PVDF dynamic observability'),
 ('modes','Mode independence / observability'), ('recovery','Reversible deformation'),
 ('fatigue','Fatigue risk (higher is safer)'), ('fabrication','Fabrication feasibility'),
 ('electronics','Readout cost / complexity (higher is simpler)'),
 ('numerical','Numerical tractability'),
)

@dataclass(frozen=True)
class HybridSpec:
 id: str
 name: str
 upper_family: str
 upper_topology: str
 lower_family: str
 lower_topology: str
 role: str
 rationale: str
 evidence_url: str
 scores: tuple[int, ...]
 split: float
 upper_scale: float
 lower_scale: float
 phase: float
 pvdf_count: int
 seed_thickness_mm: float = 0.0

SPECS = (
 HybridSpec('h01_serpentine_quadrant','S-Bridge / Differential Quadrant','quadrant','serpentine','quadrant','orthogonal','Compliant upper S-bends measure touch; lower orthogonal quadrant provides directional reference','Two orthogonal force-transfer stages with opposed flexures; straightforward symmetric construction','https://www.nature.com/articles/s41563-026-02508-7',(9,9,9,8,9,8,8,8,7,9),.49,.86,1.10,0.,4,.95),
 HybridSpec('h02_crown_kirigami','Graded Crown / Kirigami Hinge','crown','arched','quadrant','kirigami','Top progressive arches distribute contact; lower hinge network isolates substrate strain','Top normal sensitivity, lower strain isolation; simple common/differential readout','https://advanced.onlinelibrary.wiley.com/doi/10.1002/adsr.202400012',(9,8,8,8,8,8,7,8,8,8),.48,.82,1.05,0.,4),
 HybridSpec('h03_counterhelix_quadrant','Counter-Helix / Quadrant','chiral','counter','quadrant','orthogonal','Upper counter-helix transduces dynamic torque; lower balanced quadrant distinguishes shear','Counter-rotation should reduce undesired twist under pure axial load; experimentally unproven','https://advanced.onlinelibrary.wiley.com/doi/10.1002/adem.202401613',(8,9,8,9,9,7,7,7,6,8),.50,.80,1.13,3.14159/4,4),
 HybridSpec('h04_arched_trellis','Catenary Arch / Radial Trellis','crown','arched','crown','woven','High upper compliance with lower redundant bracing','A conservative, buildable two-stage normal sensor and FEM reference','https://www.jos.ac.cn/article/doi/10.1088/1674-4926/24080006',(9,7,8,7,8,9,8,9,8,8),.47,.83,1.15,0.,4),
 HybridSpec('h05_auxtwist','Auxetic Re-entrant / Chiral Torsion','quadrant','auxetic','chiral','helical','Upper re-entrant deformation amplifies lateral gradients; lower chiral stage responds to torsion','Distinct modes may improve identifiability but add buckling and fatigue risk','https://www.sciencedirect.com/science/article/pii/S2211285524008747',(8,9,8,9,9,7,6,6,6,7),.48,.85,1.08,3.14159/4,4),
 HybridSpec('h06_mirror_braid','Mirrored S-Pairs / Counter-Braids','quadrant','serpentine','chiral','braided','Mirrored upper paths give X/Y differential channels; lower braids provide common-mode filtering','Two independent mechanical signatures may separate contact from chassis strain','https://www.sciencedirect.com/science/article/pii/S1385894725080283',(8,9,8,9,9,7,6,7,6,7),.49,.83,1.10,3.14159/8,4),
 HybridSpec('h07_rigid_island','Rigid-Island Upper / Compliant Crown','quadrant','orthogonal','crown','radial','Stiff upper surface localizes force, lower flexible crown transmits common pressure','Probes a mechanically reversed allocation of compliance without adding electrical channels','https://www.sciencedirect.com/science/article/pii/S1385894726085177',(8,8,9,7,8,9,8,8,8,8),.52,1.12,.78,0.,4),
 HybridSpec('h08_helix_crown','Helical Active / Dome Reference','chiral','helical','crown','arched','Upper helical PVDF acts as a dynamic receptor; lower dome acts as static force reference','Frequency-selective mechanical transduction is plausible but needs measured transfer functions','https://www.sciencedirect.com/science/article/pii/S1359836823006443',(8,8,7,9,8,8,7,8,7,8),.52,.83,1.12,0.,4),
 HybridSpec('h09_kirigami_helix','Kirigami Hinge / Helical Reference','quadrant','kirigami','chiral','counter','Upper thin hinges decouple substrate stretch, lower counter-helix offers torsional comparison','May resist whole-skin strain at expense of long-term hinge fatigue','https://advanced.onlinelibrary.wiley.com/doi/10.1002/adsr.202400012',(8,8,8,8,8,8,6,7,7,8),.46,.80,1.12,3.14159/8,4),
 HybridSpec('h10_dual_chiral','Opposed Helix / Balanced Helix','chiral','helical','chiral','counter','Two stages have opposed chirality and different stiffness for signed torque discrimination','Interesting compression-to-twist concept; strongest risk of angular-mode ambiguity','https://www.sciencedirect.com/science/article/pii/S0264127525010494',(7,9,7,9,8,7,6,7,6,7),.50,.82,1.12,3.14159/4,6,.58),
)
BY_ID={x.id:x for x in SPECS}
assert len(SPECS)==len(BY_ID)==10
assert all(len(s.scores)==10 and all(0<=v<=10 for v in s.scores) for s in SPECS)


def ranked():
 return sorted(SPECS,key=lambda x:(-sum(x.scores),x.id))


def library_json():
 return {'score_type':'a_priori_engineering_hypothesis_NOT_FEM',
         'criteria':[{'id':a,'label':b} for a,b in CRITERIA],
         'architectures':[
          {'id':s.id,'name':s.name,'rank':rank,'total':sum(s.scores),
           'upper_family':s.upper_family,'upper_topology':s.upper_topology,
           'lower_family':s.lower_family,'lower_topology':s.lower_topology,
           'role':s.role,'rationale':s.rationale,'evidence_url':s.evidence_url,
           'scores':dict(zip((a for a,b in CRITERIA),s.scores)),
           'params':{'split':s.split,'upper_scale':s.upper_scale,
                     'lower_scale':s.lower_scale,'phase':s.phase,'pvdf_count':s.pvdf_count,
                     'seed_thickness_mm':s.seed_thickness_mm}}
          for rank,s in enumerate(ranked(),1)]}


def genome_for(spec, rng=None):
 import random
 from advanced import new_genome
 rng=rng if rng is not None else random.Random(1701)
 # Preserve all baseline fields while creating a genuinely new 2-stage genotype.
 family=spec.upper_family
 g=new_genome(family,rng)
 g.update(hybrid_id=spec.id,hybrid_split=spec.split,
          hybrid_upper_scale=spec.upper_scale,hybrid_lower_scale=spec.lower_scale,
          hybrid_phase=spec.phase,hybrid_plate_thickness=.65,hybrid_sensor_mode=0,
          piezo_count=spec.pvdf_count,topology='hybrid')
 if spec.seed_thickness_mm>0:
  g['thickness']=spec.seed_thickness_mm
 g['radius']=min(g['radius'],6.6)
 g['height']=max(6.2,float(g['height']))
 g['pad_offset_x']=0.0;g['pad_offset_y']=0.0
 g['asymmetry']=0.0 if family=='quadrant' else g.get('asymmetry',0.0)
 return g
