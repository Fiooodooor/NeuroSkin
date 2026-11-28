"""Local-only CSV import of instrumented tactile-rig measurements.

This module does NOT assert hardware validation merely because a file was read.
It performs schema, units, finite-value and group-leakage checks, and produces
an independent held-out estimate when enough measured contact positions exist.
CSV files are not accessible through the web API.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import csv
import json
import math
import argparse
import numpy as np

from sensor_metrics import decoder_holdout, NOISE_SIGMA

EXPECTED = ('session_id','position_group','indenter','force_x_N','force_y_N','force_z_N',
            'contact_x_mm','contact_y_mm','c1_pF','c2_pF','c3_pF','c4_pF',
            'lateral_x_pF','lateral_y_pF','torsion_mT')
FEATURE_COLUMNS = EXPECTED[8:]
TARGET_COLUMNS = EXPECTED[3:8]
MAX_FILE_SIZE = 25 * 1024 * 1024


def load_measured_csv(path: str | Path, *, assumed_noise=None, seed: int = 3322):
    p = Path(path).resolve(strict=True)
    if not p.is_file() or p.stat().st_size > MAX_FILE_SIZE:
        raise ValueError('Measurement file missing or exceeds 25 MiB')
    raw = p.read_bytes()
    if b'\x00' in raw:
        raise ValueError('Binary or NUL-containing CSV is not accepted')
    # UTF8 BOM allowed; all other encodings are intentionally unsupported.
    text = raw.decode('utf-8-sig')
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None or any(k not in reader.fieldnames for k in EXPECTED):
        raise ValueError('Missing required measurement CSV columns')
    X, Y, groups, sessions, indenters = [], [], [], set(), set()
    for i, row in enumerate(reader, 2):
        try:
            y = [float(row[k]) for k in TARGET_COLUMNS]
            x = [float(row[k]) for k in FEATURE_COLUMNS]
            if not np.isfinite(x).all() or not np.isfinite(y).all():
                raise ValueError('Nonfinite numerical field')
        except (ValueError,TypeError) as exc:
            raise ValueError(f'Invalid measurement values on CSV line {i}: {exc}') from exc
        if not row['session_id'] or not row['position_group'] or not row['indenter']:
            raise ValueError(f'Missing session, position, or indenter label on CSV line {i}')
        sessions.add(row['session_id']);indenters.add(row['indenter'])
        X.append(x);Y.append(y);groups.append(row['position_group'])
    if len(X) < 20 or len(set(groups)) < 5:
        raise ValueError('At least 20 measurements and 5 distinct contact-position groups required')
    noise = NOISE_SIGMA if assumed_noise is None else np.asarray(assumed_noise, float)
    # With no independently characterized noise, decoder perturbations are still
    # assumed and cannot support an absolute hardware SNR claim.
    result = decoder_holdout(X,Y,groups,seed=seed,assumed_noise=noise,add_synthetic_noise=False)
    result['input_file_sha256'] = sha256(raw).hexdigest()
    result['sessions'] = sorted(sessions)
    result['indenters'] = sorted(indenters)
    result['row_count'] = len(X)
    result['position_group_count'] = len(set(groups))
    result['data_origin'] = 'user_supplied_measurement_unverified_origin'
    result['noise_provenance'] = 'assumed' if assumed_noise is None else 'externally_supplied_not_verified'
    result['qualification'] = 'T3_NOT_GRANTED: requires reference sensor calibration, uncertainty budget and independently measured noise'
    result['cautions'] = ['CSV import does not prove data authenticity',
                          'The readout model has not been recalibrated from these measurements',
                          'Grouped contact-position holdout does not replace independent hardware sessions']
    return result


def main():
    parser=argparse.ArgumentParser(description='Validate locally supplied robotic skin measurement CSV')
    parser.add_argument('csv',type=Path)
    parser.add_argument('--out',type=Path,default=Path('measured_validation.json'))
    parser.add_argument('--seed',type=int,default=3322)
    args=parser.parse_args()
    result=load_measured_csv(args.csv,seed=args.seed)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'saved':str(args.out),'qualification':result['qualification'],
                      'force_rmse_norm_N':result['force_rmse_norm_N']},indent=2))

if __name__=='__main__':
    main()
