"""Local affine DIC: integer ZNCC initialization + normalized subpixel fitting.

This module takes images and masks only, never analytical displacement.
Columns/right and rows/down define its pixel coordinate system.
"""
import numpy as np
from scipy.signal import correlate
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates, binary_erosion
from image_preprocessing import prepare_images
from dic_support import supported_subset_centres


def normalized(a):
    b = a-a.mean()
    return b/max(np.linalg.norm(b), 1e-12)


def integer_match(template, search, valid_windows=None):
    """Best integer ZNCC seed, or None when no target window is supported."""
    t = template-template.mean()
    kernel = np.ones(template.shape)
    sums = correlate(search, kernel, mode='valid', method='fft')
    sums2 = correlate(search*search, kernel, mode='valid', method='fft')
    numerator = correlate(search, t, mode='valid', method='fft')
    denominator = np.linalg.norm(t)*np.sqrt(np.maximum(sums2-sums*sums/template.size, 0))
    score = np.divide(numerator, denominator, out=np.full_like(numerator, -1.0), where=denominator > 1e-10)
    if valid_windows is not None:
        if not np.any(valid_windows):
            return None
        score = np.where(valid_windows, score, -np.inf)
    row, col = np.unravel_index(np.argmax(score), score.shape)
    return row, col, score[row, col]


def _supported(mask, r, c):
    return (np.min(r) >= 2 and np.max(r) <= mask.shape[0]-3
            and np.min(c) >= 2 and np.max(c) <= mask.shape[1]-3
            and np.all(map_coordinates(mask, [r, c], order=1,
                                       mode='constant', cval=0) > .999))


def reverse_match(point, source_spline, source_mask, target, target_spline,
                  target_mask, target_centres, dx, dy, subset_size,
                  search_radius, min_zncc, max_nfev, gradient_bound):
    """Independently match a deformed-image centre back into the reference.

    The search is centred at the observed deformed location, not the original
    reference location or an inverse analytical/forward-affine prediction.
    """
    cx, cy = point
    r, c = cy+dy, cx+dx
    if not _supported(source_mask, r, c):
        return None, np.nan, 'source_support'
    patch = source_spline.ev(r, c)
    if patch.std() < .015:
        return None, np.nan, 'low_texture'
    h = subset_size//2
    gx, gy = np.rint(point).astype(int)
    x0, x1 = max(h+2, gx-search_radius), min(target.shape[1]-h-3, gx+search_radius)
    y0, y1 = max(h+2, gy-search_radius), min(target.shape[0]-h-3, gy+search_radius)
    if x1 < x0 or y1 < y0:
        return None, np.nan, 'search_support'
    search = target[y0-h:y1+h+1, x0-h:x1+h+1]
    seed = integer_match(patch.reshape(subset_size, subset_size), search,
                         target_centres[y0:y1+1, x0:x1+1])
    if seed is None:
        return None, np.nan, 'target_support'
    iy, ix, _ = seed
    p0 = np.array([x0+ix-cx, y0+iy-cy, 0, 0, 0, 0], float)
    values = normalized(patch)
    def coords(p):
        return cy+dy+p[1]+p[4]*dx+p[5]*dy, cx+dx+p[0]+p[2]*dx+p[3]*dy
    def residual(p):
        r, c = coords(p)
        return normalized(target_spline.ev(r, c))-values
    # Inverse affine gradients can exceed the forward component bound even
    # for a valid compression. This bound covers inverse gradients for the
    # intended small-gradient regime, without seeding their fitted values.
    reverse_bound = max(gradient_bound, 2*gradient_bound/max(1-2*gradient_bound, .1))
    upper = np.array([search_radius+.75]*2+[reverse_bound]*4)
    fit = least_squares(residual, p0, bounds=(-upper, upper), max_nfev=max_nfev,
                        ftol=1e-7, xtol=1e-7, gtol=1e-7)
    zncc = float(1-fit.fun@fit.fun/2)
    if not fit.success:
        return None, zncc, 'optimizer'
    if zncc < min_zncc:
        return None, zncc, 'low_correlation'
    r, c = coords(fit.x)
    if not _supported(target_mask, r, c):
        return None, zncc, 'target_support'
    if np.any(np.abs(fit.x) > .99*upper):
        return None, zncc, 'parameter_bound'
    return np.asarray(point)+fit.x[:2], zncc, 'matched'


