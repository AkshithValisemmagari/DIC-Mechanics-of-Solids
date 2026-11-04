# Methods review and verification record

## Current verification — 2026-11-04

This record applies to the export/coverage follow-up based on main commit
`5e7b016` (after the mask-aware DIC search update). Tests were executed against
the checkout containing these follow-up changes, not merely inspected.

- The complete Python suite passed **59 tests**.
- JavaScript syntax checks and measurement-profile tests passed.
- The simulated-DOM UI workflow passed real API runs, exports, flat/stereo
  switching, coverage counts/percentages and the zero-eligible-point display.
- Two CLI regressions check the restored axial `summary.txt` export and UTF-8
  batch index generation under an ASCII-default locale.
- The existing six target-support regressions cover supported search
  alternatives, empty target support, post-refinement rejection and filter
  margins. Mechanics, flat DIC, denoising, stereo reconstruction and HTTP
  workflow checks remain part of the complete suite.

Execution environment: Linux, Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0,
Matplotlib 3.10.8 and Pillow 12.3.0. Optional JavaScript checks used Node.js
24.22.1 and jsdom 30.1.2. These are recorded test versions, not a dependency
lockfile or evidence of testing every supported environment.

Reproduce from the project folder:

```bash
python -m unittest discover -s tests -v
node tests/analysis_profiles.cjs
```

For the optional UI workflow, install jsdom in the development environment,
start a dedicated `python lab_server.py --no-browser` server on port 8765,
then run `node tests/ui_controller.cjs`. See `tests/README.md` for isolation
and log-saving guidance. Full generated run folders/logs are not tracked.

## What the checks establish

Independent tests cover displacement derivatives versus stress formulas,
physical/pixel coordinate signs, beam resultants, Kirsch hole traction and edge
concentration, known subpixel motion, square-torsion torque/warping,
triangulation, rigid-motion strain invariance and HTTP exports. DIC receives
images, support masks and correlation settings; stereo also receives camera
calibration. Ground truth is used for image generation and later validation,
not supplied as a matching displacement or seed.

Flat stress is inferred from measured strain using isotropic linear-elastic
plane stress. The 3D preview and stress colours use analytical fields, not
recovered interior stress. Square stereo DIC measures the visible face's 3D
displacement and surface strain; bulk stress remains analytical.

## Interpreting results

Displacement RMSE uses accepted, finite truth/measurement pairs. Coverage must
be read alongside it. Flat eligible-reference coverage excludes candidates
whose reference subsets cross the processed mask; all-candidate acceptance
retains those grid candidates in its denominator. Zero eligible subsets give
undefined eligible coverage, displayed as N/A. Strain/stress fits can retain
fewer points than displacement matching. Stereo candidates have full raw
reference-subset support; filtering and subsequent checks can reject more.

The cantilever excludes local rigid-clamp effects. The hole model is an
infinite-plate Kirsch field; sampled interior maxima are not measurements of
the theoretical hole-edge peak. Magnification changes only visualization.
Camera noise/blur and DIC denoising are separate selected operations.

## Limits and historical records

Canvas drawing is stubbed in the UI controller. Pixel appearance, fonts,
responsive layout and live Safari/Chrome rendering were not verified in this
follow-up. Public tunnel reachability, Render deployment and automatic Mac
service recovery were not exercised. Synthetic tests with exact stereo
calibration do not establish real-camera accuracy.

Older 14/22/37/46-test claims describe earlier releases and do not identify the
current suite. Numerical tables in `RESULTS.md`, the partial-ZIP migration in
`EXPERIMENT_UPGRADE.md`, and the earlier validation section in
`SQUARE_TORSION_STEREO.md` are explicitly historical. Their old generated
logs are not included in a clean checkout.
