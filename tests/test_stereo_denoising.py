"""Denoising preserves captures, excludes boundary mixing, and exports DIC inputs."""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from lab_config import build_config
from stereo_dic import prepare_images
from stereo_experiment import run_stereo


class StereoDenoisingTests(unittest.TestCase):
    def test_filter_noise_support_and_no_mutation(self):
        rng=np.random.default_rng(25)
        raw=.5+rng.normal(0,.1,(80,80));original=raw.copy()
        mask=np.zeros(raw.shape,bool);mask[10:70,10:70]=True
        images={'test':raw};masks={'test':mask}
        off,support,metadata=prepare_images(images,masks,0)
        self.assertIs(off,images);self.assertIs(support,masks)
        filtered,support,metadata=prepare_images(images,masks,.5)
        np.testing.assert_array_equal(raw,original)
        self.assertEqual(metadata['kernel_radius_px'],2)
        self.assertEqual(int(support['test'].sum()),56*56)
        self.assertLess(np.std(filtered['test'][15:65,15:65]),np.std(raw[15:65,15:65])*.8)
        self.assertGreater(np.max(abs(filtered['test']*255-np.rint(filtered['test']*255))),.1)
        # Modifying background cannot affect any fully supported filtered pixel.
        changed=raw.copy();changed[~mask]=1000
        other,_,_=prepare_images({'test':changed},masks,.5)
        np.testing.assert_array_equal(filtered['test'][support['test']],other['test'][support['test']])

    def test_allowed_settings(self):
        for sigma in [0,.5]:
            c=build_config(dict(benchmark='square_torsion',denoise_sigma=sigma))
            self.assertEqual(c['dic']['denoise_sigma'],sigma)
        for sigma in [-1,.2,1,float('nan'),True]:
            with self.subTest(sigma=sigma),self.assertRaises(ValueError):
                build_config(dict(benchmark='square_torsion',denoise_sigma=sigma))

    def test_exports_use_filtered_copies(self):
        c=build_config(dict(benchmark='square_torsion',length_mm=160,torque_nm=0,
                            denoise_sigma=.5,step=24,fit_radius_px=55))
        with tempfile.TemporaryDirectory() as directory:
            payload=run_stereo(c,'denoise-check',directory)
            json.dumps(payload,allow_nan=False)
            self.assertNotIn('matching_images',payload['stereo_result'])
            self.assertGreater(payload['summary']['valid_displacement_subsets'],0)
            self.assertLess(payload['summary']['displacement_vector_rmse_mm'],1e-8)
            folder=Path(directory)
            with np.load(folder/'dic_input_images.npz') as inputs:
                for key in inputs.files:
                    raw=np.asarray(Image.open(folder/(key+'.png')))/255
                    mask=np.asarray(Image.open(folder/(key+'_mask.png')))>0
                    expected,_,_=prepare_images({key:raw},{key:mask},.5)
                    np.testing.assert_array_equal(inputs[key],expected[key])
                    preview=np.asarray(Image.open(folder/(key+'_smoothed.png')))/65535
                    np.testing.assert_allclose(preview,inputs[key],atol=.5/65535)
            self.assertIn('smoothed DIC input',(folder/'report.html').read_text())
