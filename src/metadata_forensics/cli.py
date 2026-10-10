import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description='B01–B05 temporal metadata forensics')
    sub = parser.add_subparsers(dest='stage', required=True)
    for stage in ['b01','b02','b03','b04']:
        p = sub.add_parser(stage)
        p.add_argument('--n-patients', type=int, default=40 if stage == 'b01' else 4000)
        p.add_argument('--seed', type=int, default=42)
        p.add_argument('--output', type=Path, default=Path('outputs')/stage)
        if stage == 'b02':
            p.add_argument('--methods', nargs='+', choices=['nearest','assignment','sequence','likelihood'])
        if stage == 'b04':
            p.add_argument('--full', action='store_true', help='All 10 conditions instead of 3')
    p = sub.add_parser('b05')
    p.add_argument('--case', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path('outputs/b05'))
    p.add_argument('--live', action='store_true', help='Send evidence to the configured LLM endpoint')
    p.add_argument('--provider', choices=['deepseek','openai','ollama'])
    p.add_argument('--model')
    args = parser.parse_args(argv)
    if args.stage == 'b05':
        from .reporting import run_report
        run_report(args.case, args.output, live=args.live, provider=args.provider, model=args.model)
        print('LLM report saved.' if args.live else 'Evidence prepared; no API call made.')
    else:
        if args.n_patients < 2 and args.stage in ('b03','b04'):
            parser.error('Corruption experiments require at least two patients')
        from .pipeline import run_experiment
        run_experiment(args.stage, args.output, args.n_patients, args.seed,
                       full=getattr(args,'full',False), methods=getattr(args,'methods',None))

if __name__ == '__main__':
    main()
