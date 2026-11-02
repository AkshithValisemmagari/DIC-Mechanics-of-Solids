"""Run a benchmark, all benchmarks, robustness studies, or the complete project."""
import argparse
import json
import time
from pathlib import Path
from pipeline import run_experiment
from experiments.robustness import run_robustness

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark',choices=['axial_bar','cantilever','plate_with_hole','all'],default='all')
    parser.add_argument('--config',type=Path,help='Run one custom benchmark JSON (overrides --benchmark).')
    parser.add_argument('--robustness',action='store_true',help='Also run the repeated robustness study.')
    parser.add_argument('--robustness-only',action='store_true')
    parser.add_argument('--study-config',type=Path,default=ROOT/'configs/robustness.json')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs')
    args=parser.parse_args()
    started=time.perf_counter()
    names={'axial_bar':'axial_bar_dic','cantilever':'cantilever','plate_with_hole':'plate_with_hole'}
    summaries=[]
    if not args.robustness_only:
        selected=names if args.benchmark=='all' else {args.benchmark:names[args.benchmark]}
        configs=[args.config] if args.config else [ROOT/'configs'/f'{name}.json' for name in selected.values()]
        for file in configs:
            config=json.loads(file.read_text(encoding='utf-8'))
            target='axial_bar_dic' if config['benchmark']=='axial_bar' else config['benchmark']
            print('Running '+target,flush=True)
            bundle=run_experiment(config,args.output_dir/target)
            summaries.append(bundle['summary'])
            print(json.dumps(bundle['summary'],indent=2),flush=True)
    if args.robustness or args.robustness_only:
        base=json.loads((ROOT/'configs/axial_bar_dic.json').read_text(encoding='utf-8'))
        settings=json.loads(args.study_config.read_text(encoding='utf-8'))
        run_robustness(base,settings,args.output_dir/'robustness')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    if summaries:
        (args.output_dir/'benchmark_summary.json').write_text(
    json.dumps(summaries, indent=2),
    encoding='utf-8'
)
    # Only link reports that exist, so single-benchmark runs have no dead links.
    links=[]
    for title,folder in [('Axial bar','axial_bar_dic'),('Cantilever','cantilever'),('Plate with hole','plate_with_hole'),('Robustness study','robustness')]:
        if (args.output_dir/folder/'report.html').exists():
            links.append(f'<li><a href="{folder}/report.html">{title}</a></li>')
    (args.output_dir/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Virtual Solid Mechanics Lab</title><body style="font:18px system-ui;max-width:850px;margin:60px auto;padding:24px"><h1>Virtual Solid Mechanics Lab</h1><p>Analytical ground truth · Synthetic imaging · Subpixel DIC · Strain and stress · Robustness</p><ul>'+''.join(links)+'</ul><p>Open a report to inspect saved results. These links show the most recent saved run in each folder; each report includes its configuration.</p></body>')
    print(f'Finished in {time.perf_counter()-started:.1f} s. Open {args.output_dir.resolve() / "index.html"}',flush=True)


if __name__=='__main__': main()
