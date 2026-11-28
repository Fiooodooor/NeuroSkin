"""NeuroSkin 1.6 curated seed library: 10 hypotheses + 10 literature-inspired motifs.

Scores are documented engineering priors (0..10), NOT measured performance, patent novelty,
FEM results, or accuracy percentages. Seed outlines are interpreted by the shared morphology
engine into procedural 3D members; papers are inspiration, not reproduced CAD.
"""
from __future__ import annotations
from dataclasses import dataclass
import random

CRITERIA = (
    ('normal', 'Static normal-force sensing'),
    ('shear', 'Shear / direction separation'),
    ('location', 'Contact-position identifiability'),
    ('dynamic', 'PVDF dynamic signal potential'),
    ('recovery', 'Expected elastic recovery'),
    ('stretch', 'Skin strain tolerance'),
    ('fabrication', 'Fabrication plausibility'),
    ('fatigue', 'Fatigue-risk screening'),
    ('electronics', 'Readout simplicity / low power'),
    ('numerical', 'Simulatability / parameter robustness'),
)

@dataclass(frozen=True)
class Archetype:
    id: str
    title: str
    family: str
    category: str
    concept: str
    source_url: str
    scores: tuple[int,...]
    settings: tuple[tuple[str, float|int], ...]
    rationale: str

# Score order: normal, shear, location, dynamic, recovery, stretch,
# fabrication, fatigue, electronics, numerical.
SEEDS: tuple[Archetype,...] = (
 Archetype('s_wave_pairs','Opposed S-bends','quadrant','hypothesis','S-shaped paired flexures with mirrored bend directions','',(8,9,8,8,8,8,8,7,7,8),(('bow',.8),('wave_amp',.4),('thickness',.48),('piezo_count',4)), 'Symmetry and tunable lateral compliance; benchmarked against straight flexures'),
 Archetype('s_double_saddle','Double saddle','chiral','hypothesis','Two opposite torsional saddle paths carrying axial and lateral loads','',(7,9,7,8,7,7,6,6,6,7),(('twist',.9),('thickness',.55),('ribs',8)), 'Opens differential twist under mixed forcing'),
 Archetype('s_radial_ladder','Radial ladder','crown','hypothesis','Radial spokes coupled at mid-height by an annular web','',(9,7,7,7,8,7,8,8,8,8),(('thickness',.55),('ribs',8),('branch_factor',1)), 'Distributed normal loads with redundant force paths'),
 Archetype('s_opposed_helix','Counter-helical cuff','chiral','hypothesis','Alternating handedness around a circular pad','',(7,9,8,9,7,8,7,7,6,7),(('twist',1.1),('ribs',8),('thickness',.50)), 'Mechanical chirality turns shear into differential deformation'),
 Archetype('s_catenary','Tension-compression catenary','crown','hypothesis','Arched catenary-like struts that bend smoothly under compression','',(9,6,7,7,8,7,9,8,9,8),(('crown_curvature',.5),('thickness',.46)), 'Simple tool-less molding and low-stress curves'),
 Archetype('s_gradient_arch','Graded response arch','crown','hypothesis','Ribs with midspan taper and progressive radial curvature','',(9,6,7,8,8,7,8,8,9,8),(('thickness',.52),('taper',.72),('tier_count',3)), 'Potential dual-range compliance without abrupt hard-stop'),
 Archetype('s_split_helix','Split helices','chiral','hypothesis','Pair of different pitch helical substructures with phase offset','',(7,9,8,9,7,7,6,6,6,6),(('ribs',10),('twist',1.3),('split',.5)), 'Multi-band dynamic mechanical filtering hypothesis'),
 Archetype('s_tripod_triage','Tri-directional tripod','quadrant','hypothesis','Four three-directional supports producing multiple independent reaction channels','',(8,9,9,8,8,7,8,7,7,7),(('bow',.6),('thickness',.52)), 'Directional readouts and contact-location sensitivity'),
 Archetype('s_mirror_flex','Mirror flexure pairs','quadrant','hypothesis','Mirrored X/Y S-curves with nearly matched compliance','',(8,9,9,8,8,8,8,8,8,8),(('bow',.75),('thickness',.48),('piezo_count',4)), 'Separate strain modes from twisting and lateral shear'),
 Archetype('s_spatial_trellis','Spatial trellis','crown','hypothesis','Arch network with sparse diagonal braces','',(8,8,7,7,7,8,7,7,7,7),(('branch_factor',1),('ribs',8),('thickness',.45)), 'Mechanical redundancy and stable contact on larger patches'),
 Archetype('r_fish_scale','Scale-fold origami','crown','literature','Scale-inspired overlapping mechanical fields with deformation transmission','https://doi.org/10.1038/s41528-026-00563-3',(8,8,9,7,7,9,5,6,6,6),(('ribs',8),('wave_amp',.9),('thickness',.48)), 'Origami-scale capacitive e-skin; conceptual beam analogue'),
 Archetype('r_kirigami_hinge','Kirigami soft hinges','quadrant','literature','Strain-isolating thin hinge sections between stable sensing islands','https://doi.org/10.1002/adsr.202400012',(8,8,8,8,8,10,8,7,7,8),(('thickness',.44),('bow',1.),('wave_amp',.35)), 'Mechanical strain isolation derived from kirigami sensor arrays'),
 Archetype('r_buckled_pvdf','Buckled PVDF arch','chiral','literature','Buckled 3D arches transmitting pressure into out-of-plane PVDF deformation','https://doi.org/10.1038/s41528-024-00310-6',(8,8,7,10,7,8,6,6,6,6),(('twist',.9),('wave_amp',1.),('thickness',.52)), 'Literature describes buckled 3D piezo films; not exact reproduction'),
 Archetype('r_gyroid_web','Gyroid-like web','crown','literature','Smooth periodic doubly-curved interconnected cells','https://www.sciencedirect.com/science/article/pii/S0264127524009109',(9,7,7,7,9,7,6,8,8,6),(('ribs',10),('wave_count',3),('wave_amp',.55),('branch_factor',1)), 'Gyroid capacitor research; discrete web is only a stand-in for a TPMS surface'),
 Archetype('r_orthogonal_piezo','Orthogonal PVDF grid','quadrant','literature','Crossed anisotropic load paths and orthogonally sensed piezo film','https://www.sciencedirect.com/science/article/pii/S1385894726027865',(8,10,9,10,7,7,5,6,6,7),(('thickness',.48),('bow',.45),('piezo_count',4)), 'Orthogonal 3D piezoelectric force sensing with axis decomposition'),
 Archetype('r_microporous','Microporous dielectric cage','crown','literature','Soft porosity and microstructure for enhanced capacitance pressure response','https://doi.org/10.1038/s41528-026-00538-4',(10,6,7,6,8,7,7,8,9,7),(('ribs',8),('thickness',.40),('tier_count',3)), 'Microporous dielectric capacitive tactile sensor; approximate cage geometry'),
 Archetype('r_auxetic_kirigami','Auxetic kirigami cell','quadrant','literature','Re-entrant off-axis segments with negative-Poisson design inspiration','https://www.sciencedirect.com/science/article/pii/S2211285524008747',(8,9,8,9,7,9,7,7,7,7),(('thickness',.48),('bow',1.2),('wave_amp',.8)), 'Auxetic kirigami self-powered strain sensor; auxetic sign not proven here'),
 Archetype('r_rigid_island','Rigid-island flexure','quadrant','literature','Stiff sensor islands decoupled by compliant attachment links','https://doi.org/10.1038/s41528-025-00503-7',(8,8,9,7,9,9,8,8,8,8),(('thickness',.46),('bow',.65),('piezo_count',4)), 'Skin-inspired rigid island capacitive modulus detection'),
 Archetype('r_lc_origami','Origami LC honeycomb','crown','literature','Honeycomb folded pressure unit compatible with remote passive LC pickup','https://doi.org/10.1038/s41528-025-00527-z',(8,6,7,6,7,9,5,7,9,6),(('ribs',8),('wave_amp',.7),('thickness',.44)), 'Self-folding honeycomb with passive wireless LC readout; LC not modeled'),
 Archetype('r_tpms_diamond','TPMS diamond cell','chiral','literature','Multi-axial diamond/TPMS inspired intersecting curved paths','https://www.mdpi.com/2073-4360/18/19/2449',(9,8,7,7,9,7,5,8,7,6),(('ribs',8),('twist',.65),('branch_factor',1)), 'Gyroid/diamond/Schwarz piezoresistive lattice; not a TPMS FEM surface'),
)
_BY_ID = {s.id:s for s in SEEDS}
assert len(SEEDS)==20 and len(_BY_ID)==20
assert sum(s.category=='hypothesis' for s in SEEDS)==10
assert sum(s.category=='literature' for s in SEEDS)==10
assert all(len(s.scores)==10 and all(isinstance(v,int) and 0<=v<=10 for v in s.scores) for s in SEEDS)

