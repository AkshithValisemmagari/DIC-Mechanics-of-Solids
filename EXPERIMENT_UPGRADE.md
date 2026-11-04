# Historical upgrade notes

This document records an earlier partial-ZIP release, including its old circular
torsion selector and zrok/LaunchAgent instructions. It is retained as history,
not current setup guidance. Use `README.md` and `HOSTING.md` for the current
project, and `REVIEW.md` for the latest verification record.

# Experiment upgrade

This update adds measurement-line ground-truth comparisons, paired noise tests,
pure bending, and analytical solid circular-shaft torsion to the existing lab.
It uses the existing Python requirements and your existing hosting setup.

## Apply the downloaded update on your Mac

1. Duplicate your current `virtual-solid-mechanics-lab` folder as a backup.
2. Extract `experiment-upgrade.zip`. Open its `updated-files` folder.
3. Copy its contents **into your existing project folder**, replacing files with
   the same names. Merge the `web` and `tests` folders. Keep the project at the
   same path used by your LaunchAgent. This archive is an update, not a standalone
   project; keep the other project files.

   To merge from Terminal instead of Finder, open Terminal in your existing
   project folder (the one containing `main.py`), then run:

   ```bash
   cp -R "$HOME/Downloads/experiment-upgrade/updated-files/." .
   ```

   Adjust the source path if you extracted the ZIP somewhere else. Copy the whole
   update, including `torsion.py`, `noise_comparison.py`, `web/analysis.js` and
   `web/experiments.js`; replacing only `lab_server.py` is insufficient.

4. Once copying has finished, restart the already configured lab service:

   ```bash
   launchctl kickstart -k "gui/$(id -u)/com.fieldlab.server"
   ```

   If you are running manually instead, stop the old server with Ctrl+C and run
   `python main.py` from the project folder. Use your existing Python environment.

5. Open https://dic-mos.shares.zrok.io and press **Cmd+Shift+R** to reload the new
   JavaScript and styles. The zrok name and tunnel setup do not need changing.
   Restarting clears the server's current in-memory experiment session; run a new
   experiment after updating.

## Try the additions

- **Pure bending:** choose Pure bending, Aluminium, 120 mm length, 30 mm height,
  6 mm thickness and 60 N·m. Run. In Deformation, select **Signed axial stress σxx**
  to see red tension, blue compression and the neutral axis. Reverse the moment
  sign to reverse bending. The end moment arrows point in opposite directions.
- **Ground truth:** open Field comparison, select axial stress, and select a
  vertical measurement line. The graph compares analytical and recovered stress
  through the height. Horizontal lines show variation along the specimen. Error
  statistics and Download line CSV apply to that selected line.
- **Noise:** select Gaussian noise 0.025, enable **Compare with no added noise**
  and rerun. Noise comparison displays baseline and noisy images, recovered fields,
  common-centre errors and coverage. The line graph adds the baseline curve.
  Download this run includes both complete calculations and comparison CSV/JSON.
  Two DIC solves take more time than one. Noise remains optional and off by default.
- **Torsion:** select Torsion, Aluminium, length 200 mm, radius 10 mm and torque
  20 N·m. Run, rotate the 3D view and adjust magnification to see twisting. Open
  Shaft analysis for twist and radial stress curves plus a coloured cross-section.
  Torque can be negative or zero. Torsion is analytical only: no DIC/noise controls
  or recovered-field errors appear. Its download contains analytical curves/report.

The original bar, cantilever and hole experiments remain available. Magnification
changes the displayed deformation only. Stress colours use analytical stress at
actual load; errors in Field comparison refer to independent DIC estimates.
A red shaft surface is expected: all outer points have the same radius and shear
magnitude, while stress decreases to zero at its centre.

## Validation performed

- 37 Python tests passed: existing mechanics/DIC pipeline, hosting/session isolation,
  stress colours, new bending kinematics and force/moment resultants, torsion torque
  equilibrium and twist, input bounds, paired common-centre metrics and real HTTP
  exports (including private nested baseline files).
- JavaScript profile tests passed for rejection gaps, hole crossings, common valid
  centres, zero errors and CSV output.
- DOM controller tests passed for original cases, paired pure bending, measurement
  lines, analytical torsion and switching back to DIC. Canvas was stubbed for this
  controller test; it is not a Safari/Chrome visual test.
- Actual canvas images of signed bending stress, twisted shaft stress and a measured
  stress profile were rendered and inspected separately.

Commands for Python and profile checks from the project root:

```bash
python -m unittest discover -s tests -v
node tests/analysis_profiles.cjs
```

The optional `tests/ui_controller.cjs` requires Node with `jsdom` available and a
running server on port 8765. No Node dependency is needed to use the lab itself.
Details and assumptions are documented in `METHODS.md`.
