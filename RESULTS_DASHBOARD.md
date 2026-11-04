# Readable results dashboard

The Method & results tab presents existing statistics as readable counts,
error tables, rejection reasons and a compact settings line. Component errors
are expandable; the original settings/statistics JSON stays under Technical
details. Copy JSON copies that original text, with a clear fallback message
when the browser denies clipboard access.

## Interpretation and units

- Flat displacement errors remain pixel vector errors. Strain component errors
  are displayed in microstrain (× 1,000,000), stress component errors in MPa
  (÷ 1,000,000). These are display conversions, not new calculations of RMSE.
- Combined stress-component error is explicitly distinguished from von Mises
  stress error. Rows retain their own valid-point counts.
- Matching rejections use eligible minus accepted locations. Reference-mask
  exclusions are listed separately and are not counted as matching failures.
- Coverage is not labelled as accuracy. No good/bad rating or percentage error
  is inferred without an appropriate ground-truth scale.
- Values are rounded for readability, with converted full-precision values in
  table-cell titles. Tiny nonzero values use scientific notation. Missing
  metrics are shown as a dash, not zero. Technical JSON retains raw precision.
- Stereo displays its reported 3D vector displacement error and individual
  surface-strain errors. Unreported combined maxima remain unavailable; bulk
  stress is not presented as recovered from DIC.
- Legacy circular torsion displays analytical predictions with no fabricated
  measurement errors or matching statistics.

## Numerical scope and verification

No mechanics, image generation, preprocessing, DIC, strain/stress recovery,
validation or orchestration code changes are required. Server changes only
allow the new JavaScript asset and update the UI build label. Exported measured
statistics and acceptance decisions are unchanged.

`tests/results_dashboard.cjs` uses the supplied cantilever summary as a display
fixture, not as a newly executed mechanics benchmark. It checks 126/147 points,
85.7% coverage, 21 matching rejections, correct MPa/microstrain conversions,
separate component counts, missing/zero values, mode switching, clipboard
success/failure and non-mutation of source JSON. The UI/API and desktop/mobile
Chromium workflows exercise the integrated results tab and copy action.

See the PR checks for executed CI results. Screenshots are produced on a
dedicated test server, not the Mac's public tunnel.
