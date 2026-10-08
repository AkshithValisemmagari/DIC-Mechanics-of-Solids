"""Seeded speckles, physical calibration, inverse warping and camera degradation."""
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from PIL import Image


def coordinate_grid(model, shape):
    rows, cols = shape
    xmin, xmax, ymin, ymax = model.bounds
    sx, sy = (xmax-xmin)/(cols-1), (ymax-ymin)/(rows-1)
    xx, yy = np.meshgrid(xmin+np.arange(cols)*sx, ymax-np.arange(rows)*sy)
    return xx, yy, sx, sy


def generate_speckles(shape, radius_px=2.0, density=0.35, seed=2039):
    """Random dark discs on grey, with antialiased edges; values in [0,1]."""
    if radius_px <= 0 or not 0 < density < 1:
        raise ValueError('Positive radius and density between 0 and 1 required.')
    rng = np.random.default_rng(seed)
    image = np.full(shape, 0.82)
    n = int(-np.log(1-density)*np.prod(shape)/(np.pi*radius_px**2))
    for _ in range(n):
        cy, cx = rng.uniform(0, shape[0]), rng.uniform(0, shape[1])
        radius = radius_px*rng.uniform(0.7, 1.3)
        y0, y1 = max(0, int(cy-radius-1)), min(shape[0], int(cy+radius+2))
        x0, x1 = max(0, int(cx-radius-1)), min(shape[1], int(cx+radius+2))
        y, x = np.mgrid[y0:y1, x0:x1]
        coverage = np.clip(radius+0.5-np.hypot(x-cx, y-cy), 0, 1)
        image[y0:y1, x0:x1] = np.minimum(image[y0:y1, x0:x1], 0.82-0.64*coverage)
    return image


def synthetic_pair(model, config):
    settings = config['image']
    shape = tuple(settings['shape'])
    texture = generate_speckles(shape, settings['speckle_radius_px'], settings['density'], settings['seed'])
    x, y, sx, sy = coordinate_grid(model, shape)
    xr, yr = x.copy(), y.copy()
    # Fixed-point inversion: X = x_deformed - u(X); checked, never assumed exact.
    for _ in range(100):
        u, v = model.displacement(xr, yr)
        xn, yn = x-u, y-v
        change = max(np.max(np.abs(xn-xr)/sx), np.max(np.abs(yn-yr)/sy))
        xr, yr = xn, yn
        if change < 1e-8:
            break
    else:
        raise ValueError('Inverse map did not converge; reduce deformation.')
    xmin, xmax, ymin, ymax = model.bounds
    col, row = (xr-xmin)/sx, (ymax-yr)/sy
    valid_ref = model.material_mask(x, y)
    valid_def = (model.material_mask(xr, yr) & (col >= 2) & (col <= shape[1]-3)
                 & (row >= 2) & (row <= shape[0]-3))
    # Image generator uses cubic B-spline interpolation. DIC uses a separate
    # interpolation implementation (RectBivariateSpline) on saved camera pixels.
    ref = np.where(valid_ref, texture, 0.5)
    deformed = map_coordinates(ref, [row, col], order=3, mode='constant', cval=0.5)
    deformed[~valid_def] = 0.5
    u, v = model.displacement(x, y)
    u, v = np.where(valid_ref, u, np.nan), np.where(valid_ref, v, np.nan)
    return ref, deformed, valid_ref, valid_def, dict(x_m=x, y_m=y, u_m=u, v_m=v,
                                                     u_px=u/sx, v_px=-v/sy, sx=sx, sy=sy,
                                                     material_mask=valid_ref)


def degrade_pair(reference, deformed, noise_std=0.0, blur_sigma=0.0,
                 brightness_gain=1.0, brightness_offset=0.0, seed=0):
    if noise_std < 0 or blur_sigma < 0 or brightness_gain <= 0:
        raise ValueError('Noise/blur must be nonnegative and gain positive.')
    rng = np.random.default_rng(seed)
    images = []
    for i, original in enumerate((reference, deformed)):
        im = gaussian_filter(original, blur_sigma) if blur_sigma else original.copy()
        if i == 1:
            im = brightness_gain*im+brightness_offset
        im = im+rng.normal(0, noise_std, im.shape)
        # Measurement uses exactly the 8-bit values delivered as PNG files.
        images.append(np.rint(np.clip(im, 0, 1)*255).astype(np.uint8)/255.0)
    return tuple(images)


def save_image(path, image):
    Image.fromarray(np.rint(np.clip(image, 0, 1)*255).astype(np.uint8)).save(path)