def top_candidates(n=10):
    """Highest expert-prior scores with an explicit family-coverage constraint.

    At least two of each major mechanism (Crown/Chiral/Quadrant) are retained
    for 10-or-more finalist libraries. Otherwise a single attractive morphology
    can suppress exploring an entirely different response mechanism.
    This is an exploratory design-of-experiments choice, NOT a numerical FEM rank.
    """
    ranked=sorted(SEEDS,key=lambda s:(-sum(s.scores),s.id))
    if n<6:return ranked[:n]
    selected=[]
    for fam in ('crown','chiral','quadrant'):
        selected.extend([s for s in ranked if s.family==fam][:2])
    for spec in ranked:
        if len(selected)>=n:break
        if spec not in selected:selected.append(spec)
    return sorted(selected,key=lambda s:(-sum(s.scores),s.id))[:n]

def seed_genome(seed: Archetype, rng: random.Random, mutate: bool=True):
    from advanced import new_genome
    g=new_genome(seed.family,rng)
    # Curated single-stage concepts must not inherit a random hybrid identity.
    g.update(topology=seed.id,hybrid_id='none')
    for k,v in seed.settings:
        if k in g:g[k]=v
    if mutate:
        from advanced import jump
        # local small mutation without changing the named concept
        g=jump(seed.family,g,rng,'local')
    g['topology']=seed.id
    return g

def serialized_library():
    top={s.id for s in top_candidates()}
    return {'score_type':'expert_a_priori_0_to_10_per_category_not_FEM_validation',
      'categories':[{'id':k,'label':n} for k,n in CRITERIA],
      'seeds':[{'id':s.id,'title':s.title,'family':s.family,'origin':s.category,
                'concept':s.concept,'source_url':s.source_url,'criteria':dict(zip((x[0] for x in CRITERIA),s.scores)),
                'total':sum(s.scores),'selected':s.id in top,'rationale':s.rationale} for s in sorted(SEEDS,key=lambda x:(-sum(x.scores),x.id))]}
