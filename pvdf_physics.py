"""Shared uniaxial broad-face d31 transduction (mm, MPa, pC).

Stress is the effective axial film stress after mechanical transfer. This is
not a coupled piezoelectric field solution or a d33 electrode configuration.
"""
import math
D31_PC_PER_N = -23.0
EPS0_PF_MM = .0088541878128


def electrode_area_mm2(props):
    area = float(props['effective_width_mm']) * float(props['effective_span_mm'])
    if not math.isfinite(area) or area <= 0:
        raise ValueError('Invalid electrode area')
    return area


def charge_pc(props, effective_strain):
    """Signed charge from mean effective film strain, not cross-section force."""
    strain = float(effective_strain)
    modulus = float(props['pvdf_E_MPa'])
    if not math.isfinite(strain) or not math.isfinite(modulus) or modulus <= 0:
        raise ValueError('Invalid film strain or modulus')
    return D31_PC_PER_N * modulus * strain * electrode_area_mm2(props)


def capacitance_pf(props, epsilon_r=12.0):
    t = float(props['film_thickness_mm'])
    if not math.isfinite(t) or t <= 0 or not math.isfinite(epsilon_r) or epsilon_r <= 0:
        raise ValueError('Invalid film dielectric properties')
    return EPS0_PF_MM * epsilon_r * electrode_area_mm2(props) / t
