**DIC Studio — interactive Virtual Solid Mechanics Lab**

A reproducible Python project that creates analytical deformation fields,
turns them into synthetic speckle-image experiments, independently measures
motion with subpixel Digital Image Correlation (DIC), recovers strain and
stress, and quantifies errors and imaging robustness.

All seven calculation phases are implemented, with a local interactive interface.
Choose one object, material, geometry and load, then run that experiment.
The five interactive specimens are axial bar, cantilever, plate with a hole,
pure bending, and square-section torsion with synthetic stereo DIC.
Measurement-line comparisons and paired noise experiments are available for
flat specimens. Analytical circular-shaft torsion remains a backend module for
compatibility; it is not a selectable specimen in the current interface.
The archive also includes batch benchmark and robustness reports.

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

**Install on your Mac**

Use Python 3.10 or newer. In the terminal inside the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Select `.venv/bin/python` as the VS Code interpreter. NumPy, SciPy, Matplotlib
and Pillow are the only dependencies. SciPy implements image interpolation and
optimization; OpenCV is not required. No internet is needed after installation.

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

| Path | Responsibility |
|---|---|
| `main.py` | Open the interactive lab; legacy batch flags still work |
| `lab_server.py` | Local server, background experiment jobs and exports |
| `lab_config.py` | Material presets, input checks and force-to-stress conversion |
| `web/` | Browser interface, animated canvas and interactive field maps |
| `run_project.py` | Command-line batch experiments |
| `pipeline.py` | Connect all phases and save reproducible experiment outputs |
| `mechanics.py` | Axial bar, cantilever, pure bending and Kirsch hole analytical fields |
| `torsion.py` | Analytical solid circular-shaft torsion and exports |
| `square_torsion.py`, `stereo_camera.py`, `stereo_dic.py`, `stereo_experiment.py` | Square-shaft mechanics, synthetic stereo imaging, image-only reconstruction and surface strain |
| `noise_comparison.py` | Paired errors at common valid measurement centres |
| `speckle.py` | Seeded speckles, physical calibration, inverse image warp and camera degradation |
| `dic.py`, `dic_support.py` | Mask-aware affine matching and independent forward/backward verification |
| `strain.py` | Local quadratic fits to the measured displacement field |
| `stress.py` | Plane-stress elasticity, in-plane principal stresses and von Mises stress |
| `validation.py` | Displacement/strain/stress errors, match failures and coverage |
| `visualization.py` | Plots and browser-readable experiment reports |
| `experiments/robustness.py` | Repeated, one-factor-at-a-time robustness studies |
| `configs/` | All geometry, material, imaging, solver and study inputs |
| `tests/` | Physics, image-processing, recovery and invalid-input checks |
| `outputs/` | Generated images, raw measurements, ground truth, errors and reports |
| `run_axial_1d.py` | Preserved simple Phase 1 example for learning the first component |
| `METHODS.md` | Equations, coordinate conventions, limitations and references |
| `ROADMAP.md` | Map of all seven implemented phases |
| `RESULTS.md` | Historical numerical results and their interpretation limits |

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

**What each benchmark writes**

| File | Contents |
|---|---|
| `report.html` | Visual report with measured statistics |
| `reference.png`, `deformed.png` | Original 8-bit camera captures, preserved when denoising is enabled |
| `reference_smoothed.png`, `deformed_smoothed.png` | 16-bit display previews when DIC denoising is enabled |
| `dic_input_images.npz` | Exact floating-point filtered DIC inputs, saved when denoising is enabled |
| `reference_mask.png`, `deformed_mask.png` | Geometric/valid interpolation support masks |
| `config.json` | Exact settings for the run |
| `ground_truth.npz` | Dense physical coordinates, analytical displacement, pixel sizes and reference mask |
| `dic_displacements.csv` | Candidate centres, forward motion, affine gradients, ZNCC and final match status |
| `dic_consistency.csv` | Per-candidate reverse outcome, reverse ZNCC and round-trip error (flat DIC) |
| `mechanical_fields.csv` | Recovered and analytical strains/stresses; principal and von Mises results |
| `errors.csv` | Signed differences at matching reference positions |
| `summary.json` | RMSE, maximum errors, valid counts, failure rate and hole concentration comparison |
| `images_and_error.png` | Image pair and displacement-error map |
| `field_comparison.png` | Analytical, recovered and error maps |

