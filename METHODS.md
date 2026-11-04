**Purpose and separation of information**

The camera/DIC workflow below applies to flat specimens. The separate circular
shaft torsion experiment is analytical only and generates no camera or DIC data.

The analytical model generates a reference/deformed image pair. DIC receives
only the two images, image-support masks and its own measurement settings.
It never receives the true displacement. Analytical fields are evaluated again
only after matching, for comparison at the same subset centres. The support
masks are synthetic specimen geometry/boundary information, not displacement
initial guesses. Masks for an actual experiment would need separate segmentation.

**Coordinates and units**

Physical coordinates are x right and y up. Pixel coordinates are c right and
r down. For bounds [xmin, xmax, ymin, ymax], W columns and H rows:

```text
sx = (xmax - xmin) / (W - 1)       metres per column
sy = (ymax - ymin) / (H - 1)       metres per row
x = xmin + c sx
y = ymax - r sy
u_pixel = u_physical / sx
v_pixel = -v_physical / sy
```

Both physical and pixel displacement components are saved. Material and stress
calculations use SI units; plots explicitly label any conversion to mm or MPa.
The circular-hole neighbourhood intersection test uses physical distances,
including when horizontal and vertical pixel sizes differ.

**1. Analytical mechanics**

All four flat 2D benchmarks use linear isotropic plane stress. E is Young's modulus,
nu Poisson's ratio, and G = E / [2(1 + nu)].

For uniaxial tension with remote stress S:

```text
u = (S/E) x
v = -(nu S/E) y
sigma_xx = S; sigma_yy = tau_xy = 0
```

This describes uniform tension with symmetry u=0 at x=0, not a fully clamped
2D end that suppresses Poisson contraction. The separate original 1D example
uses S=P/A, u=Px/(AE), and has no transverse degree of freedom.

For the cantilever end-loading benchmark, x runs from 0 to L, y from -h/2 to h/2,
b is thickness, I=b h³/12 and positive P is an upward end shear. The fields are:

```text
q = P / (E I)
u = -q [(Lx - x²/2)y + (2 + nu)y³/6]
v = q [x²(3L - x)/6 + (1 + nu)h²x/4 + nu(L - x)y²/2]

sigma_xx = -P(L - x)y/I
sigma_yy = 0
tau_xy = P(h²/4 - y²)/(2I)
```

This is a Saint-Venant polynomial elasticity solution with a parabolic shear
traction at the end. It satisfies equilibrium, free top/bottom traction, force
and bending-moment resultants, and plane-stress constitutive compatibility.
Its displacement convention fixes the centre at x=y=0 but does not impose
u=v=0 at every point of a rigid clamp. A real clamp creates local end effects
outside this analytical benchmark. Bending and shear terms are included rather
than combining incompatible beam displacement and elasticity stress formulas.

For the infinite plate with a circular hole of radius a under remote x tension S,
r is distance from the hole centre and theta is measured counterclockwise from
positive x. Define z=a²/r² and kappa=(3-nu)/(1+nu):

```text
sigma_rr = S/2 [1 - z + (1 - 4z + 3z²) cos(2theta)]
sigma_tt = S/2 [1 + z - (1 + 3z²) cos(2theta)]
tau_rt   = -S/2 [1 + 2z - 3z²] sin(2theta)

u_r = S/(4G) {r[(kappa-1)/2 + cos(2theta)]
      + a²/r [1 + (kappa+1)cos(2theta)] - a⁴/r³ cos(2theta)}
u_t = S/(4G) {-r sin(2theta) + (1-kappa)a²/r sin(2theta)
      - a⁴/r³ sin(2theta)}

u = u_r cos(theta) - u_t sin(theta)
v = u_r sin(theta) + u_t cos(theta)
```

Polar stresses are rotated to Cartesian components in `mechanics.py`. The image
is a crop of this infinite-plate field, not the exact solution for a finite
rectangle with loaded outer edges. The hole interior is masked. An artificial
bounded extension inside the hole is used only while solving inverse pixel
coordinates; it is never treated as material ground truth.

At r=a, radial and shear tractions vanish and sigma_tt=S[1-2cos(2theta)], whose
maximum is 3S. The code tests this independently of image processing.

**2. Synthetic camera images**

A seeded pattern of antialiased dark discs forms the speckles. Their radius
varies by ±30% around the configured value. `density` controls expected disc
coverage approximately; overlap and the varying radii mean it is not an exact
black-pixel fraction.

