"""Paired scalar-field errors on identical valid measurement centres."""
import csv
import json
import numpy as np


def compare_payloads(baseline,noisy):
    if not np.array_equal(np.asarray(baseline['dic'])[:,:2],np.asarray(noisy['dic'])[:,:2]):
        raise ValueError('Paired experiments must use identical candidate centres.')
    comparison={}
    for key,field in noisy['fields'].items():
        truth=np.asarray(field['truth'],float);n=np.asarray(field['measured'],float)
        b=np.asarray(baseline['fields'][key]['measured'],float)
        np.testing.assert_allclose(truth,np.asarray(baseline['fields'][key]['truth'],float),equal_nan=True)
        bv=np.asarray(baseline['dic'])[:,9].astype(bool)&np.isfinite(b)&np.isfinite(truth)
        nv=np.asarray(noisy['dic'])[:,9].astype(bool)&np.isfinite(n)&np.isfinite(truth)
        common=bv&nv
        def errors(values):
            e=values[common]-truth[common]
            return dict(rmse=float(np.sqrt(np.mean(e*e))) if e.size else None,
                        max_abs=float(np.max(np.abs(e))) if e.size else None)
        comparison[key]=dict(label=field['label'],unit=field['unit'],common_count=int(common.sum()),
                             baseline_valid=int(bv.sum()),noisy_valid=int(nv.sum()),
                             baseline=errors(b),noisy=errors(n))
    return comparison


def save_comparison(comparison,out):
    (out/'noise_comparison.json').write_text(json.dumps(comparison,indent=2,allow_nan=False))
    with (out/'noise_comparison.csv').open('w',newline='') as file:
        writer=csv.writer(file)
        writer.writerow(['field','unit','common_count','baseline_valid','noisy_valid','baseline_rmse','noisy_rmse','baseline_max_abs','noisy_max_abs'])
        for key,v in comparison.items():
            writer.writerow([key,v['unit'],v['common_count'],v['baseline_valid'],v['noisy_valid'],v['baseline']['rmse'],v['noisy']['rmse'],v['baseline']['max_abs'],v['noisy']['max_abs']])
    import html
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in [v['label'],v['unit'],v['common_count'],v['baseline']['rmse'],v['noisy']['rmse']])+'</tr>' for v in comparison.values())
    section='<h2>Paired Gaussian noise experiment</h2><p>Identical speckle seed, load, camera blur/brightness and DIC settings; only Gaussian noise differs. Baseline still includes quantization and selected blur. Errors below use common valid centres. A single noisy trial need not worsen every metric.</p><table><tr><th>Field</th><th>Unit</th><th>Common n</th><th>Baseline RMSE</th><th>Noisy RMSE</th></tr>'+rows+'</table><p><a href="baseline/report.html">Baseline report</a> · <a href="noise_comparison.csv">Comparison CSV</a></p>'
    report=out/'report.html';report.write_text(report.read_text().replace('</body>',section+'</body>'))
