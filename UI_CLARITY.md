# UI clarity update — 2026-11-04

This update changes presentation and exposes existing diagnostics. It does not
change the mechanics, image generation, matching rules, correlation/cycle
thresholds, denoising, strain/stress recovery or acceptance decisions.

## Visible changes

- A selected flat-DIC subset shows its existing return error, allowed tolerance,
  reverse correlation and specific reverse rejection reason. Missing/disabled
  checks are distinguished from a failed check. Near-threshold values retain
  additional digits so rounded values do not obscure the decision.
- Status 5 reads “No supported target match”, covering both integer-window and
  post-fit support failures without claiming a new rejection category.
- A compact strip shows the existing reverse-verification setting and failure
  counts. Stereo shows its existing cycle/epipolar/reprojection limits.
- The matched-point card shows accepted / eligible locations and their
  percentage. Mask exclusions and all-grid acceptance move into an expandable
  explanation. This preserves the existing denominators and RMSE definitions.
- Supporting text is larger and darker. Stereo field panel heights adapt to the
  observed face aspect ratio without stretching the physical coordinates.
  Analytical twist and cross-section cards share the desktop row.
- Mobile jump links connect setup and results. Settings are not automatically
  collapsed, and the previous-result/stale-input behavior is preserved.
- Exact-zero error maps display “Error: 0” rather than artificial tiny legend
  endpoints. Tiny nonzero errors remain nonzero; no numerical rounding/filter
  is introduced into measurements, validation or exports.
- The footer displays the server interface version and startup revision. The
  revision comes from LAB_BUILD_ID, RENDER_GIT_COMMIT, or a read-only Git query;
  source archives are identified explicitly. Restart the server after pulling
  and refresh the browser to see the new interface.

## Progress reporting and API

The orchestration pipeline accepts an optional progress observer. It only
reports actual stage transitions: image generation, matching preparation,
matching/reverse verification, recovery/validation and export. No solver code
is instrumented or changed, and no estimated per-point percentages are shown.
Paired baseline progress is identified separately.

The session-protected result API now includes the existing consistency data
that was already written to dic_consistency.csv. NaN diagnostics become null
for display; original bundle measurements and CSV values are unchanged. The
settings API additionally reports the startup build. New fields are additive.

## Validation

- The presentation regression compares runs with/without the progress observer:
  images, displacement, strain, stress, invariants and summaries are identical.
- The payload regression checks diagnostic alignment, JSON-safe missing values
  and preservation of the original measurement array.
- JavaScript tests cover reason text, unavailable/disabled checks, near-limit
  precision and exact-zero handling, including tiny nonzero values.
- UI/browser checks cover the collapsed coverage explanation, quality strip,
  subset information, zero-error legend, build label, mobile navigation and
  adaptive stereo canvas heights.

See REVIEW.md and the PR's CI checks for executed test results. Screenshot
artifacts come from a dedicated CI server, not verification that a particular
public tunnel or Mac-hosted deployment is currently reachable.
