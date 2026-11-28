# What the displayed sensor parts mean

The selected-geometry view is a conceptual assembly. Its component labels describe intended functions; displaying a colored part does not establish a manufactured sensor, an electrode interface or local FEM ownership. Select a component in the tree to read its role. Selected faces receive a bright yellow highlight; ordinary PVDF/sensor colors are also warm colors.

| Part | Role and current limits |
| --- | --- |
| Contact pad | Receives touch and transmits the applied wrench into the flexures. Reduced mechanics generally uses a rigid moving pad. A continuous robot-skin membrane is a separate model. |
| Flexure | Elastic spring member. Curvature, thickness and attachments control compliance and coupling. Its bending/stretching also strains an attached PVDF film. |
| Base support | Mounting anchor, fixed in the single-button model. Compliance of a larger skin substrate is handled separately. |
| Sensor placeholder | Marks an intended sensing location. The displayed block does not resolve the electrodes, dielectric, PCB, interconnect or readout electronics. |
| PVDF film | A bonded piezoelectric polymer film. Transferred strain generates signed charge, with approximate adhesive transfer and readout dynamics. |
| Conceptual hub | The small single-stage quadrant hub under the pad: diameter 2 mm, thickness 0.4 mm. It has no dedicated sensing law, assigned magnetic function or separately modeled load-path role. It is not a validated magnet or overload stop. |
| Intermediate coupling plate | In a two-stage hybrid, the inner plate has a different function: it mechanically couples the upper and lower flexure stages. |
| Magnet placeholder | The chiral concept includes a magnetic marker. A complete calibrated magnet/Hall assembly and field solution are not implemented. |

## Static and slow sensing

The electrical surrogate aggregates support reactions into four basal quadrants. It assumes a compliant electrode gap and computes a capacitance change. A physical implementation needs two electrodes, an appropriate dielectric/gap, a readout circuit and calibration. Capacitance depends on geometry approximately as `C = epsilon * area / gap` in the parallel-plate approximation.

Four basal readings do not generally identify arbitrary Fx/Fy/Fz and contact x/y simultaneously. The current seven-channel surrogate additionally assumes two differential lateral-capacitance outputs and one torsional Hall output. Those channels are mathematical transfer laws; the quadrant hub is not a physical implementation of the assumed Hall channel.

The optional resistive response is also illustrative, not a chosen calibrated sensor material. See `electromechanics.py::signals` and `sensor_metrics.py::response_vector` for the actual channels. A real capacitive readout is illustrated by [TI's capacitive sensor front-end reference design](https://www.ti.com/tool/TIDA-00662).

## Dynamic PVDF sensing

Load deforms the flexure; adhesive transfers strain into the PVDF film. A poled film with electrodes generates charge under strain. The model uses a uniaxial d31 relation, effective film area/modulus and approximate strain transfer. The chosen film orientation and signed wiring affect the output.

A charge amplifier converts charge into voltage, followed by filtering and digitisation. Films may be read independently or combined with declared signed wiring; arbitrary summation of voltages from independent amplifiers is not a physical wiring model.

The readout has a finite leakage/RC time constant. Its signal decays under sustained strain, so PVDF complements a static channel for touch onset/release, vibration and other dynamic events. It does not supply an indefinitely stable DC force measurement alone. [TE Connectivity explains the dynamic-strain and leakage behavior](https://www.te.com/en/whitepapers/sensors/piezo-solution-for-vital-signs-monitoring.html).

Bonded-film stiffness and shear-lag corrections do not constitute a complete coupled PVDF–adhesive–elastomer/electronics solution. Hardware force accuracy and slip classification still require appropriate assembly, measurements and independent validation.

Related: [validation limits](VALIDATION.md), [current roadmap](RELEASE_PLAN_V30.md).