def run_dic(reference, deformed, mask_reference=None, mask_deformed=None,
            subset_size=25, step=16, search_radius=7, min_zncc=0.75,
            max_nfev=45, gradient_bound=0.12, denoise_sigma=0,
            fb_tolerance_px=.3, return_diagnostics=False):
    """Measure forward affine motion and optionally verify an independent return.

    fb_tolerance_px=None preserves forward-only acceptance for controlled
    comparisons. Existing 11-column output is retained; return_diagnostics
    additionally returns per-candidate reverse outcomes and pixel cycle errors.
    """
    reference, deformed = np.asarray(reference, float), np.asarray(deformed, float)
    if reference.shape != deformed.shape or reference.ndim != 2 or not np.all(np.isfinite(reference)) or not np.all(np.isfinite(deformed)):
        raise ValueError('DIC needs two finite grayscale images of equal shape.')
    if subset_size < 9 or subset_size % 2 != 1 or step < 1 or search_radius < 1:
        raise ValueError('Use an odd subset >= 9, positive step and search radius.')
    if fb_tolerance_px is not None and (isinstance(fb_tolerance_px, bool) or not np.isfinite(fb_tolerance_px) or fb_tolerance_px <= 0):
        raise ValueError('fb_tolerance_px must be finite and positive, or None to disable.')
    h = subset_size//2
    margin = h+search_radius+3
    if min(reference.shape) <= 2*margin:
        raise ValueError('Image too small for these DIC settings.')
    mr = np.ones(reference.shape, bool) if mask_reference is None else np.asarray(mask_reference, bool)
    md = np.ones(deformed.shape, bool) if mask_deformed is None else np.asarray(mask_deformed, bool)
    if mr.shape != reference.shape or md.shape != reference.shape:
        raise ValueError('Masks must match image shape.')
    inputs,support,_=prepare_images({'reference':reference,'deformed':deformed},
                                    {'reference':mr,'deformed':md},denoise_sigma)
    reference,deformed=inputs['reference'],inputs['deformed']
    mr,md=support['reference'],support['deformed']
    # Extra support avoids sampling interpolation footprints across a hole.
    mr = binary_erosion(mr, iterations=3)
    md = binary_erosion(md, iterations=3)
    reference_mask, deformed_mask = mr.astype(float), md.astype(float)
    target_centres = supported_subset_centres(md, subset_size)
    reference_centres = supported_subset_centres(mr, subset_size)
    reference_spline = RectBivariateSpline(np.arange(reference.shape[0]), np.arange(reference.shape[1]), reference) if fb_tolerance_px is not None else None
    spline = RectBivariateSpline(np.arange(deformed.shape[0]), np.arange(deformed.shape[1]), deformed)
    yy, xx = np.mgrid[-h:h+1, -h:h+1]
    dx, dy = xx.ravel(), yy.ravel()
    results = []
    diagnostics = []
    for cy in range(margin, reference.shape[0]-margin, step):
        for cx in range(margin, reference.shape[1]-margin, step):
            # Columns: cx, cy, u, v, du/dc, du/dr, dv/dc, dv/dr, zncc, valid, status
            # status: 0 accepted; 1 reference mask; 2 flat; 3 optimizer;
            # 4 correlation; 5 target support; 6 bound; 7 reverse failed; 8 cycle error.
            diagnostic = dict(round_trip_error_px=np.nan, reverse_zncc=np.nan, reverse_status='not_checked')
            diagnostics.append(diagnostic)
            row = [cx, cy]+[np.nan]*7+[0, 1]
            patch = reference[cy-h:cy+h+1, cx-h:cx+h+1]
            if not mr[cy-h:cy+h+1, cx-h:cx+h+1].all():
                results.append(row); continue
            if patch.std() < 0.015:
                row[-1] = 2; results.append(row); continue
            search = deformed[cy-h-search_radius:cy+h+search_radius+1,
                              cx-h-search_radius:cx+h+search_radius+1]
            valid_windows = target_centres[cy-search_radius:cy+search_radius+1,
                                           cx-search_radius:cx+search_radius+1]
            seed = integer_match(patch, search, valid_windows)
            if seed is None:
                row[-1] = 5; results.append(row); continue
            iy, ix, _ = seed
            p0 = np.array([ix-search_radius, iy-search_radius, 0, 0, 0, 0], float)
            target = normalized(patch.ravel())
            def coords(p):
                return cy+dy+p[1]+p[4]*dx+p[5]*dy, cx+dx+p[0]+p[2]*dx+p[3]*dy
            def residual(p):
                r, c = coords(p)
                return normalized(spline.ev(r, c))-target
            lower = [-search_radius-0.75]*2+[-gradient_bound]*4
            upper = [search_radius+0.75]*2+[gradient_bound]*4
            fit = least_squares(residual, p0, bounds=(lower, upper), max_nfev=max_nfev,
                                ftol=1e-7, xtol=1e-7, gtol=1e-7)
            r, c = coords(fit.x)
            zncc = float(1-np.dot(fit.fun, fit.fun)/2)
            status = 0
            if not fit.success: status = 3
            elif zncc < min_zncc: status = 4
            elif np.any(r < 2) or np.any(r > reference.shape[0]-3) or np.any(c < 2) or np.any(c > reference.shape[1]-3) or not np.all(map_coordinates(deformed_mask, [r, c], order=1, mode='constant', cval=0) > 0.999): status = 5
            elif np.any(np.abs(fit.x) > 0.99*np.array(upper)): status = 6
            if status == 0 and fb_tolerance_px is not None:
                back, reverse_zncc, why = reverse_match(
                    [cx+fit.x[0], cy+fit.x[1]], spline, deformed_mask,
                    reference, reference_spline, reference_mask, reference_centres,
                    dx, dy, subset_size, search_radius, min_zncc, max_nfev, gradient_bound)
                diagnostic.update(reverse_zncc=reverse_zncc, reverse_status=why)
                if back is None:
                    status = 7
                else:
                    error = float(np.linalg.norm(back-[cx, cy]))
                    diagnostic['round_trip_error_px'] = error
                    if error > fb_tolerance_px:
                        status = 8
                        diagnostic['reverse_status'] = 'cycle_error'
            elif status == 0:
                diagnostic['reverse_status'] = 'disabled'
            results.append([cx, cy, *fit.x, zncc, int(status == 0), status])
    result = np.array(results, dtype=float)
    if return_diagnostics:
        return result, dict(tolerance_px=fb_tolerance_px, points=diagnostics)
    return result


DIC_COLUMNS = 'col_px,row_px,u_px,v_px,du_dc,du_dr,dv_dc,dv_dr,zncc,valid,status'
