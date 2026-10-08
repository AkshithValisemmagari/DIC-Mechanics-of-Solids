"""Isotropic plane stress and derived invariants, SI units."""
import numpy as np


def plane_stress(strain, youngs_modulus_pa, poisson_ratio):
    E, nu = youngs_modulus_pa, poisson_ratio
    if not np.isfinite(E) or E <= 0 or not -1 < nu < 0.5:
        raise ValueError('Require E > 0 and -1 < nu < 0.5.')
    ex, ey, gamma = np.asarray(strain).T
    return np.column_stack((E/(1-nu*nu)*(ex+nu*ey),
                            E/(1-nu*nu)*(ey+nu*ex), E/(2*(1+nu))*gamma))


def invariants(stresses):
    sx, sy, tau = np.asarray(stresses).T
    mid = (sx+sy)/2
    rad = np.sqrt(((sx-sy)/2)**2+tau*tau)
    # In-plane principal stresses; third principal value is zero in plane stress.
    vm = np.sqrt(sx*sx-sx*sy+sy*sy+3*tau*tau)
    return np.column_stack((mid+rad, mid-rad, vm))
