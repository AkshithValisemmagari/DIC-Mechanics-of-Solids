**DIC Studio — current implementation map**

This map describes the current repository rather than the original seven-phase
development plan. The batch runner retains three preset flat benchmarks; the
interactive lab also supports pure bending and square-section stereo torsion.

| Capability | Implemented in | Scope |
|---|---|---|
| Flat analytical mechanics | `mechanics.py`, `configs/` | Axial bar, cantilever, plate with a hole and pure bending |
| Square-section torsion mechanics | `square_torsion.py` | Analytical square-shaft displacement, strain and stress fields |
| Synthetic flat images and camera effects | `speckle.py`, `image_preprocessing.py` | Seeded texture, deformation warping, blur/noise and optional DIC denoising |
| Flat DIC | `dic.py`, `dic_support.py` | Mask-aware subset matching, local affine subpixel refinement and optional forward/backward checks |
| Synthetic stereo imaging and reconstruction | `stereo_camera.py`, `stereo_dic.py`, `stereo_experiment.py` | Four calibrated simulated views, image-based 3D reconstruction and visible-face strain |
| Strain, stress and validation | `strain.py`, `stress.py`, `validation.py` | Displacement-derived strain, plane-stress inference and comparison with analytical truth |
| Noise and robustness studies | `noise_comparison.py`, `experiments/robustness.py`, `configs/robustness.json` | Paired noise comparisons and a configured 48-trial one-factor-at-a-time study |
| Interactive and batch workflows | `web/`, `lab_config.py`, `lab_server.py`, `pipeline.py`, `run_project.py` | Local browser lab, validated inputs, flat pipeline and three-preset batch runner |

`pipeline.py` connects these components. `run_project.py` runs the complete
project; `visualization.py` produces the reports and figures in `outputs/`.
The original `run_axial_1d.py` remains available as the simple first-step example.

The hole study reports the exact edge concentration separately from measured
interior maxima. The cantilever uses a consistent Saint-Venant elasticity
benchmark, with local clamp effects excluded. See `METHODS.md` before presenting
these results as a physical experiment.

The flat workflow remains a small-deformation, plane-stress virtual laboratory;
it is not a general FEM solver. Stereo torsion uses exact simulated camera
calibration and measures the visible front face; it is not experimental stereo
DIC. Real-camera calibration, general FEM, large-deformation mechanics and
machine learning are outside the implemented scope. Generated outputs are
written under `outputs/` and are not tracked in a clean checkout.
