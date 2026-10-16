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


def normalized(a):
    b = a-a.mean()
    return b/max(np.linalg.norm(b), 1e-12)


def integer_match(template, search):
    t = template-template.mean()
    kernel = np.ones(template.shape)
    sums = correlate(search, kernel, mode='valid', method='fft')
    sums2 = correlate(search*search, kernel, mode='valid', method='fft')
    numerator = correlate(search, t, mode='valid', method='fft')
    denominator = np.linalg.norm(t)*np.sqrt(np.maximum(sums2-sums*sums/template.size, 0))
    score = np.divide(numerator, denominator, out=np.full_like(numerator, -1.0), where=denominator > 1e-10)
    row, col = np.unravel_index(np.argmax(score), score.shape)
    return row, col, score[row, col]


def run_dic(reference, deformed, mask_reference=None, mask_deformed=None,
            subset_size=25, step=16, search_radius=7, min_zncc=0.75,
            max_nfev=45, gradient_bound=0.12, denoise_sigma=0):
    reference, deformed = np.asarray(reference, float), np.asarray(deformed, float)
    if reference.shape != deformed.shape or reference.ndim != 2 or not np.all(np.isfinite(reference)) or not np.all(np.isfinite(deformed)):
        raise ValueError('DIC needs two finite grayscale images of equal shape.')
    if subset_size < 9 or subset_size % 2 != 1 or step < 1 or search_radius < 1:
        raise ValueError('Use an odd subset >= 9, positive step and search radius.')
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
    spline = RectBivariateSpline(np.arange(deformed.shape[0]), np.arange(deformed.shape[1]), deformed)
    yy, xx = np.mgrid[-h:h+1, -h:h+1]
    dx, dy = xx.ravel(), yy.ravel()
    results = []
    for cy in range(margin, reference.shape[0]-margin, step):
        for cx in range(margin, reference.shape[1]-margin, step):
            # Columns: cx, cy, u, v, du/dc, du/dr, dv/dc, dv/dr, zncc, valid, status
            # status: 0 accepted; 1 reference mask; 2 flat; 3 optimizer;
            # 4 correlation; 5 mapped mask; 6 parameter bound.
            row = [cx, cy]+[np.nan]*7+[0, 1]
            patch = reference[cy-h:cy+h+1, cx-h:cx+h+1]
            if not mr[cy-h:cy+h+1, cx-h:cx+h+1].all():
                results.append(row); continue
            if patch.std() < 0.015:
                row[-1] = 2; results.append(row); continue
            search = deformed[cy-h-search_radius:cy+h+search_radius+1,
                              cx-h-search_radius:cx+h+search_radius+1]
            iy, ix, _ = integer_match(patch, search)
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
            elif np.any(r < 2) or np.any(r > reference.shape[0]-3) or np.any(c < 2) or np.any(c > reference.shape[1]-3) or not np.all(map_coordinates(md.astype(float), [r, c], order=1, mode='constant', cval=0) > 0.999): status = 5
            elif np.any(np.abs(fit.x) > 0.99*np.array(upper)): status = 6
            results.append([cx, cy, *fit.x, zncc, int(status == 0), status])
    return np.array(results, dtype=float)


DIC_COLUMNS = 'col_px,row_px,u_px,v_px,du_dc,du_dr,dv_dc,dv_dr,zncc,valid,status'