A material point X moves to x=X+u(X). To generate an image on deformed pixel
locations, solve X=x-u(X) iteratively, then interpolate reference intensity at X.
Convergence is checked to 1e-8 pixel; nonconvergence raises an error. This inverse
mapping is necessary for nonuniform motion: x-u(x) alone is not generally exact.
Cubic B-spline interpolation is used for generation. The DIC interpolator is a
separate bicubic spline implementation on the final camera pixels. Both still
have related interpolation assumptions; this is a synthetic benchmark, not
independent experimental validation.

The camera model applies:

1. Optional Gaussian blur to both ideal images.
2. Optional gain and offset to the deformed image.
3. Independent zero-mean Gaussian noise to each image.
4. Clipping to [0,1] and rounding to 8-bit pixel values.

With DIC denoising Off, matching uses the normalized 8-bit camera values.
With Gaussian or Wiener denoising enabled, raw capture PNGs stay unchanged;
matching uses filtered floating-point arrays saved exactly in
`dic_input_images.npz`. The `*_smoothed.png` files are 16-bit display previews
and are not reloaded for matching. Stereo exports use the same distinction
for all four captures. Camera blur is applied before capture; DIC denoising
is applied afterward. Blur width is in pixels, noise standard deviation is on
the 0–1 intensity scale. For example,
0.01 corresponds to 2.55 grey levels before clipping. Gaussian blur approximates
optical smoothing, not directional motion blur. Saturation breaks ideal
brightness invariance. Three-sigma blur footprints and interpolation support
are excluded at material/image boundaries.

**3. DIC matching**

Every reference subset is matched inside a configured search radius. Integer
initialization maximizes zero-normalized cross-correlation (ZNCC):

```text
ZNCC = sum[(f - mean(f))(g - mean(g))]
       / sqrt(sum[(f - mean(f))²] sum[(g - mean(g))²])
```

Only integer target windows whose full subset lies within the processed target
support mask can supply a seed. This includes the existing denoising and
interpolation safety margins. If no supported window exists in the search,
the subset is rejected with target-support status 5 before refinement. The
mapped subset is still checked after refinement, since an affine fit can move
or distort it across a boundary. The same initialization rule is used for
stereo matching, which reports `target_support` for this rejection. These
checks do not establish that a supported correlation peak is the correct match.

Subpixel refinement fits six local affine parameters using bounded nonlinear
least squares. For offsets dc,dr from the reference subset centre:

```text
c_deformed = c_reference + u0 + du_dc dc + du_dr dr
r_deformed = r_reference + v0 + dv_dc dc + dv_dr dr
```

The minimized residual is the difference between zero-mean unit-norm intensity
vectors (ZNSSD form). This allows translation, small rotation, extension and
shear within each subset. It is more suitable for deformation than fitting
only a translation. It is still a local affine approximation to nonlinear
fields such as the hole solution.

The solver is local: large motions beyond the search radius, severe strain,
repetitive/flat texture or destroyed patterns can fail. It has no multiscale
pyramid or automatic global recovery. No analytical seed rescues it.

| Status | Meaning |
|---:|---|
| 0 | Accepted |
| 1 | Reference subset crosses a mask/boundary |
| 2 | Reference subset lacks intensity variation |
| 3 | Optimizer failed to converge |
| 4 | Final ZNCC below the configured threshold |
| 5 | No supported integer target window, or mapped subset crosses invalid support |
| 6 | Optimizer reached a displacement/gradient bound |
| 7 | Reverse match failed source/target support, texture, correlation, optimizer or bound checks |
| 8 | Reverse match returned more than the allowed distance from the original centre |

**Forward/backward verification (flat specimens)**

After a forward fit passes, an axis-aligned subset centred at its measured
deformed location is independently matched into the reference image. Its
integer search is centred at that deformed location, not at the original
reference centre. No inverse forward parameters or analytical displacement are
used as a seed. Subpixel normalized affine fitting, processed masks, texture,
correlation, bounds and convergence checks also apply in the reverse direction.
Reverse affine bounds allow inverse compression gradients to exceed the forward
component bound in the intended small-gradient regime.

