"""Optional deterministic noise/filter sweep; emits JSON, never tunes on truth."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.ndimage import shift

# Allow `python tests/calibrate_dic_consistency.py` from a clean checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dic import run_dic
from speckle import generate_speckles, degrade_pair


def calibrate():
    rows=[]
    for seed in [4,8,17]:
        image=generate_speckles((100,120),2,.4,seed)
        target=shift(image,(-1.35,2.37),order=3,mode='constant',cval=.5)
        for noise in [0,.02,.06,.1,.15]:
            ref,deformed=degrade_pair(image,target,noise_std=noise,seed=seed+100)
            for sigma in [0,.7,1]:
                settings=dict(subset_size=21,step=20,search_radius=5,denoise_sigma=sigma)
                off=run_dic(ref,deformed,fb_tolerance_px=None,**settings)
                checked,diag=run_dic(ref,deformed,return_diagnostics=True,**settings)
                np.testing.assert_array_equal(off[:,:9],checked[:,:9])
                good=checked[:,9].astype(bool)
                errors=np.array([p['round_trip_error_px'] for p in diag['points']])
                finite=errors[np.isfinite(errors)]
                before=int(off[:,9].sum());after=int(good.sum())
                rows.append(dict(seed=seed,noise_std=noise,denoise_sigma=sigma,
                    forward_accepted=before,checked_accepted=after,
                    retained_fraction=after/before if before else None,
                    cycle_p95_px=float(np.quantile(finite,.95)) if finite.size else None,
                    vector_rmse_px=float(np.sqrt(np.mean(np.sum((checked[good,2:4]-[2.37,-1.35])**2,axis=1)))) if after else None,
                    accepted_at_tolerance={str(t):int(np.sum(errors<=t)) for t in [.1,.3,.5]}))
    return dict(subset_size=21,step=20,search_radius=5,translation_px=[2.37,-1.35],rows=rows)


if __name__=='__main__':print(json.dumps(calibrate(),indent=2,allow_nan=False))
