import unittest
import tempfile
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from image_preprocessing import prepare_images
from lab_config import build_config
from pipeline import run_experiment
from stereo_experiment import run_stereo

class FilterOptionsTests(unittest.TestCase):
    def test_filters_and_boundaries(self):
        rng=np.random.default_rng(84);raw=.5+rng.normal(0,.06,(160,160))
        mask=np.zeros(raw.shape,bool);mask[10:-10,10:-10]=True
        for option in [.5,.7,1,'wiener']:
            with self.subTest(option=option):
                out,support,meta=prepare_images({'a':raw},{'a':mask},option)
                self.assertTrue(np.isfinite(out['a']).all())
                self.assertLess(np.std(out['a'][support['a']]),np.std(raw[mask]))
                changed=raw.copy();changed[~mask]=1e3
                other,_,_=prepare_images({'a':changed},{'a':mask},option)
                np.testing.assert_allclose(out['a'][support['a']],other['a'][support['a']],atol=1e-9)
                if option!='wiener': np.testing.assert_array_equal(out['a'],gaussian_filter(raw,option,mode='reflect',truncate=4))
                else:self.assertAlmostEqual(meta['noise_variance']['a']**.5,.06,delta=.008)
        flat=np.ones((32,32))*.4
        out,_,_=prepare_images({'a':flat},{'a':np.ones(flat.shape,bool)},'wiener')
        np.testing.assert_allclose(out['a'],flat,atol=1e-14)

    def test_flat_options_exports_and_raw_preservation(self):
        for name,extra in [('axial_bar',{}),('cantilever',dict(force_n=1000)),('pure_bending',{}),('plate_with_hole',dict(length_mm=80,height_mm=80))]:
            baseline=run_experiment(build_config(dict(benchmark=name,noise_std=.05,**extra)),make_plots=False)
            for option in [.7,1,'wiener']:
                with self.subTest(name=name,option=option),tempfile.TemporaryDirectory() as folder:
                    b=run_experiment(build_config(dict(benchmark=name,noise_std=.05,denoise_sigma=option,**extra)),folder,make_plots=False)
                    np.testing.assert_array_equal(b['reference'],baseline['reference'])
                    np.testing.assert_array_equal(b['dic'][:,:2],baseline['dic'][:,:2])
                    self.assertGreater(b['summary']['valid_displacement_subsets'],0)
                    with np.load(Path(folder)/'dic_input_images.npz') as arrays:np.testing.assert_array_equal(arrays['reference'],b['matching_images']['reference'])
                    print(name,option,b['summary']['displacement_px']['vector_rmse'],flush=True)

    def test_stereo_options(self):
        for option in [.7,1,'wiener']:
            with self.subTest(option=option),tempfile.TemporaryDirectory() as folder:
                c=build_config(dict(benchmark='square_torsion',length_mm=160,torque_nm=0,denoise_sigma=option,step=24,fit_radius_px=55))
                p=run_stereo(c,'filter-test',folder)
                self.assertGreater(p['summary']['valid_displacement_subsets'],0)
                self.assertLess(p['summary']['displacement_vector_rmse_mm'],1e-8)
                self.assertTrue((Path(folder)/'left_reference_smoothed.png').exists())
                self.assertIn('Local Wiener' if option=='wiener' else f'sigma {option}',(Path(folder)/'report.html').read_text())
