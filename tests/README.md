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

The optional UI controller requires Node.js and `jsdom` in your development
environment (test-only dependencies). Start a dedicated local server on 8765:

```bash
python lab_server.py --no-browser
```

Then, in a second terminal in the same project/environment:

```bash
node tests/ui_controller.cjs
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