A successful reverse fit must return within `fb_tolerance_px` (default 0.3 px,
Euclidean image-coordinate distance) of the original reference centre. This is
a consistency tolerance, not an accuracy guarantee. A reverse source subset
may fail near a boundary even when the forward mapped footprint fits: rejection
is deliberately conservative. Per-point errors/reasons are saved separately in
`dic_consistency.csv`; the original displacement CSV keeps its 11-column schema.
Summary status counts include reverse failures (7) and cycle failures (8).

Set the batch setting to null to disable for comparisons. No filtering is
applied a second time for reverse matching. Repetitive patterns can yield a
wrong but cycle-consistent pair, or make a whole texture period unobservable.
Peak-uniqueness rejection is not enabled without separate calibration.
See `CONSISTENCY_VALIDATION.md` for the deterministic sweep and limitations.

**4. Strain and stress recovery**

Accepted centre displacements are fitted locally with a weighted quadratic
polynomial using at least six neighbours. Rank and conditioning are checked.
The gradients of that fitted displacement give:

```text
epsilon_xx = du/dx
epsilon_yy = dv/dy
gamma_xy = du/dy + dv/dx     (engineering shear strain)
```

The fit radius sets a spatial smoothing/resolution tradeoff. Neighbour links
crossing the hole are excluded. The reported strain is derived from measured
centre displacements, not directly from the analytical fields or optimizer's
affine gradients. Insufficient/ill-conditioned neighbourhoods return NaN.

```text
sigma_xx = E/(1 - nu²) (epsilon_xx + nu epsilon_yy)
sigma_yy = E/(1 - nu²) (epsilon_yy + nu epsilon_xx)
tau_xy = E/[2(1 + nu)] gamma_xy

sigma_1,2 = (sigma_xx + sigma_yy)/2
            ± sqrt[((sigma_xx - sigma_yy)/2)² + tau_xy²]
sigma_VM = sqrt(sigma_xx² - sigma_xx sigma_yy + sigma_yy² + 3 tau_xy²)
```

The reported sigma_1,2 are the two in-plane principal values. The third value
is zero; sort all three if 3D principal ordering is needed. Stress inference
requires known E, nu and plane stress; the images do not directly measure stress.
No factor of safety is computed because no strength/yield criterion is supplied.

**5. Validation and concentration factor**

For N accepted centres, vector displacement RMSE is
sqrt[sum(error_u²+error_v²)/N]. Component RMSEs and maximum vector error are
also reported. Strain/stress summaries use the same component-vector convention;
their vector RMSE is a numerical combined-component score, not a tensor-invariant
norm (engineering shear is not rescaled). Failure and coverage accompany errors.

`eligible_match_coverage_fraction` is accepted displacement matches divided by
eligible reference subsets; it is null if none are eligible. The interface
shows this beside displacement RMSE and also reports acceptance across all
candidates. Strain/stress validity is reported separately.
`coverage_fraction` uses every candidate centre, including those masked by the
hole. `eligible_match_failure_fraction` uses candidates whose reference subsets
fit inside the material; flat subsets remain eligible failures. The n_valid
field in each metric records that metric's valid sample count.

For the hole, three distinct quantities are reported:

- The analytical edge Kt=3.
- The analytical maximum sigma_xx/S on centres with valid recovered stress.
- The DIC-derived maximum sigma_xx/S on those same centres.

The last two are sampled interior ratios, not estimates of the true edge Kt.
Finite subsets and gradient windows smooth the field and leave a boundary gap.
This distinction prevents a misleading claim that a coarse measurement either
proves or disproves the theoretical stress concentration.

**6. Robustness protocol**

One factor changes at a time; three independent camera-noise seeds repeat each
setting. The default has 4 noise levels and 3 levels each for blur, brightness
gain, subset size and speckle radius: 48 runs. Other factors use background
noise=0.01. Means and sample standard deviations are plotted, with raw trials,
strain/stress errors, failures and coverage retained in CSV. No monotonic trend
is forced: mild blur can reduce interpolation artifacts while also losing detail.
Changing subset size changes both resolution and eligible measurement centres.
The default robustness study uses the axial bar to isolate imaging effects.

**References and verification**

- OpenGeoSys, “Linear elasticity: disc with hole”, analytical Kirsch stress
  equations and infinite-domain assumptions:
  https://www.opengeosys.org/stable/docs/benchmarks/small-deformations/linear_disc_with_hole/
  (That page uses a different angle/loading convention; this code uses x tension.)
- The implemented displacement expressions are checked against the independent
  stress expressions by numerical differentiation and constitutive conversion.
