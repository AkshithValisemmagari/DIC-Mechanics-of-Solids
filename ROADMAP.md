**Agreed project — implementation map**

Build → Encounter concept → Understand it → Implement → Validate.

| Phase | Implemented in | Delivered outcome |
|---|---|---|
| 1. Analytical ground truth | `mechanics.py`, `configs/` | Displacement, strain and stress for all three benchmarks |
| 2. Synthetic DIC images | `speckle.py` | Seeded reference/deformed images with checked inverse warping |
| 3. Recover displacement | `dic.py` | Integer ZNCC plus local affine subpixel refinement across a subset grid |
| 4. Validate | `validation.py`, `tests/` | Matching-coordinate errors, coverage, failures and verification tests |
| 5. Mechanical quantities | `strain.py`, `stress.py` | Displacement-derived strain, plane stress, principal and von Mises stress |
| 6. Upgrade the problem | `mechanics.py`, three benchmark configs | Axial bar, cantilever end loading and infinite plate with hole |
| 7. Robustness experiments | `experiments/robustness.py`, `configs/robustness.json` | 48 repeated trials varying five imaging/measurement factors |

`pipeline.py` connects these components. `run_project.py` runs the complete
project; `visualization.py` produces the reports and figures in `outputs/`.
The original `run_axial_1d.py` remains available as the simple first-step example.

The hole study reports the exact edge concentration separately from measured
interior maxima. The cantilever uses a consistent Saint-Venant elasticity
benchmark, with local clamp effects excluded. See `METHODS.md` before presenting
these results as a physical experiment.

All agreed phases have working code and generated results. No placeholder
modules remain. The interactive GUI is implemented in `web/`, `lab_config.py` and
`lab_server.py`. The original flat-specimen scope excludes real camera
calibration, large-deformation mechanics, general FEM, and machine learning. A
later square-torsion extension implements synthetic stereo DIC with exact
simulated camera calibration and front-face surface strain; it is not
experimental stereo DIC.
