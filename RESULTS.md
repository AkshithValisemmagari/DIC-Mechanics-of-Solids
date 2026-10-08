**Verified project results**

These values come from the included executed configurations. They are measured results, not illustrative numbers.

| Benchmark | Displacement vector RMSE (px) | Strain component-vector RMSE | Stress component-vector RMSE (MPa) | Valid displacement subsets |
|---|---:|---:|---:|---:|
| axial_bar | 0.012747 | 0.00033298 | 26.310 | 308/308 |
| cantilever | 0.015652 | 0.000730966 | 24.246 | 312/312 |
| plate_with_hole | 0.013404 | 0.00026703 | 15.285 | 284/324 |

The hole excludes subsets crossing the hole boundary. Refer to summary.json for eligible-reference failure rates and the separate number of valid strain/stress estimates. Strain/stress component-vector RMSE is a numerical combined-component score, not a tensor-invariant norm.

**Plate with hole**

- Analytical edge concentration factor: 3.0.
- Analytical maximum sigma_xx/S on valid stress centres: 1.5713.
- DIC-derived maximum sigma_xx/S on those centres: 1.4823.

The interior grid does not reach the edge. These are different sampling locations, so the interior ratio must not be presented as a recovered edge Kt.

**Robustness study**

| Noise standard deviation (0–1 intensity) | Mean displacement RMSE (px) | Sample standard deviation (px) |
|---:|---:|---:|
| 0.00 | 0.012895 | 0.000000 |
| 0.01 | 0.012686 | 0.000810 |
| 0.03 | 0.014969 | 0.001541 |
| 0.06 | 0.035442 | 0.004519 |

All five factors, all 48 trials, failure rates and strain/stress errors are available in outputs/robustness/. At zero noise, repeated seeds generate identical results. Other factors use background noise=0.01; error bars quantify noise-seed variability for the configured speckle realization.

**Verification**

The original benchmark run passed 14 tests; the interactive release extends this to 22 passing Python tests (see REVIEW.md and outputs/test_results.txt). They cover independent mechanics identities, known subpixel image shifts, brightness changes, masking/inverse mapping, independent camera noise, flat-image rejection, physical-to-pixel coordinate signs, and input checks.

**Interpretation**

Displacement is recovered at subpixel accuracy, while displacement differentiation produces larger relative strain/stress errors. The baseline axial strain is 0.004; its strain RMSE should be judged against that scale. This measurable difference is part of the project result. Pixel quantization, interpolation bias and finite fitting windows remain even without camera noise. See METHODS.md for the assumptions and error definitions.
