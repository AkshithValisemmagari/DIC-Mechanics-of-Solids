"""Phase 1: analytical ground truth, using SI units throughout."""

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class AxialBarResult:
    x_m: np.ndarray
    displacement_m: np.ndarray
    strain: np.ndarray
    stress_pa: np.ndarray


def solve_axial_bar(length_m, area_m2, youngs_modulus_pa, force_n, n_points=201):
    """Solve a uniform, linearly elastic bar with u(0)=0 and end force P.

    Positive P denotes tension. No distributed axial load is included.
    This is a 1D small-strain model, not a model of local clamp effects.
    """
    for name, value in (("length_m", length_m), ("area_m2", area_m2),
                        ("youngs_modulus_pa", youngs_modulus_pa)):
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive.")
    if not np.isfinite(force_n):
        raise ValueError("force_n must be finite.")
    if isinstance(n_points, bool) or not isinstance(n_points, (int, np.integer)) or n_points < 2:
        raise ValueError("n_points must be an integer of at least 2.")

    x = np.linspace(0.0, length_m, n_points)
    stress = force_n / area_m2
    strain = stress / youngs_modulus_pa
    return AxialBarResult(x, strain * x, np.full_like(x, strain),
                          np.full_like(x, stress))


class Benchmark:
    """Plane-stress benchmark in metres, with Cartesian y increasing upward."""

    def __init__(self, config):
        self.c = config
        self.name = config['benchmark']
        self.E = float(config['material']['youngs_modulus_pa'])
        self.nu = float(config['material']['poisson_ratio'])
        if self.E <= 0 or not np.isfinite(self.E) or not -1 < self.nu < 0.5:
            raise ValueError('Require E > 0 and -1 < nu < 0.5.')
        if self.name not in ('axial_bar', 'cantilever', 'plate_with_hole', 'pure_bending'):
            raise ValueError('Unknown benchmark.')
        self.bounds = np.array(config['domain_m'], dtype=float)
        if self.bounds.shape != (4,) or not np.all(np.isfinite(self.bounds)):
            raise ValueError('domain_m must contain finite xmin, xmax, ymin, ymax.')
        if self.bounds[1] <= self.bounds[0] or self.bounds[3] <= self.bounds[2]:
            raise ValueError('Domain must have positive width and height.')
        self.hole_radius = float(config.get('hole_radius_m', 0))
        if not np.isfinite(self.hole_radius) or self.hole_radius < 0:
            raise ValueError('hole_radius_m must be finite and nonnegative.')
        if self.name == 'plate_with_hole' and self.hole_radius <= 0:
            raise ValueError('Hole radius must be positive.')
        if self.name in ('cantilever', 'pure_bending'):
            self.L = float(config['length_m'])
            self.h = float(config['height_m'])
            thickness = float(config['thickness_m'])
            self.I = thickness * self.h**3 / 12
            dimensions = np.array([self.L, self.h, thickness, self.I])
            if not np.all(np.isfinite(dimensions)) or np.any(dimensions <= 0):
                raise ValueError('Beam dimensions must be finite and positive.')
        load = config.get('remote_stress_pa', config.get('moment_nm', config.get('force_n')))
        if load is None or not np.isfinite(load):
            raise ValueError('A finite load is required.')

    def material_mask(self, x, y):
        mask = np.ones(np.broadcast(x, y).shape, dtype=bool)
        if self.name == 'plate_with_hole':
            mask &= x*x + y*y >= self.hole_radius**2
        return mask

    def displacement(self, x, y):
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        if self.name == 'axial_bar':
            e = self.c['remote_stress_pa'] / self.E
            return e*x, -self.nu*e*y
        if self.name == 'pure_bending':
            # A rigid translation/rotation is fixed by v(0,0)=v(L,0)=0,
            # u(L/2,0)=0. These set the display reference, not end clamps.
            k = self.c['moment_nm']/(self.E*self.I)
            xi = x-self.L/2
            return -k*xi*y, k*(xi*xi-(self.L/2)**2+self.nu*y*y)/2
        if self.name == 'cantilever':
            # Saint-Venant plane-stress end-shear solution, not an exact clamp.
            q = self.c['force_n'] / (self.E*self.I)
            u = -q*((self.L*x-x*x/2)*y + (2+self.nu)*y**3/6)
            v = q*(x*x*(3*self.L-x)/6 + (1+self.nu)*self.h**2*x/4
                   + self.nu*(self.L-x)*y*y/2)
            return u, v
        a = self.hole_radius
        actual_r = np.hypot(x, y)
        r = np.maximum(actual_r, a)
        t = np.arctan2(y, x)
        k = (3-self.nu)/(1+self.nu)  # plane stress
        G = self.E/(2*(1+self.nu))
        q = self.c['remote_stress_pa']/(4*G)
        ur = q*(r*((k-1)/2+np.cos(2*t))
                + a*a/r*(1+(k+1)*np.cos(2*t)) - a**4/r**3*np.cos(2*t))
        ut = q*(-r*np.sin(2*t) + a*a/r*(1-k)*np.sin(2*t)
                - a**4/r**3*np.sin(2*t))
        # Continue boundary displacement inward with bounded magnitude. The
        # extension is only numerical support for inversion, never material.
        scale = np.minimum(actual_r/a, 1.0)
        return scale*(ur*np.cos(t)-ut*np.sin(t)), scale*(ur*np.sin(t)+ut*np.cos(t))

    def stress(self, x, y):
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        zero = np.zeros_like(x)
        if self.name == 'axial_bar':
            return zero+self.c['remote_stress_pa'], zero, zero
        if self.name == 'pure_bending':
            return -self.c['moment_nm']*y/self.I, zero, zero
        if self.name == 'cantilever':
            q = self.c['force_n']/self.I
            return -q*(self.L-x)*y, zero, q*(self.h*self.h/4-y*y)/2
        a = self.hole_radius
        r = np.maximum(np.hypot(x, y), a*0.25)
        t = np.arctan2(y, x)
        z = (a/r)**2
        S = self.c['remote_stress_pa']
        rr = S/2*(1-z+(1-4*z+3*z*z)*np.cos(2*t))
        tt = S/2*(1+z-(1+3*z*z)*np.cos(2*t))
        rt = -S/2*(1+2*z-3*z*z)*np.sin(2*t)
        c, s = np.cos(t), np.sin(t)
        return rr*c*c+tt*s*s-2*rt*s*c, rr*s*s+tt*c*c+2*rt*s*c, (rr-tt)*s*c+rt*(c*c-s*s)

    def strain(self, x, y):
        sx, sy, t = self.stress(x, y)
        return (sx-self.nu*sy)/self.E, (sy-self.nu*sx)/self.E, 2*(1+self.nu)*t/self.E
