# Verification

From the project directory, run the physics, DIC, denoising, export,
configuration and HTTP workflow tests:

```bash
python -m unittest discover -s tests -v
node tests/analysis_profiles.cjs
```

The HTTP tests start their own test server and exercise flat specimens, paired
bending, analytical circular torsion, session access and exports. Separate image
tests exercise square stereo torsion. CLI tests check the axial summary files
and UTF-8 batch-index export under an ASCII-default locale.

The optional JavaScript checks use Node 24 and the committed development lock.
Run `npm ci --ignore-scripts` to install jsdom and Playwright; these are test-only
dependencies. Start a dedicated local server on 8765:

```bash
python lab_server.py --no-browser
```

Then, in a second terminal in the same project/environment:

```bash
npm run test:ui
```

Do not share this dedicated test server with a public classroom session. You
can set `LAB_RUNS_DIR` before starting it to isolate generated files. The test
checks controls, real API runs, exports, coverage counts/percentages, zero
eligible-point display, and switching between flat/stereo views. Canvas drawing
is stubbed, so it does not verify pixels, fonts or layout in a live browser.

See `REVIEW.md` for the dated verification record. To save your own test log:

```bash
python -m unittest discover -s tests -v > test-results.log 2>&1
```

Generated outputs/logs are not distributed as verification evidence in a clean
checkout. Tests on synthetic images do not establish real-camera accuracy.


## Independent consistency validation

`test_dic_consistency.py` covers known affine deformation/brightness, repeated
texture, reverse source support, forward-only comparisons, invalid thresholds,
and diagnostic exports. The periodic-texture test deliberately demonstrates a
case where a wrong physical correspondence can remain cycle-consistent.

For the deterministic 45-case tolerance sweep:

```bash
python tests/calibrate_dic_consistency.py > consistency-calibration.json
```

## Real Chromium and CI

With the dedicated lab server running:

```bash
npx playwright install chromium
npm run test:browser
```

The smoke script uses actual desktop/mobile Chromium canvases and API runs,
checks coverage, fields, stereo, browser errors and horizontal overflow, and
saves screenshots under `outputs/browser-check/`. It does not establish Safari
or real-camera correctness. Browser binaries must be installed successfully.

`.github/workflows/verify.yml` defines Python 3.12/3.13 tests plus locked Node
profile/controller/Chromium checks. It uses read-only repository permissions;
the browser job uploads screenshots/logs as a review artifact. A committed
workflow is not evidence of a successful CI run: inspect the PR's checks.


## UI presentation regression checks

`npm test` also checks display-only reverse explanations and exact-zero labels.
`test_presentation_payload.py` verifies that adding a progress observer leaves
images, displacement, strain, stress and summaries exactly unchanged, and that
the API exposes existing reverse diagnostics without modifying measurements.
The UI/browser workflows check the compact coverage details, verification strip,
subset return information, build label, mobile jump links and shorter stereo
field canvases. Progress is reported by stage; the solver is not instrumented
with estimated per-point completion.


## Results-dashboard presentation checks

`npm test` includes `results_dashboard.cjs`. Its cantilever fixture verifies
display-only MPa/microstrain conversion, individual sample counts, rejection
denominators, mode-specific metrics, missing values, copying and unchanged
source JSON. The fixture is not a new mechanics benchmark. The UI/controller
and real Chromium checks also exercise the dashboard, expandable component
errors, collapsed technical JSON and actual clipboard copying. No solver or
validation thresholds are changed.

## Stereo-preview delivery checks

`npm test` includes `stereo_previews.cjs`, which uses controlled image events
and a virtual clock to check the two-request limit, lazy mode selection,
successful-image reuse, bounded retries, timeout recovery, manual retry,
mode changes, decode failures and stale callbacks from a previous run.

The Chromium script deliberately returns HTTP 502 for both smoothed After
previews. It verifies automatic recovery for one, a persistent per-panel error
and manual recovery for the other, and actual image pixels in all four panels
in both preview modes. It also checks that summary values remain unchanged.
Screenshots include the failure state and the recovered desktop/mobile views.
These tests simulate gateway failures; they do not diagnose the public tunnel.
