"""Shared, optional DIC preprocessing of captured grayscale images."""
import numpy as np
from scipy.ndimage import gaussian_filter, binary_erosion


def prepare_images(images,masks,sigma=0):
    """Filter captured images, preserving floating-point values and raw inputs.

    The separable Gaussian has finite radius 2 at sigma 0.5. A square
    erosion excludes every pixel whose kernel would touch masked background.
    ImageMatcher adds its existing three-pixel spline/support margin.
    """
    if isinstance(sigma,bool) or sigma not in (0,.5):
        raise ValueError('DIC denoising must be Off (0) or Mild (0.5 px).')
    radius=int(4*sigma+.5)
    if not radius:return images,masks,dict(method='off',sigma_px=0,kernel_radius_px=0)
    filtered={key:gaussian_filter(np.asarray(im,float),sigma=sigma,mode='reflect',truncate=4.0)
              for key,im in images.items()}
    support={key:binary_erosion(mask,structure=np.ones((3,3),bool),iterations=radius)
             for key,mask in masks.items()}
    return filtered,support,dict(method='gaussian',sigma_px=sigma,kernel_radius_px=radius)


