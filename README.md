**DIC Studio — interactive Virtual Solid Mechanics Lab**

A reproducible Python project that creates analytical deformation fields,
turns them into synthetic speckle-image experiments, independently measures
motion with subpixel Digital Image Correlation (DIC), recovers strain and
stress, and quantifies errors and imaging robustness.

The mechanics-to-measurement workflow is implemented, with a local interactive interface.
Choose one object, material, geometry and load, then run that experiment.
The five interactive specimens are axial bar, cantilever, plate with a hole,
pure bending, and square-section torsion with synthetic stereo DIC.
Measurement-line comparisons and paired noise experiments are available for
flat specimens. Analytical circular-shaft torsion remains a backend module for
compatibility; it is not a selectable specimen in the current interface.
The batch commands generate benchmark and robustness reports under `outputs/`.

**Project report**

The project report describes the mechanics models, synthetic image generation,
flat and stereo DIC workflows, validation, results, and limitations. [Read the
report](reports/DIC_MOS.pdf).

**Start here**

1. Extract the ZIP and open the project folder in VS Code.
2. Install the dependencies using the commands below (once).
3. Run `python main.py`. Your browser opens the local virtual lab.
4. Select the object, material, dimensions and force, bending moment or torque. Click **Run experiment**.
5. Explore **Deformation**, **Images & DIC**, **Field comparison**, **Noise comparison**, and **Method & results**. Square torsion has a dedicated **Stereo DIC** view instead of the flat-specimen DIC tabs.

Keep the terminal running while using the lab. Press Ctrl+C to stop it.
If the browser does not open automatically, use the localhost address printed
in the terminal. Do not open `web/index.html` directly: its controls need the
Python calculation server. No account, external service or JavaScript package
installation is required. By default the lab listens on your own computer; see `HOSTING.md` for hosting settings.

Changing inputs marks existing results as stale. The charts continue to display
the last completed run until you rerun. Controls are disabled during a calculation.
Camera noise and blur default to zero and are applied only at the chosen levels.
Each run has a separate output folder and a **Download this run** ZIP export.

**Install**

Use Python 3.10 or newer. Create a virtual environment and install the runtime
dependencies from the project folder.

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Select `.venv\Scripts\python.exe` as the VS Code interpreter. If you prefer to
activate the environment in PowerShell, run `.venv\Scripts\Activate.ps1` first
and then use `python -m pip install -r requirements.txt`.

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Select `.venv/bin/python` as the VS Code interpreter. NumPy, SciPy, Matplotlib
and Pillow are the only runtime dependencies. SciPy implements image
interpolation and optimization; OpenCV is not required. No internet is needed
after installation.

**Run the project**

```bash
# Open the interactive lab (default):
python main.py

# All three batch benchmarks, without opening the lab:
python run_project.py

# Complete project, including the 48 repeated robustness trials:
python run_project.py --robustness

# A single benchmark:
python run_project.py --benchmark plate_with_hole

# Only the robustness study:
python run_project.py --robustness-only

# Your own configuration and a separate output directory:
python run_project.py --config configs/cantilever.json --output-dir outputs/my_trial

# Original introductory 1D axial-bar calculation:
python run_axial_1d.py

# Verification tests:
python -m unittest discover -s tests -v
```

Runtime depends on the machine and settings. Redirect console output to a log
if you want to retain timings; generated outputs and logs are not tracked by Git. Existing results in the selected output folders are
replaced. Use `--output-dir` to retain another experiment. The report index links
to existing results, which may be from different runs; each folder saves its own
configuration. Images are saved to disk; no interactive plotting window opens.

**Files and folders**

| Entry point | Responsibility |
|---|---|
| `main.py`, `lab_server.py`, `web/` | Interactive browser lab and local API |
| `run_project.py`, `pipeline.py` | Batch experiments and flat-DIC workflow |
| `mechanics.py`, `speckle.py`, `dic.py`, `strain.py`, `stress.py`, `validation.py` | Core mechanics-to-measurement computation |
| `square_torsion.py`, `stereo_camera.py`, `stereo_dic.py`, `stereo_experiment.py` | Synthetic stereo torsion workflow |
| `configs/`, `experiments/`, `tests/` | Experiment inputs, robustness study and verification suite |
| `outputs/` | Generated, locally retained experiment results; ignored by Git |

**Reproducible development environment (optional)**

Normal lab use still needs only `requirements.txt`. For the Python 3.12 reference
versions used in verification, install the full hash-checked dependency lock:

```bash
python -m pip install --require-hashes -r requirements-lock.txt
```

`requirements-reference.in` records the direct reference pins. The generated
lock includes transitive dependencies and platform artifact hashes. To refresh
it deliberately with uv, use the compile command in its header, then rerun tests.
The reference lock targets Python 3.12+; it is separate from the broader normal
runtime requirements. CI exercises Linux Python 3.12/3.13; other environments
still need verification.

Optional JavaScript tests use Node 24 and `npm ci` with the committed package
lock. `npm test` runs profiles; `npm run test:ui` needs a dedicated local lab
server. `npm run test:browser` additionally needs Playwright Chromium installed.
No Node packages or browser automation are needed to run the lab normally.

**Configuration files**

- `axial_bar.json`: original 1D example (used by `run_axial_1d.py`).
- `axial_bar_dic.json`: 2D uniaxial plane-stress experiment, with Poisson contraction.
- `cantilever.json`: Saint-Venant end-loaded beam experiment.
- `plate_with_hole.json`: cropped observation window in the infinite-plate Kirsch solution.
- `robustness.json`: parameter levels, repeat seeds and study image size.

Mechanics inputs use metres, newtons and pascals. DIC lengths use pixels.
Camera intensity values are normalized to 0–1. Positive physical y points up;
image rows point down. The conversion is handled explicitly in the pipeline.

Adjust the image scale and physical loading together to get measurable motion.
The supplied examples have physically specified deformation, not an undisclosed
visual magnification. Loads are linear-elastic benchmark inputs, not a claim
that any particular real material stays elastic at those stresses.

**Outputs and scientific scope**

Runs save their exact configuration, summary statistics, measurement data and
plots under `outputs/`. That directory is ignored by Git; use a new output
folder to preserve earlier runs. See `RESULTS.md` for the reproducibility
procedure.

The flat workflow uses local small-deformation plane-stress models. Stress is
inferred from recovered strain and the configured elastic law. Square-torsion
stereo uses exact simulated calibration to recover visible-face motion and
surface strain; it is not experimental stereo DIC. The visual magnification
changes the display only. See `METHODS.md` and `SQUARE_TORSION_STEREO.md` for
assumptions and interpretation limits.

**Detailed documentation**

- `METHODS.md`: equations, coordinate conventions and constitutive assumptions.
- `ROADMAP.md`: current implementation map and project scope.
- `RESULTS.md`: historical results and instructions for producing current runs.
- `REVIEW.md`, `CONSISTENCY_VALIDATION.md`: verification records and limitations.
- `RESULTS_DASHBOARD.md`: result definitions and display rules.
- `HOSTING.md`: local hosting, updates and deployment.
- `tests/README.md`: Python, JavaScript, UI and browser test instructions.

**Use another local port**

```bash
python main.py --port 8766
```

Keep the terminal running while using the lab. Reloading restores the latest
completed run while the same server is active; restarting the server starts a
fresh workspace. See `HOSTING.md` for update and deployment instructions.
