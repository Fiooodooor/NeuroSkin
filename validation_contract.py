"""Versioned and fail-closed validation contracts (NeuroSkin 2.2).

Protocol hashes are based on canonical JSON, not filesystem metadata. Tiers are
claims requiring explicit evidence, never inferred from numerical fitness.
"""
from __future__ import annotations

from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import platform
from pathlib import Path
from typing import Any, Literal
import json
import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROTOCOL_PATH = Path(__file__).with_name('validation_protocol_v30.json')
SCHEMA_VERSION = 'neuroskin.validation_report.v1'
Fidelity = Literal['T0', 'T1', 'T2', 'T3']
SOURCE_TYPES = ('synthetic_surrogate', 'linear_fem', 'nonlinear_fem', 'hardware_measurement')
TIER_RANK = {'T0': 0, 'T1': 1, 'T2': 2, 'T3': 3}


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(obj: Any) -> str:
    return sha256(canonical_json(obj)).hexdigest()


class Protocol(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: Literal['neuroskin.validation_protocol.v0.1']
    purpose: str
    units: dict[str, str]
    design_envelope: dict[str, Any]
    dataset_splits: dict[str, Any]
    load_cases: dict[str, Any]
    metrics: dict[str, str]
    fidelity_tiers: dict[str, str]
    promotion_policy: dict[str, Any]

    @model_validator(mode='after')
    def check_ranges(self):
        splits = self.dataset_splits
        fractions = [float(splits[f'{part}_fraction']) for part in ('train', 'validation', 'test')]
        if any(x <= 0 or x >= 1 for x in fractions) or abs(sum(fractions) - 1) > 1e-10:
            raise ValueError('Dataset fractions must be positive and sum to 1')
        loads = self.load_cases
        if not loads['normal_forces_N'] or any(float(f) <= 0 for f in loads['normal_forces_N']):
            raise ValueError('Positive normal loads required')
        if len(loads['contact_grid']['resolution']) != 2 or any(int(v) < 3 for v in loads['contact_grid']['resolution']):
            raise ValueError('Contact grid must be >=3x3')
        if self.promotion_policy['top_k'] != 3 or not self.promotion_policy['same_fidelity_tier_only']:
            raise ValueError('Top-3 and same-tier promotion are mandatory')
        if set(self.fidelity_tiers) != set(TIER_RANK):
            raise ValueError('Explicit T0..T3 fidelity tiers required')
        return self


def load_protocol(path: str | Path | None = None) -> Protocol:
    p = Path(path) if path is not None else PROTOCOL_PATH
    if p.stat().st_size > 256_000:
        raise ValueError('Protocol file exceeds safe size')
    return Protocol.model_validate_json(p.read_text(encoding='utf-8'))


class TestResult(BaseModel):
    __test__ = False  # Pytest must not mistake the Pydantic schema for a test class.
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80)
    status: Literal['pass', 'fail', 'not_run', 'unsupported']
    source: Literal['synthetic_surrogate', 'linear_fem', 'nonlinear_fem', 'hardware_measurement']
    metric: float | None = None
    limit: float | None = None
    reason: str = ''

    @model_validator(mode='after')
    def finite(self):
        for field in ('metric', 'limit'):
            value = getattr(self, field)
            if value is not None and not math.isfinite(value):
                raise ValueError(f'Non-finite {field} not permitted')
        return self


class Evidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    solver: str
    solver_hash: str
    material_hash: str
    seed: int
    noise_provenance: Literal['assumed', 'measured']
    calibration_specimen: str | None = None
    measured_data_sha256: str | None = None
    mesh_convergence_verified: bool = False
    independent_validation_verified: bool = False
    nonlinear_contact_verified: bool = False
    environment_versions: dict[str, str] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['neuroskin.validation_report.v1'] = SCHEMA_VERSION
    candidate_id: str
    family: str
    protocol_hash: str
    genome_hash: str
    evidence: Evidence
    tier: Fidelity = 'T0'
    source: Literal['synthetic_surrogate', 'linear_fem', 'nonlinear_fem', 'hardware_measurement']
    tests: list[TestResult]
    metrics: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    eligible_for_same_tier_promotion: bool = False
    pass_current_tier: bool = False

    @model_validator(mode='after')
    def enforce_fidelity_and_completeness(self):
        # Fail closed: no unknown, duplicate, or missing mandatory tests.
        identifiers = [t.id for t in self.tests]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Duplicate validation test IDs')
        required = {'contact_load', 'no_contact', 'independent_holdout',
                    'sensor_covariance', 'geometry_screen'}
        existing = {t.id: t for t in self.tests}
        if required - set(existing):
            raise ValueError(f'Missing mandatory tests: {sorted(required-set(existing))}')
        passing = all(existing[k].status == 'pass' for k in required)
        if self.tier == 'T1':
            passing = passing and self.evidence.mesh_convergence_verified and 'continuum_fem' in existing and existing['continuum_fem'].status == 'pass'
        if self.tier == 'T2':
            passing = passing and self.evidence.mesh_convergence_verified and self.evidence.nonlinear_contact_verified and self.evidence.independent_validation_verified and 'nonlinear_contact' in existing and existing['nonlinear_contact'].status == 'pass'
        if self.tier == 'T3':
            passing = passing and self.evidence.noise_provenance == 'measured' and self.evidence.calibration_specimen is not None and self.evidence.measured_data_sha256 is not None and self.evidence.independent_validation_verified and self.source == 'hardware_measurement' and 'hardware_test' in existing and existing['hardware_test'].status == 'pass'
        if self.tier != 'T0' and self.source == 'synthetic_surrogate':
            raise ValueError('Synthetic data cannot be labeled as higher-fidelity validation')
        if self.pass_current_tier and not passing:
            raise ValueError('Validation report claims success without required evidence')
        if self.eligible_for_same_tier_promotion and not passing:
            raise ValueError('Candidate cannot be promoted on incomplete/failed tests')
        return self


def candidate_comparable(a: dict, b: dict) -> tuple[bool, str]:
    """Strictly compare protocol/fidelity before comparing any scalar score."""
    if not a or not b:
        return False, 'missing_report'
    if a.get('protocol_hash') != b.get('protocol_hash'):
        return False, 'different_protocol_hash'
    if a.get('tier') != b.get('tier'):
        return False, 'different_fidelity_tier'
    for key in ('noise_provenance', 'mesh_convergence_verified'):
        if a.get('evidence', {}).get(key) != b.get('evidence', {}).get(key):
            return False, f'different_{key}'
    return True, 'same_protocol_fidelity_noise_basis'


def choose_validated_champion(incumbent: dict | None, contenders: list[dict]):
    """No cross-tier score comparison. Incomparable incumbent stays incumbent.

    The function requires a ValidationReport in candidate['validation_v30'].
    Score is a *within-tier* screening tie-breaker, not physical accuracy.
    """
    items = ([incumbent] if incumbent is not None else []) + list(contenders)
    for item in items:
        if not item or 'validation_v30' not in item:
            raise ValueError('Every contender needs a completed validation report')
        ValidationReport.model_validate(item['validation_v30'])
    if not items:
        return None, {'reason': 'no_candidates'}
    anchor = incumbent['validation_v30'] if incumbent else items[0]['validation_v30']
    eligible = []
    rejected = []
    for c in items:
        report = c['validation_v30']
        ok, reason = candidate_comparable(anchor, report)
        if ok and report['eligible_for_same_tier_promotion']:
            eligible.append(c)
        else:
            rejected.append({'id': c['id'], 'reason': reason if not ok else 'validation_not_passed'})
    if not eligible:
        return incumbent, {'reason': 'no_eligible_comparable_candidate', 'rejected': rejected}
    best = max(eligible, key=lambda x: (float(x['audit']['audit_score']), x is incumbent))
    if incumbent is not None and best is not incumbent and incumbent in eligible:
        if float(best['audit']['audit_score']) <= float(incumbent['audit']['audit_score']) + 1e-8:
            best = incumbent
    return best, {'reason': 'same_tier_verified_selection', 'rejected': rejected,
                  'selected': best['id'], 'replaced': incumbent is not None and best['id'] != incumbent['id']}


def runtime_versions() -> dict[str, str]:
    """Archive package versions for numerical reproducibility."""
    result={'python':platform.python_version(), 'platform':platform.platform()}
    for name in ('numpy','scipy','numba','trimesh','pydantic','fastapi'):
        try:result[name]=version(name)
        except PackageNotFoundError:result[name]='not_installed'
    return result
