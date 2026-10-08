**Interactive release — methods review**

**What was checked**

The displacement/strain/stress relationships, image-to-physical coordinate signs,
small-strain plane-stress conversion, beam resultants, Kirsch free-hole traction,
and the separation between analytical image generation and image-only DIC were
reviewed. The existing independent physics and image-recovery tests remain part
of the test suite.

**Corrections and additions**

- At zero force, hole concentration ratios are undefined and now return null rather than dividing by zero. The analytical normalized edge factor remains 3 as a property of the loading solution.
- Hole-crossing checks for strain-fit neighbours now use physical geometry, accounting for unequal horizontal/vertical pixel sizes.
- Normalized interior ratios divide each stress by the nominal stress before taking a maximum, preserving the intended sign convention for negative loads in batch configurations.
- User force is explicitly converted using the gross area for bar/plate. Cantilever force remains an end shear load.
- Preset materials use fixed illustrative elastic constants; custom materials are validated separately. Yielding is not inferred from a material label.
- The interface checks geometry, numeric finiteness, subset parity, fitting support, predicted strain, displacement gradients and search-range compatibility before starting.
- Each run saves its own configuration and outputs. Changed inputs mark displayed results stale. Animation and visual magnification never alter the actual measurement results.
- Colour maps compare only common valid sample locations, use a shared scale for truth/recovery, and centre signed-error colours at zero.
- The local server runs one calculation at a time; run submission requires a per-server request token. It listens on 127.0.0.1 only.

**Interpretation retained**

The cantilever is a Saint-Venant end-loaded elasticity benchmark, not an exact
rigid-clamp boundary solution. The plate is a window into an infinite-plate
Kirsch field, not a finite-width plate simulation. Finite subsets leave a gap
at the hole, so sampled interior concentration and theoretical edge Kt are
reported separately. Noise/blur are selected camera parameters, not automatic
random changes to every experiment. Displacement differentiation can amplify
strain and stress errors even in clean images.

**Verification evidence**

All 22 Python tests passed. See `outputs/test_results.txt` for the executed suite, including the
HTTP workflow for all three objects and ZIP-export contents. The test suite
covers material/force conversion, custom material selection, input rejection,
zero-force hole recovery, unequal pixel scales and JSON handling as well as
the earlier mechanics and DIC checks.

The browser used for live screenshot testing timed out in this environment.
Visual appearance was therefore not verified in a live browser. The HTML/CSS,
JavaScript syntax, UI controller tests and real HTTP calculation/export workflow
were checked separately. The simulated-DOM interaction checks passed for material presets, custom inputs, running, object selection, field switching, stale results, zero load and error handling. This limitation is documented rather than treating
an unavailable screenshot as a passed visual test.
