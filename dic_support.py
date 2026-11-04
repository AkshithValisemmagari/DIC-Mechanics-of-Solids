"""Integer subset support on already processed DIC target masks."""
import numpy as np


def supported_subset_centres(mask, subset_size):
    """Return a full-image map of fully supported integer subset centres.

    Callers supply masks after denoising and interpolation-margin erosion.
    An integer summed-area table counts invalid pixels exactly, including holes.
    The two-pixel image limit also matches the final subpixel support checks.
    """
    mask = np.asarray(mask, dtype=bool)
    supported = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    if min(height, width) < subset_size:
        return supported
    invalid = np.pad((~mask).astype(np.int64), ((1, 0), (1, 0)))
    integral = invalid.cumsum(axis=0).cumsum(axis=1)
    size = subset_size
    counts = (integral[size:, size:] - integral[:-size, size:]
              - integral[size:, :-size] + integral[:-size, :-size])
    half = size // 2
    supported[half:height-half, half:width-half] = counts == 0
    edge = half + 2
    supported[:edge, :] = False
    supported[height-edge:, :] = False
    supported[:, :edge] = False
    supported[:, width-edge:] = False
    return supported
