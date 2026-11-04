# Flat-DIC consistency validation — 2026-11-04

Checks below were executed in Linux with the Python 3.12 reference environment.
They support a conservative default; they do not establish a universal optimum.

## Deterministic tolerance sweep

45 cases: texture seeds 4/8/17, camera noise 0/0.02/0.06/0.10/0.15, and DIC denoising
Off/Gaussian 0.7/Gaussian 1.0. Images are 100 × 120 px, subsets 21 px, step
20 px, search radius 5 px, and imposed translation (2.37, -1.35) px.
The same forward solutions are compared with reverse verification enabled
and disabled; forward fitted values remain exactly unchanged.

| Camera noise std | Forward accepted | Accepted after reverse checks | Largest per-case cycle P95 (px) | Largest accepted displacement RMSE (px) |
|---:|---:|---:|---:|---:|
| 0 | 165 | 165 | 0.0583 | 0.0276 |
| 0.02 | 165 | 165 | 0.0578 | 0.0268 |
| 0.06 | 165 | 164 | 0.0808 | 0.0462 |
| 0.1 | 165 | 156 | 0.2306 | 0.0741 |
| 0.15 | 165 | 141 | 0.3930 | 0.1057 |

P95 uses reverse matches with a finite return error; reverse failures are
not silently assigned zero error. Counts include those failures. The 0.3 px
default exceeds the observed per-case P95 values through noise 0.06, while
rejecting the many-pixel false return in the duplicate-texture test. At noise
0.10/0.15, some valid-looking forward matches fail reverse quality or cycle
checks; lower accepted counts must be considered alongside RMSE.
This limited sweep is not a proof that 0.3 px is optimal.

Reproduce detailed results (including counts at 0.1/0.3/0.5 px):

```bash
python tests/calibrate_dic_consistency.py > consistency-calibration.json
```

## Representative mechanics runs

Noise 0.03, Gaussian denoising 1.0 px, subset 25, step 24, fit radius 55 px,
search radius 12 px and default texture seed 2039. Use `build_config` defaults,
with cantilever force 1000 N and plate length/height 80 mm; other loads and
dimensions are the current UI defaults. Each comparison changes only
`config["dic"]["fb_tolerance_px"]` between null and 0.3.

| Specimen | Accepted before → after | Displacement RMSE before → after (px) | Runtime before → after (s) |
|---|---:|---:|---:|
| axial_bar | 70 → 70 | 0.016517 → 0.016517 | 0.833 → 1.408 |
| cantilever | 70 → 70 | 0.016648 → 0.016648 | 0.876 → 1.417 |
| plate_with_hole | 172 → 171 | 0.018326 → 0.018366 | 2.287 → 3.777 |
| pure_bending | 70 → 70 | 0.017119 → 0.017119 | 0.770 → 1.423 |

These are single-run timings in this environment, not Mac performance promises.
The hole run loses one point on reverse support/quality and its accepted-point
RMSE rises slightly. This is expected evidence that consistency checks do not
guarantee smaller RMSE or greater coverage. Reverse checking adds fitting work.

## Targeted failure and limitation tests

- Known affine translation, rotation/shear, compression and brightness change
  retain high coverage with subpixel displacement accuracy.
- A noisy duplicate source patch correlates strongly with a shared target patch,
  but reverse matching selects the other source copy: status 8 rejects it.
- Reverse source support is checked explicitly; empty/invalid support is not
  accepted simply because correlation is high.
- A whole period of repeated texture outside the configured search produces
  an image identical to zero motion. Both directions can agree and still miss
  that physical motion. A cycle check is a consistency test, not uniqueness proof.

No correlation-peak uniqueness threshold is enabled in this change. That needs
separate experiments and calibration; adding one does not solve every periodic
ambiguity. Stereo keeps its existing independent cycle checks.

## Verification boundary

The full unit suite and simulated UI checks are recorded in `REVIEW.md`. A real
Chromium smoke test and CI workflow are provided, but the local browser download
failed with a truncated/invalid ZIP. No live-browser pass is claimed here.
Inspect the PR workflow results and its browser screenshots before considering
the browser verification complete. Safari and physical camera data remain untested.