Invalid strain/stress entries are NaN in CSV files. Only valid measurements enter
RMSE. The top card shows matched / eligible reference locations and their
percentage. Expand “How match coverage is calculated” for mask exclusions
and acceptance across all grid candidates. Eligible
reference subsets fit fully inside the processed reference mask. These counts
describe displacement; strain/stress fitting may retain fewer points. Stereo
candidates already require full raw reference support, and additional points
may fail after filtering or matching. Status codes and masks explain omitted measurements. `dic_displacements.csv`
retains rejected optimizer estimates for diagnostics; use `valid == 1` when
analyzing them. No zero-displacement percentage errors are used.

**Flat-DIC consistency checks**

Forward matches now undergo an independent reverse match from the measured
location in the deformed image back into the reference image. The default
maximum return error is **0.3 px**, using the same filtered images and mask
margins. Status 7 means the reverse match failed; status 8 means it returned to
a different reference location. All earlier checks still apply. Failed forward
estimates remain in the diagnostic CSV but are excluded from recovered fields.

`summary.json` records the effective threshold and rejection counts;
`dic_consistency.csv` records every reverse outcome. A batch configuration can
set `dic.fb_tolerance_px` to `null` for a controlled forward-only comparison.
The current website enables 0.3 px. A compact verification strip shows the
existing tolerance and rejection counts; selecting a flat subset shows its
existing return error, reverse correlation and rejection reason. These are
presentation additions, not new acceptance rules. The server build is shown
in the footer, and mobile jump links connect setup and results. Progress
messages report actual calculation stages, not estimated point counts.
Reverse checking adds a second fit for
forward-accepted points and can increase runtime or reduce coverage. It cannot
guarantee uniqueness for repeated texture. See `CONSISTENCY_VALIDATION.md` for
measured checks and their limits. Stereo retains its existing cycle checks.

**Robustness study**

The default runs 16 parameter settings × 3 independent noise seeds = 48 trials.
It varies noise strength, Gaussian blur width, deformed-image brightness gain,
subset size and speckle radius. The speckle realization is held fixed within
each size setting; camera noise changes between repeats. Other studies have a
small background noise level of 0.01 to avoid identical repeats. Zero-noise
repeats are deterministic. These repeats quantify noise variability, not
uncertainty over all possible speckle patterns.

Open `outputs/robustness/report.html`. Raw trial and grouped results, settings,
plots and the study's base configuration are saved alongside it.

**Limits you should state when presenting**

The flat-specimen workflow is a local, small-deformation, 2D plane-stress DIC
laboratory, not a general FEM solver. A separate square-torsion workflow
implements synthetic stereo DIC with exact simulated calibration and measures
the visible front face; it is not a general experimental stereo-DIC system. The
project is complete for its stated benchmarks and studies,
but does not guarantee exact recovery. Finite pixels, interpolation, local
shape functions, gradient fitting and noise all introduce measurable error.
The hole-edge concentration factor is analytically 3; the measured interior
maximum is reported separately because a finite subset cannot reach that edge.
The cantilever's analytical field excludes local rigid-clamp effects. Full
assumptions and interpretation are in `METHODS.md`.

**Interactive controls and views**

