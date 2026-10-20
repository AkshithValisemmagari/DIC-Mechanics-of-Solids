"""Shared denoising for flat specimens and paired noise experiments."""
import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from lab_config import build_config
from pipeline import run_experiment
from dic import run_dic
from image_preprocessing import prepare_images
from lab_server import make_payload
from noise_comparison import compare_payloads
from visualization import write_report

CASES=[('axial_bar',dict(force_n=40000)),('cantilever',dict(height_mm=30,thickness_mm=6,force_n=1000)),
       ('plate_with_hole',dict(length_mm=80,height_mm=80,force_n=40000)),('pure_bending',dict(height_mm=30,thickness_mm=6,moment_nm=60))]

class AllDICDenoisingTests(unittest.TestCase):
    def test_all_specimens_preserve_captures_and_candidate_grid(self):
        for name,settings in CASES:
            with self.subTest(specimen=name):
                c=build_config(dict(benchmark=name,noise_std=.05,**settings))
                off=run_experiment(c,make_plots=False)
                c=copy.deepcopy(c);c['dic']['denoise_sigma']=.5
                mild=run_experiment(c,make_plots=False)
                np.testing.assert_array_equal(off['reference'],mild['reference'])
                np.testing.assert_array_equal(off['deformed'],mild['deformed'])
                np.testing.assert_array_equal(off['dic'][:,:2],mild['dic'][:,:2])
                self.assertGreater(mild['summary']['valid_displacement_subsets'],0)
                self.assertEqual(mild['summary']['preprocessing']['sigma_px'],.5)
                for key in ['reference','deformed']:self.assertFalse(np.array_equal(mild[key],mild['matching_images'][key]))
                print(name,'Off:',off['summary']['valid_displacement_subsets'],off['summary']['displacement_px']['vector_rmse'],
                      'Mild:',mild['summary']['valid_displacement_subsets'],mild['summary']['displacement_px']['vector_rmse'])
                # CLI/direct DIC and the pipeline must apply the filter exactly once.
                direct=run_dic(mild['reference'],mild['deformed'],mild['mask_reference'],mild['mask_deformed'],**c['dic'])
                np.testing.assert_allclose(direct,mild['dic'],equal_nan=True,atol=0,rtol=0)

    def test_paired_noise_and_exports(self):
        c=build_config(dict(benchmark='pure_bending',height_mm=30,thickness_mm=6,noise_std=.05,denoise_sigma=.5,compare_noise=True))
        with tempfile.TemporaryDirectory() as folder:
            noisy=run_experiment(c,folder,make_plots=False)
            baseconfig=copy.deepcopy(c);baseconfig['camera']['noise_std']=0
            base=run_experiment(baseconfig,Path(folder)/'baseline',make_plots=False)
            p=make_payload(noisy,'test');b=make_payload(base,'test')
            comparison=compare_payloads(b,p)
            self.assertTrue(comparison)
            self.assertEqual(b['summary']['preprocessing'],p['summary']['preprocessing'])
            for run,sub in [(noisy,Path(folder)),(base,Path(folder)/'baseline')]:
                write_report(run,sub)
                self.assertIn('smoothed DIC input',(sub/'report.html').read_text())
                with np.load(sub/'dic_input_images.npz') as inputs:
                    for key in ['reference','deformed']:
                        np.testing.assert_array_equal(inputs[key],run['matching_images'][key])
                        preview=np.asarray(Image.open(sub/(key+'_smoothed.png')))/65535
                        np.testing.assert_allclose(preview,inputs[key],atol=.5/65535)

    def test_flat_setting_validation(self):
        for name,_ in CASES:
            for value in [True,.1,1.1,-1]:
                with self.subTest(name=name,value=value),self.assertRaises(ValueError):
                    build_config(dict(benchmark=name,denoise_sigma=value))
