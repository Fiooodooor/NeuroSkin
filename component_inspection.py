"""Stable conceptual component IDs and face spans, not FEM element ownership."""
import numpy as np
import trimesh

LABELS={'base':'Support','contact':'Contact pad','flexure':'Flexure','sensor':'Sensor placeholder','inner':'Conceptual internal feature','piezo':'PVDF film'}
FUNCTIONS={
    'base':'Mounting support; fixed in the single-button model. A skin substrate has a separate compliance model.',
    'contact':'Receives external touch and transfers load to the flexures; treated as a rigid moving pad in reduced mechanics.',
    'flexure':'Elastic spring member. Bending and stretching transmit loads to the supports and strain the bonded PVDF film.',
    'sensor':'Sensor location placeholder, not a resolved electrode/dielectric/PCB assembly. Basal capacitance is computed from assumed mount compliance and reaction force; it is not a calibrated hardware measurement.',
    'inner':'Conceptual internal feature with no dedicated sensor or separately modeled load-path role. It is not a validated magnet, Hall sensor or overload stop.',
    'piezo':'Bonded PVDF film converts transferred strain to charge. Charge-amplifier/RC response is approximated; sustained DC force needs a complementary static channel.',
}


def pack_components(groups,members,film_members,stage_by_member,hybrid,family=None):
    """Use exactly the primitives consumed by the ordinary mesh export."""
    if len(members)!=len(stage_by_member) or len(groups.get('flexure',[]))!=len(members):
        raise ValueError('Component/member count mismatch')
    if len(groups.get('piezo',[]))!=len(film_members):
        raise ValueError('Component/film count mismatch')
    components=[];nodes=[]
    for part,primitives in groups.items():
        if not primitives:continue
        merged=trimesh.util.concatenate(primitives)
        components.append({'part':part,'vertices':np.round(merged.vertices,3).tolist(),'faces':merged.faces.tolist()})
        face_start=0;vertex_start=0
        for i,mesh in enumerate(primitives):
            node={'id':f'{part}:{i}','part':part,'label':f'{LABELS[part]} {i+1}',
                  'face_start':face_start,'face_count':len(mesh.faces),
                  'vertex_start':vertex_start,'vertex_count':len(mesh.vertices),
                  'bounds_mm':np.round(mesh.bounds,4).tolist(),
                  'stage':'assembly','member_index':None,'film_index':None,'function':FUNCTIONS[part]}
            if part=='flexure':
                pts,r,tag=members[i]
                node.update(stage=stage_by_member[i],member_index=i,role=tag,
                            centerline_length_mm=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()),
                            nominal_radius_mm=float(r))
            elif part=='piezo':
                film_index,member_index=film_members[i]
                node.update(id=f'piezo:{film_index}',film_index=film_index,
                            label=f'PVDF film {film_index+1}',stage=stage_by_member[member_index],
                            member_index=member_index,bonded_to=f'flexure:{member_index}')
            elif part=='inner' and hybrid:
                node.update(label='Intermediate coupling plate',stage='interface',
                            function='Mechanical coupling plate between the upper and lower stages; transmits load between their flexures.')
            elif part=='inner' and family=='quadrant':
                node.update(label='Conceptual hub',function=FUNCTIONS['inner'])
            elif part in ('base','sensor'):node['stage']='base'
            elif part=='contact':node['stage']='contact'
            if part=='sensor' and family=='chiral' and not hybrid and i==4:
                node.update(label='Magnet placeholder',function='Conceptual magnetic marker. The Hall torsion channel is an assumed local transfer law, not a solved magnet/Hall assembly.')
            nodes.append(node)
            face_start+=len(mesh.faces);vertex_start+=len(mesh.vertices)
        if face_start!=len(merged.faces) or vertex_start!=len(merged.vertices):
            raise ValueError('Unexpected mesh concatenation layout')
    return {'components':components,'component_tree':{'schema':1,'nodes':nodes,
             'stage_order':['contact','upper','interface','lower','single','base','assembly'],
             'note':'Concept mesh primitives and actual generated film attachments. IDs are local to the candidate geometry. No FEM element mapping or measured local force.'},
            'note':'Concept geometry with tapered detailed flexures; separate mechanics uses reduced-order proxy and/or actual FEM depending on workflow.'}