- Object: axial bar, end-loaded cantilever, plate with a hole, pure bending, or square-beam torsion with stereo DIC.
- Material: illustrative aluminium, steel, copper and titanium properties, or custom E and nu. These are editable elastic-model inputs, not material certification.
- Geometry: length, height/width, thickness and hole radius where applicable; all entered in mm.
- Load: positive force for bar/plate/cantilever, signed end moment for pure bending, or signed torque for torsion. Zero-load runs are supported.
- Camera: Gaussian noise, blur and brightness gain; speckle radius, coverage and seed.
- DIC: subset size, grid spacing, search radius and strain-fit radius.
- Animation: play/pause, load fraction and clearly labelled visual magnification. It shows analytical deformation; DIC results remain the actual full-load measurement.
- Images: before/after view, adjustable overlay, clickable measured subsets and magnified crops. Image row displacement is positive downward.
- Fields: analytical/recovered/error maps at actual valid centres, shared analytical/recovered colour scale, and an error scale centred at zero.
- Results: numerical statistics, assumptions, exact run settings, a report and a downloadable run archive.

The interface rejects inputs outside the local solver's intended range: more
than 2% predicted strain, excessive displacement gradients, motion beyond the
selected search window, invalid geometry, or insufficient strain-fit radius.
These are numerical/model limits, not safety or elastic-yield limits for a real material.
Force is converted with gross area (height × thickness) for bar/plate; the hole
case remains an infinite-plate solution with an equivalent nominal load.

Use a different local port if needed:

```bash
python main.py --port 8766
```

The interactive server must remain running. Reloading the page restores the
latest completed run while the same server is alive; restarting the server
starts a fresh workspace. Saved run folders remain available on disk.
See `REVIEW.md` for the methods review and verification scope.

**3D stress colours**

In Deformation, choose a 3D surface colour: von Mises stress (default), axial or transverse stress magnitude, shear stress magnitude, or Plain specimen. Blue indicates low stress and red high stress; the colour bar is in MPa and remains fixed at the full-load range during playback. The current sampled peak scales with the load fraction. Colours use analytical stress evaluated at display vertices, including the hole boundary, and are constant through thickness under the existing plane-stress model. Surface cells show average vertex magnitudes. Magnification changes geometry only. Red does not indicate failure. Signed stress and DIC comparisons remain in Field comparison.

After an update, pull the complete repository, restart your configured lab server,
and hard-refresh the browser. See `HOSTING.md`. Historical partial-update ZIP
instructions are not the current installation procedure.


**New experiment views**

- **Measurement lines:** in Field comparison, choose a field, horizontal or vertical
  direction, and a measured row/column. The graph overlays analytical values and
  independently recovered DIC values. RMSE, maximum absolute error and point count
  describe that line. Download its CSV. Gaps preserve invalid points and the hole.
- **Paired noise:** set Gaussian noise above zero, enable **Compare with no added
  noise**, then run. Noise comparison displays both camera images, recovered fields
  on a shared colour scale and errors at common valid centres. Field comparison
  adds the baseline curve. Both runs are in the downloaded ZIP. This requires two
  DIC calculations, so expect roughly twice the calculation work. Noise remains
  off by default; baseline still has quantization and any selected blur/brightness.
- **Pure bending:** select the rectangular beam, material, dimensions and end moment
  in N·m. Equal and opposite end moments produce constant bending moment and zero
  shear force. Negative moment reverses bending. Use **Signed axial stress σxx**
  for red tension, blue compression and a nearly white neutral axis. DIC, noise
  comparisons and line profiles work for this case.
- **Square torsion:** select material, square side, shaft length and torque in N·m.
  Both ends rotate about a middle-section reference. Stereo DIC measures 3D
  displacement and surface strain from four synthetic camera images. Interior
  stress and the 3D preview remain analytical. See `SQUARE_TORSION_STEREO.md`.
- **Legacy circular torsion:** `torsion.py` remains available through the backend
  API for compatibility, with analytical curves and no image-based measurement.
  The current specimen selector does not expose this mode.

The visual magnification slider exaggerates deformation (rotation for torsion);
reported numbers and stress colours use the actual load. The batch runner keeps
its three original presets; pure bending and square torsion are selected in the interactive lab.
See `METHODS.md` for equations, `REVIEW.md` for the verification record and
`HOSTING.md` for updates/deployment. `EXPERIMENT_UPGRADE.md` is historical.
