"""Local quadratic displacement fitting; small strain in physical coordinates."""
import numpy as np
from scipy.spatial import cKDTree


def recover_strain(dic, sx, sy, radius_px, hole_center_px=None, hole_radius_px=0):
    """Fit neighbouring valid displacement values, not ground-truth values.

    Returns exx, eyy, engineering gamma_xy at every candidate centre.
    NaN means insufficient or ill-conditioned neighbourhood.
    """
    out = np.full((len(dic), 3), np.nan)
    valid = dic[:, 9].astype(bool)
    ids = np.flatnonzero(valid)
    if len(ids) < 6:
        return out
    points = dic[ids, :2]
    tree = cKDTree(points)
    for i, global_id in enumerate(ids):
        near = np.array(tree.query_ball_point(points[i], radius_px), dtype=int)
        if hole_center_px is not None:
            # Reject neighbour links intersecting the circular hole.
            # Measure hole intersections in physical geometry, even when
            # horizontal and vertical pixel scales differ.
            metric = np.array([1.0, sy/sx])
            start = (points[i]-hole_center_px)*metric
            vector = (points[near]-points[i])*metric
            denom = np.sum(vector*vector, axis=1)
            t = np.clip(-np.sum(start*vector, axis=1)/np.maximum(denom, 1e-20), 0, 1)
            keep = np.linalg.norm(start+t[:, None]*vector, axis=1) > hole_radius_px
            near = near[keep]
        if len(near) < 6:
            continue
        d = (points[near]-points[i])/radius_px
        a, b = d[:, 0], d[:, 1]
        A = np.column_stack((np.ones(len(near)), a, b, a*a, a*b, b*b))
        weight = np.exp(-np.sum(d*d, axis=1))
        Aw = A*weight[:, None]
        if np.linalg.matrix_rank(Aw) < 6 or np.linalg.cond(Aw) > 1e5:
            continue
        coeff = np.linalg.lstsq(Aw, dic[ids[near], 2:4]*weight[:, None], rcond=None)[0]
        du_dc, dv_dc = coeff[1]/radius_px
        du_dr, dv_dr = coeff[2]/radius_px
        out[global_id] = du_dc, dv_dr, -sx/sy*du_dr-sy/sx*dv_dc
    return out
