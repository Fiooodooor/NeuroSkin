"""CLI access to standardized synthetic validation, no web server required."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from evaluation_v30 import evaluate_protocol
from validation_contract import load_protocol


def main():
    parser=argparse.ArgumentParser(description='Versioned NeuroSkin T0 validation benchmark')
    parser.add_argument('--genome',required=True,type=Path,help='Genome JSON (not executable code)')
    parser.add_argument('--family',choices=['crown','chiral','quadrant'],required=True)
    parser.add_argument('--seed',type=int,default=3322)
    parser.add_argument('--out',type=Path,default=Path('validation_report_v30.json'))
    parser.add_argument('--mc-samples',type=int,default=8)
    args=parser.parse_args()
    if args.genome.stat().st_size > 1_000_000:
        parser.error('Genome JSON exceeds 1 MiB')
    genome=json.loads(args.genome.read_text(encoding='utf-8'))
    if not isinstance(genome,dict):
        parser.error('Genome JSON must be an object')
    # Never deserialize pickles and never import code from a genome.
    report=evaluate_protocol(args.family,genome,seed=args.seed,
                             monte_carlo_samples=args.mc_samples)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'report':str(args.out),'tier':report['tier'],
                      'pass_current_tier':report['pass_current_tier'],
                      'protocol_hash':report['protocol_hash']},indent=2))

if __name__=='__main__':
    main()
