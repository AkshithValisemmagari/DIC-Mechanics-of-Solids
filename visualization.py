"""Plot analytical fields; plot units are explicitly labelled."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_axial_bar(result, destination):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), layout="constrained")
    fields = [(result.displacement_m * 1e3, "Displacement (mm)", "Displacement"),
              (result.strain * 1e6, "Strain (microstrain)", "Strain"),
              (result.stress_pa / 1e6, "Stress (MPa)", "Stress")]
    for ax, (values, ylabel, title) in zip(axes, fields):
        ax.plot(result.x_m, values, color="#176B87", linewidth=2.5)
        ax.set(xlabel="Reference position x (m)", ylabel=ylabel, title=title)
        ax.grid(alpha=0.25)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    fig.suptitle("Uniform axial bar | Analytical ground truth", fontsize=15)
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def plot_experiment(b, out):
    import numpy as np
    from stress import invariants
    fig, ax = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    for a, key, title in zip(ax[:2], ['reference', 'deformed'], ['Reference image', 'Deformed image']):
        a.imshow(b[key], cmap='gray', vmin=0, vmax=1); a.set_title(title); a.set_axis_off()
    d = b['dic']; good = d[:, 9].astype(bool)
    error = np.linalg.norm(d[:, 2:4]-b['true_disp'], axis=1)
    ax[2].imshow(b['reference'], cmap='gray', vmin=0, vmax=1, alpha=0.3)
    scatter = ax[2].scatter(d[good, 0], d[good, 1], c=error[good], s=22, cmap='magma', vmin=0)
    ax[2].set(title='Displacement error (pixels)', xlabel='Column (px)', ylabel='Row (px)')
    fig.colorbar(scatter, ax=ax[2], shrink=0.75)
    fig.savefig(out/'images_and_error.png', dpi=160); plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(12, 10), layout='constrained')
    pairs = [(np.linalg.norm(b['true_disp'], axis=1), np.linalg.norm(d[:, 2:4], axis=1), 'Displacement magnitude (px)'),
             (b['true_strain'][:, 0]*1e6, b['strain'][:, 0]*1e6, 'Axial strain (microstrain)'),
             (invariants(b['true_stress'])[:, 2]/1e6, b['invariants'][:, 2]/1e6, 'Von Mises stress (MPa)')]
    for row, (truth, measured, label) in enumerate(pairs):
        mask = good & np.isfinite(measured)
        vals = np.concatenate((truth[mask], measured[mask]))
        lo, hi = (float(vals.min()), float(vals.max())) if len(vals) else (0, 1)
        for col, (values, title) in enumerate([(truth, 'Analytical'), (measured, 'DIC-derived'), (measured-truth, 'Signed error')]):
            a = axes[row, col]
            kwargs = dict(vmin=lo, vmax=hi, cmap='viridis') if col != 2 else dict(cmap='coolwarm')
            m = a.scatter(b['x'][mask]*1000, b['y'][mask]*1000, c=values[mask], s=25, **kwargs)
            a.set(title=f'{title}: {label}', xlabel='x (mm)', ylabel='y (mm)', aspect='equal')
            fig.colorbar(m, ax=a, shrink=0.7)
    fig.savefig(out/'field_comparison.png', dpi=150); plt.close(fig)


def write_report(b, out):
    import html
    import json
    summary = html.escape(json.dumps(b['summary'], indent=2))
    name = html.escape(b['config']['benchmark'].replace('_', ' ').title())
    meta=b['summary'].get('preprocessing',{})
    sigma=meta.get('kernel_radius_px',0)
    label=('Local Wiener denoising (5 x 5 px)' if meta.get('method')=='wiener' else f"Gaussian denoising (sigma {meta.get('sigma_px',0)} px)")
    preprocessing=(f'{label} was applied to both captured images before DIC. Original captures are preserved. Exact floating-point DIC inputs are in dic_input_images.npz.' if sigma else 'DIC denoising: Off.')
    previews=(''.join(f'<h3>{key.title()} · smoothed DIC input</h3><img src="{key}_smoothed.png" alt="Smoothed {key} DIC input">' for key in ('reference','deformed')) if sigma else '')
    page = f'''<!doctype html><html><head><meta charset="utf-8"><title>{name} — DIC report</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#183344;background:#f7fafc}}img{{width:100%;background:white}}pre{{white-space:pre-wrap;background:#e8eff3;padding:24px;border-radius:12px}}h1{{font-size:34px}}p{{line-height:1.6}}</style></head>
<body><h1>{name}: virtual DIC experiment</h1><p>Known analytical deformation → synthetic camera images → independent image matching → displacement gradients → plane-stress recovery → validation.</p>
<p>Physical coordinates: x right, y up. Image coordinates: columns right, rows down. Displacement errors are in pixels; all exported mechanical quantities use SI units.</p>
<img src="images_and_error.png" alt="Reference, deformed image and displacement errors">
<img src="field_comparison.png" alt="Analytical and recovered fields and errors">
<p>{preprocessing}</p>{previews}
<h2>Measured results</h2><pre>{summary}</pre>
<p>These results include 8-bit quantization and interpolation. Stress is inferred using the specified elastic constants. Invalid measurements are excluded from RMSE and included in coverage/failure counts. The hole benchmark samples an infinite plate; finite subsets cannot recover its edge peak directly. The cantilever benchmark uses Saint-Venant end loading, with local clamp effects excluded.</p>
<p>See config.json for all inputs, dic_displacements.csv for match status, mechanical_fields.csv for recovered fields, and errors.csv for numerical differences.</p></body></html>'''
    (out/'report.html').write_text(page)
