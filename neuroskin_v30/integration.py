"""Bounded experimental APIs. Neither candidate ranking nor evidence tier is promoted."""
from pathlib import Path
from functools import lru_cache
from hashlib import sha256
from validation_contract import digest, runtime_versions
from threading import BoundedSemaphore
from typing import Literal
import numpy as np
from scipy.optimize import nnls
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict
from .mesh import box_mesh, hex8_to_tet4
from .nonlinear_fem import NeoHookean, TetNeoHookeanSolver
from neuroskin_multiscale import tile_response

# One expensive nonlinear request per server process, no unbounded queue.
CONTACT_SLOT = BoundedSemaphore(1)
FUSION_SLOT = BoundedSemaphore(1)


class Selection(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    selection: str = 'best'
    index: str = '0'
    family: str = 'crown'
    run_id: str | None = None
    generation: int | None = None
    piezo_count_override: int | None = None
    piezo_wiring_override: int | None = None
    expected_live_run_id: str | None = None
    expected_candidate_id: str | None = None


class FusionInput(Selection):
    grid: Literal[3,5] = 3
    frequency_hz: float = Field(25., ge=0., le=150.)
    seed: int = Field(3322, ge=0, le=2**32-1)


class BoxInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    n: int = Field(1, ge=1, le=3)
    layered: bool = False
    second_young_MPa: float = Field(10., ge=.01, le=1000.)
    young_MPa: float = Field(2., ge=.01, le=1000.)
    poisson: float = Field(.3, ge=0., le=.45)
    side_mm: float = Field(1., ge=.1, le=20.)
    indentation_mm: float = Field(.025, gt=0., le=1.)
    penalty_N_per_mm3: float = Field(100., ge=.1, le=10000.)


class CandidateContact(Selection):
    material_model: Literal['homogeneous','stiff_plates'] = 'homogeneous'
    plate_young_MPa: float = Field(10., ge=.01, le=1000.)
    plate_poisson: float = Field(.3, ge=0., le=.45)
    pitch_mm: float = Field(2., ge=.5, le=2.5)
    indentation_mm: float = Field(.025, gt=0., le=.25)
    poisson: float = Field(.35, ge=0., le=.45)
    penalty_N_per_mm3: float = Field(100., ge=.1, le=10000.)
    allow_inflated_geometry: bool = False


class Contact(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    x_mm: float
    y_mm: float
    force_N: float = Field(gt=0., le=1.)


class TileInput(Selection):
    size: Literal[3,5,7,8] = 3
    pitch_mm: float = Field(20., ge=1., le=100.)
    coupling_N_mm: float = Field(.2, ge=0., le=100.)
    membrane_model: Literal['spring','tensioned_q1','nonlinear_coupled'] = 'spring'
    membrane_kinematics: Literal['fixed_inplane','relaxed_inplane'] = 'fixed_inplane'
    membrane_young_MPa: float = Field(2., gt=0., le=100.)
    membrane_thickness_mm: float = Field(.5, gt=0., le=5.)
    substrate_young_MPa: float = Field(1., gt=0., le=1000.)
    substrate_thickness_mm: float = Field(4., gt=0., le=20.)
    pretension_N_mm: float = Field(.2, gt=0., le=20.)
    membrane_subdivisions: Literal[4,8] = 4
    noise_N: float = Field(0., ge=0., le=.1)
    seed: int = Field(42, ge=0, le=2**32-1)
    contacts: list[Contact] = Field(min_length=1, max_length=8)


class TileOptimizeInput(Selection):
    patch_side_mm: float = Field(120., ge=60., le=300.)
    sizes: list[Literal[3,5,7,8]] = Field(default_factory=lambda:[3,5,7],min_length=1,max_length=4)
    tensions: list[float] = Field(default_factory=lambda:[.1,.3,1.],min_length=1,max_length=3)
    substrate_depths_mm: list[float] = Field(default_factory=lambda:[2.,4.],min_length=1,max_length=2)
    membrane_young_MPa: float = Field(2.,gt=0,le=100.)
    membrane_thickness_mm: float = Field(.5,gt=0,le=5.)
    substrate_young_MPa: float = Field(1.,gt=0,le=1000.)
    noise_N: float = Field(.001,ge=0,le=.1)
    seed: int = Field(42,ge=0,le=2**32-10)
    include_library: bool = True
    finalists: int = Field(2,ge=1,le=3)
    compute_workers: int = Field(2,ge=1,le=4)


@lru_cache(maxsize=1)
def diagnostic_source_hash():
    """Fingerprint the application source at process startup/first diagnostic."""
    root=Path(__file__).resolve().parents[1]
    files=list(root.glob('*.py'))+list((root/'neuroskin_v30').glob('*.py'))
    files += [root/'VERSION',root/'validation_protocol_v30.json']
    h=sha256()
    for path in sorted(files):
        h.update(path.relative_to(root).as_posix().encode()+b'\0')
        h.update(path.read_bytes()+b'\0')
    return h.hexdigest()


def diagnostic_context(result, path, req, candidate=None, genome=None):
    """Bind normalized request, source and environment to a diagnostic result.

    Candidate identity is intentionally separate from common experiment settings.
    Matching keys permit diagnostic comparisons, not physical qualification.
    """
    request=req.model_dump(mode='json')
    identity={k:request[k] for k in Selection.model_fields if k in request}
    settings={k:v for k,v in request.items() if k not in identity}
    basis={'path':path,'settings':settings,'solver_hash':diagnostic_source_hash(),
           'runtime':runtime_versions()}
    result['diagnostic_context']={**basis,'schema':1,'comparison_key':digest(basis),
        'selection':identity,'candidate_id':str(candidate['id']) if candidate is not None else None,
        'genome_hash':digest({'family':candidate['family'],'genome':genome}) if candidate is not None else None}
    return result


def contact_report(mesh, material, indentation, penalty, fixed=None, *, materials=None, material_ids=None):
    height = float(np.ptp(mesh.nodes[:,2]))
    if indentation >= .25*height:
        raise ValueError('Indentation must be below 25% of mesh height')
    solver = TetNeoHookeanSolver(mesh, material,materials=materials,material_ids=material_ids)
    from .material_regions import surface_topology
    used,fields=surface_topology(mesh,solver.material_ids,include_owners=True);fields['stages']=[]
    owners=np.asarray(fields['face_element_ids']);material_fields=[]
    def capture(indent,result):
        e=solver.element_fields(result.displacement_mm)
        fields['stages'].append({'indentation_mm':indent,'displacement_mm':result.displacement_mm[used].tolist(),
            'face_von_mises_MPa':e['von_mises_MPa'][owners].tolist(),'face_J':e['J'][owners].tolist()})
        material_fields.append([{'id':i,'strain_energy_Nmm':float(e['energy_Nmm'][mask].sum()),
            'max_von_mises_MPa':float(e['von_mises_MPa'][mask].max()),'min_J':float(e['J'][mask].min())}
            for i in range(len(solver.materials)) if np.any(mask:=solver.material_ids==i)])
    stages = solver.contact_cycle([0., indentation/2, indentation, 0.],
                                  penalty_N_per_mm3=penalty, fixed_dofs=fixed,capture=capture)
    for stage,regions in zip(stages,material_fields):
        stage['material_fields']=regions
        stage['vertical_balance_error_N'] = abs(stage['reactions_sum_N'][2]-stage['contact_force_N'])
    return {'mesh':mesh.metrics(), 'stages':stages, 'contact_fields':fields,'materials':solver.material_summary(), 'model':'compressible_neo_hookean_TET4',
            'evidence':'DIAGNOSTIC_ONLY', 'T2_qualified':False,
            'limitations':['elastic, perfectly bonded material regions; no interface slip','frictionless planar nodal penalty contact',
                           'no independent mesh/penalty convergence','no PVDF, adhesive or electrical coupling']}


def distribute_contacts(size, pitch, contacts):
    """Bilinear nodal load basis, exactly preserving total force and first moments."""
    f = np.zeros((size,size))
    for contact in contacts:
        x,y = contact.x_mm/pitch,contact.y_mm/pitch
        if not (0 <= x <= size-1 and 0 <= y <= size-1):
            raise ValueError('Contact lies outside the taxel-centre grid')
        i,j = min(int(x),size-2),min(int(y),size-2)
        a,b = x-i,y-j
        for dy,dx,w in ((0,0,(1-a)*(1-b)),(0,1,a*(1-b)),(1,0,(1-a)*b),(1,1,a*b)):
            f[j+dy,i+dx] += contact.force_N*w
    return f


def tile_report(kz, req):
    n,pitch = req.size,req.pitch_mm
    k = np.full((n,n),kz)
    f = distribute_contacts(n,pitch,req.contacts)
    if req.membrane_model=='nonlinear_coupled':
        from nonlinear_skin_tile import NonlinearSkinTile,Substrate3D
        substrate=Substrate3D(n,pitch,req.substrate_thickness_mm,req.substrate_young_MPa)
        cls=NonlinearSkinTile
        if req.membrane_kinematics=='relaxed_inplane':
            from relaxed_membrane import RelaxedSkinTile
            cls=RelaxedSkinTile
        membrane=cls(k,pitch,req.pretension_N_mm,req.membrane_young_MPa,req.membrane_thickness_mm,
                                   subdivisions=req.membrane_subdivisions,substrate=substrate)
        result=membrane.solve([(c.x_mm,c.y_mm,c.force_N) for c in req.contacts]);transfer=result['transfer']
        model=req.membrane_kinematics+'_von_karman_Q1_with_condensed_linear_TET4_substrate'
        limitations=['moderate rotation membrane; '+('fixed in-plane perimeter with interior relaxation' if req.membrane_kinematics=='relaxed_inplane' else 'constrained in-plane displacement')+'; no wrinkling, bending or tangential pad coupling',
                     'linear elastic 3D substrate, clamped bottom, coarse TET4; no mesh convergence',
                     'bilateral receptor springs and point contacts; no detachment or sensor calibration',
                     'inverse uses zero-load linearization, not nonlinear inverse or independently calibrated decoder']
    elif req.membrane_model=='tensioned_q1':
        from membrane_tile import MembraneTile
        membrane=MembraneTile(k,pitch,req.pretension_N_mm,req.membrane_subdivisions)
        result=membrane.solve([(c.x_mm,c.y_mm,c.force_N) for c in req.contacts])
        transfer=result['transfer']
        model='linear_pretensioned_Q1_membrane_bonded_pad_springs'
        limitations=['prescribed isotropic membrane pretension; small transverse slope; no bending or in-plane stretch solve',
                     'finite square pads with bilateral mean displacement springs; no pad detachment, resolved 3D substrate or readout calibration',
                     'inverse basis uses taxel-centre point loads; off-centre contacts are not exactly in this basis',
                     'point load footprint is mesh-dependent; no contact multiplicity identification']
    else:
        result = tile_response(k,req.coupling_N_mm,f)
        # Same scalar operator for all basis vectors; preserve legacy model.
        transfer = np.column_stack([tile_response(k,req.coupling_N_mm,e.reshape(n,n))['reaction_N'].ravel() for e in np.eye(n*n)])
        model='linear_scalar_nearest_neighbour_tile'
        limitations=['assumed scalar coupling and direct reaction sensing','matched-model synthetic inverse problem',
                     'no physical membrane, curvature or readout calibration','contact multiplicity is not identified']
    y = result['reaction_N'].ravel()+np.random.default_rng(req.seed).normal(0.,req.noise_N,n*n)
    reconstruction, residual = nnls(transfer,y)
    reconstructed = reconstruction.reshape(n,n)
    def centroid(grid):
        if grid.sum()<=1e-12:return None
        iy,ix=np.indices(grid.shape)
        return [float((grid*ix).sum()*pitch/grid.sum()),float((grid*iy).sum()*pitch/grid.sum())]
    extra={k:result[k] for k in ('membrane_surface','membrane_energy_Nmm','spring_energy_Nmm','energy_balance_error_Nmm','free_residual_N','minimum_reaction_N','maximum_membrane_slope','small_slope_screen','small_slope_screen_limit','moderate_slope_screen','membrane_stretch_energy_Nmm','substrate_energy_Nmm','energy_balance_definition','substrate','receptor_compression_mm','iterations','inverse_basis','membrane_kinematics','inplane_displacement_max_mm') if k in result}
    return {'tier':'T0','model':model,'kz_N_mm':float(kz),**extra,
            'pitch_mm':pitch,'input_contacts':[c.model_dump(mode='json') for c in req.contacts],'load_grid_N':f.tolist(),'reaction_N':result['reaction_N'].tolist(),
            'displacement_mm':result['displacement_mm'].tolist(),'noisy_reactions_N':y.reshape(n,n).tolist(),
            'reconstructed_load_N':reconstructed.tolist(),'input_centroid_mm':centroid(f),
            'reconstructed_centroid_mm':centroid(reconstructed),'force_balance_error_N':result['force_balance_error_N'],
            'reconstruction_grid_rmse_N':float(np.sqrt(np.mean((f-reconstructed)**2))),
            'reconstruction_residual_N':float(residual),'transfer_condition':float(np.linalg.cond(transfer)),
            'limitations':limitations}


def build_router(select_candidate, preview_genome, current_run_id=None, compute=None):
    router=APIRouter()
    heavy=compute.route if compute is not None else (lambda name: lambda fn: fn)
    def resolve(req):
        def check_run():
            if req.expected_live_run_id is not None and (current_run_id is None or current_run_id()!=req.expected_live_run_id):
                raise HTTPException(409,'Live experiment changed; rebind the lab to the current candidate')
        check_run()
        c=select_candidate(req.selection,req.index,req.family,req.run_id,req.generation)
        check_run()
        if c is None:raise HTTPException(404,'Candidate not found')
        if req.expected_candidate_id is not None and str(c['id'])!=req.expected_candidate_id:
            raise HTTPException(409,'Candidate changed; rebind the lab')
        return c,preview_genome(c,req.piezo_count_override,req.piezo_wiring_override)

    @router.get('/v30')
    def lab():
        return FileResponse(Path(__file__).with_name('lab.html'),headers={'Cache-Control':'no-cache'})

    @router.get('/api/v30/capabilities')
    def capabilities():
        return {'nonlinear_box':True,'nonlinear_multimaterial_TET4':True,'nonlinear_voxel_candidate_diagnostic':True,'tile_T0':True,'tensioned_membrane_T0':True,'nonlinear_coupled_tile_T0':True,'multiscale_tile_optimization_T0':True,'sensor_fusion_T0':True,
                'T2_qualified':False,'T3_required_for_release':False,'T3_required_for_evolution':False,
                'hardware_certified':False}

    @router.post('/api/v30/nonlinear/contact-box')
    @heavy('verification_box')
    def box(req:BoxInput):
        if not CONTACT_SLOT.acquire(blocking=False):raise HTTPException(409,'Nonlinear solver busy')
        try:
            mesh=box_mesh(req.n,req.n,req.n*(2 if req.layered else 1),(req.side_mm,)*3)
            mat=NeoHookean(req.young_MPa,req.poisson);opts={}
            if req.layered:
                from .material_regions import layered_box_ids
                opts={'materials':[mat,NeoHookean(req.second_young_MPa,req.poisson)],'material_ids':layered_box_ids(mesh)}
            out=contact_report(mesh,mat,req.indentation_mm,req.penalty_N_per_mm3,**opts)
            return diagnostic_context(out,'nonlinear/contact-box',req)
        except (ValueError,RuntimeError,MemoryError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:CONTACT_SLOT.release()

    @router.post('/api/v30/nonlinear/candidate')
    @heavy('nonlinear_contact')
    def candidate(req:CandidateContact):
        c,g=resolve(req)
        if not CONTACT_SLOT.acquire(blocking=False):raise HTTPException(409,'Nonlinear solver busy')
        try:
            from physical_fem import voxel_mesh,FEMConfig
            m=voxel_mesh(c['family'],g,FEMConfig(pitch_mm=req.pitch_mm,max_cells=250),build_surface=False)
            if m.inflated_features and not req.allow_inflated_geometry:
                raise ValueError('Voxel geometry inflated; diagnostic override required or use a resolved mesh')
            mesh=hex8_to_tet4(m.nodes,m.elements)
            fixed=(3*m.bottom[:,None]+np.arange(3)[None,:]).ravel()
            mat=NeoHookean(float(g.get('material_E',1.)),req.poisson);opts={}
            if req.material_model=='stiff_plates':
                from .material_regions import receptor_plate_ids
                opts={'materials':[mat,NeoHookean(req.plate_young_MPa,req.plate_poisson)],
                      'material_ids':receptor_plate_ids(m,{**g,'_material_family':c['family']})}
            out=contact_report(mesh,mat,req.indentation_mm,req.penalty_N_per_mm3,fixed,**opts)
            out.update(candidate_id=c['id'],family=c['family'],mesh_source='voxel_HEX8_subdivision',
                       pitch_mm=req.pitch_mm,inflated_features=m.inflated_features,geometry_warning=m.geometry_warning)
            return diagnostic_context(out,'nonlinear/candidate',req,c,g)
        except (ValueError,RuntimeError,MemoryError,np.linalg.LinAlgError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:CONTACT_SLOT.release()

    @router.post('/api/v30/fusion')
    @heavy('sensor_fusion')
    def fusion(req:FusionInput):
        c,g=resolve(req)
        if not FUSION_SLOT.acquire(blocking=False):raise HTTPException(409,'Fusion solver busy')
        try:
            from sensor_fusion import evaluate_fusion
            result=evaluate_fusion(c['family'],g,grid=req.grid,frequency_hz=req.frequency_hz,seed=req.seed)
            result.update(candidate_id=c['id'],family=c['family'])
            return diagnostic_context(result,'fusion',req,c,g)
        except (ValueError,RuntimeError,ArithmeticError,np.linalg.LinAlgError) as exc:raise HTTPException(422,str(exc)) from exc
        finally:FUSION_SLOT.release()

    def solve_tile(req):
        c,g=resolve(req)
        try:
            from advanced import curve_stiffness
            k=curve_stiffness(c['family'],g,E=float(g.get('material_E',1.)))
            kz=1./np.linalg.solve(k,np.array([0.,0.,1.,0.,0.,0.]))[2]
            out=tile_report(kz,req)
            if out.get('substrate'):
                # Reference membrane is at nominal receptor top, substrate
                # top is at receptor base; substrate thickness is below that.
                out['substrate']['surface']['reference_z_mm']=-float(g['height'])
            out.update(candidate_id=c['id'],family=c['family'])
            return diagnostic_context(out,'tile',req,c,g)
        except (ValueError,RuntimeError,np.linalg.LinAlgError) as exc:raise HTTPException(422,str(exc)) from exc
    @router.post('/api/v30/tile')
    def tile(req:TileInput):
        if req.membrane_model=='nonlinear_coupled':raise HTTPException(422,'Use /api/v30/tile/nonlinear for coupled analysis')
        return solve_tile(req)

    @router.post('/api/v30/tile/nonlinear')
    @heavy('nonlinear_tile')
    def nonlinear_tile(req:TileInput):
        if req.membrane_model!='nonlinear_coupled':raise HTTPException(422,'Select nonlinear_coupled model')
        return solve_tile(req)
    @router.post('/api/v30/tile/optimize')
    @heavy('tile_optimization')
    def tile_optimize(req:TileOptimizeInput):
        c,g=resolve(req)
        try:
            if any(not .001<=v<=20 for v in req.tensions) or any(not .1<=v<=20 for v in req.substrate_depths_mm):
                raise ValueError('Tension and substrate depth outside bounded range')
            from tile_optimization import receptor_descriptor,designs,optimize
            receptors=[receptor_descriptor(c,g)]
            receptor_models={str(c['id']):(c,g)}
            if req.include_library:
                import random
                from hybrid_library import ranked,genome_for
                for spec in ranked():
                    identity='hybrid-'+spec.id
                    if identity==c['id']:continue
                    other=genome_for(spec,random.Random(1701))
                    model={'id':identity,'family':spec.upper_family}
                    receptors.append(receptor_descriptor(model,other))
                    receptor_models[identity]=(model,other)
                    if len(receptors)>=3:break
            ds,excluded=designs(receptors,req.patch_side_mm,req.sizes,req.tensions,req.substrate_depths_mm,
                req.substrate_young_MPa,req.membrane_young_MPa,req.membrane_thickness_mm,req.noise_N,req.seed)
            allocation=compute.current_allocation() if compute is not None else None
            workers=allocation['cpu_workers'] if allocation else 1
            progress=compute.progress_callback() if compute is not None else lambda _:None
            out=optimize(ds,excluded,req.finalists,workers,progress)
            from skin_patch_preview import attach_skin_previews
            attach_skin_previews(out,receptor_models)
            out.update(candidate_id=c['id'],family=c['family'])
            return diagnostic_context(out,'tile/optimize',req,c,g)
        except (ValueError,RuntimeError,ArithmeticError,np.linalg.LinAlgError,MemoryError) as exc:raise HTTPException(422,str(exc)) from exc
    return router