- Additional tests check beam load/moment resultants, free surfaces, hole-edge
  traction/Kt, known rigid translation, axial affine image recovery, independent
  noise, flat-image rejection and physical/image coordinate conversion.

These checks establish implementation consistency for the included scope.
Synthetic interpolation, finite resolution and local field fitting remain
measurement limitations, shown explicitly by the saved error reports.


**Pure bending by equal and opposite end moments**

For a rectangular beam of length L, height h, thickness b, I=b h³/12 and
signed moment M, define k=M/(EI) and xi=x-L/2:

```text
u(x,y) = -k xi y
v(x,y) = k [xi² - (L/2)² + nu y²] / 2
sigma_xx = -M y/I
sigma_yy = tau_xy = 0
```

These displacements give exx=-k y, eyy=nu k y and engineering gamma_xy=0,
matching plane-stress elasticity. The Poisson term in v is retained. Removing
rigid motion sets v(0,0)=v(L,0)=0 and u(L/2,0)=0; this is a reference choice,
not a physical rigid clamp. End stress resultants are -M about z at x=0 and +M
at x=L; net force is zero. Top and bottom surfaces are traction-free. Positive
M puts y>0 in compression and y<0 in tension. This small-strain solution excludes
local load-introduction effects, yielding and buckling.

**Analytical circular-shaft torsion**

For solid radius R, length L, torque T about +x and isotropic E, nu:

```text
G = E / [2(1+nu)]
J = pi R^4 / 2
 theta(x) = T x/(G J)
tau_x_theta(r) = T r/J
sigma_von_mises(r) = sqrt(3) abs(tau_x_theta(r))
```

The left reference section has theta(0)=0; its reaction balances the torque at
the right end. Positive torque rotates +y toward +z. The maximum shear is |T|R/J
and the end angle is TL/(GJ). Stress is constant along x and increases linearly
with r, so a uniformly red outer surface is expected. End caps and the separate
cross-section view display its radial gradient. At zero torque all stresses and
angles are zero. Negative torque changes signed angle/shear, not von Mises stress.

The renderer rotates each circular section, keeping its radius constant. The
visual angle is theta times the magnification and playback fraction. This is a
display transformation of a small-strain analytical solution, not a nonlinear
solid solver. Curves and reported values use actual full load. Limits enforce
length >= 4 radii, maximum shear strain <= 2%, and |end angle| <= 0.35 rad;
local end effects and material failure are excluded. No DIC estimates, synthetic
speckles, error claims or noise comparison are produced for this case.

**Interactive line comparisons and paired noise**

Profiles select an actual candidate pixel row or column. Their horizontal axis
is the corresponding physical x or y coordinate in mm, sorted in ascending order.
Analytical and measured values are evaluated at those same centres. Rejected or
nonfinite estimates break measured curves; segments crossing the circular hole
are also broken. Connecting samples does not create new estimates. The CSV stores
actual centres, analytical values and available measurements, with empty cells
for unavailable values. Physical displacement components use x-right/y-up signs.

Paired runs share mechanics, geometry, texture seed, camera seed, blur, brightness,
image dimensions, DIC settings and strain windows. Only Gaussian noise standard
deviation changes to zero for the baseline. Reference/deformed noise remains
independent within a run. Camera intensities are in [0,1] before 8-bit quantization;
noise is clipped along with the image, so saturation can affect the experiment.
Baseline is not mathematically error-free: interpolation, quantization and
selected blur/brightness remain. Repeating identical inputs reproduces the pair.

Each field's paired errors use the intersection of its finite, accepted centres
in both runs. Coverage counts are shown separately. Line statistics apply this
same intersection restricted to the selected line. For n common points,
RMSE=sqrt(sum((measured-truth)^2)/n) and maximum error=max(abs(measured-truth)).
With n=0, errors are unavailable rather than zero. The top displacement card is
vector error; the selected displacement-magnitude field uses scalar magnitude
error. A single noise realization need not worsen every metric.

Mechanics references: MIT OpenCourseWare, Mechanics of Materials, torsion notes
(https://ocw.mit.edu/courses/3-11-mechanics-of-materials-fall-1999/0e0845a9e3abe430080eaffb0c5015ba_MIT3_11F99_torsion.pdf),
and Unified Engineering Materials and Structures, bending lectures
(https://ocw.mit.edu/courses/16-001-unified-engineering-materials-and-structures-fall-2021/mit16_001_f21_lec30lec31lec32.pdf).
