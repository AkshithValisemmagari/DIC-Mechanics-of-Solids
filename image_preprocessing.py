"""Optional captured-image preprocessing; no mechanics or clean-image access."""
import numpy as np
from scipy.ndimage import gaussian_filter, binary_erosion, uniform_filter, convolve


def validate_denoising(value):
    if isinstance(value, str) and value == 'wiener': return value
    if isinstance(value, (bool, np.bool_)): raise ValueError('Select Off, Gaussian 0.5 / 0.7 / 1.0 px, or Local Wiener.')
    try: value = float(value)
    except (ValueError, TypeError): raise ValueError('Invalid DIC denoising option.')
    if value not in (0, .5, .7, 1.): raise ValueError('Select Off, Gaussian 0.5 / 0.7 / 1.0 px, or Local Wiener.')
    return value


def prepare_images(images, masks, sigma=0):
    """Gaussian or adaptive 5x5 local Wiener filtering, in floating point.

    Wiener: mean + max(0, 1 - noise_variance/local_variance)*(image-mean).
    Noise is estimated independently per capture using the median absolute
    deviation of a normalized second-difference high-pass response on valid
    material only. This robust estimate can still include fine texture; it
    is not ground truth. No simulated noise setting is read here.
    All kernel footprints touching background are excluded from DIC support.
    """
    sigma=validate_denoising(sigma)
    if sigma == 0: return images,masks,dict(method='off',sigma_px=0,kernel_radius_px=0)
    wiener=sigma == 'wiener';radius=2 if wiener else int(4*sigma+.5)
    support={k:binary_erosion(m,structure=np.ones((3,3),bool),iterations=radius) for k,m in masks.items()}
    filtered={};estimates={}
    for key,image in images.items():
        im=np.asarray(image,float)
        if not wiener:
            filtered[key]=gaussian_filter(im,sigma=sigma,mode='reflect',truncate=4.0)
            continue
        kernel=np.outer([1.,-2.,1.],[1.,-2.,1.])/6.
        valid=binary_erosion(masks[key],structure=np.ones((3,3),bool))
        response=convolve(im,kernel,mode='reflect')[valid]
        noise_std=float(np.median(np.abs(response-np.median(response)))/.6744897501960817) if response.size else 0.
        estimates[key]=noise_std**2
        mean=uniform_filter(im,size=5,mode='reflect')
        variance=np.maximum(uniform_filter(im*im,size=5,mode='reflect')-mean*mean,0)
        weight=np.zeros_like(im)
        np.divide(np.maximum(variance-noise_std**2,0),variance,out=weight,where=variance>np.finfo(float).eps)
        filtered[key]=mean+weight*(im-mean)
    metadata=dict(method='wiener' if wiener else 'gaussian',sigma_px=None if wiener else sigma,kernel_radius_px=radius)
    if wiener: metadata.update(window_size_px=5,noise_variance=estimates,noise_estimator='masked high-pass MAD')
    return filtered,support,metadata
