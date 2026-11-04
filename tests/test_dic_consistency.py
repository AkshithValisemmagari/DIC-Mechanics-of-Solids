"""Image-based reverse checks and their ambiguity/acceptance limits."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
from scipy.ndimage import map_coordinates, shift
from dic import run_dic
from speckle import generate_speckles, degrade_pair
from lab_config import build_config
from pipeline import run_experiment


class ConsistencyTests(unittest.TestCase):
    def test_known_affine_motion_and_brightness(self):
        image=generate_speckles((100,120),2,.4,8)
        centre=np.array([60,50]);A=np.array([[1.02,.015],[-.01,.975]]);motion=np.array([1.7,-1.2])
        y,x=np.indices(image.shape);points=np.stack((x,y),axis=-1)
        original=(points-centre-motion)@np.linalg.inv(A).T+centre
        warped=map_coordinates(image,[original[:,:,1],original[:,:,0]],order=3,mode='constant',cval=.5)
        ref,warped=degrade_pair(image,warped,brightness_gain=.85,brightness_offset=.05,noise_std=.01,seed=18)
        d,diag=run_dic(ref,warped,subset_size=21,step=20,search_radius=5,return_diagnostics=True)
        good=d[:,9].astype(bool);truth=(d[:,:2]-centre)@(A-np.eye(2)).T+motion
        self.assertGreater(good.mean(),.85)
        self.assertLess(np.sqrt(np.mean(np.sum((d[good,2:4]-truth[good])**2,axis=1))),.08)
        self.assertTrue(all(diag['points'][i]['round_trip_error_px']<=.3 for i in np.flatnonzero(good)))

    def test_duplicate_texture_rejects_nonreturning_match(self):
        rng=np.random.default_rng(52);ref=rng.uniform(.2,.8,(120,120));target=rng.uniform(.2,.8,ref.shape)
        template=rng.uniform(.2,.8,(9,9))
        ref[36:45,12:21]=template
        ref[36:45,36:45]=template+rng.normal(0,.003,template.shape)
        target[36:45,24:33]=template
        settings=dict(subset_size=9,step=200,search_radius=33)
        forward=run_dic(ref,target,fb_tolerance_px=None,**settings)
        checked,diag=run_dic(ref,target,return_diagnostics=True,**settings)
        self.assertEqual(forward[0,10],0)
        self.assertEqual(checked[0,10],8)
        self.assertEqual(checked[0,9],0)
        self.assertGreater(diag['points'][0]['round_trip_error_px'],20)
        np.testing.assert_array_equal(forward[0,2:9],checked[0,2:9])

    def test_reverse_support_failure_is_distinct(self):
        rng=np.random.default_rng(3);image=rng.uniform(.2,.8,(80,100))
        # Exercise the real reverse source-support guard independently of
        # optimizer/correlation outcomes.
        from dic import reverse_match
        from scipy.interpolate import RectBivariateSpline
        from dic_support import supported_subset_centres
        y,x=np.mgrid[-4:5,-4:5];mask=np.ones(image.shape);mask[30,30]=0
        spline=RectBivariateSpline(np.arange(80),np.arange(100),image)
        point,score,reason=reverse_match([30,30],spline,mask,image,spline,np.ones_like(mask),
            supported_subset_centres(np.ones_like(mask,bool),9),x.ravel(),y.ravel(),9,5,.75,45,.12)
        self.assertIsNone(point);self.assertEqual(reason,'source_support')

    def test_periodic_motion_can_remain_unobservable(self):
        # A whole texture period outside the configured search is identical
        # to zero motion. Even a zero cycle error cannot prove uniqueness.
        tile=np.random.default_rng(5).uniform(.2,.8,(9,9));image=np.tile(tile,(12,14))
        target=np.roll(image,9,axis=1)
        np.testing.assert_array_equal(target,image)
        d=run_dic(image,target,subset_size=17,step=24,search_radius=4)
        good=d[:,9].astype(bool);self.assertTrue(good.all())
        np.testing.assert_allclose(d[good,2:4],0,atol=1e-7)

    def test_disable_preserves_forward_values_and_bad_thresholds_rejected(self):
        image=generate_speckles((90,110),2,.4,4);target=shift(image,(-.7,1.3),order=3)
        off=run_dic(image,target,subset_size=21,step=24,search_radius=5,fb_tolerance_px=None)
        checked=run_dic(image,target,subset_size=21,step=24,search_radius=5)
        np.testing.assert_array_equal(off[:,:9],checked[:,:9])
        for invalid in [0,-1,float('nan'),float('inf'),True]:
            with self.subTest(value=invalid),self.assertRaises(ValueError):
                run_dic(image,target,fb_tolerance_px=invalid)

    def test_diagnostics_export_and_effective_setting(self):
        c=build_config(dict(benchmark='axial_bar',force_n=0,step=24,fit_radius_px=55))
        with tempfile.TemporaryDirectory() as folder:
            b=run_experiment(c,folder,make_plots=False)
            self.assertEqual(b['summary']['forward_backward']['tolerance_px'],.3)
            self.assertEqual(len(b['consistency']['points']),len(b['dic']))
            lines=(Path(folder)/'dic_consistency.csv').read_text().splitlines()
            self.assertEqual(len(lines),len(b['dic'])+1)
            self.assertIn('reverse_status',lines[0])
            self.assertTrue(any('matched' in line for line in lines[1:]))


if __name__=='__main__':unittest.main()
