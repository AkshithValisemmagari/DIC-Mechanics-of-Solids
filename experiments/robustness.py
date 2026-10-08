"""One-factor-at-a-time image robustness studies with repeated noise seeds."""
import copy
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import run_experiment


def run_robustness(base_config, settings, output_dir):
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    base = copy.deepcopy(base_config)
    base['image']['shape'] = settings['image_shape']
    base['dic']['step'] = settings['step']
    base['strain']['fit_radius_px'] = settings['step']*2.25
    rows = []
    for factor, levels in settings['factors'].items():
        for level in levels:
            for repeat, seed in enumerate(settings['seeds']):
                c = copy.deepcopy(base)
                c['camera']['seed'] = seed
                c['camera']['noise_std'] = settings['background_noise_std']
                if factor in ('noise_std', 'blur_sigma', 'brightness_gain'):
                    c['camera'][factor] = level
                elif factor == 'subset_size': c['dic']['subset_size'] = level
                elif factor == 'speckle_radius_px': c['image']['speckle_radius_px'] = level
                else: raise ValueError('Unsupported study factor: '+factor)
                b = run_experiment(c, make_plots=False)
                s = b['summary']
                rows.append(dict(factor=factor, level=level, repeat=repeat, noise_seed=seed,
                                 displacement_rmse_px=s['displacement_px']['vector_rmse'],
                                 strain_rmse=s['strain']['vector_rmse'], stress_rmse_pa=s['stress_pa']['vector_rmse'],
                                 failure_fraction=s['eligible_match_failure_fraction'],
                                 coverage_fraction=s['coverage_fraction'], valid_subsets=s['valid_displacement_subsets']))
                print(f'  {factor}={level} seed={seed}: RMSE={rows[-1]["displacement_rmse_px"]}', flush=True)
                # Checkpoint every completed trial.
                with (out/'experiment_results.csv').open('w', newline='') as f:
                    writer=csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (out/'study_settings.json').write_text(json.dumps(settings, indent=2))
    (out/'base_config.json').write_text(json.dumps(base, indent=2))
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), layout='constrained')
    grouped=[]
    for ax, (factor, levels) in zip(axes.flat, settings['factors'].items()):
        means=[]; deviations=[]
        for level in levels:
            values=[r['displacement_rmse_px'] for r in rows if r['factor']==factor and r['level']==level and r['displacement_rmse_px'] is not None]
            mean=float(np.mean(values)) if values else np.nan
            std=float(np.std(values, ddof=1)) if len(values)>1 else 0
            means.append(mean);deviations.append(std)
            grouped.append(dict(factor=factor,level=level,mean_rmse_px=mean,std_rmse_px=std,repeats=len(values)))
        ax.errorbar(levels,means,yerr=deviations,marker='o',capsize=4,color='#176B87')
        ax.set(xlabel=factor,ylabel='Displacement vector RMSE (px)',title=factor.replace('_',' ').title());ax.grid(alpha=.2)
    axes.flat[-1].axis('off')
    axes.flat[-1].text(0, .9, 'Error bars: sample standard deviation\nacross independent noise seeds.\n\nOne factor changes at a time.\nSpeckle realization held fixed.\nFailure and coverage in CSV.\nNo monotonic trend is assumed.', va='top')
    fig.savefig(out/'robustness_summary.png',dpi=160);plt.close(fig)
    with (out/'grouped_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(grouped[0]));w.writeheader();w.writerows(grouped)
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>DIC robustness study</title><body style="font:16px system-ui;max-width:1100px;margin:40px auto"><h1>DIC robustness study</h1><p>Actual repeated trials; independent camera noise in both images. Noise is specified on the 0–1 intensity scale; blur and speckle radius in pixels. Error bars are sample standard deviations, not confidence intervals.</p><img style="width:100%" src="robustness_summary.png"><p>See experiment_results.csv for strain/stress errors, match failures and coverage. Study settings and the base configuration are saved alongside the results. Different subset sizes change spatial resolution and eligible centres; this is not a fixed-centre comparison.</p></body>')
    return rows
