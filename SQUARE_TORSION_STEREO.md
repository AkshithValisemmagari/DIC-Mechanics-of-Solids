# Square torsion with stereo DIC

This update changes the torsion experiment. Axial bar, cantilever, plate with a hole, pure bending, their DIC solver, and paired noise comparison remain unchanged. Existing circular-torsion backend functions remain available for compatibility; the interactive torsion selector now uses a square beam.

## Use the experiment

1. Select **Square torsion**. Its initial geometry is 160 mm long with a 20 mm square side and 100 N·m torque. Choose a material and adjust the torque; negative torque reverses the twist.
2. Click **Run experiment**. Noise is added only at the selected camera-noise setting. Zero noise still includes interpolation and 8-bit quantization.
3. **Deformation** shows square-section twisting, axial warping, and analytical stress colours. Drag to orbit. Magnification and playback affect this view only.
4. **Stereo DIC** shows left/right images before/after loading, three displacement components, displacement magnitude, surface strains, ground-truth/error maps, a selectable measurement-row profile, analytical twist and cross-section stress, and acceptance diagnostics.
5. **Method & results → Download this run** exports images, masks, calibration, settings, summary, measured correspondences, field CSVs, interactive results, and an HTML report.

Dots are actual candidate locations. Green image dots passed the stereo checks; rejected reference dots are grey. Field maps compare only common valid truth/measured samples, with unavailable estimates marked grey. Displacement and strain have separate valid counts. No unmeasured values are filled in.

The reference images are very similar because the ideal stereo cameras are rectified and their crops align at the initially flat observed face. Depth changes produce disparity after deformation. This alignment is camera calibration, not an analytical displacement supplied to matching.

## Mechanics

The square side is b, half-side a=b/2. The shear modulus is G=E/[2(1+nu)].

The torsion constant is

    J = b^4/3 * [1 - 192/pi^5 * sum(tanh(n*pi/2)/n^5)], n=1,3,5,...

Thus J ≈ 0.140577 b^4, not the polar second moment of a circle or square. The twist rate is alpha=T/(GJ). An 80-term Fourier solution for the Prandtl stress function gives the two shear stresses and a compatible axial warping function. Exact boundary coordinates use the known zero lateral traction to remove the small truncated-series corner tail.

Camera positions use finite section rotations:

    X' = X + alpha*w(Y,Z)
    theta = alpha*(X - L/2)
    Y' = Y*cos(theta) - Z*sin(theta)
    Z' = Y*sin(theta) + Z*cos(theta)

The stress field remains the small-strain Saint-Venant elastic solution. Camera geometry and surface-strain truth use the finite-rotation mapping above. Its higher-order strains are not claimed to be a fully nonlinear elasticity solution.

Ends apply torque resultants with free warping. The middle cross-section has zero rotation; the ends rotate by -alpha*L/2 and +alpha*L/2. This is a rotational datum, not a physical clamp. Axial warping remains free, including at the middle. Local end/clamp stresses, yielding, instability and material failure are excluded. Input limits keep total end-to-end twist within 0.15 radians and maximum analytical shear strain within 2%.

## Images and measurement

Two ideal calibrated pinhole cameras observe the front face. Each camera pixel is inverse-projected onto that face using Newton iterations; cubic interpolation samples the original seeded texture. Unsupported, unconverged and back-facing pixels are masked. Selected blur, brightness and independently sampled noise are applied, followed by 8-bit quantization. Only this face is rendered for measurement; the full solid is shown separately in the 3D view.

The measurement module accepts images, support masks, camera calibration and correlation settings. It receives no torque, elastic constants, displacement field, warping function or analytical stress.

1. Full reference subsets are sampled on an integer-pixel grid centred on the supported face.
2. Integer ZNCC supplies search seeds only from fully supported target windows, using the existing denoising/interpolation mask margins. A search with no supported window is rejected as `target_support`. A six-parameter affine fit with cubic spline image sampling and an analytic intensity Jacobian refines each match; target support is checked again after refinement.
3. Correspondences are checked across cameras and time, including independently matched routes and a reverse temporal match. Rectified camera pairs use a narrow epipolar seed search.
4. Fits must converge, remain inside support and parameter bounds, and pass minimum ZNCC 0.85, cycle error 0.30 px, epipolar residual 0.25 px, and reprojection residual 0.20 px. A local image-motion consistency check flags isolated outliers. These checks detect inconsistency; they do not prove an estimate is exact.
5. Calibrated triangulation reconstructs each material point before and after loading. Their difference gives u, v and w in metres.
6. Weighted local quadratic fits reconstruct the reference and deformed surface tangents. The Green–Lagrange metric change gives surface E_xx, E_yy and engineering shear 2E_xy in local reference tangent axes. Exact rigid rotation therefore gives zero strain. At least nine reliable neighbours and a well-conditioned fit are required.
7. Ground truth is evaluated only after reconstruction at the reference-image anchor locations.

A larger subset or strain-fit radius trades spatial detail for smoothing; it does not guarantee smaller error. Sparse grids may leave no well-conditioned strain fits, especially with large subsets on a slender face. Reduce grid spacing, reduce subset size, or increase fit radius when this occurs. Missing strain remains missing and a warning is shown.

## What is measured, and what is analytical?

Measured: front-face 3D displacement and surface strain.

Analytical: full-solid stress colours, cross-section stress map and twist curve.

One observed surface does not uniquely determine the interior stress tensor. This update does not label analytical stress as DIC-recovered stress. Camera calibration is exact in the simulation; lens distortion, experimental calibration uncertainty, lighting changes from surface orientation, and real occlusion of multiple faces are outside this initial benchmark.

## Validation

The complete Python suite passed 46 tests, including existing mechanics, flat DIC, hosting/session isolation and exports. The nine new tests cover square torsion equilibrium/warping, pinhole projection/triangulation, strain invariance to rigid motion, input rejection, zero load, rigid translation/rotation images, both torque signs, added noise, failed matches, and exports. The middle-reference test additionally verifies equal and opposite end rotation and invariance of total twist, stress and surface strain. The image-based tests use the same middle reference as the animation and validation.

The interface workflow passed object selection, submission, stereo field switching, downloads, and switching back to the existing DIC experiments. That test uses a simulated DOM, not a real browser. Actual canvas drawing was separately rendered and visually inspected using a native canvas implementation.

A representative 800-pixel-wide run (aluminium, 160 mm length, 20 mm side, +100 N·m, subset 25, spacing 16 px, strain radius 36 px, seed 2039, no added noise/blur) recovered 114/114 displacement points and 110 strain estimates. Vector displacement RMSE was approximately 0.00344 mm. Component RMSE was approximately 0.00034, 0.00333 and 0.00080 mm; surface shear RMSE was about 207 microstrain. These are one simulated trial's results, not a guarantee for other settings or real cameras. Small normal-strain components can be dominated by measurement error.

## Files

New modules: `square_torsion.py`, `stereo_camera.py`, `stereo_dic.py`, `stereo_experiment.py`, and `web/stereo.js`.

Integration changes: `lab_config.py`, `lab_server.py`, `web/index.html`, `web/app.js`, `web/experiments.js`, `web/model3d.js`, and torsion-specific CSS.

Tests: `tests/test_stereo_torsion.py` and updated `tests/ui_controller.cjs`.

No new Python dependencies, hosting changes, or changes to `main.py`, `run_project.py`, `mechanics.py`, `dic.py`, `strain.py`, `stress.py`, `pipeline.py` or `speckle.py` are required.
